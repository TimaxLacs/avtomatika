"""Bot Runner Worker — обработчики задач для запуска ботов."""

import asyncio
import logging
from typing import Any, Dict

from avtomatika_worker import Worker

from .container_manager import ContainerManager
from .config import config

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Создаём менеджер контейнеров
container_manager = ContainerManager()

# Создаём воркер
worker = Worker(
    worker_type="bot-runner",
    max_concurrent_tasks=10,
    task_type_limits={
        "bot_management": 5  # Одновременно управляем до 5 ботами
    }
)


async def _notify_container_event(user_id: str, bot_id: str, action: str) -> None:
    """Callback для событий Docker (падение контейнера и т.д.)."""
    logger.warning(f"Container event: {action} for user={user_id}, bot={bot_id}")
    # TODO: Отправить уведомление в оркестратор о падении бота
    # Это можно сделать через WebSocket или HTTP callback


@worker.task("start_bot", task_type="bot_management")
async def start_bot_handler(params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """
    Обработчик запуска бота.
    
    Поддерживает три режима:
    - simple: код как текст + requirements
    - custom: архив/URL/Git с Dockerfile
    - image: готовый Docker образ
    """
    try:
        user_id = params["user_id"]
        bot_id = params["bot_id"]
        deployment_mode = params["deployment_mode"]
        env_vars = params.get("env_vars", {})
        resource_limits = params.get("resource_limits")
        
        logger.info(f"Starting bot: user={user_id}, bot={bot_id}, mode={deployment_mode}")
        
        # Проверяем квоту пользователя
        current_bots = container_manager.count_user_bots(user_id)
        if current_bots >= config.max_bots_per_user:
            return {
                "status": "failure",
                "error": {
                    "code": "QUOTA_EXCEEDED",
                    "message": f"Maximum {config.max_bots_per_user} bots per user",
                    "details": {
                        "current_bots": current_bots,
                        "max_bots": config.max_bots_per_user,
                        "active_bots": container_manager.list_user_bots(user_id)
                    }
                }
            }
        
        # 1. Собираем/получаем образ в зависимости от режима
        if deployment_mode == "simple":
            image_name = await container_manager.build_simple_image(
                user_id=user_id,
                bot_id=bot_id,
                code=params.get("code"),
                files=params.get("files"),
                requirements=params.get("requirements", []),
                entrypoint=params.get("entrypoint", "bot.py")
            )
            
        elif deployment_mode == "custom":
            image_name = await container_manager.build_custom_image(
                user_id=user_id,
                bot_id=bot_id,
                archive=params.get("archive"),
                archive_url=params.get("archive_url"),
                git_repo=params.get("git_repo"),
                git_branch=params.get("git_branch", "main"),
                git_subdir=params.get("git_subdir")
            )
            
        elif deployment_mode == "image":
            image_name = await container_manager.pull_image(
                docker_image=params["docker_image"],
                registry_auth=params.get("registry_auth")
            )
            
        else:
            return {
                "status": "failure",
                "error": {
                    "code": "INVALID_MODE",
                    "message": f"Unknown deployment mode: {deployment_mode}",
                    "hint": "Use 'simple', 'custom', or 'image'"
                }
            }
        
        # 2. Запускаем контейнер
        result = await container_manager.start_container(
            user_id=user_id,
            bot_id=bot_id,
            image_name=image_name,
            env_vars=env_vars,
            resource_limits=resource_limits
        )
        
        logger.info(f"Bot started successfully: user={user_id}, bot={bot_id}")
        
        return {
            "status": "success",
            "data": result
        }
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return {
            "status": "failure",
            "error": {
                "code": "VALIDATION_ERROR",
                "message": str(e)
            }
        }
    except Exception as e:
        logger.exception(f"Container error: {e}")
        return {
            "status": "failure",
            "error": {
                "code": "CONTAINER_ERROR",
                "message": str(e)
            }
        }


@worker.task("stop_bot", task_type="bot_management")
async def stop_bot_handler(params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """Обработчик остановки бота."""
    try:
        user_id = params["user_id"]
        bot_id = params["bot_id"]
        
        logger.info(f"Stopping bot: user={user_id}, bot={bot_id}")
        
        result = await container_manager.stop_container(
            user_id=user_id,
            bot_id=bot_id
        )
        
        return {"status": "success", "data": result}
        
    except Exception as e:
        logger.exception(f"Stop error: {e}")
        return {
            "status": "failure",
            "error": {
                "code": "STOP_ERROR",
                "message": str(e)
            }
        }


@worker.task("get_logs", task_type="bot_management")
async def get_logs_handler(params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """Обработчик получения логов."""
    try:
        user_id = params["user_id"]
        bot_id = params["bot_id"]
        lines = params.get("lines", 100)
        
        logger.info(f"Getting logs: user={user_id}, bot={bot_id}, lines={lines}")
        
        result = await container_manager.get_logs(
            user_id=user_id,
            bot_id=bot_id,
            lines=lines
        )
        
        return {"status": "success", "data": result}
        
    except Exception as e:
        logger.exception(f"Logs error: {e}")
        return {
            "status": "failure",
            "error": {
                "code": "LOGS_ERROR",
                "message": str(e)
            }
        }


@worker.task("list_bots", task_type="bot_management")
async def list_bots_handler(params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """Список ботов пользователя."""
    try:
        user_id = params["user_id"]
        
        logger.info(f"Listing bots for user={user_id}")
        
        bots = container_manager.list_user_bots(user_id)
        
        return {
            "status": "success",
            "data": {
                "bots": bots,
                "count": len(bots),
                "max_bots": config.max_bots_per_user
            }
        }
        
    except Exception as e:
        logger.exception(f"List error: {e}")
        return {
            "status": "failure",
            "error": {
                "code": "LIST_ERROR",
                "message": str(e)
            }
        }


@worker.task("check_status", task_type="bot_management")
async def check_status_handler(params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """Проверка статуса конкретного бота."""
    try:
        user_id = params["user_id"]
        bot_id = params["bot_id"]
        
        bots = container_manager.list_user_bots(user_id)
        bot = next((b for b in bots if b["bot_id"] == bot_id), None)
        
        if not bot:
            return {
                "status": "success",
                "data": {
                    "exists": False,
                    "bot_id": bot_id
                }
            }
        
        return {
            "status": "success",
            "data": {
                "exists": True,
                **bot
            }
        }
        
    except Exception as e:
        logger.exception(f"Status error: {e}")
        return {
            "status": "failure",
            "error": {
                "code": "STATUS_ERROR",
                "message": str(e)
            }
        }


def run_worker():
    """Запуск воркера."""
    logger.info("Starting Bot Runner Worker...")
    
    # Запускаем слушатель событий Docker
    async def main():
        # Запускаем event listener как background task (не блокирует)
        asyncio.create_task(
            container_manager.start_event_listener(_notify_container_event)
        )
        logger.info("Event listener started in background")
        # Теперь запускаем основной цикл воркера
        await worker.main()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        container_manager.stop_event_listener()


if __name__ == "__main__":
    run_worker()
