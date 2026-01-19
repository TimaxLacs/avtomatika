# Журнал изменений кода

Этот документ отслеживает все изменения, сделанные в коде проекта.

---

## 2024-XX-XX: Исправление обработки результатов задач

### Изменённые файлы

#### 1. `src/avtomatika/security.py`

**Проблема**: Middleware `worker_auth_middleware_factory` потреблял тело JSON запроса для `/tasks/result`, не сохраняя его для handler.

**Решение**: Добавлено сохранение распарсенных данных в `request["task_result_data"]`.

```python
# Было:
if not worker_id and request.path.endswith("/register"):
    try:
        cloned_request = request.clone()
        data = await cloned_request.json()
        worker_id = data.get("worker_id")
        request["worker_registration_data"] = data
    except Exception:
        return web.json_response({"error": "Invalid JSON body"}, status=400)

# Стало:
if not worker_id and (request.path.endswith("/register") or request.path.endswith("/tasks/result")):
    try:
        cloned_request = request.clone()
        data = await cloned_request.json()
        worker_id = data.get("worker_id")
        if request.path.endswith("/register"):
            request["worker_registration_data"] = data
        elif request.path.endswith("/tasks/result"):
            request["task_result_data"] = data
    except Exception:
        return web.json_response({"error": "Invalid JSON body"}, status=400)
```

#### 2. `src/avtomatika/engine.py`

**Проблема**: Handler `_task_result_handler` пытался читать уже потреблённое тело запроса.

**Решение**: Использование pre-parsed данных из middleware.

```python
# Было:
async def _task_result_handler(self, request: web.Request) -> web.Response:
    data = await request.json()
    # ...

# Стало:
async def _task_result_handler(self, request: web.Request) -> web.Response:
    data = request.get("task_result_data")
    if data is None:
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON body"}, status=400)
    # ...
```

#### 3. `local_test/orchestrator_server.py`

**Проблема**: Rate limiting блокировал heartbeat запросы при локальном тестировании.

**Решение**: Отключение rate limiting для локального тестирования.

```python
# Добавлено:
config.RATE_LIMITING_ENABLED = False
```

---

## 2024-XX-XX: Bot Runner System

### Новые файлы

#### bot_runner_worker/

| Файл | Описание |
|------|----------|
| `pyproject.toml` | Конфигурация пакета |
| `Dockerfile` | Docker образ воркера |
| `README.md` | Документация |
| `src/bot_runner_worker/__init__.py` | Инициализация пакета |
| `src/bot_runner_worker/config.py` | Конфигурация |
| `src/bot_runner_worker/container_manager.py` | Управление Docker контейнерами |
| `src/bot_runner_worker/worker.py` | Основной воркер |

#### src/avtomatika/blueprints/

| Файл | Описание |
|------|----------|
| `__init__.py` | Инициализация пакета blueprints |
| `bot_runner.py` | Blueprint для управления ботами |
| `bot_runner_validator.py` | Валидация запросов с понятными ошибками |

#### avtomatika_bot_cli/

| Файл | Описание |
|------|----------|
| `pyproject.toml` | Конфигурация пакета |
| `README.md` | Документация |
| `src/avtomatika_bot_cli/__init__.py` | Инициализация пакета |
| `src/avtomatika_bot_cli/cli.py` | CLI клиент |

#### examples/bots/

| Файл | Описание |
|------|----------|
| `echo_bot.py` | Пример простого эхо-бота |
| `multi_file_bot/bot.py` | Пример бота из нескольких файлов |
| `multi_file_bot/handlers.py` | Обработчики для multi-file бота |
| `custom_bot/Dockerfile` | Пример кастомного Dockerfile |
| `custom_bot/requirements.txt` | Зависимости кастомного бота |
| `custom_bot/bot.py` | Код кастомного бота |
| `README.md` | Документация примеров |

#### Docker и конфигурация

| Файл | Описание |
|------|----------|
| `docker-compose.bot-runner.yml` | Docker Compose для Bot Runner |
| `Dockerfile.orchestrator` | Dockerfile оркестратора с blueprint |

---

## Шаблон для новых изменений

```markdown
## YYYY-MM-DD: Описание изменений

### Изменённые файлы

#### `path/to/file.py`

**Проблема**: Описание проблемы

**Решение**: Описание решения

```python
# Было:
old_code()

# Стало:
new_code()
```

### Новые файлы

| Файл | Описание |
|------|----------|
| `path/to/new_file.py` | Что делает файл |

### Удалённые файлы

| Файл | Причина |
|------|---------|
| `path/to/old_file.py` | Почему удалён |
```
