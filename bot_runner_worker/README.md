# Bot Runner Worker

Worker для запуска Telegram ботов (и других) в изолированных Docker контейнерах.

## Установка

```bash
pip install -e .
```

## Требования

- Python 3.10+
- Docker
- Avtomatika Worker SDK

## Запуск

```bash
# Установка переменных окружения
export ORCHESTRATOR_URL=http://localhost:8000
export WORKER_TOKEN=your-worker-token
export WORKER_ID=bot-runner-1

# Запуск воркера
python -m bot_runner_worker.worker
```

## Поддерживаемые задачи

| Task Type | Описание |
|-----------|----------|
| `start_bot` | Запуск бота в контейнере |
| `stop_bot` | Остановка и удаление бота |
| `get_logs` | Получение логов бота |
| `list_bots` | Список ботов пользователя |
| `check_status` | Статус конкретного бота |

## Режимы деплоя

### Simple
Код передаётся как текст, автоматическая сборка образа.

### Custom  
Архив или Git репозиторий с Dockerfile.

### Image
Готовый Docker образ из registry.

## Конфигурация

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `DOCKER_NETWORK` | `bot_runner_network` | Имя Docker сети |
| `BASE_IMAGE` | `python:3.11-slim` | Базовый образ для Simple режима |
| `MAX_BOTS_PER_USER` | `3` | Максимум ботов на пользователя |
