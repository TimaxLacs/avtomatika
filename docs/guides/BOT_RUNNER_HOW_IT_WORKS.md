# Как работает Bot Runner

Подробное описание того, как работает система Bot Runner.

## Содержание

1. [Обзор системы](#обзор-системы)
2. [Компоненты](#компоненты)
3. [Поток данных](#поток-данных)
4. [Режимы деплоя](#режимы-деплоя)
5. [Жизненный цикл бота](#жизненный-цикл-бота)
6. [Безопасность](#безопасность)
7. [Лимиты и квоты](#лимиты-и-квоты)
8. [Конфигурация](#конфигурация)
9. [Структура файлов](#структура-файлов)
10. [Быстрый старт](#быстрый-старт)

---

## Обзор системы

Bot Runner — это система для запуска пользовательских Telegram ботов в изолированных Docker контейнерах. Она построена на архитектуре Avtomatika (оркестратор + воркеры).

### Ключевые особенности

- **Три режима деплоя**: Simple (код), Custom (Dockerfile), Image (готовый образ)
- **Полная изоляция**: Каждый бот работает в отдельном Docker контейнере
- **Лимиты ресурсов**: Память, CPU, время работы
- **Простой CLI**: Удобные команды для управления ботами
- **Понятные ошибки**: Детальные сообщения с подсказками

---

## Компоненты

### 1. CLI клиент (`avtomatika_bot_cli`)

Командная строка для пользователей:

```
avtomatika-bot start/stop/logs/list/status
```

**Функции:**
- Чтение файлов с кодом
- Создание архивов
- Отправка запросов в оркестратор
- Красивый вывод результатов

### 2. Оркестратор + Blueprint (`src/avtomatika/blueprints/bot_runner.py`)

Обрабатывает запросы и координирует работу:

```
init → start_bot/stop_bot/get_logs → completed/failed
```

**Функции:**
- Валидация запросов
- Маршрутизация по действиям
- Диспатч задач воркеру
- Обработка результатов

### 3. Bot Runner Worker (`bot_runner_worker`)

Управляет Docker контейнерами:

**Задачи:**
- `start_bot` — сборка образа и запуск контейнера
- `stop_bot` — остановка и удаление контейнера
- `get_logs` — получение логов
- `list_bots` — список ботов пользователя
- `check_status` — статус конкретного бота

### 4. ContainerManager

Обёртка над Docker API:

```python
class ContainerManager:
    def build_simple_image()    # Сборка из кода
    def build_custom_image()    # Сборка из архива/Git
    def pull_image()            # Скачивание готового образа
    def start_container()       # Запуск контейнера
    def stop_container()        # Остановка контейнера
    def get_logs()              # Получение логов
    def list_user_bots()        # Список ботов
```

---

## Поток данных

### Запуск бота (Simple режим)

```
┌─────────┐    ┌───────────────┐    ┌───────────────┐    ┌────────────┐
│  CLI    │───►│  Оркестратор  │───►│    Worker     │───►│   Docker   │
│         │    │               │    │               │    │            │
│ bot.py  │    │ POST /jobs    │    │ start_bot     │    │ Container  │
│ req.txt │    │ blueprint:    │    │               │    │            │
│         │    │ bot_runner    │    │ build_image() │    │            │
└─────────┘    └───────────────┘    │ start()       │    └────────────┘
                                    └───────────────┘
```

**Подробно:**

1. **CLI** читает файл `bot.py`
2. **CLI** отправляет POST /jobs:
   ```json
   {
     "blueprint": "bot_runner",
     "data": {
       "action": "start",
       "bot_id": "my-bot",
       "deployment_mode": "simple",
       "code": "import os\nfrom aiogram...",
       "requirements": ["aiogram>=3.0"],
       "env_vars": {"BOT_TOKEN": "..."}
     }
   }
   ```
3. **Оркестратор** валидирует запрос через `bot_runner_validator`
4. **Оркестратор** создаёт Job и dispatches task `start_bot`
5. **Worker** получает задачу
6. **ContainerManager** создаёт временную директорию:
   ```
   /tmp/xxx/
   ├── bot.py         (код из запроса)
   ├── requirements.txt
   └── Dockerfile     (сгенерирован)
   ```
7. **Docker** собирает образ
8. **Docker** запускает контейнер
9. **Worker** возвращает результат
10. **Оркестратор** завершает Job
11. **CLI** показывает результат

---

## Режимы деплоя

### Simple

**Когда использовать:** Простые боты, быстрые тесты

**Что отправляется:**
- Код как текст (`code` или `files`)
- Список зависимостей (`requirements`)
- Точка входа (`entrypoint`)

**Что происходит:**
1. Создаётся временная директория
2. Записывается код
3. Генерируется Dockerfile:
   ```dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY . .
   CMD ["python", "bot.py"]
   ```
4. Собирается образ
5. Запускается контейнер

### Custom

**Когда использовать:** Боты с системными зависимостями, сложная структура

**Что отправляется:**
- Архив или Git URL
- Переменные окружения

**Что происходит:**
1. Скачивается/распаковывается архив или клонируется репозиторий
2. Ищется Dockerfile
3. Собирается образ
4. Запускается контейнер

### Image

**Когда использовать:** Готовые Docker образы, CI/CD

**Что отправляется:**
- Имя образа (`docker_image`)
- Авторизация для registry (опционально)
- Переменные окружения

**Что происходит:**
1. Скачивается образ
2. Запускается контейнер

---

## Жизненный цикл бота

```
                    ┌──────────┐
                    │  start   │
                    └────┬─────┘
                         │
            ┌────────────┼────────────┐
            │            │            │
            ▼            ▼            ▼
      ┌──────────┐ ┌──────────┐ ┌──────────┐
      │  simple  │ │  custom  │ │  image   │
      │  build   │ │  build   │ │  pull    │
      └────┬─────┘ └────┬─────┘ └────┬─────┘
            │            │            │
            └────────────┼────────────┘
                         │
                         ▼
                   ┌──────────┐
                   │  running │◄─────────┐
                   └────┬─────┘          │
                        │                │
            ┌───────────┼───────────┐    │
            │           │           │    │
            ▼           ▼           ▼    │
      ┌──────────┐ ┌──────────┐ ┌────────┴─┐
      │  stop    │ │  crash   │ │ timeout  │
      │ (manual) │ │ (auto)   │ │ (24h)    │
      └────┬─────┘ └────┬─────┘ └────┬─────┘
            │           │            │
            └───────────┼────────────┘
                        │
                        ▼
                   ┌──────────┐
                   │ stopped/ │
                   │ removed  │
                   └──────────┘
```

### Состояния

| Состояние | Описание |
|-----------|----------|
| `start` | Инициация запуска |
| `building` | Сборка образа |
| `pulling` | Скачивание образа |
| `running` | Бот работает |
| `stopped` | Остановлен вручную |
| `crashed` | Упал с ошибкой |
| `timeout` | Превышено время работы |

---

## Безопасность

### Изоляция контейнеров

```python
container = docker.containers.run(
    image,
    network="bot_runner_network",  # Изолированная сеть
    security_opt=["no-new-privileges:true"],
    cap_drop=["ALL"],
    cap_add=["NET_BIND_SERVICE"],
)
```

### Защита от path traversal

```python
for member in tar.getmembers():
    abs_path = os.path.abspath(os.path.join(extract_path, member.name))
    if not abs_path.startswith(os.path.abspath(extract_path)):
        raise ValueError("Path traversal detected!")
```

### Секреты

Все секреты передаются через переменные окружения:
- Не хранятся в образах
- Не логируются
- Изолированы между контейнерами

---

## Лимиты и квоты

### Ресурсы контейнера

| Ресурс | Лимит | Описание |
|--------|-------|----------|
| Память | 256 MB | `--memory=256m` |
| CPU | 0.5 cores | `--cpus=0.5` |
| PIDs | 100 | `--pids-limit=100` |

### Квоты пользователя

| Квота | Значение |
|-------|----------|
| Максимум ботов | 3 |
| Время работы | 24 часа |

### Проверка квоты

```python
current_bots = container_manager.count_user_bots(user_id)
if current_bots >= config.max_bots_per_user:
    return {
        "status": "failure",
        "error": {
            "code": "QUOTA_EXCEEDED",
            "message": f"Maximum {config.max_bots_per_user} bots"
        }
    }
```

---

## Конфигурация

### Переменные окружения

#### Оркестратор

```env
REDIS_HOST=localhost
REDIS_PORT=6379
CLIENT_TOKEN=your-client-token
GLOBAL_WORKER_TOKEN=your-worker-token
```

#### Worker

```env
ORCHESTRATOR_URL=http://localhost:8000
WORKER_TOKEN=your-worker-token
WORKER_ID=bot-runner-1
DOCKER_NETWORK=bot_runner_network
MAX_BOTS_PER_USER=3
BASE_IMAGE=python:3.11-slim
```

#### CLI

```env
AVTOMATIKA_URL=http://localhost:8000
AVTOMATIKA_TOKEN=your-client-token
```

---

## Структура файлов

```
avtomatika/
├── bot_runner_worker/              # Worker для запуска ботов
│   ├── src/bot_runner_worker/
│   │   ├── __init__.py
│   │   ├── config.py               # Конфигурация
│   │   ├── container_manager.py    # Управление Docker
│   │   └── worker.py               # Обработчики задач
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── README.md
│
├── avtomatika_bot_cli/             # CLI клиент
│   ├── src/avtomatika_bot_cli/
│   │   ├── __init__.py
│   │   └── cli.py                  # Команды CLI
│   ├── pyproject.toml
│   └── README.md
│
├── src/avtomatika/blueprints/      # Blueprints оркестратора
│   ├── __init__.py
│   ├── bot_runner.py               # Blueprint для ботов
│   └── bot_runner_validator.py     # Валидация с подсказками
│
├── examples/bots/                  # Примеры ботов
│   ├── echo_bot.py                 # Простой эхо-бот
│   ├── multi_file_bot/             # Бот из нескольких файлов
│   └── custom_bot/                 # Бот с Dockerfile
│
├── docker-compose.bot-runner.yml   # Docker Compose
└── Dockerfile.orchestrator         # Dockerfile оркестратора
```

---

## Быстрый старт

### 1. Установка

```bash
# Клонирование
git clone <repo>
cd avtomatika

# Виртуальное окружение
python -m venv venv
source venv/bin/activate

# Установка пакетов
pip install -e ".[redis]"
cd bot_runner_worker && pip install -e . && cd ..
cd avtomatika_bot_cli && pip install -e . && cd ..
```

### 2. Запуск через Docker Compose

```bash
docker-compose -f docker-compose.bot-runner.yml up
```

### 3. Использование CLI

```bash
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

### 4. Пример бота

```python
# bot.py
import os
import asyncio
from aiogram import Bot, Dispatcher, types

bot = Bot(token=os.environ["BOT_TOKEN"])
dp = Dispatcher()

@dp.message()
async def echo(message: types.Message):
    await message.answer(f"You said: {message.text}")

asyncio.run(dp.start_polling(bot))
```

```bash
avtomatika-bot start my-echo --simple bot.py \
  -r "aiogram>=3.0" \
  -e BOT_TOKEN=123:ABC...
```

---

## FAQ

### Почему бот не запускается?

1. Проверьте логи: `avtomatika-bot logs <bot_id>`
2. Проверьте токен бота
3. Убедитесь что зависимости указаны правильно

### Как передать несколько файлов?

```bash
avtomatika-bot start my-bot --simple bot.py handlers.py utils.py \
  --entrypoint bot.py \
  -r "aiogram>=3.0"
```

### Как использовать кастомный Dockerfile?

```bash
avtomatika-bot start my-bot --custom ./my_project/
```

Убедитесь что в директории есть `Dockerfile`.

### Как использовать готовый образ?

```bash
avtomatika-bot start my-bot --image ghcr.io/user/bot:v1 \
  -e BOT_TOKEN=...
```

### Сколько ботов можно запустить?

По умолчанию 3 бота на пользователя. Лимит настраивается через `MAX_BOTS_PER_USER`.

### Как долго работает бот?

По умолчанию 24 часа. После этого контейнер автоматически останавливается.
