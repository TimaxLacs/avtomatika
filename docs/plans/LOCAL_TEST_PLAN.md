# План локального тестирования

Этот документ описывает пошаговый план для локального тестирования взаимодействия воркера и оркестратора.

## Обзор

```
┌─────────────┐     HTTP      ┌─────────────┐
│             │ ◄──────────── │             │
│ Orchestrator│               │   Worker    │
│  :8000      │ ──────────►   │             │
└─────────────┘               └─────────────┘
      ▲
      │ HTTP
      │
┌─────────────┐
│   Client    │
│  (curl/CLI) │
└─────────────┘
```

## Файлы для тестирования

```
local_test/
├── orchestrator_server.py   # Минимальный оркестратор
├── worker_client.py         # Минимальный воркер
└── test_requests.sh         # Тестовые запросы
```

## Пошаговая инструкция

### 1. Подготовка окружения

```bash
# Создаём виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Устанавливаем зависимости
pip install -e ".[all]"
cd avtomatika_worker && pip install -e . && cd ..
```

### 2. Запуск оркестратора

```bash
# Терминал 1
source venv/bin/activate
python local_test/orchestrator_server.py
```

Ожидаемый вывод:
```
==================================================
Orchestrator is running on http://localhost:8000
==================================================

Registered blueprints:
  - test_workflow

Auth tokens:
  - Client token: test-client-token
  - Worker token: test-worker-token
...
```

### 3. Запуск воркера

```bash
# Терминал 2
source venv/bin/activate
python local_test/worker_client.py
```

Ожидаемый вывод:
```
==================================================
Starting worker: test-worker-xxx
Orchestrator URL: http://localhost:8000
==================================================

Registered task handlers:
  - process_data
...
```

### 4. Отправка тестового запроса

```bash
# Терминал 3
bash local_test/test_requests.sh
```

Или вручную:

```bash
# Создаём job
curl -X POST http://localhost:8000/jobs \
  -H "Authorization: Bearer test-client-token" \
  -H "Content-Type: application/json" \
  -d '{
    "blueprint": "test_workflow",
    "data": {"input": "Hello, World!"}
  }'

# Ответ:
# {"job_id": "abc123...", "state": "init", ...}

# Проверяем статус (несколько раз)
curl -X GET http://localhost:8000/jobs/abc123... \
  -H "Authorization: Bearer test-client-token"

# Когда state = "completed":
# {"job_id": "abc123...", "state": "completed", "data": {...}}
```

## Ожидаемый workflow

1. **Клиент** создаёт job (`POST /jobs`)
2. **Оркестратор** создаёт job в state "init"
3. **Executor** запускает handler для state "init"
4. Handler вызывает `dispatch_task()` — создаётся задача
5. **Воркер** получает задачу (`GET /workers/{id}/tasks`)
6. **Воркер** выполняет задачу (обработчик `process_data`)
7. **Воркер** отправляет результат (`POST /tasks/result`)
8. **Оркестратор** получает результат, переходит в state "completed"
9. **Клиент** видит `state: "completed"` при запросе статуса

## Логи

### Оркестратор

```
INFO - [Job abc123] Init state - dispatching task to worker
DEBUG - Task dispatched: task_id=xyz789, type=process_data
INFO - Task result received: task_id=xyz789, status=success
INFO - [Job abc123] Completed! Task result: {...}
```

### Воркер

```
INFO - Worker registered successfully
DEBUG - Polling for tasks...
INFO - [Task] Processing data for job abc123
INFO - [Task] Payload: Hello, World!
INFO - [Task] Completed processing for job abc123
DEBUG - Task result submitted: task_id=xyz789
```

## Возможные проблемы

### 1. Connection refused

**Симптом**: Воркер не может подключиться к оркестратору

**Решение**: Убедитесь что оркестратор запущен и слушает на порту 8000

### 2. 401 Unauthorized

**Симптом**: Запросы отклоняются с ошибкой авторизации

**Решение**: Проверьте что используете правильные токены:
- Client: `test-client-token`
- Worker: `test-worker-token`

### 3. 429 Too Many Requests

**Симптом**: Heartbeat или другие запросы блокируются

**Решение**: Rate limiting отключён в `orchestrator_server.py`. Если проблема остаётся, проверьте `config.RATE_LIMITING_ENABLED = False`

### 4. Job остаётся в "init"

**Симптом**: Job не переходит в следующее состояние

**Решение**: 
- Проверьте что воркер запущен и зарегистрирован
- Проверьте логи на ошибки
- Убедитесь что воркер поддерживает нужный task_type

## API Reference

### POST /jobs
Создание job
```json
{
  "blueprint": "test_workflow",
  "data": {"input": "value"}
}
```

### GET /jobs/{job_id}
Получение статуса job

### POST /workers/register
Регистрация воркера (автоматически)

### GET /workers/{worker_id}/tasks
Получение задач воркером

### POST /tasks/result
Отправка результата задачи
```json
{
  "job_id": "...",
  "task_id": "...",
  "worker_id": "...",
  "result": {
    "status": "success",
    "data": {...}
  }
}
```
