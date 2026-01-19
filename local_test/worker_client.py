"""Минимальный клиент воркера для локального тестирования."""

import asyncio
import os
import sys
import uuid

# Добавляем путь к src для импорта
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "avtomatika_worker", "src"))

# Устанавливаем переменные окружения ПЕРЕД импортом Worker
os.environ["ORCHESTRATOR_URL"] = "http://localhost:8000"
os.environ["WORKER_ID"] = f"test-worker-{uuid.uuid4().hex[:8]}"
os.environ["WORKER_TOKEN"] = "test-worker-token"

print("Environment set up:")
print(f"  ORCHESTRATOR_URL: {os.environ['ORCHESTRATOR_URL']}")
print(f"  WORKER_ID: {os.environ['WORKER_ID']}")
print(f"  WORKER_TOKEN: {os.environ['WORKER_TOKEN']}")

from avtomatika_worker import Worker

# Создаём воркер
print("\nCreating worker...")
worker = Worker(
    worker_type="test-processor",
    max_concurrent_tasks=5,
)
print("Worker created!")


@worker.task("process_data")
async def process_data_handler(params: dict, **kwargs) -> dict:
    """Обработчик тестовой задачи."""
    job_id = params.get("job_id", "unknown")
    payload = params.get("payload", "")
    
    print(f"[Task] Processing data for job {job_id}")
    print(f"[Task] Payload: {payload}")
    
    # Симулируем работу
    await asyncio.sleep(2)
    
    # Возвращаем результат
    result = {
        "processed_payload": payload.upper() if isinstance(payload, str) else payload,
        "worker_id": os.environ.get("WORKER_ID"),
        "message": "Data processed successfully!",
    }
    
    print(f"[Task] Completed processing for job {job_id}")
    
    return {
        "status": "success",
        "data": result,
    }


async def main():
    """Запуск воркера."""
    print("=" * 50)
    print(f"Starting worker: {os.environ['WORKER_ID']}")
    print(f"Orchestrator URL: {os.environ['ORCHESTRATOR_URL']}")
    print("=" * 50)
    print()
    print("Registered task handlers:")
    print("  - process_data")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 50)
    
    sys.stdout.flush()
    await worker.main()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped by user")
