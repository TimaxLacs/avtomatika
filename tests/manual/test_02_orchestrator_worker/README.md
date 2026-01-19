# Тест 02: Orchestrator + Worker

## Информация

| Параметр | Значение |
|----------|----------|
| Статус | ✅ PASSED |
| Дата | 2026-01-18 |
| Время | ~06:05 |

## Описание

Проверка полного цикла взаимодействия оркестратора и воркера:
- Создание Job через API
- Отправка задачи воркеру (dispatch)
- Выполнение задачи воркером
- Получение результата оркестратором
- Переход в состояние completed

## Компоненты

- **Оркестратор**: http://localhost:8000
- **Воркер**: test-worker-*
- **Blueprint**: test_workflow
- **API Endpoint**: POST /api/jobs/test

## Команды запуска

```bash
# Терминал 1 - Оркестратор
cd ~/projects/avtomatika
source venv/bin/activate
python local_test/orchestrator_server.py

# Терминал 2 - Воркер
cd ~/projects/avtomatika
source venv/bin/activate
python -u local_test/worker_client.py

# Терминал 3 - Тестовый запрос
curl -X POST http://localhost:8000/api/jobs/test \
  -H "X-Avtomatika-Token: test-client-token" \
  -H "Content-Type: application/json" \
  -d '{"input": "Test message"}'
```

## Логи оркестратора

### Запуск
```
Orchestrator is running on http://localhost:8000
Registered blueprints:
  - test_workflow
Auth tokens:
  - Client token: test-client-token
  - Worker token: test-worker-token
```

### Регистрация воркера
```
Worker 'test-worker-b0c70b75' registered with info: {
  'worker_id': 'test-worker-b0c70b75',
  'worker_type': 'test-processor',
  'supported_tasks': ['process_data'],
  'max_concurrent_tasks': 5
}
```

### Диспетчеризация задачи
```
Job 31c0f6fe-650e-4c67-9a15-641ec32266b7 dispatching task: {
  'type': 'process_data',
  'params': {'job_id': '...', 'payload': 'SUCCESS TEST!'},
  'transitions': {'success': 'completed', 'failure': 'failed'}
}
Found 1 available workers
Dispatching task 'process_data' to worker test-worker-b0c70b75 (strategy: default)
Task successfully enqueued for worker
```

## Логи воркера

```
Main started
Starting comm task
Starting polling task
Registering worker
Worker registered
Polling started
[Task] Processing data for job 31c0f6fe-650e-4c67-9a15-641ec32266b7
[Task] Payload: SUCCESS TEST!
[Task] Completed processing for job 31c0f6fe-650e-4c67-9a15-641ec32266b7
```

## Результат Job

```json
{
    "id": "31c0f6fe-650e-4c67-9a15-641ec32266b7",
    "blueprint_name": "test_workflow",
    "current_state": "completed",
    "initial_data": {
        "input": "SUCCESS TEST!"
    },
    "state_history": {
        "processed_payload": "SUCCESS TEST!",
        "worker_id": "test-worker-b0c70b75",
        "message": "Data processed successfully!"
    },
    "status": "running"
}
```

## Результаты проверок

| Проверка | Результат |
|----------|-----------|
| Оркестратор запустился на :8000 | ✅ |
| Воркер зарегистрировался | ✅ |
| Job создался | ✅ |
| Задача отправлена воркеру | ✅ |
| Воркер выполнил задачу | ✅ |
| Результат получен | ✅ |
| Job перешёл в completed | ✅ |

## Исправленные баги

1. **telemetry.py** - `NoOpTraceContextTextMapPropagator` не вызывался как класс
2. **executor.py** - `tracer` не был определён в fallback case
3. **security.py** - `task_result_data` не сохранялся для middleware
4. **engine.py** - `TASK_STATUS_SUCCESS` не был импортирован

## Выводы

Полный цикл оркестратор-воркер работает корректно:
1. API принимает запросы с аутентификацией
2. Blueprint обрабатывает состояния
3. Dispatcher находит и выбирает воркера
4. Воркер получает и выполняет задачи
5. Результаты возвращаются в Job
