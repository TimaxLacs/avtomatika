# Руководство по интеграции проекта в Avtomatika Worker

Это руководство описывает, как интегрировать ваш проект в воркер Avtomatika.

## Содержание

1. [Обзор](#обзор)
2. [Быстрый старт](#быстрый-старт)
3. [Создание обработчиков задач](#создание-обработчиков-задач)
4. [Возврат результатов](#возврат-результатов)
5. [Обработка ошибок](#обработка-ошибок)
6. [Конфигурация](#конфигурация)
7. [Примеры интеграции](#примеры-интеграции)

---

## Обзор

Воркер Avtomatika — это процесс, который:
1. Регистрируется в оркестраторе
2. Получает задачи из очереди
3. Выполняет задачи с помощью зарегистрированных обработчиков
4. Возвращает результаты оркестратору

### Архитектура

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   Оркестратор   │◄────►│     Воркер      │◄────►│   Ваш код       │
│                 │      │                 │      │                 │
│  - Blueprints   │      │  - Регистрация  │      │  - Бизнес-логика│
│  - Job Queue    │      │  - Polling      │      │  - API клиенты  │
│  - Dispatch     │      │  - Handlers     │      │  - БД           │
└─────────────────┘      └─────────────────┘      └─────────────────┘
```

---

## Быстрый старт

### 1. Установка

```bash
pip install avtomatika-worker
```

### 2. Минимальный воркер

```python
import asyncio
from avtomatika_worker import Worker

# Создание воркера
worker = Worker(
    orchestrator_url="http://localhost:8000",
    worker_id="my-worker-1",
    worker_token="your-secret-token",
    worker_type="my-service"
)

# Регистрация обработчика задачи
@worker.task("process_data")
async def process_data(params: dict) -> dict:
    """Обработчик задачи типа 'process_data'."""
    input_value = params.get("input")
    result = input_value.upper()  # Ваша логика
    
    return {
        "status": "success",
        "data": {"result": result}
    }

# Запуск
if __name__ == "__main__":
    asyncio.run(worker.main())
```

### 3. Запуск

```bash
export ORCHESTRATOR_URL=http://localhost:8000
export WORKER_TOKEN=your-secret-token

python my_worker.py
```

---

## Создание обработчиков задач

### Базовый обработчик

```python
@worker.task("task_type_name")
async def handler(params: dict) -> dict:
    # params содержит данные от оркестратора
    return {"status": "success", "data": {...}}
```

### Доступ к метаданным задачи

```python
@worker.task("my_task")
async def handler(params: dict, task_id: str = None, job_id: str = None) -> dict:
    print(f"Processing task {task_id} for job {job_id}")
    return {"status": "success"}
```

### Категории задач (для лимитов)

```python
worker = Worker(
    ...,
    task_type_limits={
        "heavy": 2,    # Максимум 2 тяжёлые задачи одновременно
        "light": 10,   # Максимум 10 лёгких задач
    }
)

@worker.task("process_image", task_type="heavy")
async def process_image(params: dict) -> dict:
    ...

@worker.task("send_notification", task_type="light")
async def send_notification(params: dict) -> dict:
    ...
```

---

## Возврат результатов

### Успешный результат

```python
@worker.task("my_task")
async def handler(params: dict) -> dict:
    result = do_work(params)
    
    return {
        "status": "success",
        "data": {
            "output": result,
            "metadata": {...}
        }
    }
```

### Ошибка

```python
@worker.task("my_task")
async def handler(params: dict) -> dict:
    try:
        result = do_work(params)
        return {"status": "success", "data": result}
    except ValueError as e:
        return {
            "status": "failure",
            "error": {
                "code": "VALIDATION_ERROR",
                "message": str(e)
            }
        }
```

### Повторяемая ошибка (retry)

```python
@worker.task("my_task")
async def handler(params: dict) -> dict:
    try:
        result = call_external_api(params)
        return {"status": "success", "data": result}
    except ConnectionError:
        # Оркестратор повторит задачу
        return {
            "status": "retry",
            "error": {
                "code": "CONNECTION_ERROR",
                "message": "Failed to connect to external service"
            }
        }
```

---

## Обработка ошибок

### Автоматическая обработка исключений

Если обработчик выбрасывает исключение, воркер автоматически возвращает ошибку:

```python
@worker.task("my_task")
async def handler(params: dict) -> dict:
    if not params.get("required_field"):
        raise ValueError("required_field is missing")
    
    # Если исключение не поймано, воркер отправит:
    # {"status": "failure", "error": {"message": "required_field is missing"}}
```

### Graceful shutdown

```python
import signal

async def main():
    # Обработка сигналов для корректного завершения
    loop = asyncio.get_event_loop()
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown()))
    
    await worker.main()

async def shutdown():
    print("Shutting down gracefully...")
    await worker.stop()  # Дожидается завершения текущих задач
```

---

## Конфигурация

### Через переменные окружения

```bash
export ORCHESTRATOR_URL=http://localhost:8000
export WORKER_ID=worker-1
export WORKER_TOKEN=secret
export WORKER_TYPE=my-service
export HEARTBEAT_INTERVAL=30
export POLL_INTERVAL=1
export MAX_CONCURRENT_TASKS=10
```

### Через код

```python
worker = Worker(
    orchestrator_url="http://localhost:8000",
    worker_id="worker-1",
    worker_token="secret",
    worker_type="my-service",
    heartbeat_interval=30,
    poll_interval=1,
    max_concurrent_tasks=10,
    task_type_limits={
        "heavy": 2,
        "light": 10
    }
)
```

### Ресурсы воркера

```python
worker = Worker(
    ...,
    resources={
        "cpu": 4,
        "memory_gb": 16,
        "gpu": True,
        "gpu_memory_gb": 8
    }
)
```

---

## Примеры интеграции

### Интеграция парсера VK/Telegram

```python
import asyncio
from avtomatika_worker import Worker
from sno_parser import TelegramParser, VKParser

worker = Worker(
    orchestrator_url="http://localhost:8000",
    worker_id="parser-worker-1",
    worker_token="secret",
    worker_type="parser"
)

# Инициализация парсеров
tg_parser = None
vk_parser = None

async def init_parsers():
    global tg_parser, vk_parser
    tg_parser = TelegramParser(api_id="...", api_hash="...")
    await tg_parser.start()
    
    vk_parser = VKParser(token="...")

@worker.task("parse_telegram")
async def parse_telegram(params: dict) -> dict:
    channel = params["channel"]
    limit = params.get("limit", 100)
    
    messages = await tg_parser.get_channel_messages(channel, limit)
    
    return {
        "status": "success",
        "data": {
            "channel": channel,
            "messages": [m.to_dict() for m in messages],
            "count": len(messages)
        }
    }

@worker.task("parse_vk")
async def parse_vk(params: dict) -> dict:
    group = params["group"]
    limit = params.get("limit", 100)
    
    posts = await vk_parser.get_wall(group, limit)
    
    return {
        "status": "success",
        "data": {
            "group": group,
            "posts": posts,
            "count": len(posts)
        }
    }

async def main():
    await init_parsers()
    await worker.main()

if __name__ == "__main__":
    asyncio.run(main())
```

### Интеграция с базой данных

```python
import asyncio
import asyncpg
from avtomatika_worker import Worker

worker = Worker(...)
db_pool = None

async def init_db():
    global db_pool
    db_pool = await asyncpg.create_pool(
        "postgresql://user:pass@localhost/db"
    )

@worker.task("save_user")
async def save_user(params: dict) -> dict:
    async with db_pool.acquire() as conn:
        user_id = await conn.fetchval(
            "INSERT INTO users (name, email) VALUES ($1, $2) RETURNING id",
            params["name"],
            params["email"]
        )
    
    return {
        "status": "success",
        "data": {"user_id": user_id}
    }

@worker.task("get_user")
async def get_user(params: dict) -> dict:
    async with db_pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE id = $1",
            params["user_id"]
        )
    
    if not user:
        return {
            "status": "failure",
            "error": {"code": "NOT_FOUND", "message": "User not found"}
        }
    
    return {
        "status": "success",
        "data": dict(user)
    }

async def main():
    await init_db()
    await worker.main()

if __name__ == "__main__":
    asyncio.run(main())
```

### Интеграция с внешним API

```python
import aiohttp
from avtomatika_worker import Worker

worker = Worker(...)

@worker.task("fetch_weather")
async def fetch_weather(params: dict) -> dict:
    city = params["city"]
    api_key = params.get("api_key") or os.environ["WEATHER_API_KEY"]
    
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://api.weather.com/v1/current?city={city}&key={api_key}"
        ) as response:
            if response.status != 200:
                return {
                    "status": "retry",
                    "error": {
                        "code": "API_ERROR",
                        "message": f"Weather API returned {response.status}"
                    }
                }
            
            data = await response.json()
    
    return {
        "status": "success",
        "data": {
            "city": city,
            "temperature": data["temp"],
            "conditions": data["conditions"]
        }
    }
```

---

## Полезные практики

### 1. Логирование

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@worker.task("my_task")
async def handler(params: dict) -> dict:
    logger.info(f"Processing task with params: {params}")
    # ...
    logger.info("Task completed successfully")
```

### 2. Метрики

```python
from prometheus_client import Counter, Histogram

tasks_total = Counter("worker_tasks_total", "Total tasks", ["task_type", "status"])
task_duration = Histogram("worker_task_duration_seconds", "Task duration")

@worker.task("my_task")
async def handler(params: dict) -> dict:
    with task_duration.time():
        try:
            result = await do_work(params)
            tasks_total.labels(task_type="my_task", status="success").inc()
            return {"status": "success", "data": result}
        except Exception:
            tasks_total.labels(task_type="my_task", status="failure").inc()
            raise
```

### 3. Таймауты

```python
import asyncio

@worker.task("my_task")
async def handler(params: dict) -> dict:
    try:
        result = await asyncio.wait_for(
            slow_operation(params),
            timeout=30.0
        )
        return {"status": "success", "data": result}
    except asyncio.TimeoutError:
        return {
            "status": "failure",
            "error": {"code": "TIMEOUT", "message": "Operation timed out"}
        }
```
