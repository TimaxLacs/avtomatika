<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/docker-24.0+-blue.svg" alt="Docker 24.0+">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="MIT License">
  <img src="https://img.shields.io/badge/status-alpha-orange.svg" alt="Alpha">
</p>

<h1 align="center">🤖 Avtomatika Bot Runner</h1>

<p align="center">
  <strong>Платформа для запуска Telegram ботов в изолированных Docker контейнерах</strong>
</p>

<p align="center">
  <a href="#-быстрый-старт">Быстрый старт</a> •
  <a href="#-возможности">Возможности</a> •
  <a href="#-архитектура">Архитектура</a> •
  <a href="#-команды-cli">CLI</a> •
  <a href="#-документация">Документация</a>
</p>

---

## 📋 Обзор

**Avtomatika Bot Runner** — система для развёртывания и управления Telegram ботами с полной изоляцией через Docker. Поддерживает три режима деплоя: от простого кода до готовых Docker образов.

```bash
# Запустить бота из файла — одна команда
avtomatika-bot start my-bot --simple bot.py -r "aiogram>=3.0" -e BOT_TOKEN=123:ABC
```

## ✨ Возможности

| Функция | Описание |
|---------|----------|
| 🚀 **Три режима деплоя** | Simple (код), Custom (Dockerfile), Image (готовый образ) |
| 🔒 **Изоляция** | Каждый бот в отдельном Docker контейнере |
| 📊 **Мониторинг** | Логи, статусы, автоматическое отслеживание падений |
| ⚡ **CLI** | Удобные команды для управления ботами |
| 🔄 **Обновления** | Обновление бота без простоя |
| 📦 **Лимиты** | Квоты на ресурсы (RAM, CPU, количество ботов) |

## 🏗️ Архитектура

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│             │     │             │     │             │     │             │
│     CLI     │────►│ Оркестратор │────►│   Worker    │────►│   Docker    │
│             │     │             │     │             │     │             │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                           │                   │
                           ▼                   ▼
                    ┌─────────────┐     ┌─────────────┐
                    │    Redis    │     │  Containers │
                    └─────────────┘     └─────────────┘
```

**Компоненты:**
- **CLI** (`avtomatika-bot`) — командная строка для пользователей
- **Оркестратор** — координирует работу, валидирует запросы
- **Worker** — управляет Docker контейнерами
- **Redis** — хранит состояния и очереди

## 🚀 Быстрый старт

### Требования

- Python 3.10+
- Docker 24.0+
- Redis (опционально)

### Установка

```bash
# Клонирование
git clone https://github.com/your-username/avtomatika.git
cd avtomatika

# Виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Установка
pip install -e ".[redis]"
cd bot_runner_worker && pip install -e . && cd ..
cd avtomatika_bot_cli && pip install -e . && cd ..
```

### Запуск системы

```bash
# С Docker Compose (рекомендуется)
docker-compose -f docker-compose.bot-runner.yml up -d

# Или вручную
python local_test/orchestrator_server.py  # Терминал 1
python -m bot_runner_worker.worker        # Терминал 2
```

### Первый бот

```bash
# Настройка
export AVTOMATIKA_TOKEN=test-client-token

# Запуск бота
avtomatika-bot start echo-bot --simple examples/bots/echo_bot.py \
  -r "aiogram>=3.0" \
  -e BOT_TOKEN=your_telegram_token

# Проверка
avtomatika-bot list
avtomatika-bot logs echo-bot

# Остановка
avtomatika-bot stop echo-bot
```

## 💻 Команды CLI

### Запуск бота

```bash
# Simple режим — код как файлы
avtomatika-bot start <bot_id> --simple <files...> [options]

# Custom режим — директория с Dockerfile
avtomatika-bot start <bot_id> --custom <path>
avtomatika-bot start <bot_id> --git <repo_url>

# Image режим — готовый Docker образ
avtomatika-bot start <bot_id> --image <image:tag>
```

### Управление

```bash
avtomatika-bot list                  # Список ботов
avtomatika-bot status <bot_id>       # Статус бота
avtomatika-bot logs <bot_id>         # Логи
avtomatika-bot logs <bot_id> -f      # Логи в реальном времени
avtomatika-bot update <bot_id> ...   # Обновить код
avtomatika-bot stop <bot_id>         # Остановить
```

### Опции

| Опция | Описание |
|-------|----------|
| `-e KEY=VALUE` | Переменная окружения |
| `-r REQUIREMENTS` | Зависимости (файл или список) |
| `--entrypoint FILE` | Точка входа |
| `--branch BRANCH` | Git ветка |
| `-v, --verbose` | Подробный вывод |

## 📂 Структура проекта

```
avtomatika/
├── src/avtomatika/           # Оркестратор
│   ├── blueprints/           # Blueprints (bot_runner)
│   ├── storage/              # Хранилище (Redis, Memory)
│   └── ...
├── bot_runner_worker/        # Worker для Docker
│   └── src/bot_runner_worker/
│       ├── worker.py
│       └── container_manager.py
├── avtomatika_bot_cli/       # CLI клиент
│   └── src/avtomatika_bot_cli/
│       └── cli.py
├── examples/bots/            # Примеры ботов
├── docs/                     # Документация
│   ├── guides/               # Руководства
│   └── plans/                # Планы разработки
└── local_test/               # Локальное тестирование
```

## 📚 Документация

### Руководства

| Документ | Описание |
|----------|----------|
| [Testing Guide](docs/guides/TESTING_GUIDE.md) | Полное руководство по тестированию |
| [Bot Runner How It Works](docs/guides/BOT_RUNNER_HOW_IT_WORKS.md) | Как работает система |
| [Worker Integration](docs/guides/WORKER_INTEGRATION_GUIDE.md) | Интеграция своих воркеров |
| [Internals Deep Dive](docs/guides/INTERNALS_DEEP_DIVE.md) | Внутреннее устройство |
| [Mac Testing](docs/guides/MAC_TESTING_GUIDE.md) | Тестирование на macOS |

### Планы и спецификации

| Документ | Описание |
|----------|----------|
| [Docker Bot Runner Plan](docs/plans/DOCKER_BOT_RUNNER_PLAN.md) | Архитектура Bot Runner |
| [Bot Runner Use Cases](docs/plans/BOT_RUNNER_USE_CASES.md) | Сценарии использования |
| [Parser System Plan](docs/plans/PARSER_SYSTEM_PLAN.md) | План парсера VK/Telegram |
| [Local Test Plan](docs/plans/LOCAL_TEST_PLAN.md) | План локального тестирования |

### Cookbook

- [Creating a Blueprint](docs/cookbook/creating_a_blueprint.md)
- [Creating a Worker](docs/cookbook/creating_a_worker.md)
- [Advanced Topics](docs/cookbook/advanced_topics.md)

## ⚙️ Конфигурация

### Переменные окружения

```bash
# CLI
AVTOMATIKA_URL=http://localhost:8000
AVTOMATIKA_TOKEN=your-token

# Оркестратор
REDIS_HOST=localhost
REDIS_PORT=6379
CLIENT_TOKEN=client-token
GLOBAL_WORKER_TOKEN=worker-token

# Worker
ORCHESTRATOR_URL=http://localhost:8000
WORKER_TOKEN=worker-token
MAX_BOTS_PER_USER=3
```

### Лимиты по умолчанию

| Параметр | Значение |
|----------|----------|
| Память | 256 MB |
| CPU | 0.5 cores |
| Макс. ботов | 3 на пользователя |
| Время работы | 24 часа |

## 🧪 Тестирование

```bash
# Unit тесты
pytest

# С покрытием
pytest --cov=src/avtomatika

# Локальное тестирование
python local_test/orchestrator_server.py  # Терминал 1
python local_test/worker_client.py        # Терминал 2
bash local_test/test_requests.sh          # Терминал 3
```

## 🔧 Режимы деплоя

### Simple — для простых ботов

```bash
# Один файл
avtomatika-bot start bot1 --simple bot.py -r "aiogram>=3.0" -e BOT_TOKEN=...

# Несколько файлов
avtomatika-bot start bot2 --simple bot.py handlers.py -r "aiogram>=3.0" -e BOT_TOKEN=...

# Директория
avtomatika-bot start bot3 --simple ./my_bot/ --entrypoint main.py -r requirements.txt -e BOT_TOKEN=...
```

### Custom — для сложных проектов

```bash
# Локальная директория с Dockerfile
avtomatika-bot start bot4 --custom ./my_project/ -e BOT_TOKEN=...

# Git репозиторий
avtomatika-bot start bot5 --git https://github.com/user/bot.git -e BOT_TOKEN=...
```

### Image — готовые образы

```bash
# Публичный образ
avtomatika-bot start bot6 --image myuser/telegram-bot:v1 -e BOT_TOKEN=...

# Приватный registry
avtomatika-bot start bot7 --image ghcr.io/user/bot:latest \
  --registry-user user --registry-pass token \
  -e BOT_TOKEN=...
```

## 📝 Примеры ботов

```python
# examples/bots/echo_bot.py
import os
import asyncio
from aiogram import Bot, Dispatcher, types

bot = Bot(token=os.environ["BOT_TOKEN"])
dp = Dispatcher()

@dp.message()
async def echo(message: types.Message):
    await message.answer(f"Echo: {message.text}")

asyncio.run(dp.start_polling(bot))
```

Больше примеров в [examples/bots/](examples/bots/).

## 🤝 Контрибьютинг

1. Fork репозитория
2. Создайте ветку (`git checkout -b feature/amazing`)
3. Commit изменений (`git commit -m 'Add amazing feature'`)
4. Push в ветку (`git push origin feature/amazing`)
5. Откройте Pull Request

## 📄 Лицензия

MIT License. См. [LICENSE](LICENSE).

---

<p align="center">
  Made with ❤️ by Avtomatika Team
</p>
