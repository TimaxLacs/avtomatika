"""Bot Runner Worker - запуск ботов в изолированных Docker контейнерах."""

from .worker import worker, container_manager
from .container_manager import ContainerManager
from .config import Config, DEFAULT_LIMITS

__version__ = "1.0.0a1"
__all__ = [
    "worker",
    "container_manager", 
    "ContainerManager",
    "Config",
    "DEFAULT_LIMITS",
]
