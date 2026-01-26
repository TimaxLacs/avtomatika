# 🐳 Avtomatika Bot Runner Worker

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Required-2496ED?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

**Воркер для запуска и управления Telegram-ботами в Docker-контейнерах**

[Установка](#-установка) •
[Конфигурация](#️-конфигурация) •
[Архитектура](#-архитектура) •
[API](#-api)

</div>

---

## ✨ Возможности

- 🐳 **Docker-изоляция**: каждый бот в отдельном контейнере
- 🔄 **Три режима деплоя**: Simple, Custom (Dockerfile/Git), Image
- 📊 **Мониторинг**: логи, статусы, события контейнеров
- 🛡️ **Безопасность**: лимиты ресурсов, изоляция сети
- 🔗 **Avtomatika SDK**: интеграция с оркестратором

---

## 📦 Установка

### Docker (рекомендуется)

```bash
docker pull ghcr.io/YOUR_USERNAME/avtomatika-bot-runner-worker:latest

docker run -d \
  --name bot-runner-worker \
  -e ORCHESTRATOR_URL=http://orchestrator:8000 \
  -e WORKER_TOKEN=your-worker-token \
  -e WORKER_ID=bot-runner-1 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  ghcr.io/YOUR_USERNAME/avtomatika-bot-runner-worker:latest
```

### Из исходников

```bash
git clone https://github.com/YOUR_USERNAME/avtomatika-bot-runner-worker.git
cd avtomatika-bot-runner-worker
pip install -e .
```

---

## ⚙️ Конфигурация

### Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `ORCHESTRATOR_URL` | URL оркестратора Avtomatika | `http://localhost:8000` |
| `WORKER_TOKEN` | Токен аутентификации воркера | — (обязательно) |
| `WORKER_ID` | Уникальный ID воркера | `bot-runner-{uuid}` |
| `WORKER_TYPE` | Тип воркера | `bot-runner` |
| `MAX_BOTS_PER_USER` | Лимит ботов на пользователя | `3` |
| `BOT_MAX_RUNTIME_HOURS` | Макс. время работы бота (часы) | `24` |
| `DOCKER_NETWORK` | Docker-сеть для ботов | `avtomatika_bot_network` |
| `CONTAINER_MEMORY_LIMIT` | Лимит RAM | `256m` |
| `CONTAINER_CPU_LIMIT` | Лимит CPU | `0.5` |

### Пример `.env`

```env
ORCHESTRATOR_URL=http://orchestrator:8000
WORKER_TOKEN=secure-worker-token-12345
WORKER_ID=bot-runner-prod-1
MAX_BOTS_PER_USER=3
BOT_MAX_RUNTIME_HOURS=24
DOCKER_NETWORK=avtomatika_bots
CONTAINER_MEMORY_LIMIT=256m
CONTAINER_CPU_LIMIT=0.5
```

---

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                    Bot Runner Worker                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │   Worker    │  │  Container   │  │  Docker Events   │   │
│  │   (SDK)     │◀─│   Manager    │◀─│    Listener      │   │
│  └──────┬──────┘  └──────┬───────┘  └──────────────────┘   │
│         │                │                                  │
│         ▼                ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  Docker Engine                       │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐             │   │
│  │  │  Bot 1  │  │  Bot 2  │  │  Bot 3  │   ...       │   │
│  │  │Container│  │Container│  │Container│             │   │
│  │  └─────────┘  └─────────┘  └─────────┘             │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────┐
              │   Avtomatika Orchestrator │
              └───────────────────────────┘
```

---

## 📡 API (Task Types)

Worker регистрирует следующие типы задач:

### `start_bot`

Запуск нового бота.

```json
{
  "user_id": "user123",
  "bot_id": "my-bot",
  "deployment_mode": "simple",
  "code": "import aiogram...",
  "requirements": ["aiogram>=3.0"],
  "entrypoint": "bot.py",
  "env_vars": {"BOT_TOKEN": "123:ABC"}
}
```

**Режимы деплоя:**

| Режим | Параметры |
|-------|-----------|
| `simple` | `code` или `files`, `requirements`, `entrypoint` |
| `custom` | `git_repo` + `git_branch` или `archive`/`archive_url` |
| `image` | `docker_image`, `registry_auth` (опционально) |

### `stop_bot`

Остановка бота.

```json
{
  "user_id": "user123",
  "bot_id": "my-bot"
}
```

### `get_logs`

Получение логов.

```json
{
  "user_id": "user123",
  "bot_id": "my-bot",
  "lines": 100
}
```

### `list_bots`

Список ботов пользователя.

```json
{
  "user_id": "user123"
}
```

### `check_status`

Статус конкретного бота.

```json
{
  "user_id": "user123",
  "bot_id": "my-bot"
}
```

---

## 🐳 Docker Compose

### Полный стек

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 3

  orchestrator:
    image: ghcr.io/YOUR_USERNAME/avtomatika:latest
    ports:
      - "8000:8000"
    environment:
      - REDIS_HOST=redis
      - CLIENT_TOKEN=your-client-token
      - GLOBAL_WORKER_TOKEN=your-worker-token
    depends_on:
      redis:
        condition: service_healthy

  bot-runner-worker:
    image: ghcr.io/YOUR_USERNAME/avtomatika-bot-runner-worker:latest
    environment:
      - ORCHESTRATOR_URL=http://orchestrator:8000
      - WORKER_TOKEN=your-worker-token
      - WORKER_ID=bot-runner-1
      - MAX_BOTS_PER_USER=3
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    depends_on:
      - orchestrator

networks:
  default:
    driver: bridge
  bot_network:
    name: avtomatika_bot_network
    driver: bridge
```

---

## 📁 Структура проекта

```
bot_runner_worker/
├── src/
│   └── bot_runner_worker/
│       ├── __init__.py
│       ├── config.py           # Конфигурация
│       ├── container_manager.py # Управление Docker
│       └── worker.py           # Основной воркер
├── Dockerfile
├── pyproject.toml
└── README.md
```

---

## 🔗 Связанные репозитории

| Компонент | Описание | Репозиторий |
|-----------|----------|-------------|
| **Orchestrator** | Ядро системы Avtomatika | [avtomatika](https://github.com/YOUR_USERNAME/avtomatika) |
| **CLI** | Командная строка для пользователей | [avtomatika-bot-cli](https://github.com/YOUR_USERNAME/avtomatika-bot-cli) |
| **Worker SDK** | SDK для создания воркеров | [avtomatika-worker](https://github.com/YOUR_USERNAME/avtomatika-worker) |

---

## 🛡️ Безопасность

- **Изоляция контейнеров**: каждый бот в отдельной сети
- **Лимиты ресурсов**: RAM, CPU на контейнер
- **Автоостановка**: боты останавливаются через 24 часа
- **Лимит на пользователя**: максимум 3 бота

---

## 📄 Лицензия

MIT License

---

<div align="center">

**[⬆ Наверх](#-avtomatika-bot-runner-worker)**

Made with ❤️ for Avtomatika

</div>
