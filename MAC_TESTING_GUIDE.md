# Тестирование Avtomatika на macOS

## 📋 Общий вердикт

✅ **Да, проект полностью тестируется на macOS без проблем.**

Проект спроектирован с учётом возможности тестирования без внешних зависимостей.

---

## Архитектура тестирования

### Замена внешних зависимостей на моки

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRODUCTION                                    │
├─────────────────────────────────────────────────────────────────┤
│  Redis Server  │  PostgreSQL  │  Real Workers  │  OpenTelemetry │
└────────┬───────┴───────┬──────┴───────┬────────┴───────┬────────┘
         │               │              │                │
         │    ТЕСТЫ ИСПОЛЬЗУЮТ МОКИ    │                │
         │               │              │                │
         ▼               ▼              ▼                ▼
┌────────────────┬───────────────┬─────────────┬─────────────────┐
│   fakeredis    │  NoOpHistory  │  AsyncMock  │  ConsoleExporter│
│   (in-memory)  │  Storage      │  Workers    │  (stdout)       │
└────────────────┴───────────────┴─────────────┴─────────────────┘
```

### Что используется в тестах

| Компонент | Production | Тесты |
|-----------|------------|-------|
| **State Storage** | Redis | `fakeredis` (in-memory Redis mock) |
| **History Storage** | PostgreSQL/SQLite | `NoOpHistoryStorage` (заглушка) |
| **Workers** | Реальные воркеры | `AsyncMock` / Inline handlers |
| **Tracing** | Jaeger/Zipkin | `ConsoleSpanExporter` (вывод в stdout) |
| **HTTP Client** | aiohttp | `pytest-aiohttp` test client |

---

## Зависимости для тестирования

### Установка тестовых зависимостей

```bash
# Установка всех зависимостей, включая тестовые
pip install -e ".[all,test]"

# Или только тестовые без опциональных
pip install -e ".[test]"
```

### Что устанавливается (из `pyproject.toml`)

```toml
[project.optional-dependencies]
test = [
    "pytest~=9.0",
    "pytest-asyncio~=1.1",
    "fakeredis~=2.33",          # ← In-memory Redis mock
    "pytest-aiohttp~=1.1",      # ← aiohttp test client
    "pytest-mock~=3.14",        # ← Mocking utilities
    "aioresponses~=0.7",        # ← HTTP response mocking
    "backports.zstd~=1.2",      # ← Compression testing
    "opentelemetry-instrumentation-aiohttp-client",
]
```

### Системные зависимости

Единственная **опциональная** системная зависимость — **Graphviz** (для визуализации blueprints):

```bash
# macOS (Homebrew)
brew install graphviz

# Без него тесты визуализации будут пропущены, но остальные работают
```

---

## Запуск тестов

### Основные команды

```bash
# Все тесты
pytest tests/

# С подробным выводом
pytest tests/ -v

# Конкретный файл
pytest tests/test_dispatcher.py

# Конкретный тест
pytest tests/test_integration.py::test_sub_blueprint_flow -v

# Параллельное выполнение (с pytest-xdist)
pytest tests/ -n auto

# С покрытием кода
pytest tests/ --cov=src/avtomatika --cov-report=html
```

### Маркеры тестов

```bash
# Пропустить e2e тесты (если есть)
pytest tests/ -m "not e2e"

# Только async тесты
pytest tests/ -m asyncio
```

---

## Структура тестов

### Основные тестовые файлы

```
tests/
├── conftest.py                    # Fixtures для всех тестов
├── clients.toml                   # Тестовые клиентские конфиги
├── workers.toml                   # Тестовые конфиги воркеров
├── storage_test_suite.py          # Базовый test suite для storage
│
├── test_blueprint_conditions.py   # Условные переходы в blueprints
├── test_blueprints.py             # Создание и валидация blueprints
├── test_client_config_loader.py   # Загрузка клиентских конфигов
├── test_compression.py            # Сжатие ответов (gzip, zstd)
├── test_config_validation.py      # Валидация конфигурации
├── test_context.py                # ActionFactory и контекст
├── test_dispatcher.py             # Распределение задач
├── test_dispatcher_extended.py    # Расширенные тесты диспетчера
├── test_engine.py                 # OrchestratorEngine
├── test_error_handling.py         # Обработка ошибок
├── test_executor.py               # JobExecutor
├── test_health_checker.py         # HealthChecker
├── test_history.py                # History storage
├── test_integration.py            # Интеграционные тесты
├── test_logging_config.py         # Конфигурация логирования
├── test_memory_locking.py         # Distributed locks (memory)
├── test_memory_storage.py         # MemoryStorage
├── test_metrics.py                # Prometheus метрики
├── test_noop_history.py           # NoOp history storage
├── test_postgres_history.py       # PostgreSQL history (с skip)
├── test_ratelimit.py              # Rate limiting
├── test_redis_locking.py          # Distributed locks (redis)
├── test_redis_storage.py          # RedisStorage (fakeredis)
├── test_reputation.py             # Расчёт репутации
├── test_telemetry.py              # OpenTelemetry
├── test_watcher.py                # Watcher (таймауты)
├── test_worker_config_loader.py   # Загрузка конфигов воркеров
└── test_ws_manager.py             # WebSocket manager
```

---

## Ключевые fixtures

### `conftest.py` — главные fixtures

```python
# 1. Fakeredis клиент (автоматическая очистка)
@pytest_asyncio.fixture
async def redis_client():
    client = redis.FakeRedis(decode_responses=False)
    yield client
    await client.aclose()

# 2. MemoryStorage (для простых тестов)
@pytest.fixture
def memory_storage():
    return MemoryStorage()

# 3. RedisStorage с fakeredis
@pytest.fixture
def redis_storage(redis_client):
    return RedisStorage(redis_client)

# 4. Полное приложение aiohttp (для интеграционных тестов)
@pytest_asyncio.fixture
async def app(request, config, redis_storage):
    engine = OrchestratorEngine(storage, config)
    # ... настройка blueprints ...
    yield engine.app
    await engine.on_shutdown(engine.app)

# 5. OpenTelemetry с ConsoleExporter
@pytest.fixture(scope="session", autouse=True)
def tracing_setup():
    provider = TracerProvider()
    processor = SimpleSpanProcessor(ConsoleSpanExporter(out=sys.stdout))
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
```

---

## Тестирование без внешних сервисов

### 1. Redis → fakeredis

```python
# Полностью in-memory, без реального Redis
from fakeredis import aioredis as redis

client = redis.FakeRedis(decode_responses=False)

# Поддерживает большинство Redis-команд:
# - GET, SET, DEL, EXPIRE
# - LPUSH, BRPOP, LLEN
# - ZADD, ZRANGEBYSCORE, ZREM
# - HSET, HGETALL
# - И другие...

# Ограничения fakeredis (обработаны в коде):
# - BZPOPMAX имеет fallback на ZPOPMAX
# - Lua-скрипты имеют fallback на GET/DECR
```

### 2. PostgreSQL → NoOpHistoryStorage или пропуск

```python
# NoOpHistoryStorage — заглушка, не сохраняет ничего
class NoOpHistoryStorage(HistoryStorageBase):
    async def log_job_event(self, event_data): pass
    async def log_worker_event(self, event_data): pass
    async def get_job_history(self, job_id): return []
    # ...

# PostgreSQL тесты пропускаются без реальной БД
@pytest.mark.skipif(
    not postgres_available,
    reason="PostgreSQL not available"
)
async def test_postgres_history():
    ...
```

### 3. Workers → AsyncMock

```python
from unittest.mock import AsyncMock

# Мок воркера
mock_worker = {
    "worker_id": "test-worker",
    "supported_tasks": ["test_task"],
    "status": "idle",
}

# Мок storage
mock_storage = MagicMock()
mock_storage.get_available_workers = AsyncMock(return_value=[mock_worker])
mock_storage.enqueue_task_for_worker = AsyncMock()
```

### 4. HTTP запросы → pytest-aiohttp

```python
@pytest.mark.asyncio
async def test_create_job(aiohttp_client, app):
    client = await aiohttp_client(app)
    
    resp = await client.post(
        "/api/v1/jobs/my_flow",
        json={"input": "data"},
        headers={"X-Avtomatika-Token": "token"}
    )
    assert resp.status == 202
```

---

## Пример полного интеграционного теста

```python
# tests/test_integration.py

# Создаём blueprint прямо в тесте
parent_bp = StateMachineBlueprint(
    name="parent_flow",
    api_endpoint="/jobs/parent_flow",
    api_version="v1"
)

@parent_bp.handler_for("start", is_start=True)
async def parent_start(context, actions):
    actions.transition_to("finished")

@parent_bp.handler_for("finished", is_end=True)
async def parent_finished(context, actions):
    pass

# Параметризуем fixture для добавления blueprints
@pytest.mark.parametrize(
    "app",
    [{"extra_blueprints": [parent_bp]}],
    indirect=True,
)
@pytest.mark.asyncio
async def test_job_flow(aiohttp_client, app):
    client = await aiohttp_client(app)
    storage = app[STORAGE_KEY]
    
    # Инициализируем квоту клиента
    await storage.initialize_client_quota("user_token_vip", 5)
    
    # Создаём job
    headers = {"X-Avtomatika-Token": "user_token_vip"}
    resp = await client.post("/api/v1/jobs/parent_flow", json={}, headers=headers)
    assert resp.status == 202
    job_id = (await resp.json())["job_id"]
    
    # Ждём завершения (polling)
    for _ in range(10):
        await asyncio.sleep(0.1)
        state = await storage.get_job_state(job_id)
        if state.get("current_state") == "finished":
            break
    
    assert state["current_state"] == "finished"
```

---

## Потенциальные проблемы на macOS

### 1. ❌ Проблема: `graphviz` не установлен

```
FileNotFoundError: [Errno 2] No such file or directory: 'dot'
```

**Решение:**
```bash
brew install graphviz
```

### 2. ❌ Проблема: fakeredis не поддерживает некоторые команды

```
ResponseError: unknown command `BZPOPMAX`
```

**Решение:** Уже обработано в коде — есть fallback:
```python
# В RedisStorage.dequeue_task_for_worker()
except ResponseError as e:
    if "unknown command" in str(e).lower():
        # Non-blocking fallback for tests
        res = await self._redis.zpopmax(key)
```

### 3. ❌ Проблема: Порт занят

```
OSError: [Errno 48] Address already in use
```

**Решение:** Тесты используют случайные порты через aiohttp test client.

### 4. ❌ Проблема: Медленные async тесты

**Решение:**
```bash
# Параллельное выполнение
pip install pytest-xdist
pytest tests/ -n auto
```

---

## Тестирование Worker SDK

Worker SDK (`avtomatika_worker`) также можно тестировать локально:

```bash
cd avtomatika_worker
pip install -e ".[test]"
pytest tests/
```

### Пример теста воркера

```python
from avtomatika_worker import Worker
from unittest.mock import AsyncMock
import aiohttp

@pytest.mark.asyncio
async def test_worker_task_registration():
    worker = Worker(worker_type="test-worker")
    
    @worker.task("my_task")
    async def my_handler(params, **kwargs):
        return {"status": "success", "data": {"result": params["x"] * 2}}
    
    # Проверяем регистрацию
    assert "my_task" in worker._task_handlers
    
    # Мокаем HTTP сессию
    worker._http_session = AsyncMock(spec=aiohttp.ClientSession)
    
    # Тестируем обработчик напрямую
    result = await worker._task_handlers["my_task"]["func"](
        {"x": 5}, task_id="t1", job_id="j1"
    )
    assert result["status"] == "success"
    assert result["data"]["result"] == 10
```

---

## Итоговый checklist

| Требование | Статус | Комментарий |
|------------|--------|-------------|
| Python 3.11+ | ✅ | `brew install python@3.11` |
| pip/venv | ✅ | Стандартно в Python |
| Redis | ✅ | Не нужен — fakeredis |
| PostgreSQL | ✅ | Не нужен — NoOpHistoryStorage |
| Graphviz | ⚠️ | Опционально, для визуализации |
| pytest | ✅ | Установится через `[test]` |

## Команда для быстрого старта

```bash
# 1. Клонируем и переходим
cd /Users/timax/projects/avtomatika

# 2. Создаём виртуальное окружение
python3.11 -m venv .venv
source .venv/bin/activate

# 3. Устанавливаем с тестовыми зависимостями
pip install -e ".[all,test]"

# 4. Опционально: Graphviz
brew install graphviz

# 5. Запускаем тесты
pytest tests/ -v

# 6. С покрытием
pytest tests/ --cov=src/avtomatika --cov-report=term-missing
```

---

## Заключение

Проект **Avtomatika** имеет отличную тестовую инфраструктуру и полностью тестируется на macOS:

- 🟢 **Нет зависимости от внешних сервисов** — fakeredis, NoOp storage, AsyncMock
- 🟢 **Async-first** — все тесты используют pytest-asyncio
- 🟢 **Изолированные fixtures** — каждый тест получает чистое состояние
- 🟢 **Параметризация** — легко тестировать разные blueprints
- 🟢 **100% совместимость с macOS** — нет platform-specific кода
