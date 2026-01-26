# 📦 Гайд по публикации репозиториев Avtomatika

Это руководство описывает процесс публикации трёх связанных репозиториев:

1. **avtomatika** — Orchestrator (ядро)
2. **avtomatika-bot-runner-worker** — Worker для ботов
3. **avtomatika-bot-cli** — CLI для пользователей

---

## 📋 Содержание

1. [Подготовка](#1-подготовка)
2. [Создание репозиториев на GitHub](#2-создание-репозиториев-на-github)
3. [Публикация Orchestrator](#3-публикация-orchestrator)
4. [Публикация Bot Runner Worker](#4-публикация-bot-runner-worker)
5. [Публикация CLI](#5-публикация-cli)
6. [Docker образы](#6-docker-образы)
7. [PyPI публикация](#7-pypi-публикация)
8. [Обновление ссылок](#8-обновление-ссылок)

---

## 1. Подготовка

### Установка инструментов

```bash
# GitHub CLI
brew install gh  # macOS
# или https://cli.github.com/

# Авторизация
gh auth login

# Проверка
gh auth status
```

### Структура директорий

Текущая структура:
```
avtomatika/                    # Orchestrator
├── avtomatika_bot_cli/        # CLI (будет отдельным репо)
├── bot_runner_worker/         # Worker (будет отдельным репо)
├── src/avtomatika/            # Код оркестратора
└── ...
```

---

## 2. Создание репозиториев на GitHub

### Вариант A: Через GitHub CLI

```bash
# 1. Orchestrator (основной)
gh repo create avtomatika \
  --public \
  --description "State-Machine Orchestrator for distributed workflows" \
  --license MIT

# 2. Bot Runner Worker
gh repo create avtomatika-bot-runner-worker \
  --public \
  --description "Worker for running Telegram bots in Docker containers" \
  --license MIT

# 3. CLI
gh repo create avtomatika-bot-cli \
  --public \
  --description "CLI for managing Telegram bots via Avtomatika" \
  --license MIT
```

### Вариант B: Через веб-интерфейс

1. Перейдите на https://github.com/new
2. Создайте 3 репозитория с именами:
   - `avtomatika`
   - `avtomatika-bot-runner-worker`
   - `avtomatika-bot-cli`

---

## 3. Публикация Orchestrator

### 3.1. Подготовка репозитория

```bash
cd /path/to/avtomatika

# Создаём временные копии директорий для отдельных репо
mkdir -p ../temp_repos
cp -r avtomatika_bot_cli ../temp_repos/
cp -r bot_runner_worker ../temp_repos/

# Удаляем эти директории из основного репо (они будут отдельными)
rm -rf avtomatika_bot_cli
rm -rf bot_runner_worker

# Обновляем .gitignore
echo "avtomatika_bot_cli/" >> .gitignore
echo "bot_runner_worker/" >> .gitignore
```

### 3.2. Git setup и push

```bash
# Инициализация (если ещё не сделано)
git init

# Добавляем файлы
git add .

# Коммит
git commit -m "Initial release: Avtomatika Orchestrator v1.0.0"

# Добавляем remote
git remote add origin https://github.com/YOUR_USERNAME/avtomatika.git

# Push
git push -u origin main

# Создаём тег
git tag -a v1.0.0 -m "Initial release"
git push origin v1.0.0
```

---

## 4. Публикация Bot Runner Worker

### 4.1. Создание отдельного репозитория

```bash
cd ../temp_repos/bot_runner_worker

# Инициализация
git init

# Добавляем файлы
git add .

# Коммит
git commit -m "Initial release: Bot Runner Worker v1.0.0"

# Remote
git remote add origin https://github.com/YOUR_USERNAME/avtomatika-bot-runner-worker.git

# Push
git push -u origin main

# Тег
git tag -a v1.0.0 -m "Initial release"
git push origin v1.0.0
```

### 4.2. Обновление зависимостей в pyproject.toml

```toml
[project]
name = "avtomatika-bot-runner-worker"
version = "1.0.0"
dependencies = [
    "avtomatika-worker>=1.0.0",
    "docker>=6.0.0",
]
```

---

## 5. Публикация CLI

### 5.1. Создание отдельного репозитория

```bash
cd ../temp_repos/avtomatika_bot_cli

# Инициализация
git init

# Добавляем файлы
git add .

# Коммит
git commit -m "Initial release: Avtomatika Bot CLI v1.0.0"

# Remote
git remote add origin https://github.com/YOUR_USERNAME/avtomatika-bot-cli.git

# Push
git push -u origin main

# Тег
git tag -a v1.0.0 -m "Initial release"
git push origin v1.0.0
```

### 5.2. Обновление pyproject.toml

```toml
[project]
name = "avtomatika-bot-cli"
version = "1.0.0"
dependencies = [
    "requests>=2.28.0",
    "rich>=13.0.0",
]

[project.scripts]
avtomatika-bot = "avtomatika_bot_cli.cli:main"
```

---

## 6. Docker образы

### 6.1. GitHub Container Registry (GHCR)

#### Orchestrator

```bash
cd /path/to/avtomatika

# Логин в GHCR
echo $GITHUB_TOKEN | docker login ghcr.io -u YOUR_USERNAME --password-stdin

# Сборка
docker build -t ghcr.io/YOUR_USERNAME/avtomatika:latest -f Dockerfile.orchestrator .
docker build -t ghcr.io/YOUR_USERNAME/avtomatika:v1.0.0 -f Dockerfile.orchestrator .

# Push
docker push ghcr.io/YOUR_USERNAME/avtomatika:latest
docker push ghcr.io/YOUR_USERNAME/avtomatika:v1.0.0
```

#### Bot Runner Worker

```bash
cd bot_runner_worker

# Сборка
docker build -t ghcr.io/YOUR_USERNAME/avtomatika-bot-runner-worker:latest .
docker build -t ghcr.io/YOUR_USERNAME/avtomatika-bot-runner-worker:v1.0.0 .

# Push
docker push ghcr.io/YOUR_USERNAME/avtomatika-bot-runner-worker:latest
docker push ghcr.io/YOUR_USERNAME/avtomatika-bot-runner-worker:v1.0.0
```

### 6.2. GitHub Actions для автоматической сборки

Создайте `.github/workflows/docker.yml`:

```yaml
name: Build and Push Docker

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            ghcr.io/${{ github.repository }}:latest
            ghcr.io/${{ github.repository }}:${{ github.ref_name }}
```

---

## 7. PyPI публикация

### 7.1. Подготовка

```bash
# Установка инструментов
pip install build twine

# Создание аккаунта на PyPI
# https://pypi.org/account/register/

# Создание API токена
# https://pypi.org/manage/account/token/
```

### 7.2. Сборка и публикация

```bash
# Orchestrator
cd /path/to/avtomatika
python -m build
twine upload dist/*

# CLI
cd /path/to/avtomatika-bot-cli
python -m build
twine upload dist/*

# Worker
cd /path/to/avtomatika-bot-runner-worker
python -m build
twine upload dist/*
```

### 7.3. GitHub Actions для автоматической публикации

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install build twine
      
      - name: Build
        run: python -m build
      
      - name: Publish
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: twine upload dist/*
```

---

## 8. Обновление ссылок

После публикации обновите ссылки в README файлах:

### Orchestrator README.md

```markdown
| [avtomatika](https://github.com/YOUR_USERNAME/avtomatika) | Orchestrator |
| [avtomatika-bot-runner-worker](https://github.com/YOUR_USERNAME/avtomatika-bot-runner-worker) | Bot Runner |
| [avtomatika-bot-cli](https://github.com/YOUR_USERNAME/avtomatika-bot-cli) | CLI |
```

### CLI README.md

```markdown
pip install avtomatika-bot-cli
```

### Badges

```markdown
![PyPI](https://img.shields.io/pypi/v/avtomatika)
![Downloads](https://img.shields.io/pypi/dm/avtomatika)
```

---

## 📝 Чеклист публикации

### Orchestrator (avtomatika)
- [ ] README.md обновлён
- [ ] pyproject.toml версия установлена
- [ ] LICENSE файл есть
- [ ] Git репозиторий создан
- [ ] Код запушен
- [ ] Тег создан
- [ ] Docker образ опубликован
- [ ] PyPI пакет опубликован

### Bot Runner Worker
- [ ] README.md обновлён
- [ ] pyproject.toml версия установлена
- [ ] Dockerfile готов
- [ ] Git репозиторий создан
- [ ] Код запушен
- [ ] Docker образ опубликован

### CLI
- [ ] README.md обновлён
- [ ] pyproject.toml с entry point
- [ ] Git репозиторий создан
- [ ] Код запушен
- [ ] PyPI пакет опубликован

---

## 🔧 Troubleshooting

### Docker push fails

```bash
# Проверьте авторизацию
docker login ghcr.io

# Проверьте права на пакеты в настройках репо
# Settings → Actions → General → Workflow permissions
```

### PyPI upload fails

```bash
# Проверьте имя пакета (не занято ли)
pip search avtomatika-bot-cli

# Используйте TestPyPI сначала
twine upload --repository testpypi dist/*
```

---

## 🎉 Готово!

После публикации пользователи смогут:

```bash
# Установить CLI
pip install avtomatika-bot-cli

# Запустить инфраструктуру
docker-compose -f docker-compose.bot-runner.yml up -d

# Создать бота
avtomatika-bot start my-bot --simple bot.py -r "aiogram>=3.0"
```

---

<div align="center">

**Успешной публикации! 🚀**

</div>
