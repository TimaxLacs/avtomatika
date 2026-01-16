# План локального тестирования Orchestrator + Worker

## 🎯 Цель

Запустить минимальный сценарий взаимодействия:
1. Orchestrator принимает job
2. Job отправляет задачу Worker'у
3. Worker выполняет задачу
4. Результат возвращается в Orchestrator
5. Job завершается

---

## 📋 Шаги

### Шаг 1: Подготовка окружения

```bash
cd /Users/timax/projects/avtomatika

# Создать виртуальное окружение (если ещё нет)
python3.11 -m venv .venv
source .venv/bin/activate

# Установить оба пакета в режиме разработки
pip install -e ".[all,test]"
pip install -e "./avtomatika_worker[test]"
```

---

### Шаг 2: Создать файл Orchestrator'а

Создай файл `local_test/orchestrator_server.py`:

```python
"""
Минимальный Orchestrator для локального тестирования.
Запуск: python local_test/orchestrator_server.py
"""
import asyncio
from avtomatika import OrchestratorEngine, StateMachineBlueprint
from avtomatika.storage.memory import MemoryStorage
from avtomatika.config import Config

# === Конфигурация ===
config = Config()
config.CLIENT_TOKEN = "test-client-token"
config.GLOBAL_WORKER_TOKEN = "test-worker-token"
config.LOG_LEVEL = "DEBUG"
config.LOG_FORMAT = "text"  # Читаемый формат для отладки

# === Storage ===
storage = MemoryStorage()

# === Blueprint ===
bp = StateMachineBlueprint(
    name="test_flow",
    api_endpoint="/jobs/test",
    api_version="v1"
)

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
        }
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
    await storage.save_client_config("test-client-token", {
        "token": "test-client-token",
        "plan": "test",
        "params": {}
    })
    await storage.initialize_client_quota("test-client-token", 1000)

async def main():
    await setup_client()
    await engine.start()
    print("\n" + "="*60)
    print("ORCHESTRATOR RUNNING on http://localhost:8080")
    print("="*60)
    print("\nEndpoints:")
    print("  POST /api/v1/jobs/test  - Create a job")
    print("  GET  /api/v1/jobs/{id}  - Get job status")
    print("\nHeaders required:")
    print("  X-Avtomatika-Token: test-client-token")
    print("="*60 + "\n")
    
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        await engine.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

---

### Шаг 3: Создать файл Worker'а

Создай файл `local_test/worker_client.py`:

```python
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
        }
    }

if __name__ == "__main__":
    print("\n" + "="*60)
    print("WORKER STARTING...")
    print("="*60)
    print(f"\nWorker ID: {os.environ['WORKER_ID']}")
    print(f"Orchestrator: {os.environ['ORCHESTRATOR_URL']}")
    print(f"Supported tasks: echo_task")
    print("="*60 + "\n")
    
    worker.run()
```

---

### Шаг 4: Создать директорию и файлы

```bash
mkdir -p local_test
```

Затем создай файлы вручную или через редактор:
- `local_test/orchestrator_server.py`
- `local_test/worker_client.py`

---

### Шаг 5: Запуск теста

**Терминал 1 — Orchestrator:**

```bash
cd /Users/timax/projects/avtomatika
source .venv/bin/activate
python local_test/orchestrator_server.py
```

Ожидаемый вывод:
```
============================================================
ORCHESTRATOR RUNNING on http://localhost:8080
============================================================

Endpoints:
  POST /api/v1/jobs/test  - Create a job
  GET  /api/v1/jobs/{id}  - Get job status

Headers required:
  X-Avtomatika-Token: test-client-token
============================================================
```

**Терминал 2 — Worker:**

```bash
cd /Users/timax/projects/avtomatika
source .venv/bin/activate
python local_test/worker_client.py
```

Ожидаемый вывод:
```
============================================================
WORKER STARTING...
============================================================

Worker ID: local-test-worker
Orchestrator: http://localhost:8080
Supported tasks: echo_task
============================================================

Registering worker
Sending heartbeats
Worker registered
Waiting for registration
Polling started
```

**Терминал 3 — Создание Job'а:**

```bash
# Создать job
curl -X POST http://localhost:8080/api/v1/jobs/test \
  -H "Content-Type: application/json" \
  -H "X-Avtomatika-Token: test-client-token" \
  -d '{"message": "Hello World", "multiply": 3}'
```

Ответ:
```json
{"status": "accepted", "job_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"}
```

**Проверить статус:**

```bash
# Заменить JOB_ID на реальный ID из предыдущего ответа
curl http://localhost:8080/api/v1/jobs/JOB_ID \
  -H "X-Avtomatika-Token: 2cb6c52a-a122-4fe4-87c4-e7eb2da42259" | python -m json.tool
```

---

### Шаг 6: Что должно произойти

**В терминале Orchestrator:**

```
==================================================
[ORCHESTRATOR] Job abc123 started
[ORCHESTRATOR] Initial data: {'message': 'Hello World', 'multiply': 3}
[ORCHESTRATOR] Dispatching task to worker...
==================================================

... (после обработки воркером) ...

==================================================
[ORCHESTRATOR] Job abc123 COMPLETED!
[ORCHESTRATOR] Result from worker: {
    'processed_message': 'Hello World Hello World Hello World',
    'original_message': 'Hello World',
    'multiplied_by': 3
}
==================================================
```

**В терминале Worker:**

```
==================================================
[WORKER] Received task task-xyz
[WORKER] Job ID: abc123
[WORKER] Params: {'message': 'Hello World', 'multiply': 3}
==================================================
[WORKER] Processing...
[WORKER] Done! Result: Hello World Hello World Hello World
==================================================
```

---

## 🧪 Дополнительные тесты

### Тест 1: Проверка списка воркеров

```bash
curl http://localhost:8080/api/v1/workers \
  -H "X-Avtomatika-Token: test-client-token" | python -m json.tool
```

### Тест 2: Тест с ошибкой

Добавь в worker ещё одну задачу, которая падает:

```python
@worker.task("failing_task")
async def failing_task_handler(params, **kwargs):
    print("[WORKER] This task will fail!")
    return {
        "status": "failure",
        "error": {
            "code": "TRANSIENT_ERROR",
            "message": "Intentional failure for testing"
        }
    }
```

И измени blueprint для её использования.

### Тест 3: Несколько Job'ов подряд

```bash
for i in {1..5}; do
  curl -X POST http://localhost:8080/api/v1/jobs/test \
    -H "Content-Type: application/json" \
    -H "X-Avtomatika-Token: test-client-token" \
    -d "{\"message\": \"Message $i\", \"multiply\": $i}"
  echo ""
done
```

---

## 📁 Итоговая структура

```
avtomatika/
├── local_test/
│   ├── orchestrator_server.py    # Сервер оркестратора
│   └── worker_client.py          # Клиент воркера
├── src/
│   └── avtomatika/
└── avtomatika_worker/
    └── src/
        └── avtomatika_worker/
```

---

## ❓ Troubleshooting

### Проблема: Worker не может подключиться

```
Error registering with http://localhost:8080: Connection refused
```

**Решение:** Убедись, что Orchestrator запущен первым.

### Проблема: 401 Unauthorized

```json
{"error": "Unauthorized: Invalid token"}
```

**Решение:** Проверь, что токены совпадают:
- В Orchestrator: `config.GLOBAL_WORKER_TOKEN = "test-worker-token"`
- В Worker: `os.environ["WORKER_TOKEN"] = "test-worker-token"`

### Проблема: Task не выполняется

Worker зарегистрирован, но задачи не приходят.

**Решение:** Проверь, что `task_type` в `dispatch_task()` совпадает с именем в `@worker.task()`:
```python
# В blueprint:
actions.dispatch_task(task_type="echo_task", ...)

# В worker:
@worker.task("echo_task")  # ← Должно совпадать!
```

### Проблема: Job застрял в "waiting_for_worker"

**Причина:** Worker не берёт задачу.

**Диагностика:**
```bash
# Проверить статус job'а
curl http://localhost:8080/api/v1/jobs/JOB_ID \
  -H "X-Avtomatika-Token: test-client-token" | python -m json.tool
```

Смотри поле `"status"` и `"task_worker_id"`.

---

## ✅ Checklist успешного теста

- [ ] Orchestrator запустился на порту 8080
- [ ] Worker зарегистрировался (видно в логах)
- [ ] Worker отправляет heartbeats (каждые 15 сек)
- [ ] POST /jobs/test возвращает 202 и job_id
- [ ] В логах Orchestrator видно "Dispatching task"
- [ ] В логах Worker видно "Received task"
- [ ] Worker возвращает результат
- [ ] В логах Orchestrator видно "COMPLETED"
- [ ] GET /jobs/{id} показывает `current_state: "completed"`
