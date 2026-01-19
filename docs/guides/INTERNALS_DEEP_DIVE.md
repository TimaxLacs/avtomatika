# Глубокое погружение во внутреннее устройство Avtomatika

Этот документ описывает внутреннее устройство оркестратора и воркера, их взаимодействие и ключевые механизмы.

## Содержание

1. [Обзор архитектуры](#обзор-архитектуры)
2. [Оркестратор](#оркестратор)
3. [Воркер](#воркер)
4. [Протокол взаимодействия](#протокол-взаимодействия)
5. [Хранилище данных](#хранилище-данных)
6. [Отказоустойчивость](#отказоустойчивость)

---

## Обзор архитектуры

```
┌─────────────────────────────────────────────────────────────────────┐
│                           КЛИЕНТЫ                                    │
│                    (HTTP API / WebSocket)                            │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         ОРКЕСТРАТОР                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   Engine     │  │  Executor    │  │  Dispatcher  │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   Watcher    │  │  Scheduler   │  │ HealthChecker│              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    ХРАНИЛИЩЕ (Redis / Memory)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │    Jobs      │  │   Workers    │  │    Queues    │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          ВОРКЕРЫ                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   Worker 1   │  │   Worker 2   │  │   Worker N   │              │
│  │ (type: gpu)  │  │ (type: cpu)  │  │(type: custom)│              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Оркестратор

### Ключевые компоненты

#### 1. OrchestratorEngine (`engine.py`)

Главный класс, объединяющий все компоненты:

```python
class OrchestratorEngine:
    def __init__(self, config, storage):
        self.config = config
        self.storage = storage
        self.blueprints = {}  # Зарегистрированные blueprints
        self.executor = None  # JobExecutor
        self.watcher = None   # Watcher
        # ...
    
    def register_blueprint(self, blueprint):
        """Регистрирует blueprint для обработки jobs."""
        self.blueprints[blueprint.name] = blueprint
    
    def create_app(self):
        """Создаёт aiohttp приложение с маршрутами."""
        app = web.Application(middlewares=[...])
        app.router.add_post("/jobs", self._create_job_handler)
        app.router.add_get("/jobs/{job_id}", self._get_job_handler)
        app.router.add_post("/workers/register", self._register_worker_handler)
        app.router.add_get("/workers/{worker_id}/tasks", self._get_tasks_handler)
        app.router.add_post("/tasks/result", self._task_result_handler)
        return app
```

#### 2. StateMachineBlueprint (`blueprint.py`)

Определяет workflow как конечный автомат:

```python
blueprint = StateMachineBlueprint("my_workflow")

@blueprint.state("init")
async def init_handler(data, actions, job_id):
    # Начальное состояние
    actions.dispatch_task(
        task_type="process",
        params={"input": data["value"]},
        transitions={"success": "completed", "failure": "failed"}
    )

@blueprint.state("completed")
async def completed_handler(data, actions, task_result):
    # Финальное состояние
    pass
```

#### 3. JobExecutor (`executor.py`)

Выполняет jobs, вызывая handlers:

```python
class JobExecutor:
    async def process_job(self, job_id: str):
        job = await self.storage.get_job(job_id)
        blueprint = self.blueprints[job["blueprint"]]
        handler = blueprint.get_handler(job["state"])
        
        # Подготовка аргументов через Dependency Injection
        kwargs = self._resolve_dependencies(handler, job)
        
        # Вызов handler
        await handler(**kwargs)
        
        # Обработка actions (переходы, задачи)
        await self._process_actions(job_id)
```

#### 4. Dispatcher (`dispatcher.py`)

Выбирает воркера для задачи:

```python
class Dispatcher:
    async def dispatch(self, task_type, params, job_id):
        # Получаем список доступных воркеров
        workers = await self.storage.get_available_workers(task_type)
        
        # Выбираем по стратегии
        worker = self._select_worker(workers, strategy=self.config.DISPATCH_STRATEGY)
        
        # Создаём задачу
        task = {
            "task_id": generate_id(),
            "task_type": task_type,
            "params": params,
            "job_id": job_id,
            "worker_id": worker["worker_id"]
        }
        
        # Добавляем в очередь воркера
        await self.storage.add_task_to_queue(worker["worker_id"], task)
```

#### 5. Watcher (`watcher.py`)

Следит за таймаутами и зависшими jobs:

```python
class Watcher:
    async def run(self):
        while True:
            async with self.storage.acquire_lock("watcher"):
                # Находим jobs с истёкшим таймаутом
                stale_jobs = await self.storage.find_stale_jobs(
                    timeout=self.config.JOB_TIMEOUT
                )
                
                for job_id in stale_jobs:
                    await self._handle_timeout(job_id)
            
            await asyncio.sleep(self.config.WATCHER_INTERVAL)
```

---

## Воркер

### Ключевые компоненты

#### 1. Worker (`worker.py`)

Основной класс воркера:

```python
class Worker:
    def __init__(self, orchestrator_url, worker_id, worker_token):
        self.orchestrator_url = orchestrator_url
        self.worker_id = worker_id
        self.worker_token = worker_token
        self.task_handlers = {}  # Зарегистрированные обработчики
        self.current_tasks = {}  # Выполняемые задачи
    
    def task(self, task_type):
        """Декоратор для регистрации обработчика задач."""
        def decorator(func):
            self.task_handlers[task_type] = func
            return func
        return decorator
    
    async def main(self):
        """Главный цикл воркера."""
        await self._register()
        
        asyncio.create_task(self._heartbeat_loop())
        asyncio.create_task(self._poll_tasks_loop())
        
        await asyncio.Event().wait()  # Бесконечное ожидание
```

#### 2. Регистрация воркера

```python
async def _register(self):
    response = await self.session.post(
        f"{self.orchestrator_url}/workers/register",
        json={
            "worker_id": self.worker_id,
            "worker_type": self.worker_type,
            "task_types": list(self.task_handlers.keys()),
            "resources": self._get_resources(),
        },
        headers={"Authorization": f"Bearer {self.worker_token}"}
    )
```

#### 3. Получение и выполнение задач

```python
async def _poll_tasks_loop(self):
    while True:
        # Получаем задачи из очереди
        response = await self.session.get(
            f"{self.orchestrator_url}/workers/{self.worker_id}/tasks"
        )
        tasks = await response.json()
        
        for task in tasks:
            # Запускаем обработку в отдельной задаче
            asyncio.create_task(self._execute_task(task))
        
        await asyncio.sleep(self.poll_interval)

async def _execute_task(self, task):
    handler = self.task_handlers[task["task_type"]]
    
    try:
        result = await handler(task["params"])
        status = "success"
    except Exception as e:
        result = {"error": str(e)}
        status = "failure"
    
    # Отправляем результат
    await self._submit_result(task["task_id"], task["job_id"], status, result)
```

---

## Протокол взаимодействия

### Последовательность взаимодействия

```
Клиент              Оркестратор           Воркер
   │                    │                    │
   │  POST /jobs        │                    │
   │ ─────────────────► │                    │
   │  {job_id}          │                    │
   │ ◄───────────────── │                    │
   │                    │                    │
   │                    │  POST /workers/register
   │                    │ ◄───────────────────
   │                    │  OK                 │
   │                    │ ──────────────────►│
   │                    │                    │
   │                    │  (Executor runs)   │
   │                    │  dispatch_task()   │
   │                    │                    │
   │                    │  GET /workers/{id}/tasks
   │                    │ ◄───────────────────
   │                    │  [{task}]          │
   │                    │ ──────────────────►│
   │                    │                    │
   │                    │    (task execution)│
   │                    │                    │
   │                    │  POST /tasks/result│
   │                    │ ◄───────────────────
   │                    │                    │
   │                    │  (Executor runs)   │
   │                    │  transition()      │
   │                    │                    │
   │  GET /jobs/{id}    │                    │
   │ ─────────────────► │                    │
   │  {state: completed}│                    │
   │ ◄───────────────── │                    │
```

### API Endpoints

| Endpoint | Method | Описание |
|----------|--------|----------|
| `/jobs` | POST | Создать job |
| `/jobs/{job_id}` | GET | Статус job |
| `/jobs/{job_id}/cancel` | POST | Отменить job |
| `/workers/register` | POST | Регистрация воркера |
| `/workers/{worker_id}/tasks` | GET | Получить задачи |
| `/workers/{worker_id}/heartbeat` | POST | Heartbeat |
| `/tasks/result` | POST | Отправить результат |

---

## Хранилище данных

### Структура данных в Redis

```
# Jobs
jobs:{job_id} -> HASH {
    blueprint: "workflow_name",
    state: "current_state",
    data: {...},
    status: "active|completed|failed",
    created_at: timestamp,
    updated_at: timestamp
}

# Workers
workers:{worker_id} -> HASH {
    worker_type: "cpu|gpu|custom",
    task_types: ["type1", "type2"],
    status: "active|busy|offline",
    last_heartbeat: timestamp
}

# Task Queues
worker_queues:{worker_id} -> LIST [task1, task2, ...]

# Pending Tasks
pending_tasks:{job_id} -> HASH {
    task_id: {task_data}
}

# Locks
locks:{resource} -> STRING (with TTL)
```

### MemoryStorage vs RedisStorage

| Аспект | MemoryStorage | RedisStorage |
|--------|---------------|--------------|
| Персистентность | Нет | Да |
| Масштабирование | Один процесс | Несколько инстансов |
| Скорость | Очень быстро | Быстро |
| Использование | Тесты, разработка | Production |

---

## Отказоустойчивость

### 1. Таймауты задач

```python
# При dispatch_task
actions.dispatch_task(
    task_type="process",
    params={...},
    timeout_seconds=60  # Таймаут 60 секунд
)
```

### 2. Retry механизм

```python
# В конфигурации blueprint
@blueprint.state("process", retries=3, retry_delay=5)
async def process_handler(data, actions):
    ...
```

### 3. Heartbeat воркеров

```python
# Воркер отправляет heartbeat каждые N секунд
async def _heartbeat_loop(self):
    while True:
        await self.session.post(
            f"{self.orchestrator_url}/workers/{self.worker_id}/heartbeat"
        )
        await asyncio.sleep(self.heartbeat_interval)
```

### 4. Watcher для зависших jobs

Watcher автоматически перемещает jobs в failed если:
- Таймаут задачи истёк
- Воркер не отвечает
- Job "завис" в промежуточном состоянии

---

## Расширение системы

### Создание своего Blueprint

```python
from avtomatika import StateMachineBlueprint

my_blueprint = StateMachineBlueprint("my_workflow")

@my_blueprint.state("init")
async def init(data, actions):
    actions.transition_to("processing")

@my_blueprint.state("processing")
async def processing(data, actions):
    actions.dispatch_task(
        task_type="my_task",
        params=data,
        transitions={"success": "done", "failure": "error"}
    )

@my_blueprint.state("done")
async def done(data, actions):
    pass  # Финальное состояние

# Регистрация
engine.register_blueprint(my_blueprint)
```

### Создание своего Worker

```python
from avtomatika_worker import Worker

worker = Worker(
    orchestrator_url="http://localhost:8000",
    worker_id="my-worker",
    worker_token="secret"
)

@worker.task("my_task")
async def handle_my_task(params):
    result = process(params)
    return {"status": "success", "data": result}

asyncio.run(worker.main())
```
