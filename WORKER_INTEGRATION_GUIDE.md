# Руководство по интеграции своего проекта в Worker

Это руководство описывает, как добавить свою бизнес-логику в воркер Avtomatika.

---

## Оглавление

1. [Архитектура](#архитектура)
2. [Быстрый старт](#быстрый-старт)
3. [Создание задач (Task Handlers)](#создание-задач-task-handlers)
4. [Параметры и результаты](#параметры-и-результаты)
5. [Обработка ошибок](#обработка-ошибок)
6. [Отправка прогресса](#отправка-прогресса)
7. [Конфигурация воркера](#конфигурация-воркера)
8. [Интеграция с Blueprint](#интеграция-с-blueprint)
9. [Примеры реальных сценариев](#примеры-реальных-сценариев)
10. [Best Practices](#best-practices)

---

## Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                      ORCHESTRATOR                            │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐      │
│  │  Blueprint  │───▶│   Engine    │───▶│  Dispatcher │      │
│  │ (ваш flow)  │    │             │    │             │      │
│  └─────────────┘    └─────────────┘    └──────┬──────┘      │
└────────────────────────────────────────────────│─────────────┘
                                                 │
                              dispatch_task("your_task", params)
                                                 │
                                                 ▼
┌─────────────────────────────────────────────────────────────┐
│                        WORKER                                │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  @worker.task("your_task")                          │    │
│  │  async def your_task_handler(params, **kwargs):     │    │
│  │      # ВАШ КОД ЗДЕСЬ                                │    │
│  │      result = await your_business_logic(params)     │    │
│  │      return {"status": "success", "data": result}   │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## Быстрый старт

### Шаг 1: Создайте файл воркера

```python
# my_worker.py
import asyncio
import os

# Конфигурация через переменные окружения
os.environ["ORCHESTRATOR_URL"] = "http://localhost:8080"
os.environ["WORKER_ID"] = "my-custom-worker"
os.environ["WORKER_TOKEN"] = "your-worker-token"

from avtomatika_worker import Worker

# Создаём воркер
worker = Worker(
    worker_type="my-project-worker",
    max_concurrent_tasks=10,
)

# Регистрируем задачу
@worker.task("my_task")
async def my_task_handler(params, task_id, job_id, **kwargs):
    # Ваша бизнес-логика
    input_data = params.get("input")
    result = f"Processed: {input_data}"
    
    return {
        "status": "success",
        "data": {"output": result}
    }

if __name__ == "__main__":
    worker.run()
```

### Шаг 2: Запустите воркер

```bash
python my_worker.py
```

---

## Создание задач (Task Handlers)

### Базовый синтаксис

```python
@worker.task("task_name")
async def handler_name(params, task_id, job_id, **kwargs):
    # params — словарь с параметрами от оркестратора
    # task_id — уникальный ID задачи
    # job_id — ID родительского job'а
    
    return {
        "status": "success",  # или "failure"
        "data": {...}         # данные результата
    }
```

### Доступные аргументы в handler

| Аргумент | Тип | Описание |
|----------|-----|----------|
| `params` | `dict` | Параметры задачи от оркестратора |
| `task_id` | `str` | Уникальный ID задачи |
| `job_id` | `str` | ID job'а, которому принадлежит задача |
| `priority` | `float` | Приоритет задачи (0.0 по умолчанию) |
| `send_progress` | `callable` | Функция для отправки прогресса |
| `add_to_hot_cache` | `callable` | Добавить данные в hot cache |
| `remove_from_hot_cache` | `callable` | Удалить из hot cache |

### Пример с использованием всех аргументов

```python
@worker.task("complex_task")
async def complex_handler(
    params,
    task_id,
    job_id,
    priority,
    send_progress,
    **kwargs
):
    total_steps = params.get("steps", 10)
    
    for step in range(total_steps):
        # Выполняем работу
        await asyncio.sleep(0.5)
        
        # Отправляем прогресс
        await send_progress(
            job_id=job_id,
            task_id=task_id,
            progress=(step + 1) / total_steps * 100,
            message=f"Step {step + 1}/{total_steps}"
        )
    
    return {"status": "success", "data": {"steps_completed": total_steps}}
```

---

## Параметры и результаты

### Структура params (входные данные)

Params — это словарь, который вы передаёте в `dispatch_task()` из Blueprint:

```python
# В Blueprint (оркестратор)
actions.dispatch_task(
    task_type="process_image",
    params={
        "image_url": "https://example.com/image.jpg",
        "filters": ["blur", "grayscale"],
        "quality": 85
    },
    transitions={"success": "done", "failure": "error"}
)
```

```python
# В Worker
@worker.task("process_image")
async def process_image(params, **kwargs):
    url = params["image_url"]       # "https://example.com/image.jpg"
    filters = params["filters"]     # ["blur", "grayscale"]
    quality = params["quality"]     # 85
    
    # Обрабатываем...
    return {"status": "success", "data": {"processed_url": "..."}}
```

### Структура результата

```python
# Успешный результат
{
    "status": "success",
    "data": {
        # Любые данные, которые нужно передать обратно
        "output": "...",
        "metadata": {...}
    }
}

# Результат с ошибкой
{
    "status": "failure",
    "error": {
        "code": "TRANSIENT_ERROR",  # или "PERMANENT_ERROR"
        "message": "Описание ошибки"
    }
}
```

### Как данные передаются в следующий handler

Результат воркера попадает в `state_history` следующего состояния:

```python
# Worker возвращает:
return {
    "status": "success",
    "data": {"processed_message": "Hello World Hello World"}
}

# В следующем handler Blueprint:
@bp.handler_for("completed")
async def completed_handler(job_id, state_history, actions):
    # state_history содержит результат воркера:
    # {"processed_message": "Hello World Hello World"}
    print(f"Result: {state_history['processed_message']}")
```

---

## Обработка ошибок

### Типы ошибок

| Код ошибки | Поведение |
|------------|-----------|
| `TRANSIENT_ERROR` | Задача будет повторена (retry) |
| `PERMANENT_ERROR` | Задача сразу помечается как failed |

### Пример обработки ошибок

```python
@worker.task("risky_task")
async def risky_handler(params, **kwargs):
    try:
        result = await do_risky_operation(params)
        return {"status": "success", "data": result}
    
    except NetworkError as e:
        # Временная ошибка — оркестратор повторит задачу
        return {
            "status": "failure",
            "error": {
                "code": "TRANSIENT_ERROR",
                "message": f"Network error: {e}"
            }
        }
    
    except ValidationError as e:
        # Постоянная ошибка — повторять бессмысленно
        return {
            "status": "failure",
            "error": {
                "code": "PERMANENT_ERROR",
                "message": f"Invalid input: {e}"
            }
        }
    
    except Exception as e:
        # Неизвестная ошибка — лучше считать временной
        return {
            "status": "failure",
            "error": {
                "code": "TRANSIENT_ERROR",
                "message": f"Unexpected error: {e}"
            }
        }
```

### Автоматическая обработка исключений

Если handler выбрасывает исключение, воркер автоматически вернёт `TRANSIENT_ERROR`:

```python
@worker.task("auto_error_task")
async def auto_error_handler(params, **kwargs):
    # Если здесь возникнет исключение,
    # воркер автоматически вернёт:
    # {"status": "failure", "error": {"code": "TRANSIENT_ERROR", "message": "..."}}
    raise RuntimeError("Something went wrong")
```

---

## Отправка прогресса

Для длительных задач можно отправлять промежуточный прогресс:

```python
@worker.task("long_task")
async def long_task_handler(params, task_id, job_id, send_progress, **kwargs):
    files = params["files"]
    total = len(files)
    
    for i, file in enumerate(files):
        # Обрабатываем файл
        await process_file(file)
        
        # Отправляем прогресс
        await send_progress(
            job_id=job_id,
            task_id=task_id,
            progress=int((i + 1) / total * 100),
            message=f"Processed {i + 1}/{total} files"
        )
    
    return {"status": "success", "data": {"files_processed": total}}
```

---

## Конфигурация воркера

### Через переменные окружения

```bash
# Основные
export ORCHESTRATOR_URL="http://orchestrator:8080"
export WORKER_ID="worker-1"
export WORKER_TOKEN="secret-token"

# Ресурсы
export MAX_CONCURRENT_TASKS="10"
export CPU_CORES="4"

# Тюнинг
export HEARTBEAT_INTERVAL="15"
export TASK_POLL_TIMEOUT="30"
```

### Через код

```python
worker = Worker(
    worker_type="gpu-worker",
    max_concurrent_tasks=5,
    task_type_limits={
        "heavy_task": 2,    # Максимум 2 параллельных heavy_task
        "light_task": 10    # Максимум 10 параллельных light_task
    }
)
```

### Ограничение параллелизма по типу задачи

```python
worker = Worker(
    worker_type="mixed-worker",
    max_concurrent_tasks=20,  # Общий лимит
    task_type_limits={
        "gpu_inference": 1,   # Только одна GPU-задача одновременно
        "cpu_task": 10,       # До 10 CPU-задач
        "io_task": 15         # До 15 IO-bound задач
    }
)
```

---

## Интеграция с Blueprint

### Полный пример: Оркестратор + Воркер

**Blueprint (оркестратор):**

```python
# orchestrator.py
from avtomatika import OrchestratorEngine, StateMachineBlueprint
from avtomatika.config import Config
from avtomatika.storage.memory import MemoryStorage

config = Config()
config.CLIENT_TOKEN = "client-token"
config.GLOBAL_WORKER_TOKEN = "worker-token"

storage = MemoryStorage()

bp = StateMachineBlueprint(
    name="image_processing",
    api_endpoint="/jobs/process-image",
    api_version="v1"
)

@bp.handler_for("start", is_start=True)
async def start(job_id, initial_data, actions):
    # Отправляем задачу воркеру
    actions.dispatch_task(
        task_type="resize_image",
        params={
            "image_url": initial_data["url"],
            "width": initial_data.get("width", 800),
            "height": initial_data.get("height", 600)
        },
        transitions={
            "success": "apply_filters",
            "failure": "failed"
        }
    )

@bp.handler_for("apply_filters")
async def apply_filters(job_id, state_history, actions):
    # state_history содержит результат предыдущей задачи
    resized_url = state_history["resized_url"]
    
    actions.dispatch_task(
        task_type="apply_filters",
        params={
            "image_url": resized_url,
            "filters": ["sharpen", "contrast"]
        },
        transitions={
            "success": "completed",
            "failure": "failed"
        }
    )

@bp.handler_for("completed", is_end=True)
async def completed(job_id, state_history, actions):
    print(f"Job {job_id} completed! Final image: {state_history['final_url']}")

@bp.handler_for("failed", is_end=True)
async def failed(job_id, state_history, actions):
    print(f"Job {job_id} failed!")

engine = OrchestratorEngine(storage, config)
engine.register_blueprint(bp)
```

**Worker:**

```python
# image_worker.py
import os
os.environ["ORCHESTRATOR_URL"] = "http://localhost:8080"
os.environ["WORKER_ID"] = "image-worker-1"
os.environ["WORKER_TOKEN"] = "worker-token"

from avtomatika_worker import Worker

worker = Worker(worker_type="image-processor", max_concurrent_tasks=5)

@worker.task("resize_image")
async def resize_image(params, **kwargs):
    url = params["image_url"]
    width = params["width"]
    height = params["height"]
    
    # Ваша логика ресайза
    resized_url = f"{url}?w={width}&h={height}"
    
    return {
        "status": "success",
        "data": {"resized_url": resized_url}
    }

@worker.task("apply_filters")
async def apply_filters(params, **kwargs):
    url = params["image_url"]
    filters = params["filters"]
    
    # Ваша логика применения фильтров
    final_url = f"{url}?filters={','.join(filters)}"
    
    return {
        "status": "success",
        "data": {"final_url": final_url}
    }

if __name__ == "__main__":
    worker.run()
```

---

## Примеры реальных сценариев

### 1. ML Inference Worker

```python
import torch
from transformers import pipeline

worker = Worker(
    worker_type="ml-inference",
    max_concurrent_tasks=2,  # GPU memory limited
)

# Загружаем модель один раз при старте
classifier = pipeline("sentiment-analysis", device=0)

@worker.task("sentiment_analysis")
async def sentiment_analysis(params, **kwargs):
    text = params["text"]
    
    # Выполняем инференс
    result = classifier(text)[0]
    
    return {
        "status": "success",
        "data": {
            "label": result["label"],
            "score": result["score"]
        }
    }
```

### 2. Video Processing Worker

```python
import ffmpeg

worker = Worker(
    worker_type="video-processor",
    max_concurrent_tasks=3,
    task_type_limits={
        "transcode_4k": 1,  # Только один 4K одновременно
        "transcode_1080p": 2
    }
)

@worker.task("transcode_4k")
async def transcode_4k(params, task_id, job_id, send_progress, **kwargs):
    input_path = params["input_path"]
    output_path = params["output_path"]
    
    # Получаем длительность видео
    probe = ffmpeg.probe(input_path)
    duration = float(probe['format']['duration'])
    
    # Запускаем транскодинг с отслеживанием прогресса
    process = (
        ffmpeg
        .input(input_path)
        .output(output_path, vcodec='libx264', crf=18)
        .overwrite_output()
        .run_async(pipe_stderr=True)
    )
    
    # Парсим прогресс из stderr ffmpeg
    while True:
        line = process.stderr.readline()
        if not line:
            break
        # Парсим time=00:00:00.00 и отправляем прогресс
        ...
    
    return {
        "status": "success",
        "data": {"output_path": output_path}
    }
```

### 3. Web Scraping Worker

```python
import aiohttp
from bs4 import BeautifulSoup

worker = Worker(
    worker_type="scraper",
    max_concurrent_tasks=50  # IO-bound, можно много
)

@worker.task("scrape_page")
async def scrape_page(params, **kwargs):
    url = params["url"]
    selectors = params.get("selectors", {})
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            html = await response.text()
    
    soup = BeautifulSoup(html, 'html.parser')
    
    data = {}
    for name, selector in selectors.items():
        element = soup.select_one(selector)
        data[name] = element.text.strip() if element else None
    
    return {
        "status": "success",
        "data": data
    }
```

---

## Best Practices

### 1. Идемпотентность

Задачи могут быть повторены. Убедитесь, что повторное выполнение безопасно:

```python
@worker.task("create_user")
async def create_user(params, **kwargs):
    user_id = params["user_id"]
    
    # Проверяем, существует ли уже
    existing = await db.get_user(user_id)
    if existing:
        return {"status": "success", "data": {"user": existing}}
    
    # Создаём нового
    user = await db.create_user(user_id, params["data"])
    return {"status": "success", "data": {"user": user}}
```

### 2. Таймауты

Всегда устанавливайте таймауты для внешних вызовов:

```python
import asyncio

@worker.task("call_api")
async def call_api(params, **kwargs):
    try:
        result = await asyncio.wait_for(
            external_api_call(params),
            timeout=30.0
        )
        return {"status": "success", "data": result}
    except asyncio.TimeoutError:
        return {
            "status": "failure",
            "error": {"code": "TRANSIENT_ERROR", "message": "API timeout"}
        }
```

### 3. Логирование

```python
import logging

logger = logging.getLogger(__name__)

@worker.task("important_task")
async def important_task(params, task_id, job_id, **kwargs):
    logger.info(f"Starting task {task_id} for job {job_id}")
    logger.debug(f"Params: {params}")
    
    try:
        result = await do_work(params)
        logger.info(f"Task {task_id} completed successfully")
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}", exc_info=True)
        raise
```

### 4. Graceful Shutdown

Воркер автоматически обрабатывает SIGTERM/SIGINT, но убедитесь, что ваши задачи корректно завершаются:

```python
@worker.task("long_running")
async def long_running(params, **kwargs):
    try:
        for item in params["items"]:
            await process_item(item)
    except asyncio.CancelledError:
        # Задача отменена — сохраняем состояние
        await save_progress()
        raise
```

### 5. Структура проекта

```
my_project/
├── workers/
│   ├── __init__.py
│   ├── base.py          # Базовые настройки воркера
│   ├── image_worker.py  # Задачи обработки изображений
│   ├── ml_worker.py     # ML задачи
│   └── utils/
│       ├── __init__.py
│       └── helpers.py
├── blueprints/
│   ├── __init__.py
│   └── image_pipeline.py
├── requirements.txt
└── docker-compose.yml
```

---

## Запуск в продакшене

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY workers/ ./workers/

ENV ORCHESTRATOR_URL=http://orchestrator:8080
ENV WORKER_TOKEN=production-token
ENV MAX_CONCURRENT_TASKS=10

CMD ["python", "-m", "workers.image_worker"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  orchestrator:
    build: ./orchestrator
    ports:
      - "8080:8080"
    environment:
      - REDIS_HOST=redis
      - GLOBAL_WORKER_TOKEN=production-token

  worker-1:
    build: ./workers
    environment:
      - ORCHESTRATOR_URL=http://orchestrator:8080
      - WORKER_ID=worker-1
      - WORKER_TOKEN=production-token
    deploy:
      replicas: 3

  redis:
    image: redis:7-alpine
```

---

## Troubleshooting

| Проблема | Решение |
|----------|---------|
| Worker не получает задачи | Проверьте, что `task_type` в Blueprint совпадает с `@worker.task("...")` |
| 401 Unauthorized | Проверьте `WORKER_TOKEN` и `GLOBAL_WORKER_TOKEN` |
| 429 Too Many Requests | Увеличьте rate limit или отключите для тестирования |
| Задача выполнена, но job не переходит в следующее состояние | Проверьте, что результат содержит правильный `status` |
