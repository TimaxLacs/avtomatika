"""Минимальный сервер оркестратора для локального тестирования."""

import asyncio
import logging
import os
import sys

# Добавляем путь к src для импорта avtomatika
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from avtomatika.engine import OrchestratorEngine
from avtomatika.config import Config
from avtomatika.storage.memory import MemoryStorage
from avtomatika.blueprint import StateMachineBlueprint

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# 1. Создаём тестовый Blueprint
test_blueprint = StateMachineBlueprint("test_workflow", api_endpoint="/jobs/test")


@test_blueprint.state("init")
async def init_handler(initial_data: dict, actions, job_id: str):
    """Начальное состояние: отправляем задачу воркеру."""
    logger.info(f"[Job {job_id}] Init state - dispatching task to worker")
    logger.info(f"[Job {job_id}] Initial data: {initial_data}")
    
    # Отправляем задачу воркеру
    actions.dispatch_task(
        task_type="process_data",
        params={
            "job_id": job_id,
            "payload": initial_data.get("input", "default payload"),
        },
        transitions={
            "success": "completed",
            "failure": "failed",
        },
        timeout_seconds=60,
    )


@test_blueprint.state("completed")
async def completed_handler(initial_data: dict, actions, job_id: str, state_history: dict):
    """Успешное завершение."""
    task_result = state_history.get("task_result")
    logger.info(f"[Job {job_id}] Completed! Task result: {task_result}")


@test_blueprint.state("failed")
async def failed_handler(initial_data: dict, actions, job_id: str, state_history: dict):
    """Ошибка."""
    task_result = state_history.get("task_result")
    logger.error(f"[Job {job_id}] Failed! Task result: {task_result}")


async def main():
    """Запуск оркестратора."""
    
    # 1. Конфигурация
    config = Config()
    config.CLIENT_TOKEN = "test-client-token"
    config.GLOBAL_WORKER_TOKEN = "test-worker-token"
    config.RATE_LIMITING_ENABLED = False  # Отключаем для локального тестирования
    config.API_HOST = "localhost"
    config.API_PORT = 8000
    
    # 2. Storage (используем MemoryStorage для простоты)
    storage = MemoryStorage()
    
    # Регистрируем тестового клиента
    await storage.save_client_config("test-client-token", {
        "token": "test-client-token",
        "name": "test-client",
        "allowed_blueprints": ["test_workflow"],
    })
    
    # Инициализируем квоту для клиента
    await storage.initialize_client_quota("test-client-token", 1000)
    
    # 3. Создаём engine
    engine = OrchestratorEngine(config=config, storage=storage)
    
    # 4. Регистрируем blueprint
    engine.register_blueprint(test_blueprint)
    
    # 5. Запускаем сервер
    await engine.start()
    
    logger.info("=" * 50)
    logger.info("Orchestrator is running on http://localhost:8000")
    logger.info("=" * 50)
    logger.info("")
    logger.info("Registered blueprints:")
    logger.info("  - test_workflow")
    logger.info("")
    logger.info("Auth tokens:")
    logger.info(f"  - Client token: {config.CLIENT_TOKEN}")
    logger.info(f"  - Worker token: {config.GLOBAL_WORKER_TOKEN}")
    logger.info("")
    logger.info("API endpoints:")
    logger.info("  POST /api/jobs/test - create job")
    logger.info("  GET  /api/jobs/{job_id} - get job status")
    logger.info("  POST /_worker/workers/register - register worker")
    logger.info("  GET  /_worker/workers/{worker_id}/tasks/next - get next task")
    logger.info("  POST /_worker/tasks/result - submit task result")
    logger.info("")
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 50)
    
    try:
        # Ждём Ctrl+C
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        logger.info("Shutting down...")
        await engine.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped by user")
