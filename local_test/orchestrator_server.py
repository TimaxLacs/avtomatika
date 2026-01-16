"""
Минимальный Orchestrator для локального тестирования.
Запуск: python local_test/orchestrator_server.py
"""
import asyncio

from avtomatika import OrchestratorEngine, StateMachineBlueprint
from avtomatika.config import Config
from avtomatika.storage.memory import MemoryStorage

# === Конфигурация ===
config = Config()
config.CLIENT_TOKEN = "test-client-token"
config.GLOBAL_WORKER_TOKEN = "test-worker-token"
config.LOG_LEVEL = "DEBUG"
config.LOG_FORMAT = "text"  # Читаемый формат для отладки
config.RATE_LIMITING_ENABLED = False  # Отключаем для локального тестирования

# === Storage ===
storage = MemoryStorage()

# === Blueprint ===
bp = StateMachineBlueprint(name="test_flow", api_endpoint="/jobs/test", api_version="v1")


@bp.handler_for("start", is_start=True)
async def start_handler(job_id, initial_data, actions):
    """Начальное состояние — отправляем задачу воркеру."""
    print(f"\n{'='*50}")
    print(f"[ORCHESTRATOR] Job {job_id} started")
    print(f"[ORCHESTRATOR] Initial data: {initial_data}")
    print(f"[ORCHESTRATOR] Dispatching task to worker...")
    print(f"{'='*50}\n")

    actions.dispatch_task(
        task_type="echo_task",
        params={
            "message": initial_data.get("message", "Hello from Orchestrator!"),
            "multiply": initial_data.get("multiply", 2),
        },
        transitions={
            "success": "completed",
            "failure": "failed",
        },
    )


@bp.handler_for("completed", is_end=True)
async def completed_handler(job_id, state_history, actions):
    """Успешное завершение."""
    print(f"\n{'='*50}")
    print(f"[ORCHESTRATOR] Job {job_id} COMPLETED!")
    print(f"[ORCHESTRATOR] Result from worker: {state_history}")
    print(f"{'='*50}\n")


@bp.handler_for("failed", is_end=True)
async def failed_handler(job_id, state_history, actions):
    """Ошибка."""
    print(f"\n{'='*50}")
    print(f"[ORCHESTRATOR] Job {job_id} FAILED!")
    print(f"[ORCHESTRATOR] Error info: {state_history}")
    print(f"{'='*50}\n")


# === Engine ===
engine = OrchestratorEngine(storage, config)
engine.register_blueprint(bp)


# Нужно вручную добавить клиентский токен в storage
async def setup_client():
    await storage.save_client_config(
        "test-client-token", {"token": "test-client-token", "plan": "test", "params": {}}
    )
    await storage.initialize_client_quota("test-client-token", 1000)


async def main():
    await setup_client()
    await engine.start()
    print("\n" + "=" * 60)
    print("ORCHESTRATOR RUNNING on http://localhost:8080")
    print("=" * 60)
    print("\nEndpoints:")
    print("  POST /api/v1/jobs/test  - Create a job")
    print("  GET  /api/v1/jobs/{id}  - Get job status")
    print("  GET  /api/v1/workers    - List workers")
    print("\nHeaders required:")
    print("  X-Avtomatika-Token: test-client-token")
    print("=" * 60 + "\n")

    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        await engine.stop()


if __name__ == "__main__":
    asyncio.run(main())
