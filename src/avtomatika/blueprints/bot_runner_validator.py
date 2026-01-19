"""Валидатор запросов для Bot Runner с понятными ошибками."""

import re
from typing import Any


class ValidationError(Exception):
    """Ошибка валидации с детальной информацией."""
    
    def __init__(
        self, 
        code: str, 
        message: str, 
        details: dict | None = None,
        hint: str | None = None, 
        example: dict | None = None
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
        self.hint = hint
        self.example = example
    
    def to_dict(self) -> dict:
        """Преобразует ошибку в словарь для JSON ответа."""
        result = {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }
        if self.hint:
            result["error"]["hint"] = self.hint
        if self.example:
            result["error"]["example"] = self.example
        return result


# Паттерн для валидации bot_id
BOT_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')

# Допустимые значения
VALID_ACTIONS = ("start", "stop", "logs", "list", "status")
VALID_DEPLOYMENT_MODES = ("simple", "custom", "image")


def validate_bot_request(data: dict[str, Any]) -> None:
    """
    Валидирует запрос на создание/управление ботом.
    
    Args:
        data: Данные запроса
        
    Raises:
        ValidationError: Если запрос невалиден
    """
    action = data.get("action")
    
    # Проверка action
    if not action:
        raise ValidationError(
            code="MISSING_REQUIRED_FIELD",
            message="Отсутствует обязательное поле 'action'",
            details={"field": "action", "required": True},
            hint="Укажите действие: 'start', 'stop', 'logs', 'list' или 'status'",
            example={
                "valid_values": list(VALID_ACTIONS),
                "request": {
                    "action": "start",
                    "bot_id": "my-bot",
                    "deployment_mode": "simple",
                    "code": "...",
                    "env_vars": {"BOT_TOKEN": "..."}
                }
            }
        )
    
    if action not in VALID_ACTIONS:
        # Попробуем угадать что имел в виду пользователь
        hint = None
        action_lower = action.lower()
        for valid in VALID_ACTIONS:
            if valid.startswith(action_lower[:2]):
                hint = f"Возможно вы имели в виду '{valid}'?"
                break
        
        raise ValidationError(
            code="INVALID_ACTION",
            message=f"Неизвестное действие: '{action}'",
            details={"field": "action", "value": action},
            hint=hint,
            example={"valid_values": list(VALID_ACTIONS)}
        )
    
    # Для list не нужны дополнительные поля
    if action == "list":
        return
    
    # Проверка bot_id (для всех кроме list)
    bot_id = data.get("bot_id")
    if not bot_id:
        raise ValidationError(
            code="MISSING_REQUIRED_FIELD",
            message="Отсутствует обязательное поле 'bot_id'",
            details={"field": "bot_id", "required": True},
            hint="Укажите уникальный идентификатор бота",
            example={"valid_examples": ["my-bot", "echo_bot_v2", "parser-123"]}
        )
    
    if not BOT_ID_PATTERN.match(bot_id):
        raise ValidationError(
            code="INVALID_BOT_ID",
            message="Недопустимый формат bot_id",
            details={"bot_id": bot_id, "reason": "Недопустимые символы или длина"},
            hint="Используйте только буквы, цифры, дефисы и подчёркивания (макс. 64 символа)",
            example={
                "valid_format": "^[a-zA-Z0-9_-]{1,64}$",
                "valid_examples": ["my-bot", "echo_bot_v2"],
                "invalid_examples": ["my bot", "bot!@#", "очень-длинное-название"]
            }
        )
    
    # Для stop, logs, status больше ничего не нужно
    if action in ("stop", "logs", "status"):
        return
    
    # Валидация для start
    _validate_start_request(data)


def _validate_start_request(data: dict[str, Any]) -> None:
    """Валидация запроса на запуск бота."""
    
    deployment_mode = data.get("deployment_mode")
    
    if not deployment_mode:
        raise ValidationError(
            code="MISSING_REQUIRED_FIELD",
            message="Отсутствует обязательное поле 'deployment_mode'",
            details={"field": "deployment_mode", "required": True},
            hint="Выберите режим деплоя",
            example={
                "valid_values": list(VALID_DEPLOYMENT_MODES),
                "descriptions": {
                    "simple": "Код как текст + requirements (самый простой)",
                    "custom": "Директория/архив/Git с Dockerfile",
                    "image": "Готовый Docker образ"
                }
            }
        )
    
    if deployment_mode not in VALID_DEPLOYMENT_MODES:
        # Попробуем угадать
        hint = None
        mode_lower = deployment_mode.lower()
        if mode_lower in ("simpel", "simle", "sinple", "sipmle"):
            hint = "Возможно вы имели в виду 'simple'?"
        elif mode_lower in ("costom", "cusotm", "custm"):
            hint = "Возможно вы имели в виду 'custom'?"
        elif mode_lower in ("img", "imge", "imagee"):
            hint = "Возможно вы имели в виду 'image'?"
        
        raise ValidationError(
            code="INVALID_DEPLOYMENT_MODE",
            message=f"Неизвестный режим деплоя: '{deployment_mode}'",
            details={"field": "deployment_mode", "value": deployment_mode},
            hint=hint,
            example={"valid_values": list(VALID_DEPLOYMENT_MODES)}
        )
    
    # Валидация по режиму
    if deployment_mode == "simple":
        _validate_simple_mode(data)
    elif deployment_mode == "custom":
        _validate_custom_mode(data)
    elif deployment_mode == "image":
        _validate_image_mode(data)
    
    # Проверка env_vars
    env_vars = data.get("env_vars", {})
    if not isinstance(env_vars, dict):
        raise ValidationError(
            code="INVALID_ENV_VARS",
            message="Поле 'env_vars' должно быть объектом",
            details={"field": "env_vars", "type": type(env_vars).__name__},
            example={"env_vars": {"BOT_TOKEN": "123:ABC...", "DEBUG": "true"}}
        )


def _validate_simple_mode(data: dict[str, Any]) -> None:
    """Валидация режима simple."""
    
    has_code = "code" in data and data["code"]
    has_files = "files" in data and data["files"]
    
    if not has_code and not has_files:
        raise ValidationError(
            code="MISSING_CODE",
            message="Для режима 'simple' необходимо указать код бота",
            details={"deployment_mode": "simple", "missing": ["code", "files"]},
            hint="Укажите 'code' для одного файла или 'files' для нескольких",
            example={
                "single_file": {
                    "deployment_mode": "simple",
                    "code": "import os\\nfrom aiogram import Bot...",
                    "entrypoint": "bot.py",
                    "requirements": ["aiogram>=3.0"]
                },
                "multiple_files": {
                    "deployment_mode": "simple",
                    "files": {
                        "bot.py": "import os\\nfrom handlers import...",
                        "handlers.py": "from aiogram import..."
                    },
                    "entrypoint": "bot.py"
                }
            }
        )
    
    if has_code and has_files:
        raise ValidationError(
            code="CONFLICTING_FIELDS",
            message="Укажите либо 'code', либо 'files', но не оба",
            details={"conflicting": ["code", "files"]},
            hint="'code' — для одного файла, 'files' — для нескольких"
        )
    
    if has_files:
        files = data["files"]
        if not isinstance(files, dict):
            raise ValidationError(
                code="INVALID_FILES_FORMAT",
                message="Поле 'files' должно быть объектом {filename: content}",
                details={"field": "files", "type": type(files).__name__},
                example={"files": {"bot.py": "код...", "utils.py": "код..."}}
            )
        
        if not files:
            raise ValidationError(
                code="EMPTY_FILES",
                message="Поле 'files' не может быть пустым",
                example={"files": {"bot.py": "import aiogram..."}}
            )
        
        # Проверяем что все значения - строки
        for filename, content in files.items():
            if not isinstance(content, str):
                raise ValidationError(
                    code="INVALID_FILE_CONTENT",
                    message=f"Содержимое файла '{filename}' должно быть строкой",
                    details={"filename": filename, "type": type(content).__name__}
                )
    
    # Проверка requirements
    requirements = data.get("requirements", [])
    if not isinstance(requirements, list):
        raise ValidationError(
            code="INVALID_REQUIREMENTS",
            message="Поле 'requirements' должно быть списком",
            details={"field": "requirements", "type": type(requirements).__name__},
            example={"requirements": ["aiogram>=3.0", "aiohttp"]}
        )


def _validate_custom_mode(data: dict[str, Any]) -> None:
    """Валидация режима custom."""
    
    # Используем bool() чтобы гарантировать boolean значения для sum()
    has_archive = bool(data.get("archive"))
    has_archive_url = bool(data.get("archive_url"))
    has_git_repo = bool(data.get("git_repo"))
    
    sources = [has_archive, has_archive_url, has_git_repo]
    
    if not any(sources):
        raise ValidationError(
            code="MISSING_SOURCE",
            message="Для режима 'custom' необходимо указать источник кода",
            details={
                "deployment_mode": "custom", 
                "missing": ["archive", "archive_url", "git_repo"]
            },
            hint="Укажите один из способов загрузки кода",
            example={
                "options": [
                    {
                        "description": "Git репозиторий",
                        "request": {
                            "deployment_mode": "custom",
                            "git_repo": "https://github.com/user/bot.git"
                        }
                    },
                    {
                        "description": "URL на архив",
                        "request": {
                            "deployment_mode": "custom",
                            "archive_url": "https://example.com/bot.tar.gz"
                        }
                    },
                    {
                        "description": "Архив в base64",
                        "request": {
                            "deployment_mode": "custom",
                            "archive": "H4sIAAAAAAAAA..."
                        }
                    }
                ]
            }
        )
    
    if sum(sources) > 1:
        provided = []
        if has_archive:
            provided.append("archive")
        if has_archive_url:
            provided.append("archive_url")
        if has_git_repo:
            provided.append("git_repo")
            
        raise ValidationError(
            code="CONFLICTING_SOURCES",
            message="Укажите только один источник кода",
            details={"provided": provided},
            hint="Выберите один способ: archive, archive_url или git_repo"
        )
    
    if has_git_repo:
        git_repo = data["git_repo"]
        if not git_repo.startswith(("https://", "git@", "http://")):
            raise ValidationError(
                code="INVALID_GIT_URL",
                message="Неверный формат Git URL",
                details={"git_repo": git_repo},
                hint="URL должен начинаться с 'https://', 'http://' или 'git@'",
                example={
                    "valid": [
                        "https://github.com/user/repo.git",
                        "git@github.com:user/repo.git"
                    ]
                }
            )
    
    if has_archive_url:
        archive_url = data["archive_url"]
        if not archive_url.startswith(("https://", "http://")):
            raise ValidationError(
                code="INVALID_ARCHIVE_URL",
                message="Неверный формат URL архива",
                details={"archive_url": archive_url},
                hint="URL должен начинаться с 'https://' или 'http://'"
            )


def _validate_image_mode(data: dict[str, Any]) -> None:
    """Валидация режима image."""
    
    if "docker_image" not in data or not data["docker_image"]:
        raise ValidationError(
            code="MISSING_DOCKER_IMAGE",
            message="Для режима 'image' необходимо указать имя Docker образа",
            details={"deployment_mode": "image", "missing": ["docker_image"]},
            example={
                "request": {
                    "deployment_mode": "image",
                    "docker_image": "ghcr.io/user/mybot:v1.0",
                    "registry_auth": {
                        "username": "...",
                        "password": "..."
                    },
                    "env_vars": {"BOT_TOKEN": "..."}
                }
            }
        )
    
    docker_image = data["docker_image"]
    
    # Базовая проверка формата образа
    if " " in docker_image:
        raise ValidationError(
            code="INVALID_IMAGE_NAME",
            message="Имя Docker образа содержит пробелы",
            details={"docker_image": docker_image},
            example={
                "valid": [
                    "python:3.11-slim",
                    "ghcr.io/user/bot:v1.0",
                    "registry.example.com/mybot:latest"
                ]
            }
        )
    
    # Проверка registry_auth
    registry_auth = data.get("registry_auth")
    if registry_auth:
        if not isinstance(registry_auth, dict):
            raise ValidationError(
                code="INVALID_REGISTRY_AUTH",
                message="Поле 'registry_auth' должно быть объектом",
                details={"type": type(registry_auth).__name__},
                example={
                    "registry_auth": {
                        "username": "myuser",
                        "password": "mytoken"
                    }
                }
            )
        
        if "username" not in registry_auth or "password" not in registry_auth:
            raise ValidationError(
                code="INCOMPLETE_REGISTRY_AUTH",
                message="Для registry_auth требуются поля 'username' и 'password'",
                details={"provided": list(registry_auth.keys())},
                example={
                    "registry_auth": {
                        "username": "myuser",
                        "password": "mytoken"
                    }
                }
            )
