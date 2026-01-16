# История изменений кода

Этот документ содержит все изменения, внесённые в код проекта Avtomatika.

---

## 2026-01-12: Исправление бага с отправкой результатов задач

### Проблема
Worker успешно выполнял задачи, но Orchestrator отклонял результаты с ошибкой **400 Bad Request**. Также heartbeats блокировались rate limiter'ом (429 Too Many Requests).

### Причины
1. **Баг в `security.py`**: Middleware читал JSON body для аутентификации воркера, но не сохранял данные для `/tasks/result` endpoint. Handler пытался повторно прочитать уже "съеденный" body.
2. **Агрессивный rate limiting**: По умолчанию 5 запросов за 60 секунд — слишком мало для heartbeats.

### Изменения

#### 1. `src/avtomatika/security.py`

**Было:**
```python
if not worker_id and (request.path.endswith("/register") or request.path.endswith("/tasks/result")):
    try:
        cloned_request = request.clone()
        data = await cloned_request.json()
        worker_id = data.get("worker_id")
        # Attach the parsed data to the request so the handler doesn't need to re-parse
        if request.path.endswith("/register"):
            request["worker_registration_data"] = data
    except Exception:
        return web.json_response({"error": "Invalid JSON body"}, status=400)
```

**Стало:**
```python
if not worker_id and (request.path.endswith("/register") or request.path.endswith("/tasks/result")):
    try:
        cloned_request = request.clone()
        data = await cloned_request.json()
        worker_id = data.get("worker_id")
        # Attach the parsed data to the request so the handler doesn't need to re-parse
        if request.path.endswith("/register"):
            request["worker_registration_data"] = data
        elif request.path.endswith("/tasks/result"):
            request["task_result_data"] = data  # <-- ДОБАВЛЕНО
    except Exception:
        return web.json_response({"error": "Invalid JSON body"}, status=400)
```

#### 2. `src/avtomatika/engine.py`

**Было:**
```python
async def _task_result_handler(self, request: web.Request) -> web.Response:
    import logging

    try:
        data = await request.json()
        job_id = data.get("job_id")
        task_id = data.get("task_id")
        result = data.get("result", {})
        result_status = result.get("status", "success")
        error_message = result.get("error")
        payload_worker_id = data.get("worker_id")
    except Exception:
        return web.json_response({"error": "Invalid JSON body"}, status=400)
```

**Стало:**
```python
async def _task_result_handler(self, request: web.Request) -> web.Response:
    import logging

    # Use pre-parsed data from middleware if available, otherwise read the body
    data = request.get("task_result_data")
    if data is None:
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON body"}, status=400)

    job_id = data.get("job_id")
    task_id = data.get("task_id")
    result = data.get("result", {})
    result_status = result.get("status", "success")
    error_message = result.get("error")
    payload_worker_id = data.get("worker_id")
```

#### 3. `local_test/orchestrator_server.py`

**Добавлено:**
```python
config.RATE_LIMITING_ENABLED = False  # Отключаем для локального тестирования
```

---

## 2026-01-12: Merge с upstream (origin/main)

### Действие
Выполнен merge с оригинальным репозиторием для получения обновлений:
- Beta 6: Native Distributed Scheduler and Global Timezone Support
- Beta 5: Reliability, Redis Streams, and Concurrency Control
- Beta 4: Interactive API Docs and Configuration Specs

### Конфликты и разрешение

#### `src/avtomatika/engine.py`

**Конфликт:** Различия в `_task_result_handler`:
- Локальная версия: использовала pre-parsed data из middleware
- Upstream версия: использовала константы `TASK_STATUS_SUCCESS` и `json_response` helper

**Решение:** Объединены оба подхода:
- Сохранена логика с pre-parsed data (исправление бага)
- Использованы константы и helper-функции из upstream

**Итоговый код:**
```python
async def _task_result_handler(self, request: web.Request) -> web.Response:
    import logging

    # Use pre-parsed data from middleware if available, otherwise read the body
    data = request.get("task_result_data")
    if data is None:
        try:
            data = await request.json(loads=loads)
        except Exception:
            return json_response({"error": "Invalid JSON body"}, status=400)

    job_id = data.get("job_id")
    task_id = data.get("task_id")
    result = data.get("result", {})
    result_status = result.get("status", TASK_STATUS_SUCCESS)  # Используем константу
    error_message = result.get("error")
    payload_worker_id = data.get("worker_id")
```

### Новые файлы из upstream
- `docs/` — документация API, архитектура, конфигурация
- `src/avtomatika/constants.py` — константы для статусов
- `src/avtomatika/scheduler.py` — планировщик задач
- `src/avtomatika/scheduler_config_loader.py` — загрузка конфигурации планировщика

---

## Созданные файлы для локального тестирования

### `local_test/orchestrator_server.py`
Минимальный сервер оркестратора для локального тестирования.

### `local_test/worker_client.py`
Минимальный клиент воркера с двумя тестовыми задачами:
- `echo_task` — повторяет сообщение N раз
- `failing_task` — всегда возвращает ошибку (для тестирования)

### `local_test/test_requests.sh`
Скрипт с curl-командами для тестирования API.

---

## Шаблон для новых изменений

```markdown
## YYYY-MM-DD: Краткое описание изменения

### Проблема
Описание проблемы

### Причины
Почему это произошло

### Изменения

#### `путь/к/файлу.py`

**Было:**
\`\`\`python
старый код
\`\`\`

**Стало:**
\`\`\`python
новый код
\`\`\`
```
