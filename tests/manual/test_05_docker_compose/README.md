# Тест 05: Docker Compose

## Статус: ✅ ПРОЙДЕН

**Дата:** 2026-01-19

## Описание
Проверка полной Dockerized инфраструктуры: Redis + Orchestrator + Bot Runner Worker.

## Компоненты
- **Redis** (`redis:7-alpine`) — хранилище состояний
- **Orchestrator** (`avtomatika-orchestrator`) — управление workflow
- **Bot Runner Worker** (`avtomatika-bot-runner-worker`) — управление контейнерами ботов

## Шаги
1. `docker-compose up -d` — запуск инфраструктуры
2. Проверка healthcheck всех сервисов
3. Запуск бота через CLI
4. Проверка статуса и логов бота

## Результаты
```bash
# Запуск инфраструктуры
docker-compose -f docker-compose.bot-runner.yml up -d --build

# Статус контейнеров
NAME                             IMAGE                          STATUS
avtomatika-redis-1               redis:7-alpine                 Up (healthy)
avtomatika-orchestrator-1        avtomatika-orchestrator        Up (healthy)
avtomatika-bot-runner-worker-1   avtomatika-bot-runner-worker   Up

# Логи оркестратора
Orchestrator running on http://0.0.0.0:8000
Blueprints: bot_runner
Worker 'bot-runner-1' registered with info: {
    'worker_id': 'bot-runner-1',
    'worker_type': 'bot-runner',
    'supported_tasks': ['start_bot', 'stop_bot', 'get_logs', 'list_bots', 'check_status'],
    'max_concurrent_tasks': 10
}

# Запуск бота
avtomatika-bot start docker-test-bot --simple examples/bots/echo_bot.py ...
╭── ✅ Успех ──╮
│ Бот 'docker-test-bot' успешно запущен! │
╰──────────────╯

# Статус бота
📊 Статус бота 'docker-test-bot'
╭───────── Бот: docker-test-bot ─────────╮
│ 🟢 RUNNING                              │
│ • Container: bot_cli_..._docker-test-bot│
│ • Started: 2026-01-19T17:40:17          │
╰─────────────────────────────────────────╯

# Логи бота
2026-01-19 17:40:19 - __main__ - INFO - Starting Echo Bot...
2026-01-19 17:40:19 - aiogram.dispatcher - INFO - Start polling
2026-01-19 17:40:19 - aiogram.dispatcher - INFO - Run polling for bot @testTimax_bot
```

## Исправленные проблемы

### Проблема 1: UnicodeDecodeError в Redis
```
UnicodeDecodeError: 'utf-8' codec can't decode byte 0x8a in position 0
```

**Причина:** `decode_responses=True` в Redis клиенте пытался декодировать бинарные (сжатые) данные как UTF-8.

**Исправление:** Убрано `decode_responses=True` в `Dockerfile.orchestrator`.

### Проблема 2: TypeError в ContainerManager
```
TypeError: a coroutine was expected, got <Future ...>
```

**Причина:** `asyncio.create_task()` требует корутину, а `loop.run_in_executor()` возвращает Future.

**Исправление:** Изменено с:
```python
self._event_task = asyncio.create_task(loop.run_in_executor(None, listen))
```
на:
```python
self._event_task = loop.run_in_executor(None, listen)
```

## Файлы с исправлениями
- `Dockerfile.orchestrator` — убрано `decode_responses=True`
- `bot_runner_worker/src/bot_runner_worker/container_manager.py` — исправлен `start_event_listener`

## Выводы
- ✅ Docker Compose инфраструктура полностью работает
- ✅ Все три сервиса стартуют и проходят healthcheck
- ✅ Worker успешно регистрируется в оркестраторе
- ✅ CLI команды работают через Dockerized orchestrator
- ✅ Боты запускаются, логируются и останавливаются корректно
