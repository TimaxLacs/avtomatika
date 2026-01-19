"""Управление Docker контейнерами для ботов."""

import asyncio
import base64
import logging
import os
import subprocess
import tarfile
import tempfile
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Coroutine

import aiohttp
import docker
from docker.errors import ImageNotFound, NotFound

from .config import config, SIMPLE_DOCKERFILE_TEMPLATE, DEFAULT_LIMITS

logger = logging.getLogger(__name__)


class ContainerManager:
    """Управление Docker контейнерами для ботов."""
    
    def __init__(self):
        self.docker_client = docker.from_env()
        self._ensure_network()
        self._event_task: asyncio.Task | None = None
    
    def _ensure_network(self) -> None:
        """Создаёт изолированную сеть для ботов если её нет."""
        try:
            self.docker_client.networks.get(config.docker_network)
            logger.info(f"Docker network '{config.docker_network}' already exists")
        except NotFound:
            self.docker_client.networks.create(
                config.docker_network,
                driver="bridge",
                internal=False,  # Разрешаем доступ в интернет (для Telegram API)
                attachable=True
            )
            logger.info(f"Created Docker network '{config.docker_network}'")
    
    @staticmethod
    def _sanitize_name(name: str) -> str:
        """Очищает строку от небезопасных символов для Docker."""
        return "".join(c for c in name if c.isalnum() or c in "-_").lower()
    
    def _get_container_name(self, user_id: str, bot_id: str) -> str:
        """Генерирует уникальное имя контейнера."""
        safe_user = self._sanitize_name(user_id)
        safe_bot = self._sanitize_name(bot_id)
        return f"bot_{safe_user}_{safe_bot}"
    
    def _get_image_name(self, user_id: str, bot_id: str) -> str:
        """Генерирует имя образа."""
        safe_user = self._sanitize_name(user_id)
        safe_bot = self._sanitize_name(bot_id)
        return f"bot_image_{safe_user}_{safe_bot}:latest"
    
    def _get_log_config(self) -> dict:
        """Возвращает конфигурацию логирования для Docker."""
        return {
            "type": "json-file",
            "config": {
                "max-size": config.log_max_size,
                "max-file": config.log_max_file
            }
        }
    
    async def build_simple_image(
        self,
        user_id: str,
        bot_id: str,
        code: str | None = None,
        files: dict[str, str] | None = None,
        requirements: list[str] | None = None,
        entrypoint: str = "bot.py"
    ) -> str:
        """
        Собирает образ из кода пользователя (Simple режим).
        
        Args:
            user_id: ID пользователя
            bot_id: ID бота
            code: Код одного файла (текст)
            files: Словарь {filename: content} для нескольких файлов
            requirements: Список pip зависимостей
            entrypoint: Точка входа
            
        Returns:
            Имя собранного образа
        """
        image_name = self._get_image_name(user_id, bot_id)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Сохраняем файлы
            if files:
                for filename, content in files.items():
                    filepath = tmppath / filename
                    filepath.parent.mkdir(parents=True, exist_ok=True)
                    filepath.write_text(content, encoding="utf-8")
                    logger.debug(f"Written file: {filename}")
            elif code:
                (tmppath / entrypoint).write_text(code, encoding="utf-8")
                logger.debug(f"Written single file: {entrypoint}")
            else:
                raise ValueError("Either 'code' or 'files' must be provided")
            
            # Создаём requirements.txt
            reqs = requirements or []
            (tmppath / "requirements.txt").write_text("\n".join(reqs))
            
            # Создаём Dockerfile
            dockerfile_content = SIMPLE_DOCKERFILE_TEMPLATE.format(
                base_image=config.base_image,
                entrypoint=entrypoint
            )
            (tmppath / "Dockerfile").write_text(dockerfile_content)
            
            # Собираем образ
            logger.info(f"Building image {image_name} for user={user_id}, bot={bot_id}")
            
            loop = asyncio.get_event_loop()
            image, build_logs = await loop.run_in_executor(
                None,
                lambda: self.docker_client.images.build(
                    path=str(tmppath),
                    tag=image_name,
                    rm=True,
                    forcerm=True
                )
            )
            
            logger.info(f"Successfully built image {image_name}")
        
        return image_name
    
    async def build_custom_image(
        self,
        user_id: str,
        bot_id: str,
        archive: str | None = None,
        archive_url: str | None = None,
        git_repo: str | None = None,
        git_branch: str = "main",
        git_subdir: str | None = None
    ) -> str:
        """
        Собирает образ из архива или Git репозитория (Custom режим).
        
        Args:
            user_id: ID пользователя
            bot_id: ID бота
            archive: Base64 encoded tar.gz архив
            archive_url: URL для скачивания архива
            git_repo: URL Git репозитория
            git_branch: Ветка Git
            git_subdir: Подпапка с Dockerfile
            
        Returns:
            Имя собранного образа
        """
        image_name = self._get_image_name(user_id, bot_id)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            dockerfile_path = None
            
            if git_repo:
                # Клонируем Git репозиторий
                logger.info(f"Cloning Git repo: {git_repo} (branch: {git_branch})")
                
                clone_path = tmppath / "repo"
                cmd = [
                    "git", "clone", 
                    "--depth", "1", 
                    "-b", git_branch, 
                    git_repo, 
                    str(clone_path)
                ]
                
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                )
                
                if result.returncode != 0:
                    raise ValueError(f"Git clone failed: {result.stderr}")
                
                dockerfile_path = clone_path
                if git_subdir:
                    dockerfile_path = clone_path / git_subdir
                    
            else:
                # Работаем с архивом
                archive_path = tmppath / "archive.tar.gz"
                
                if archive:
                    logger.info("Decoding base64 archive")
                    archive_bytes = base64.b64decode(archive)
                    archive_path.write_bytes(archive_bytes)
                    
                elif archive_url:
                    logger.info(f"Downloading archive from {archive_url}")
                    async with aiohttp.ClientSession() as session:
                        async with session.get(archive_url, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                            if resp.status != 200:
                                raise ValueError(f"Failed to download archive: HTTP {resp.status}")
                            archive_bytes = await resp.read()
                            archive_path.write_bytes(archive_bytes)
                else:
                    raise ValueError("One of 'archive', 'archive_url', or 'git_repo' required")
                
                # Распаковываем
                logger.info("Extracting archive")
                extract_path = tmppath / "extracted"
                extract_path.mkdir()
                
                with tarfile.open(archive_path, "r:gz") as tar:
                    # Безопасная распаковка
                    def is_within_directory(directory, target):
                        abs_directory = os.path.abspath(directory)
                        abs_target = os.path.abspath(target)
                        return abs_target.startswith(abs_directory)
                    
                    for member in tar.getmembers():
                        member_path = os.path.join(extract_path, member.name)
                        if not is_within_directory(extract_path, member_path):
                            raise ValueError("Archive contains path traversal attempt")
                    
                    tar.extractall(extract_path)
                
                # Находим Dockerfile
                for root, dirs, files_list in os.walk(extract_path):
                    if "Dockerfile" in files_list:
                        dockerfile_path = Path(root)
                        break
            
            if not dockerfile_path or not (dockerfile_path / "Dockerfile").exists():
                raise ValueError("Dockerfile not found in archive/repository")
            
            # Собираем образ
            logger.info(f"Building custom image {image_name}")
            
            loop = asyncio.get_event_loop()
            image, build_logs = await loop.run_in_executor(
                None,
                lambda: self.docker_client.images.build(
                    path=str(dockerfile_path),
                    tag=image_name,
                    rm=True,
                    forcerm=True
                )
            )
            
            logger.info(f"Successfully built custom image {image_name}")
        
        return image_name
    
    async def pull_image(
        self,
        docker_image: str,
        registry_auth: dict | None = None
    ) -> str:
        """
        Скачивает готовый образ из registry (Image режим).
        
        Args:
            docker_image: Имя образа (e.g., ghcr.io/user/bot:v1)
            registry_auth: Credentials для приватного registry
            
        Returns:
            Имя скачанного образа
        """
        logger.info(f"Pulling image: {docker_image}")
        
        loop = asyncio.get_event_loop()
        
        auth_config = None
        if registry_auth:
            auth_config = {
                "username": registry_auth.get("username"),
                "password": registry_auth.get("password")
            }
        
        await loop.run_in_executor(
            None,
            lambda: self.docker_client.images.pull(docker_image, auth_config=auth_config)
        )
        
        logger.info(f"Successfully pulled image: {docker_image}")
        return docker_image
    
    async def start_container(
        self,
        user_id: str,
        bot_id: str,
        image_name: str,
        env_vars: dict[str, str],
        resource_limits: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Запускает контейнер с ботом.
        
        Args:
            user_id: ID пользователя
            bot_id: ID бота
            image_name: Имя Docker образа
            env_vars: Переменные окружения
            resource_limits: Лимиты ресурсов (опционально)
            
        Returns:
            Информация о запущенном контейнере
        """
        container_name = self._get_container_name(user_id, bot_id)
        
        # Мержим лимиты с дефолтными
        limits = {**DEFAULT_LIMITS, **(resource_limits or {})}
        
        # Проверяем, не запущен ли уже
        try:
            existing = self.docker_client.containers.get(container_name)
            if existing.status == "running":
                logger.warning(f"Container {container_name} already running")
                return {
                    "status": "already_running",
                    "container_id": existing.id,
                    "container_name": container_name
                }
            else:
                logger.info(f"Removing stopped container {container_name}")
                existing.remove(force=True)
        except NotFound:
            pass
        
        # Запускаем контейнер
        logger.info(f"Starting container {container_name} from image {image_name}")
        
        started_at = datetime.utcnow().isoformat()
        
        loop = asyncio.get_event_loop()
        container = await loop.run_in_executor(
            None,
            lambda: self.docker_client.containers.run(
                image_name,
                name=container_name,
                detach=True,
                environment=env_vars,
                network=config.docker_network,
                mem_limit=f"{limits['memory_mb']}m",
                nano_cpus=int(limits['cpu_cores'] * 1e9),
                pids_limit=config.default_limits.pids_limit,
                restart_policy={"Name": "unless-stopped"},
                log_config=self._get_log_config(),
                security_opt=config.security_opt,
                cap_drop=config.cap_drop,
                cap_add=config.cap_add,
                labels={
                    "bot_runner": "true",
                    "user_id": user_id,
                    "bot_id": bot_id,
                    "started_at": started_at
                }
            )
        )
        
        logger.info(f"Container {container_name} started with ID {container.id}")
        
        return {
            "status": "started",
            "container_id": container.id,
            "container_name": container_name,
            "started_at": started_at
        }
    
    async def stop_container(self, user_id: str, bot_id: str) -> dict[str, Any]:
        """
        Останавливает и удаляет контейнер.
        
        Args:
            user_id: ID пользователя
            bot_id: ID бота
            
        Returns:
            Статус остановки
        """
        container_name = self._get_container_name(user_id, bot_id)
        
        try:
            container = self.docker_client.containers.get(container_name)
            logger.info(f"Stopping container {container_name}")
            
            container.stop(timeout=config.stop_timeout_seconds)
            container.remove()
            
            # Удаляем образ если это был simple/custom (не внешний образ)
            image_name = self._get_image_name(user_id, bot_id)
            try:
                self.docker_client.images.remove(image_name, force=True)
                logger.info(f"Removed image {image_name}")
            except ImageNotFound:
                pass  # Это был режим image, образ не наш
            
            logger.info(f"Container {container_name} stopped and removed")
            return {"status": "stopped", "container_name": container_name}
            
        except NotFound:
            logger.warning(f"Container {container_name} not found")
            return {"status": "not_found", "container_name": container_name}
    
    async def get_logs(
        self, 
        user_id: str, 
        bot_id: str, 
        lines: int = 100
    ) -> dict[str, Any]:
        """
        Получает логи контейнера.
        
        Args:
            user_id: ID пользователя
            bot_id: ID бота
            lines: Количество строк
            
        Returns:
            Логи и статус контейнера
        """
        container_name = self._get_container_name(user_id, bot_id)
        
        try:
            container = self.docker_client.containers.get(container_name)
            logs = container.logs(tail=lines, timestamps=True).decode("utf-8")
            
            return {
                "status": "success",
                "logs": logs,
                "container_status": container.status,
                "container_name": container_name
            }
        except NotFound:
            return {
                "status": "not_found", 
                "logs": None,
                "container_name": container_name
            }
    
    def list_user_bots(self, user_id: str) -> list[dict[str, Any]]:
        """
        Возвращает список всех ботов пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Список ботов с их статусами
        """
        containers = self.docker_client.containers.list(
            all=True,
            filters={
                "label": [
                    "bot_runner=true",
                    f"user_id={user_id}"
                ]
            }
        )
        
        return [
            {
                "bot_id": c.labels.get("bot_id"),
                "container_id": c.id,
                "container_name": c.name,
                "status": c.status,
                "started_at": c.labels.get("started_at")
            }
            for c in containers
        ]
    
    def count_user_bots(self, user_id: str) -> int:
        """Возвращает количество активных ботов пользователя."""
        containers = self.docker_client.containers.list(
            filters={
                "label": [
                    "bot_runner=true",
                    f"user_id={user_id}"
                ],
                "status": "running"
            }
        )
        return len(containers)
    
    async def start_event_listener(
        self, 
        on_container_die: Callable[[str, str, str], Coroutine[Any, Any, None]]
    ) -> None:
        """
        Запускает слушатель Docker Events для отслеживания падений контейнеров.
        
        Args:
            on_container_die: Callback функция (user_id, bot_id, event_action)
        """
        loop = asyncio.get_event_loop()
        
        def listen():
            logger.info("Starting Docker events listener")
            try:
                for event in self.docker_client.events(
                    decode=True,
                    filters={
                        "type": "container",
                        "event": ["die", "stop", "kill", "oom"],
                        "label": "bot_runner=true"
                    }
                ):
                    actor = event.get("Actor", {})
                    labels = actor.get("Attributes", {})
                    user_id = labels.get("user_id")
                    bot_id = labels.get("bot_id")
                    action = event.get("Action", "unknown")
                    
                    if user_id and bot_id:
                        logger.info(f"Container event: {action} for user={user_id}, bot={bot_id}")
                        asyncio.run_coroutine_threadsafe(
                            on_container_die(user_id, bot_id, action),
                            loop
                        )
            except Exception as e:
                logger.error(f"Docker events listener error: {e}")
        
        # Запускаем в отдельном потоке (run_in_executor возвращает Future, не coroutine)
        self._event_task = loop.run_in_executor(None, listen)
    
    def stop_event_listener(self) -> None:
        """Останавливает слушатель событий."""
        if self._event_task:
            self._event_task.cancel()
            self._event_task = None
