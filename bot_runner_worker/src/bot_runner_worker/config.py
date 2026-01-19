"""Конфигурация Bot Runner Worker."""

import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResourceLimits:
    """Лимиты ресурсов для контейнеров."""
    
    memory_mb: int = 256
    cpu_cores: float = 0.5
    pids_limit: int = 100
    timeout_hours: int = 24


@dataclass
class Config:
    """Конфигурация воркера."""
    
    # Docker
    docker_network: str = field(
        default_factory=lambda: os.getenv("DOCKER_NETWORK", "bot_runner_network")
    )
    base_image: str = field(
        default_factory=lambda: os.getenv("BASE_IMAGE", "python:3.11-slim")
    )
    
    # Лимиты
    max_bots_per_user: int = field(
        default_factory=lambda: int(os.getenv("MAX_BOTS_PER_USER", "3"))
    )
    default_limits: ResourceLimits = field(default_factory=ResourceLimits)
    
    # Логирование Docker
    log_max_size: str = "10m"
    log_max_file: str = "1"
    
    # Таймауты
    build_timeout_seconds: int = 300  # 5 минут на сборку
    stop_timeout_seconds: int = 10
    
    # Безопасность
    security_opt: list[str] = field(
        default_factory=lambda: ["no-new-privileges:true"]
    )
    cap_drop: list[str] = field(default_factory=lambda: ["ALL"])
    cap_add: list[str] = field(default_factory=lambda: ["NET_BIND_SERVICE"])


# Синглтон конфигурации
config = Config()

# Для обратной совместимости
DEFAULT_LIMITS = {
    "memory_mb": config.default_limits.memory_mb,
    "cpu_cores": config.default_limits.cpu_cores,
    "timeout_hours": config.default_limits.timeout_hours,
}


# Шаблон Dockerfile для Simple режима
SIMPLE_DOCKERFILE_TEMPLATE = """FROM {base_image}

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода
COPY . .

# Запуск
CMD ["python", "{entrypoint}"]
"""
