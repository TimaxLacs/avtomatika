import json
import os
import socket
import uuid
from typing import Any, Dict, List, Optional


class WorkerConfig:
    """Класс для централизованного управления конфигурацией воркера.
    Считывает параметры из переменных окружения и предоставляет значения по умолчанию.
    """

    def __init__(self):
        # --- Основная информация о воркере ---
        self.worker_id: str = os.getenv("WORKER_ID", f"worker-{uuid.uuid4()}")
        self.worker_type: str = os.getenv("WORKER_TYPE", "generic-cpu-worker")
        self.worker_port: int = int(os.getenv("WORKER_PORT", "8083"))
        self.hostname: str = socket.gethostname()
        try:
            self.ip_address: str = socket.gethostbyname(self.hostname)
        except socket.gaierror:
            self.ip_address: str = "127.0.0.1"

        # --- Настройки Оркестратора ---
        self.orchestrators: List[Dict[str, Any]] = self._get_orchestrators_config()

        # --- Безопасность ---
        self.worker_token: str = os.getenv(
            "WORKER_INDIVIDUAL_TOKEN",
            os.getenv("WORKER_TOKEN", "your-secret-worker-token"),
        )

        # --- Ресурсы и производительность ---
        self.cost_per_second: float = float(os.getenv("WORKER_COST_PER_SECOND", "0.01"))
        self.max_concurrent_tasks: int = int(os.getenv("MAX_CONCURRENT_TASKS", "10"))
        self.resources: Dict[str, Any] = {
            "cpu_cores": int(os.getenv("CPU_CORES", "4")),
            "gpu_info": self._get_gpu_info(),
        }

        # --- Установленное ПО и модели (читаются как JSON-строки) ---
        self.installed_software: Dict[str, str] = self._load_json_from_env(
            "INSTALLED_SOFTWARE",
            default={"python": "3.9"},
        )
        self.installed_models: List[Dict[str, str]] = self._load_json_from_env(
            "INSTALLED_MODELS",
            default=[],
        )

        # --- Параметры для тюнинга ---
        self.heartbeat_interval: float = float(os.getenv("HEARTBEAT_INTERVAL", "15"))
        self.result_max_retries: int = int(os.getenv("RESULT_MAX_RETRIES", "5"))
        self.result_retry_initial_delay: float = float(
            os.getenv("RESULT_RETRY_INITIAL_DELAY", "1.0"),
        )
        self.heartbeat_debounce_delay: float = float(os.getenv("WORKER_HEARTBEAT_DEBOUNCE_DELAY", 0.1))
        self.task_poll_timeout: float = float(os.getenv("TASK_POLL_TIMEOUT", "30"))
        self.task_poll_error_delay: float = float(
            os.getenv("TASK_POLL_ERROR_DELAY", "5.0"),
        )
        self.idle_poll_delay: float = float(os.getenv("IDLE_POLL_DELAY", "0.01"))
        self.enable_websockets: bool = os.getenv("WORKER_ENABLE_WEBSOCKETS", "false").lower() == "true"
        self.multi_orchestrator_mode: str = os.getenv("MULTI_ORCHESTRATOR_MODE", "FAILOVER")

    def _get_orchestrators_config(self) -> List[Dict[str, Any]]:
        """
        Загружает конфигурацию оркестраторов из переменной окружения ORCHESTRATORS_CONFIG.
        Для обратной совместимости, если она не установлена, использует ORCHESTRATOR_URL.
        """
        orchestrators_json = os.getenv("ORCHESTRATORS_CONFIG")
        if orchestrators_json:
            try:
                orchestrators = json.loads(orchestrators_json)
                for o in orchestrators:
                    if "priority" not in o:
                        o["priority"] = 10
                orchestrators.sort(key=lambda x: (x.get("priority", 10), x.get("url")))
                return orchestrators
            except json.JSONDecodeError:
                print("Warning: Could not decode JSON from ORCHESTRATORS_CONFIG. Falling back to default.")

        orchestrator_url = os.getenv("ORCHESTRATOR_URL", "http://localhost:8080")
        return [{"url": orchestrator_url, "priority": 1}]

    def _get_gpu_info(self) -> Optional[Dict[str, Any]]:
        """Собирает информацию о GPU из переменных окружения.
        Возвращает None, если GPU не сконфигурирован.
        """
        gpu_model = os.getenv("GPU_MODEL")
        if not gpu_model:
            return None

        return {
            "model": gpu_model,
            "vram_gb": int(os.getenv("GPU_VRAM_GB", "0")),
        }

    def _load_json_from_env(self, key: str, default: Any) -> Any:
        """Безопасно загружает JSON-строку из переменной окружения."""
        value = os.getenv(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                print(
                    f"Warning: Could not decode JSON from environment variable {key}.",
                )
                return default
        return default
