"""CLI клиент для управления ботами через Avtomatika."""

import argparse
import base64
import hashlib
import io
import json
import os
import sys
import tarfile
import time
from pathlib import Path
from typing import Optional

import requests
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.live import Live
from rich.text import Text

console = Console()


class BotRunnerCLI:
    """CLI клиент для управления ботами через Avtomatika."""
    
    def __init__(self, orchestrator_url: str, token: str):
        self.orchestrator_url = orchestrator_url.rstrip("/")
        self.token = token
        # Создаём стабильный user_id из токена
        self.user_id = f"cli_{hashlib.sha256(token.encode()).hexdigest()[:16]}"
        self.headers = {
            "X-Avtomatika-Token": token,
            "Content-Type": "application/json"
        }
    
    def _send_request(self, data: dict, wait: bool = True, verbose: bool = False) -> dict:
        """Отправляет запрос в оркестратор."""
        try:
            # Добавляем user_id для идентификации пользователя
            data["user_id"] = self.user_id
            
            if verbose:
                console.print(f"[dim]→ POST {self.orchestrator_url}/api/jobs/bot_runner[/dim]")
                console.print(f"[dim]   user_id: {self.user_id}[/dim]")
            
            response = requests.post(
                f"{self.orchestrator_url}/api/jobs/bot_runner",
                headers=self.headers,
                json=data,
                timeout=60
            )
            
            result = response.json()
            
            if verbose:
                console.print(f"[dim]← Status: {response.status_code}[/dim]")
            
            if response.status_code >= 400:
                self._print_error(result)
                sys.exit(1)
            
            job_id = result.get("job_id")
            
            if wait and job_id:
                return self._wait_for_job(job_id, verbose=verbose)
            
            return result
            
        except requests.exceptions.ConnectionError:
            console.print(f"[red]❌ Не удалось подключиться к {self.orchestrator_url}[/red]")
            console.print("[dim]Проверьте что оркестратор запущен и URL корректен[/dim]")
            sys.exit(1)
        except requests.RequestException as e:
            console.print(f"[red]❌ Ошибка запроса: {e}[/red]")
            sys.exit(1)
    
    def _wait_for_job(self, job_id: str, timeout: int = 300, verbose: bool = False) -> dict:
        """Ждёт завершения job'а."""
        console.print(f"[dim]Job ID: {job_id}[/dim]")
        
        start_time = time.time()
        last_state = ""
        
        with console.status("[bold blue]Обработка...") as status:
            while time.time() - start_time < timeout:
                try:
                    response = requests.get(
                        f"{self.orchestrator_url}/api/jobs/{job_id}",
                        headers=self.headers,
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        # Оркестратор возвращает current_state и status
                        current_state = result.get("current_state", "")
                        job_status = result.get("status", "")
                        
                        display_state = f"{current_state} ({job_status})"
                        
                        if display_state != last_state:
                            if verbose:
                                console.print(f"[dim]   State: {last_state} → {display_state}[/dim]")
                            last_state = display_state
                        
                        status.update(f"[bold blue]Состояние: {display_state}")
                        
                        # Job завершён когда current_state = completed/failed или status = quarantined
                        if current_state in ("completed", "failed") or job_status == "quarantined":
                            result["state"] = current_state  # Для совместимости
                            return result
                    
                    time.sleep(1)
                    
                except requests.RequestException:
                    time.sleep(2)
        
        console.print("[yellow]⚠️ Таймаут ожидания[/yellow]")
        return {"state": "timeout", "job_id": job_id}
    
    def _print_error(self, result: dict):
        """Красиво выводит ошибку с полной информацией."""
        error = result.get("error", {})
        data = result.get("data", {})
        
        # Извлекаем ошибку из разных мест
        if not error and isinstance(data, dict):
            error = data.get("error", {})
        
        if isinstance(error, dict):
            message = error.get("message", "Неизвестная ошибка")
            code = error.get("code", "ERROR")
            details = error.get("details", {})
            hint = error.get("hint")
            example = error.get("example")
            
            console.print(Panel(
                f"[bold red]{message}[/bold red]\n\n"
                f"[dim]Код ошибки: {code}[/dim]",
                title="❌ Ошибка",
                border_style="red"
            ))
            
            if details:
                console.print("\n[bold]📋 Детали:[/bold]")
                for key, value in details.items():
                    console.print(f"   • {key}: {value}")
            
            if hint:
                console.print(f"\n[bold cyan]💡 Подсказка:[/bold cyan] {hint}")
            
            if example:
                console.print("\n[bold]📝 Пример правильного запроса:[/bold]")
                syntax = Syntax(
                    json.dumps(example, indent=2, ensure_ascii=False),
                    "json",
                    theme="monokai",
                    line_numbers=False
                )
                console.print(syntax)
        else:
            console.print(f"[red]❌ Ошибка: {error or result}[/red]")
        
        # Показываем полный результат для отладки
        if os.environ.get("DEBUG"):
            console.print("\n[dim]Debug - полный ответ:[/dim]")
            console.print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    
    def _print_result(self, result: dict, success_message: str = "Операция выполнена"):
        """Выводит результат операции."""
        state = result.get("state", "unknown")
        data = result.get("data", {})
        
        if state == "completed":
            bot_data = data.get("result", data)
            
            # Проверяем на ошибку в data
            if isinstance(bot_data, dict) and bot_data.get("status") == "failure":
                self._print_error({"error": bot_data.get("error", bot_data)})
                return False
            
            console.print(Panel(
                f"[bold green]{success_message}[/bold green]",
                title="✅ Успех",
                border_style="green"
            ))
            
            # Показываем детали если есть
            if isinstance(bot_data, dict):
                for key, value in bot_data.items():
                    if key not in ("status",) and value:
                        console.print(f"   • {key}: {value}")
            
            return True
        
        elif state == "failed":
            self._print_error(data)
            return False
        
        else:
            console.print(f"[yellow]⚠️ Неожиданное состояние: {state}[/yellow]")
            return False
    
    def _read_file(self, path: str) -> str:
        """Читает содержимое файла."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            console.print(f"[red]❌ Файл не найден: {path}[/red]")
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]❌ Ошибка чтения файла {path}: {e}[/red]")
            sys.exit(1)
    
    def _read_files(self, paths: list[str]) -> dict[str, str]:
        """Читает несколько файлов/директорий."""
        files = {}
        
        for path in paths:
            p = Path(path)
            
            if p.is_file():
                files[p.name] = self._read_file(str(p))
            elif p.is_dir():
                for file_path in p.rglob("*"):
                    if file_path.is_file() and not file_path.name.startswith("."):
                        relative = file_path.relative_to(p)
                        files[str(relative)] = self._read_file(str(file_path))
            else:
                console.print(f"[red]❌ Путь не существует: {path}[/red]")
                sys.exit(1)
        
        return files
    
    def _create_archive(self, path: str) -> str:
        """Создаёт tar.gz архив и возвращает base64."""
        p = Path(path)
        
        if p.is_file() and (p.suffix in (".tar", ".gz", ".tgz") or p.name.endswith(".tar.gz")):
            console.print(f"[dim]Использую существующий архив: {path}[/dim]")
            with open(p, "rb") as f:
                return base64.b64encode(f.read()).decode()
        
        if not p.is_dir():
            console.print(f"[red]❌ Путь должен быть директорией или архивом: {path}[/red]")
            sys.exit(1)
        
        if not (p / "Dockerfile").exists():
            console.print(f"[red]❌ Dockerfile не найден в {path}[/red]")
            console.print("[dim]Для режима 'custom' требуется Dockerfile[/dim]")
            sys.exit(1)
        
        console.print(f"[dim]Создание архива из {path}...[/dim]")
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
            tar.add(p, arcname=".")
        
        encoded = base64.b64encode(buffer.getvalue()).decode()
        console.print(f"[dim]Размер архива: {len(buffer.getvalue()) / 1024:.1f} KB[/dim]")
        
        return encoded
    
    def _parse_env_vars(self, env_list: list[str]) -> dict[str, str]:
        """Парсит переменные окружения из списка KEY=VALUE."""
        result = {}
        for item in env_list:
            if "=" not in item:
                console.print(f"[red]❌ Неверный формат переменной: {item}[/red]")
                console.print("[dim]Используйте формат: KEY=VALUE[/dim]")
                sys.exit(1)
            key, value = item.split("=", 1)
            result[key] = value
        return result
    
    def _parse_requirements(self, requirements: str | None) -> list[str]:
        """Парсит requirements из строки (через запятую) или файла."""
        if not requirements:
            return []
        
        if os.path.isfile(requirements):
            with open(requirements) as f:
                return [
                    line.strip() 
                    for line in f 
                    if line.strip() and not line.startswith("#")
                ]
        return [r.strip() for r in requirements.split(",") if r.strip()]
    
    def _build_start_data(
        self,
        bot_id: str,
        deployment_mode: str,
        sources: list[str] | None = None,
        entrypoint: str | None = None,
        requirements: str | None = None,
        env_vars: list[str] | None = None,
        inline_code: str | None = None,
        custom_source: str | None = None,
        git_branch: str | None = None,
        docker_image: str | None = None,
        registry_user: str | None = None,
        registry_pass: str | None = None
    ) -> dict:
        """Создаёт данные для запроса start/update."""
        data = {
            "bot_id": bot_id,
            "deployment_mode": deployment_mode,
            "env_vars": self._parse_env_vars(env_vars or [])
        }
        
        if deployment_mode == "simple":
            if inline_code:
                data["code"] = inline_code
            elif sources and len(sources) == 1 and Path(sources[0]).is_file():
                data["code"] = self._read_file(sources[0])
            elif sources:
                data["files"] = self._read_files(sources)
            
            if entrypoint:
                data["entrypoint"] = entrypoint
            elif sources:
                first_path = Path(sources[0])
                data["entrypoint"] = first_path.name if first_path.is_file() else "bot.py"
            else:
                data["entrypoint"] = "bot.py"
            
            if requirements:
                data["requirements"] = self._parse_requirements(requirements)
                
        elif deployment_mode == "custom":
            if custom_source:
                if custom_source.startswith(("https://", "git@")) and (
                    ".git" in custom_source or 
                    "github.com" in custom_source or 
                    "gitlab.com" in custom_source
                ):
                    data["git_repo"] = custom_source
                    if git_branch:
                        data["git_branch"] = git_branch
                elif custom_source.startswith("http"):
                    data["archive_url"] = custom_source
                else:
                    data["archive"] = self._create_archive(custom_source)
                    
        elif deployment_mode == "image":
            data["docker_image"] = docker_image
            if registry_user and registry_pass:
                data["registry_auth"] = {
                    "username": registry_user,
                    "password": registry_pass
                }
        
        return data
    
    def start_simple(
        self,
        bot_id: str,
        sources: list[str],
        entrypoint: Optional[str] = None,
        requirements: Optional[str] = None,
        env_vars: list[str] | None = None,
        inline_code: Optional[str] = None,
        verbose: bool = False
    ):
        """Запуск бота в режиме simple."""
        if inline_code:
            console.print("[dim]Режим: inline код[/dim]")
        elif len(sources) == 1 and Path(sources[0]).is_file():
            console.print(f"[dim]Режим: один файл ({sources[0]})[/dim]")
        else:
            console.print(f"[dim]Режим: несколько файлов/директория[/dim]")
        
        if requirements:
            reqs = self._parse_requirements(requirements)
            console.print(f"[dim]Requirements: {len(reqs)} пакетов[/dim]")
        
        data = self._build_start_data(
            bot_id=bot_id,
            deployment_mode="simple",
            sources=sources,
            entrypoint=entrypoint,
            requirements=requirements,
            env_vars=env_vars,
            inline_code=inline_code
        )
        data["action"] = "start"
        
        console.print(f"\n[bold]🚀 Запуск бота '{bot_id}'...[/bold]\n")
        result = self._send_request(data, verbose=verbose)
        self._print_result(result, f"Бот '{bot_id}' успешно запущен!")
    
    def start_custom(
        self,
        bot_id: str,
        source: str,
        env_vars: list[str] | None = None,
        git_branch: Optional[str] = None,
        verbose: bool = False
    ):
        """Запуск бота в режиме custom."""
        if source.startswith(("https://", "git@")):
            console.print(f"[dim]📦 Источник: Git репозиторий[/dim]")
        elif source.startswith("http"):
            console.print(f"[dim]📦 Источник: URL архива[/dim]")
        else:
            console.print(f"[dim]📦 Источник: локальная директория[/dim]")
        
        data = self._build_start_data(
            bot_id=bot_id,
            deployment_mode="custom",
            custom_source=source,
            git_branch=git_branch,
            env_vars=env_vars
        )
        data["action"] = "start"
        
        console.print(f"\n[bold]🚀 Запуск бота '{bot_id}'...[/bold]\n")
        result = self._send_request(data, verbose=verbose)
        self._print_result(result, f"Бот '{bot_id}' успешно запущен!")
    
    def start_image(
        self,
        bot_id: str,
        docker_image: str,
        env_vars: list[str] | None = None,
        registry_user: Optional[str] = None,
        registry_pass: Optional[str] = None,
        verbose: bool = False
    ):
        """Запуск бота из Docker образа."""
        console.print(f"[dim]📦 Образ: {docker_image}[/dim]")
        
        data = self._build_start_data(
            bot_id=bot_id,
            deployment_mode="image",
            docker_image=docker_image,
            registry_user=registry_user,
            registry_pass=registry_pass,
            env_vars=env_vars
        )
        data["action"] = "start"
        
        console.print(f"\n[bold]🚀 Запуск бота '{bot_id}'...[/bold]\n")
        result = self._send_request(data, verbose=verbose)
        self._print_result(result, f"Бот '{bot_id}' успешно запущен!")
    
    def update(
        self,
        bot_id: str,
        sources: list[str] | None = None,
        entrypoint: Optional[str] = None,
        requirements: Optional[str] = None,
        env_vars: list[str] | None = None,
        custom_source: Optional[str] = None,
        git_branch: Optional[str] = None,
        docker_image: Optional[str] = None,
        registry_user: Optional[str] = None,
        registry_pass: Optional[str] = None,
        verbose: bool = False
    ):
        """Обновление (перезапуск) бота с новым кодом."""
        console.print(f"\n[bold]🔄 Обновление бота '{bot_id}'...[/bold]\n")
        
        # Сначала останавливаем
        console.print("[dim]Шаг 1/2: Остановка текущего бота...[/dim]")
        stop_result = self._send_request({"action": "stop", "bot_id": bot_id}, verbose=verbose)
        
        if stop_result.get("state") != "completed":
            # Бот мог не существовать - это OK для update
            console.print("[dim]   (бот не был запущен или уже остановлен)[/dim]")
        else:
            console.print("[dim]   ✓ Остановлен[/dim]")
        
        # Определяем режим
        console.print("[dim]Шаг 2/2: Запуск с новым кодом...[/dim]")
        
        if sources:
            deployment_mode = "simple"
        elif custom_source:
            deployment_mode = "custom"
        elif docker_image:
            deployment_mode = "image"
        else:
            console.print("[red]❌ Не указан источник кода для обновления[/red]")
            console.print("[dim]Укажите --simple, --custom, --git или --image[/dim]")
            sys.exit(1)
        
        data = self._build_start_data(
            bot_id=bot_id,
            deployment_mode=deployment_mode,
            sources=sources,
            entrypoint=entrypoint,
            requirements=requirements,
            env_vars=env_vars,
            custom_source=custom_source,
            git_branch=git_branch,
            docker_image=docker_image,
            registry_user=registry_user,
            registry_pass=registry_pass
        )
        data["action"] = "start"
        
        result = self._send_request(data, verbose=verbose)
        self._print_result(result, f"Бот '{bot_id}' успешно обновлён!")
    
    def restart(self, bot_id: str, verbose: bool = False):
        """Перезапуск бота без изменения кода."""
        console.print(f"\n[bold]🔄 Перезапуск бота '{bot_id}'...[/bold]\n")
        
        # Останавливаем
        console.print("[dim]Остановка...[/dim]")
        stop_result = self._send_request({"action": "stop", "bot_id": bot_id}, verbose=verbose)
        
        if stop_result.get("state") != "completed":
            console.print("[red]❌ Не удалось остановить бота[/red]")
            self._print_error(stop_result.get("data", {}))
            return
        
        # TODO: Для полного restart нужно сохранять конфигурацию бота
        # Пока просто показываем сообщение
        console.print("[yellow]⚠️ Для перезапуска с тем же кодом используйте:[/yellow]")
        console.print(f"[dim]   avtomatika-bot start {bot_id} --simple <ваши файлы>[/dim]")
    
    def stop(self, bot_id: str, verbose: bool = False):
        """Остановка бота."""
        console.print(f"\n[bold]🛑 Остановка бота '{bot_id}'...[/bold]\n")
        
        result = self._send_request({"action": "stop", "bot_id": bot_id}, verbose=verbose)
        self._print_result(result, f"Бот '{bot_id}' остановлен")
    
    def logs(self, bot_id: str, lines: int = 100, follow: bool = False, verbose: bool = False):
        """Получение логов бота."""
        console.print(f"\n[bold]📜 Логи бота '{bot_id}'[/bold]\n")
        
        if follow:
            self._follow_logs(bot_id, lines)
        else:
            result = self._send_request({
                "action": "logs", 
                "bot_id": bot_id,
                "lines": lines
            }, verbose=verbose)
            
            if result.get("state") == "completed":
                # Данные в state_history (результат task)
                data = result.get("state_history", {})
                logs = data.get("logs", "")
                status = data.get("container_status", "unknown")
                
                # Статус с эмодзи
                status_emoji = "🟢" if status == "running" else "🔴" if status == "exited" else "⚪"
                console.print(f"[dim]Статус контейнера: {status_emoji} {status}[/dim]\n")
                
                if logs:
                    # Подсветка ошибок в логах
                    for line in logs.split("\n"):
                        if "ERROR" in line or "Error" in line or "error" in line:
                            console.print(f"[red]{line}[/red]")
                        elif "WARNING" in line or "Warning" in line or "warning" in line:
                            console.print(f"[yellow]{line}[/yellow]")
                        elif "INFO" in line:
                            console.print(f"[dim]{line}[/dim]")
                        else:
                            console.print(line)
                else:
                    console.print("[dim]Логи пусты[/dim]")
            else:
                self._print_error(result.get("data", {}).get("error", result))
    
    def _follow_logs(self, bot_id: str, initial_lines: int = 50):
        """Следит за логами в реальном времени."""
        console.print("[dim]Режим слежения за логами (Ctrl+C для выхода)...[/dim]\n")
        
        last_logs = ""
        try:
            while True:
                result = self._send_request({
                    "action": "logs",
                    "bot_id": bot_id,
                    "lines": initial_lines
                }, wait=True, verbose=False)
                
                if result.get("state") == "completed":
                    # Данные в state_history (результат task)
                    data = result.get("state_history", {})
                    logs = data.get("logs", "")
                    
                    # Показываем только новые строки
                    if logs != last_logs:
                        new_lines = logs[len(last_logs):] if logs.startswith(last_logs) else logs
                        if new_lines.strip():
                            for line in new_lines.strip().split("\n"):
                                if "ERROR" in line:
                                    console.print(f"[red]{line}[/red]")
                                elif "WARNING" in line:
                                    console.print(f"[yellow]{line}[/yellow]")
                                else:
                                    console.print(line)
                        last_logs = logs
                
                time.sleep(2)
                
        except KeyboardInterrupt:
            console.print("\n[dim]Остановлено[/dim]")
    
    def list_bots(self, verbose: bool = False):
        """Список ботов пользователя."""
        console.print("\n[bold]📋 Ваши боты[/bold]\n")
        
        result = self._send_request({"action": "list"}, verbose=verbose)
        
        if result.get("state") == "completed":
            # Данные в state_history (результат task)
            data = result.get("state_history", {})
            bots = data.get("bots", [])
            max_bots = data.get("max_bots", 3)
            
            if not bots:
                console.print("[dim]У вас нет активных ботов[/dim]")
                console.print(f"[dim]Лимит: 0/{max_bots}[/dim]")
                return
            
            table = Table(title=f"Боты ({len(bots)}/{max_bots})")
            table.add_column("Bot ID", style="cyan")
            table.add_column("Статус", style="green")
            table.add_column("Запущен", style="dim")
            
            for bot in bots:
                status = bot.get("status", "unknown")
                if status == "running":
                    status_display = "🟢 running"
                elif status == "exited":
                    status_display = "🔴 exited"
                else:
                    status_display = f"⚪ {status}"
                
                table.add_row(
                    bot["bot_id"],
                    status_display,
                    bot.get("started_at", "N/A")
                )
            
            console.print(table)
        else:
            self._print_error(result.get("data", {}).get("error", result))
    
    def status(self, bot_id: str, verbose: bool = False):
        """Статус конкретного бота."""
        console.print(f"\n[bold]📊 Статус бота '{bot_id}'[/bold]\n")
        
        result = self._send_request({"action": "status", "bot_id": bot_id}, verbose=verbose)
        
        if result.get("state") == "completed":
            # Данные в state_history (результат task)
            data = result.get("state_history", {})
            
            if not data.get("exists"):
                console.print(f"[yellow]Бот '{bot_id}' не найден[/yellow]")
                return
            
            status = data.get("status", "unknown")
            if status == "running":
                status_display = "🟢 RUNNING"
                border_style = "green"
            elif status == "exited":
                status_display = "🔴 STOPPED"
                border_style = "red"
            else:
                status_display = f"⚪ {status.upper()}"
                border_style = "blue"
            
            console.print(Panel(
                f"[bold]{status_display}[/bold]\n\n"
                f"• Container: {data.get('container_name', 'N/A')}\n"
                f"• Started: {data.get('started_at', 'N/A')}",
                title=f"Бот: {bot_id}",
                border_style=border_style
            ))
            
            # Если бот упал, предлагаем посмотреть логи
            if status != "running":
                console.print(f"\n[dim]Посмотреть логи: avtomatika-bot logs {bot_id}[/dim]")
        else:
            self._print_error(result.get("data", {}).get("error", result))


def main():
    """Главная функция CLI."""
    
    parser = argparse.ArgumentParser(
        description="CLI для управления ботами через Avtomatika Bot Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  # Запуск простого бота
  %(prog)s start my-bot --simple bot.py -r "aiogram>=3.0" -e BOT_TOKEN=123:ABC

  # Запуск из нескольких файлов
  %(prog)s start my-bot --simple bot.py handlers.py -r "aiogram>=3.0" -e BOT_TOKEN=123:ABC

  # Запуск из директории с Dockerfile
  %(prog)s start my-bot --custom ./my-project/ -e BOT_TOKEN=123:ABC

  # Запуск из Git
  %(prog)s start my-bot --git https://github.com/user/bot.git -e BOT_TOKEN=123:ABC

  # Обновление бота (остановка + запуск с новым кодом)
  %(prog)s update my-bot --simple bot_v2.py -r "aiogram>=3.0" -e BOT_TOKEN=123:ABC

  # Остановка
  %(prog)s stop my-bot

  # Логи (с подсветкой ошибок)
  %(prog)s logs my-bot -n 100

  # Логи в реальном времени
  %(prog)s logs my-bot --follow

  # Список ботов
  %(prog)s list

Переменные окружения:
  AVTOMATIKA_URL     URL оркестратора (по умолчанию: http://localhost:8000)
  AVTOMATIKA_TOKEN   Токен авторизации
  DEBUG              Показывать отладочную информацию
        """
    )
    
    parser.add_argument(
        "--url", 
        default=os.environ.get("AVTOMATIKA_URL", "http://localhost:8000"),
        help="URL оркестратора"
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("AVTOMATIKA_TOKEN"),
        help="Токен авторизации"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Подробный вывод"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Команда")
    
    # === START ===
    start_parser = subparsers.add_parser("start", help="Запустить бота")
    start_parser.add_argument("bot_id", help="Уникальный ID бота")
    
    mode_group = start_parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--simple", nargs="+", metavar="FILE", help="Режим simple: файлы с кодом")
    mode_group.add_argument("--custom", metavar="PATH", help="Режим custom: директория с Dockerfile")
    mode_group.add_argument("--git", metavar="URL", help="Режим custom: Git репозиторий")
    mode_group.add_argument("--image", metavar="IMAGE", help="Режим image: Docker образ")
    
    start_parser.add_argument("--inline", action="store_true", help="Код через --code")
    start_parser.add_argument("--code", help="Код бота (для --inline)")
    start_parser.add_argument("--entrypoint", help="Точка входа (по умолчанию: bot.py)")
    start_parser.add_argument("-r", "--requirements", help="Requirements (файл или через запятую)")
    start_parser.add_argument("-e", "--env", action="append", default=[], help="Переменные окружения KEY=VALUE")
    start_parser.add_argument("--branch", help="Git ветка")
    start_parser.add_argument("--registry-user", help="Логин registry")
    start_parser.add_argument("--registry-pass", help="Пароль registry")
    
    # === UPDATE ===
    update_parser = subparsers.add_parser("update", help="Обновить бота (остановка + запуск с новым кодом)")
    update_parser.add_argument("bot_id", help="ID бота")
    
    update_mode = update_parser.add_mutually_exclusive_group(required=True)
    update_mode.add_argument("--simple", nargs="+", metavar="FILE", help="Режим simple")
    update_mode.add_argument("--custom", metavar="PATH", help="Режим custom")
    update_mode.add_argument("--git", metavar="URL", help="Git репозиторий")
    update_mode.add_argument("--image", metavar="IMAGE", help="Docker образ")
    
    update_parser.add_argument("--entrypoint", help="Точка входа")
    update_parser.add_argument("-r", "--requirements", help="Requirements")
    update_parser.add_argument("-e", "--env", action="append", default=[], help="Переменные окружения")
    update_parser.add_argument("--branch", help="Git ветка")
    update_parser.add_argument("--registry-user", help="Логин registry")
    update_parser.add_argument("--registry-pass", help="Пароль registry")
    
    # === RESTART ===
    restart_parser = subparsers.add_parser("restart", help="Перезапустить бота")
    restart_parser.add_argument("bot_id", help="ID бота")
    
    # === STOP ===
    stop_parser = subparsers.add_parser("stop", help="Остановить бота")
    stop_parser.add_argument("bot_id", help="ID бота")
    
    # === LOGS ===
    logs_parser = subparsers.add_parser("logs", help="Логи бота")
    logs_parser.add_argument("bot_id", help="ID бота")
    logs_parser.add_argument("-n", "--lines", type=int, default=100, help="Количество строк")
    logs_parser.add_argument("-f", "--follow", action="store_true", help="Следить за логами в реальном времени")
    
    # === LIST ===
    subparsers.add_parser("list", help="Список ботов")
    
    # === STATUS ===
    status_parser = subparsers.add_parser("status", help="Статус бота")
    status_parser.add_argument("bot_id", help="ID бота")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if not args.token:
        console.print(
            "[red]❌ Токен не указан.[/red]\n"
            "[dim]Используйте --token или переменную AVTOMATIKA_TOKEN[/dim]"
        )
        sys.exit(1)
    
    cli = BotRunnerCLI(args.url, args.token)
    verbose = getattr(args, 'verbose', False)
    
    if args.command == "start":
        if args.simple:
            cli.start_simple(
                bot_id=args.bot_id,
                sources=args.simple if not args.inline else [],
                entrypoint=args.entrypoint,
                requirements=args.requirements,
                env_vars=args.env,
                inline_code=args.code if args.inline else None,
                verbose=verbose
            )
        elif args.custom:
            cli.start_custom(args.bot_id, args.custom, args.env, verbose=verbose)
        elif args.git:
            cli.start_custom(args.bot_id, args.git, args.env, args.branch, verbose=verbose)
        elif args.image:
            cli.start_image(args.bot_id, args.image, args.env, args.registry_user, args.registry_pass, verbose=verbose)
    
    elif args.command == "update":
        cli.update(
            bot_id=args.bot_id,
            sources=args.simple,
            entrypoint=args.entrypoint,
            requirements=args.requirements,
            env_vars=args.env,
            custom_source=args.custom or args.git,
            git_branch=args.branch,
            docker_image=args.image,
            registry_user=args.registry_user,
            registry_pass=args.registry_pass,
            verbose=verbose
        )
    
    elif args.command == "restart":
        cli.restart(args.bot_id, verbose=verbose)
    
    elif args.command == "stop":
        cli.stop(args.bot_id, verbose=verbose)
    
    elif args.command == "logs":
        cli.logs(args.bot_id, args.lines, follow=args.follow, verbose=verbose)
    
    elif args.command == "list":
        cli.list_bots(verbose=verbose)
    
    elif args.command == "status":
        cli.status(args.bot_id, verbose=verbose)


if __name__ == "__main__":
    main()
