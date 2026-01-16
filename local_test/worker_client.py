"""
Минимальный Worker для локального тестирования.
Запуск: python local_test/worker_client.py
"""
import asyncio
import os

# Устанавливаем переменные окружения ДО импорта Worker
os.environ["ORCHESTRATOR_URL"] = "http://localhost:8080"
os.environ["WORKER_ID"] = "local-test-worker"
os.environ["WORKER_TOKEN"] = "test-worker-token"

from avtomatika_worker import Worker

# === Worker ===
worker = Worker(
    worker_type="test-worker",
    max_concurrent_tasks=5,
)


@worker.task("echo_task")
async def echo_task_handler(params, task_id, job_id, **kwargs):
    """
    Простая задача: получает сообщение и число,
    возвращает сообщение повторённое N раз.
    """
    print(f"\n{'='*50}")
    print(f"[WORKER] Received task {task_id}")
    print(f"[WORKER] Job ID: {job_id}")
    print(f"[WORKER] Params: {params}")
    print(f"{'='*50}")

    message = params.get("message", "default")
    multiply = params.get("multiply", 1)

    # Имитируем работу
    print(f"[WORKER] Processing...")
    await asyncio.sleep(1)

    result_message = (message + " ") * multiply

    print(f"[WORKER] Done! Result: {result_message.strip()}")
    print(f"{'='*50}\n")

    return {
        "status": "success",
        "data": {
            "processed_message": result_message.strip(),
            "original_message": message,
            "multiplied_by": multiply,
        },
    }


@worker.task("failing_task")
async def failing_task_handler(params, **kwargs):
    """Задача, которая всегда падает (для тестирования ошибок)."""
    print("[WORKER] This task will fail!")
    return {
        "status": "failure",
        "error": {"code": "TRANSIENT_ERROR", "message": "Intentional failure for testing"},
    }


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("WORKER STARTING...")
    print("=" * 60)
    print(f"\nWorker ID: {os.environ['WORKER_ID']}")
    print(f"Orchestrator: {os.environ['ORCHESTRATOR_URL']}")
    print(f"Supported tasks: echo_task, failing_task")
    print("=" * 60 + "\n")

    worker.run()
