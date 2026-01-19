# Гайд по тестированию Bot Runner System

Полное руководство по тестированию системы развёртывания ботов.

---

## Содержание

1. [Обзор системы](#1-обзор-системы)
2. [Схема работы](#2-схема-работы)
3. [Подготовка к тестированию](#3-подготовка-к-тестированию)
4. [Тестирование без Docker](#4-тестирование-без-docker)
5. [Тестирование с Docker](#5-тестирование-с-docker)
6. [Сценарии тестирования](#6-сценарии-тестирования)
7. [Базовые функции](#7-базовые-функции)
8. [Чеклист тестирования](#8-чеклист-тестирования)

---

## 1. Обзор системы

### Компоненты

```
┌─────────────────────────────────────────────────────────────────────┐
│                         КОМПОНЕНТЫ СИСТЕМЫ                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐        │
│  │     CLI      │     │ Оркестратор  │     │    Worker    │        │
│  │              │     │              │     │              │        │
│  │ avtomatika-  │────►│  Blueprint   │────►│  Container   │        │
│  │ bot          │     │  Validator   │     │  Manager     │        │
│  └──────────────┘     └──────────────┘     └──────────────┘        │
│                                                   │                 │
│                                                   ▼                 │
│                                            ┌──────────────┐        │
│                                            │    Docker    │        │
│                                            │  Containers  │        │
│                                            └──────────────┘        │
└─────────────────────────────────────────────────────────────────────┘
```

### Файловая структура

```
avtomatika/
├── avtomatika_bot_cli/          # CLI клиент
│   └── src/avtomatika_bot_cli/
│       └── cli.py
├── bot_runner_worker/           # Worker для Docker
│   └── src/bot_runner_worker/
│       ├── worker.py
│       └── container_manager.py
├── src/avtomatika/blueprints/   # Blueprints оркестратора
│   ├── bot_runner.py
│   └── bot_runner_validator.py
├── examples/bots/               # Примеры ботов
├── local_test/                  # Локальное тестирование
└── docker-compose.bot-runner.yml
```

---

## 2. Схема работы

### Поэтапный процесс запуска бота

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ЭТАП 1: ЗАПРОС ОТ ПОЛЬЗОВАТЕЛЯ                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Пользователь запускает CLI:                                        │
│                                                                      │
│  $ avtomatika-bot start my-bot --simple bot.py \                    │
│      -r "aiogram>=3.0" \                                            │
│      -e BOT_TOKEN=123:ABC                                           │
│                                                                      │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    ЭТАП 2: CLI ОБРАБОТКА                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  CLI выполняет:                                                      │
│  1. Читает файл bot.py                                              │
│  2. Парсит requirements                                             │
│  3. Парсит env vars                                                 │
│  4. Формирует JSON запрос                                           │
│  5. Отправляет POST /jobs в оркестратор                             │
│                                                                      │
│  {                                                                   │
│    "blueprint": "bot_runner",                                        │
│    "data": {                                                         │
│      "action": "start",                                              │
│      "bot_id": "my-bot",                                            │
│      "deployment_mode": "simple",                                    │
│      "code": "import os\nfrom aiogram...",                          │
│      "requirements": ["aiogram>=3.0"],                              │
│      "env_vars": {"BOT_TOKEN": "123:ABC"}                           │
│    }                                                                 │
│  }                                                                   │
│                                                                      │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    ЭТАП 3: ОРКЕСТРАТОР                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  3.1 Валидация запроса (bot_runner_validator.py):                   │
│      ├── Проверка action (start/stop/logs/list/status)              │
│      ├── Проверка bot_id (формат, длина)                            │
│      ├── Проверка deployment_mode (simple/custom/image)             │
│      └── Проверка обязательных полей для режима                     │
│                                                                      │
│  3.2 Blueprint обработка (bot_runner.py):                           │
│      ├── State: init → валидация → маршрутизация                    │
│      ├── State: start_bot → dispatch_task("start_bot", params)      │
│      └── State: bot_started → completed                             │
│                                                                      │
│  3.3 Dispatcher:                                                     │
│      └── Отправляет задачу в очередь Worker'а                       │
│                                                                      │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    ЭТАП 4: BOT RUNNER WORKER                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  4.1 Получение задачи из очереди                                    │
│                                                                      │
│  4.2 Проверка квоты пользователя:                                   │
│      └── count_user_bots(user_id) < max_bots_per_user?              │
│                                                                      │
│  4.3 Подготовка образа (зависит от режима):                         │
│      ├── Simple: build_simple_image()                               │
│      ├── Custom: build_custom_image()                               │
│      └── Image: pull_image()                                        │
│                                                                      │
│  4.4 Запуск контейнера:                                             │
│      └── start_container(image, env_vars, limits)                   │
│                                                                      │
│  4.5 Возврат результата оркестратору                                │
│                                                                      │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    ЭТАП 5: DOCKER                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  5.1 Сборка образа (Simple режим):                                  │
│      ├── Создание временной директории                              │
│      ├── Запись кода в файлы                                        │
│      ├── Генерация Dockerfile                                       │
│      └── docker build                                               │
│                                                                      │
│  5.2 Запуск контейнера:                                             │
│      docker run --name bot_user_mybot \                             │
│        --memory=256m --cpus=0.5 \                                   │
│        -e BOT_TOKEN=123:ABC \                                       │
│        --network=bot_runner_network \                               │
│        bot_image_user_mybot:latest                                  │
│                                                                      │
│  5.3 Бот работает в изолированном контейнере                        │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Режимы деплоя

```
┌─────────────────────────────────────────────────────────────────────┐
│                         РЕЖИМЫ ДЕПЛОЯ                                │
├─────────────────┬─────────────────┬─────────────────────────────────┤
│     SIMPLE      │     CUSTOM      │           IMAGE                  │
├─────────────────┼─────────────────┼─────────────────────────────────┤
│                 │                 │                                  │
│  Код как текст  │  Dockerfile     │  Готовый образ                  │
│       │         │  + исходники    │       │                         │
│       ▼         │       │         │       ▼                         │
│  Генерация      │       ▼         │  docker pull                    │
│  Dockerfile     │  docker build   │       │                         │
│       │         │       │         │       │                         │
│       ▼         │       ▼         │       ▼                         │
│  docker build   │    Образ        │    Образ                        │
│       │         │       │         │       │                         │
│       ▼         │       ▼         │       ▼                         │
│    Образ        │  docker run     │  docker run                     │
│       │         │       │         │       │                         │
│       ▼         │       ▼         │       ▼                         │
│  docker run     │  Контейнер      │  Контейнер                      │
│       │         │                 │                                  │
│       ▼         │                 │                                  │
│  Контейнер      │                 │                                  │
│                 │                 │                                  │
└─────────────────┴─────────────────┴─────────────────────────────────┘
```

---

## 3. Подготовка к тестированию

### Системные требования

| Компонент | Минимум | Рекомендуется |
|-----------|---------|---------------|
| Python | 3.10 | 3.11+ |
| Docker | 20.10+ | 24.0+ |
| RAM | 2 GB | 4 GB |
| Диск | 5 GB | 10 GB |

### Установка зависимостей

```bash
# 1. Перейти в директорию проекта
cd ~/projects/avtomatika

# 2. Активировать виртуальное окружение
source venv/bin/activate

# 3. Установить основной пакет
pip install -e ".[redis]"

# 4. Установить Worker
cd bot_runner_worker && pip install -e . && cd ..

# 5. Установить CLI
cd avtomatika_bot_cli && pip install -e . && cd ..

# 6. Проверить установку
avtomatika-bot --help
```

### Переменные окружения

```bash
# Для CLI
export AVTOMATIKA_URL=http://localhost:8000
export AVTOMATIKA_TOKEN=test-client-token

# Для Worker
export ORCHESTRATOR_URL=http://localhost:8000
export WORKER_TOKEN=test-worker-token
export WORKER_ID=bot-runner-1

# Для тестового бота
export BOT_TOKEN=your_telegram_bot_token
```

---

## 4. Тестирование без Docker

Когда Docker недоступен, можно тестировать компоненты отдельно.

### 4.1 Тестирование оркестратора + воркера

```bash
# Терминал 1: Оркестратор
cd ~/projects/avtomatika
source venv/bin/activate
python local_test/orchestrator_server.py
```

```bash
# Терминал 2: Воркер
cd ~/projects/avtomatika
source venv/bin/activate
python local_test/worker_client.py
```

```bash
# Терминал 3: Тестовые запросы
bash local_test/test_requests.sh
```

### 4.2 Тестирование валидатора

```python
# test_validator.py
from src.avtomatika.blueprints.bot_runner_validator import validate_bot_request, ValidationError

# Тест 1: Успешная валидация
try:
    validate_bot_request({
        "action": "start",
        "bot_id": "my-bot",
        "deployment_mode": "simple",
        "code": "print('hello')",
        "requirements": ["aiogram>=3.0"]
    })
    print("✅ Валидация пройдена")
except ValidationError as e:
    print(f"❌ Ошибка: {e.message}")

# Тест 2: Ошибка - отсутствует action
try:
    validate_bot_request({"bot_id": "test"})
except ValidationError as e:
    print(f"✅ Ожидаемая ошибка: {e.code}")

# Тест 3: Ошибка - неверный режим
try:
    validate_bot_request({
        "action": "start",
        "bot_id": "test",
        "deployment_mode": "invalid"
    })
except ValidationError as e:
    print(f"✅ Ожидаемая ошибка: {e.code}")
```

### 4.3 Тестирование бота напрямую

```bash
# Запуск бота без системы
cd ~/projects/avtomatika
source venv/bin/activate
BOT_TOKEN=your_token python examples/bots/echo_bot.py
```

---

## 5. Тестирование с Docker

### 5.1 Запуск полной системы

```bash
# Запуск всех сервисов
docker-compose -f docker-compose.bot-runner.yml up -d

# Проверка статуса
docker-compose -f docker-compose.bot-runner.yml ps

# Логи
docker-compose -f docker-compose.bot-runner.yml logs -f
```

### 5.2 Проверка компонентов

```bash
# Проверка Redis
docker exec -it avtomatika-redis-1 redis-cli ping
# Ожидаемый ответ: PONG

# Проверка оркестратора
curl http://localhost:8000/health
# Ожидаемый ответ: {"status": "ok"}

# Проверка воркера (через логи)
docker-compose -f docker-compose.bot-runner.yml logs bot-runner-worker
```

### 5.3 Использование CLI

```bash
export AVTOMATIKA_TOKEN=test-client-token

# Запуск бота (Simple режим)
avtomatika-bot start echo-bot --simple examples/bots/echo_bot.py \
  -r "aiogram>=3.0" \
  -e BOT_TOKEN=your_token

# Проверка списка
avtomatika-bot list

# Логи бота
avtomatika-bot logs echo-bot

# Остановка
avtomatika-bot stop echo-bot
```

---

## 6. Сценарии тестирования

### Сценарий 1: Simple режим - один файл

```bash
# Подготовка
cat > /tmp/test_bot.py << 'EOF'
import os
import asyncio
from aiogram import Bot, Dispatcher, types

bot = Bot(token=os.environ["BOT_TOKEN"])
dp = Dispatcher()

@dp.message()
async def echo(m: types.Message):
    await m.answer(f"Echo: {m.text}")

asyncio.run(dp.start_polling(bot))
EOF

# Запуск
avtomatika-bot start test1 --simple /tmp/test_bot.py \
  -r "aiogram>=3.0" \
  -e BOT_TOKEN=your_token

# Проверка
avtomatika-bot status test1
avtomatika-bot logs test1

# Очистка
avtomatika-bot stop test1
```

### Сценарий 2: Simple режим - несколько файлов

```bash
# Запуск из директории
avtomatika-bot start multi-bot \
  --simple examples/bots/multi_file_bot/ \
  --entrypoint bot.py \
  -r "aiogram>=3.0" \
  -e BOT_TOKEN=your_token

# Проверка
avtomatika-bot list
```

### Сценарий 3: Custom режим - директория с Dockerfile

```bash
# Запуск
avtomatika-bot start custom-bot \
  --custom examples/bots/custom_bot/ \
  -e BOT_TOKEN=your_token

# Проверка сборки
avtomatika-bot logs custom-bot -n 200
```

### Сценарий 4: Custom режим - Git репозиторий

```bash
# Запуск из Git
avtomatika-bot start git-bot \
  --git https://github.com/user/telegram-bot.git \
  --branch main \
  -e BOT_TOKEN=your_token
```

### Сценарий 5: Image режим

```bash
# Запуск из готового образа
avtomatika-bot start image-bot \
  --image python:3.11-slim \
  -e BOT_TOKEN=your_token
```

### Сценарий 6: Проверка лимитов

```bash
# Запуск 3 ботов (максимум)
for i in 1 2 3; do
  avtomatika-bot start bot-$i --simple /tmp/test_bot.py \
    -r "aiogram>=3.0" \
    -e BOT_TOKEN=your_token
done

# Попытка запустить 4-й (должна быть ошибка)
avtomatika-bot start bot-4 --simple /tmp/test_bot.py \
  -r "aiogram>=3.0" \
  -e BOT_TOKEN=your_token
# Ожидаемо: QUOTA_EXCEEDED

# Проверка списка
avtomatika-bot list

# Очистка
for i in 1 2 3; do
  avtomatika-bot stop bot-$i
done
```

### Сценарий 7: Ошибки валидации

```bash
# Отсутствует deployment_mode
curl -X POST http://localhost:8000/jobs \
  -H "Authorization: Bearer test-client-token" \
  -H "Content-Type: application/json" \
  -d '{"blueprint": "bot_runner", "data": {"action": "start", "bot_id": "test"}}'
# Ожидаемо: MISSING_REQUIRED_FIELD с hint и example

# Неверный формат bot_id
curl -X POST http://localhost:8000/jobs \
  -H "Authorization: Bearer test-client-token" \
  -H "Content-Type: application/json" \
  -d '{"blueprint": "bot_runner", "data": {"action": "start", "bot_id": "тест бот!", "deployment_mode": "simple"}}'
# Ожидаемо: INVALID_BOT_ID
```

---

## 7. Базовые функции

### CLI команды

| Команда | Описание | Пример |
|---------|----------|--------|
| `start` | Запуск бота | `avtomatika-bot start my-bot --simple bot.py` |
| `stop` | Остановка | `avtomatika-bot stop my-bot` |
| `logs` | Просмотр логов | `avtomatika-bot logs my-bot -n 50` |
| `list` | Список ботов | `avtomatika-bot list` |
| `status` | Статус бота | `avtomatika-bot status my-bot` |

### API эндпоинты

| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | `/jobs` | Создать задачу (start/stop/logs/list) |
| GET | `/jobs/{id}` | Статус задачи |
| POST | `/workers/register` | Регистрация воркера |
| GET | `/workers/{id}/tasks` | Получить задачи |
| POST | `/tasks/result` | Отправить результат |

### Коды ошибок

| Код | Описание |
|-----|----------|
| `MISSING_REQUIRED_FIELD` | Отсутствует обязательное поле |
| `INVALID_ACTION` | Неверное действие |
| `INVALID_BOT_ID` | Неверный формат bot_id |
| `INVALID_DEPLOYMENT_MODE` | Неверный режим деплоя |
| `MISSING_CODE` | Не указан код для Simple режима |
| `MISSING_SOURCE` | Не указан источник для Custom режима |
| `QUOTA_EXCEEDED` | Превышен лимит ботов |
| `CONTAINER_ERROR` | Ошибка Docker |

---

## 8. Чеклист тестирования

### Подготовка

- [ ] Python 3.10+ установлен
- [ ] Виртуальное окружение создано
- [ ] Зависимости установлены
- [ ] Docker установлен и запущен (опционально)
- [ ] Telegram бот токен получен

### Компоненты

- [ ] Оркестратор запускается
- [ ] Воркер регистрируется
- [ ] Redis доступен (если используется)
- [ ] CLI работает

### Simple режим

- [ ] Один файл - работает
- [ ] Несколько файлов - работает
- [ ] Директория - работает
- [ ] Requirements устанавливаются
- [ ] Env vars передаются

### Custom режим

- [ ] Локальная директория - работает
- [ ] Git репозиторий - работает
- [ ] Архив URL - работает
- [ ] Dockerfile найден и используется

### Image режим

- [ ] Публичный образ - работает
- [ ] Приватный registry - работает

### Управление

- [ ] list показывает ботов
- [ ] status показывает статус
- [ ] logs показывает логи
- [ ] stop останавливает бота

### Лимиты

- [ ] Квота ботов работает
- [ ] Memory limit применяется
- [ ] CPU limit применяется

### Ошибки

- [ ] Валидация возвращает понятные ошибки
- [ ] Hint и example присутствуют
- [ ] Ошибки Docker обрабатываются

---

## Быстрый старт

```bash
# 1. Подготовка
cd ~/projects/avtomatika
source venv/bin/activate

# 2. Без Docker - тестовый бот напрямую
BOT_TOKEN=your_token python examples/bots/echo_bot.py

# 3. С Docker - полная система
docker-compose -f docker-compose.bot-runner.yml up -d
export AVTOMATIKA_TOKEN=test-client-token
avtomatika-bot start echo --simple examples/bots/echo_bot.py \
  -r "aiogram>=3.0" -e BOT_TOKEN=your_token
avtomatika-bot list
avtomatika-bot logs echo
avtomatika-bot stop echo
```

---

*Последнее обновление: Январь 2026*
