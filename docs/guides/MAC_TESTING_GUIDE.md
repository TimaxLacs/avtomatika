# Тестирование Avtomatika на macOS

Этот документ описывает, как протестировать оркестратор и воркер на macOS.

## Требования

- macOS 10.15+ (Catalina или новее)
- Python 3.10+ (рекомендуется 3.11)
- Redis (для production тестирования)
- Docker (для Bot Runner)

## Установка зависимостей

### 1. Homebrew (если не установлен)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Добавьте в ~/.zshrc или ~/.bash_profile:
eval "$(/opt/homebrew/bin/brew shellenv)"
```

### 2. Python

```bash
brew install python@3.11
```

### 3. Redis (опционально)

```bash
brew install redis
brew services start redis
```

### 4. Docker (для Bot Runner)

Скачайте и установите [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/).

## Настройка проекта

### 1. Клонирование репозитория

```bash
git clone <repository_url>
cd avtomatika
```

### 2. Создание виртуального окружения

```bash
python3.11 -m venv venv
source venv/bin/activate
```

### 3. Установка зависимостей

```bash
# Основной пакет (оркестратор)
pip install -e ".[all]"

# Worker SDK
cd avtomatika_worker
pip install -e ".[test]"
cd ..

# Bot Runner Worker (опционально)
cd bot_runner_worker
pip install -e .
cd ..

# CLI (опционально)
cd avtomatika_bot_cli
pip install -e .
cd ..
```

## Локальное тестирование

### 1. Запуск оркестратора

```bash
# Терминал 1
source venv/bin/activate
python local_test/orchestrator_server.py
```

### 2. Запуск воркера

```bash
# Терминал 2
source venv/bin/activate
python local_test/worker_client.py
```

### 3. Отправка тестового запроса

```bash
# Терминал 3
bash local_test/test_requests.sh
```

Или вручную:

```bash
curl -X POST http://localhost:8000/jobs \
  -H "Authorization: Bearer test-client-token" \
  -H "Content-Type: application/json" \
  -d '{
    "blueprint": "test_workflow",
    "data": {"input": "Hello, World!"}
  }'
```

## Запуск тестов

```bash
# Все тесты
pytest

# С подробным выводом
pytest -v

# Конкретный файл
pytest tests/test_engine.py

# С покрытием
pytest --cov=src/avtomatika
```

## Bot Runner (Docker)

### Запуск через Docker Compose

```bash
docker-compose -f docker-compose.bot-runner.yml up
```

### Использование CLI

```bash
export AVTOMATIKA_TOKEN=test-client-token

# Запуск бота
avtomatika-bot start echo-bot --simple examples/bots/echo_bot.py \
    -r "aiogram>=3.0" \
    -e BOT_TOKEN=your_token

# Список ботов
avtomatika-bot list

# Остановка
avtomatika-bot stop echo-bot
```

## Возможные проблемы

### 1. "zsh: command not found: python3.11"

Добавьте Homebrew в PATH:
```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zshrc
source ~/.zshrc
```

### 2. Конфликт зависимостей python-json-logger

Установите конкретную версию:
```bash
pip install "python-json-logger~=4.0"
```

### 3. Redis не запущен

```bash
brew services start redis
# или используйте MemoryStorage в local_test/orchestrator_server.py
```

### 4. Docker не работает

Убедитесь что Docker Desktop запущен и работает:
```bash
docker ps
```

## Полезные команды

```bash
# Проверка версии Python
python --version

# Проверка установленных пакетов
pip list | grep avtomatika

# Проверка Redis
redis-cli ping

# Проверка Docker
docker info
```
