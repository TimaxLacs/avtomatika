# План Docker Bot Runner

Подробный план реализации гибкой системы запуска ботов в Docker контейнерах.

## Содержание

1. [Обзор](#обзор)
2. [Архитектура](#архитектура)
3. [Режимы деплоя](#режимы-деплоя)
4. [Передача данных](#передача-данных)
5. [Управление контейнерами](#управление-контейнерами)
6. [Безопасность](#безопасность)
7. [Лимиты](#лимиты)
8. [API](#api)
9. [CLI клиент](#cli-клиент)
10. [План реализации](#план-реализации)

---

## Обзор

Bot Runner — система для запуска пользовательских ботов в изолированных Docker контейнерах.

### Цели

- **Гибкость**: поддержка разных способов деплоя (код, архив, образ)
- **Изоляция**: каждый бот в отдельном контейнере
- **Простота**: удобный CLI для пользователей
- **Безопасность**: лимиты ресурсов, изоляция сети

### Не-цели

- Оркестрация множества инстансов (используйте Kubernetes)
- Персистентное хранилище (боты должны быть stateless или использовать внешние БД)
- Автоматическое масштабирование

---

## Архитектура

```
┌─────────────────────────────────────────────────────────────────────┐
│                          ПОЛЬЗОВАТЕЛЬ                                │
│                                                                      │
│  ┌──────────────┐                                                   │
│  │  CLI Client  │  avtomatika-bot start/stop/logs/list              │
│  └──────┬───────┘                                                   │
└─────────┼───────────────────────────────────────────────────────────┘
          │ HTTP
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         ОРКЕСТРАТОР                                  │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │  Bot Runner  │  │   Validator  │  │  Dispatcher  │              │
│  │  Blueprint   │  │              │  │              │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└─────────┬───────────────────────────────────────────────────────────┘
          │ Task Queue
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      BOT RUNNER WORKER                               │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   Worker     │  │  Container   │  │   Docker     │              │
│  │   Handlers   │  │  Manager     │  │   Client     │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└─────────┬───────────────────────────────────────────────────────────┘
          │ Docker API
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      DOCKER КОНТЕЙНЕРЫ                               │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │  Bot 1       │  │  Bot 2       │  │  Bot 3       │              │
│  │  (user_a)    │  │  (user_a)    │  │  (user_b)    │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Режимы деплоя

### 1. Simple режим

Для простых ботов. Код передаётся как текст.

**Входные данные:**
```json
{
  "deployment_mode": "simple",
  "code": "import os\nfrom aiogram import Bot...",
  "entrypoint": "bot.py",
  "requirements": ["aiogram>=3.0", "aiohttp"],
  "env_vars": {"BOT_TOKEN": "123:ABC"}
}
```

**Или несколько файлов:**
```json
{
  "deployment_mode": "simple",
  "files": {
    "bot.py": "import os\nfrom handlers import...",
    "handlers.py": "from aiogram import..."
  },
  "entrypoint": "bot.py",
  "requirements": ["aiogram>=3.0"]
}
```

**Что происходит:**
1. Создаётся временная директория
2. Записываются файлы
3. Генерируется Dockerfile
4. Собирается образ
5. Запускается контейнер

### 2. Custom режим

Для ботов с кастомным Dockerfile.

**Источники:**
- Директория с Dockerfile (через CLI)
- tar.gz архив (base64)
- URL на архив
- Git репозиторий

**Входные данные (Git):**
```json
{
  "deployment_mode": "custom",
  "git_repo": "https://github.com/user/bot.git",
  "git_branch": "main",
  "env_vars": {"BOT_TOKEN": "123:ABC"}
}
```

**Что происходит:**
1. Клонируется репозиторий / скачивается архив
2. Находится Dockerfile
3. Собирается образ
4. Запускается контейнер

### 3. Image режим

Для готовых Docker образов.

**Входные данные:**
```json
{
  "deployment_mode": "image",
  "docker_image": "ghcr.io/user/bot:v1.0",
  "registry_auth": {
    "username": "user",
    "password": "token"
  },
  "env_vars": {"BOT_TOKEN": "123:ABC"}
}
```

**Что происходит:**
1. Скачивается образ (с авторизацией если нужно)
2. Запускается контейнер

---

## Передача данных

### CLI → Оркестратор

CLI читает файлы и отправляет их содержимое:

```python
# Один файл
data = {"code": open("bot.py").read()}

# Директория
files = {}
for f in Path("./project").rglob("*"):
    if f.is_file():
        files[str(f.relative_to("./project"))] = f.read_text()
data = {"files": files}

# Архив (для custom режима)
data = {"archive": base64.b64encode(tar_gz_bytes).decode()}
```

### Оркестратор → Worker

Данные передаются через стандартный механизм dispatch_task:

```python
actions.dispatch_task(
    task_type="start_bot",
    params={
        "user_id": "...",
        "bot_id": "...",
        "deployment_mode": "simple",
        "code": "...",
        "requirements": [...],
        "env_vars": {...}
    }
)
```

---

## Управление контейнерами

### ContainerManager

```python
class ContainerManager:
    def __init__(self):
        self.docker_client = docker.from_env()
    
    async def build_simple_image(self, user_id, bot_id, code, requirements):
        """Сборка образа из кода."""
        pass
    
    async def build_custom_image(self, user_id, bot_id, archive=None, git_repo=None):
        """Сборка образа из архива/Git."""
        pass
    
    async def pull_image(self, docker_image, registry_auth=None):
        """Скачивание готового образа."""
        pass
    
    async def start_container(self, user_id, bot_id, image_name, env_vars, limits):
        """Запуск контейнера."""
        pass
    
    async def stop_container(self, user_id, bot_id):
        """Остановка и удаление контейнера."""
        pass
    
    async def get_logs(self, user_id, bot_id, lines=100):
        """Получение логов."""
        pass
    
    def list_user_bots(self, user_id):
        """Список ботов пользователя."""
        pass
```

### Docker Labels

```python
container = docker.containers.run(
    image,
    labels={
        "bot_runner": "true",
        "user_id": user_id,
        "bot_id": bot_id,
        "started_at": timestamp
    }
)
```

### Events Listener

```python
async def start_event_listener(self, on_container_die):
    """Слушает Docker events для отслеживания падений."""
    for event in self.docker_client.events(
        filters={"type": "container", "event": ["die", "oom"]}
    ):
        if event["Actor"]["Attributes"].get("bot_runner"):
            await on_container_die(
                event["Actor"]["Attributes"]["user_id"],
                event["Actor"]["Attributes"]["bot_id"],
                event["Action"]
            )
```

---

## Безопасность

### Изоляция контейнеров

```python
container = docker.containers.run(
    image,
    network=config.docker_network,  # Изолированная сеть
    mem_limit=f"{limits['memory_mb']}m",
    nano_cpus=int(limits['cpu_cores'] * 1e9),
    pids_limit=100,
    security_opt=["no-new-privileges:true"],
    cap_drop=["ALL"],
    cap_add=["NET_BIND_SERVICE"],  # Только доступ к сети
)
```

### Безопасная распаковка архивов

```python
def is_within_directory(directory, target):
    abs_directory = os.path.abspath(directory)
    abs_target = os.path.abspath(target)
    return abs_target.startswith(abs_directory)

for member in tar.getmembers():
    member_path = os.path.join(extract_path, member.name)
    if not is_within_directory(extract_path, member_path):
        raise ValueError("Archive contains path traversal attempt")
```

### Secrets через env_vars

```json
{
  "env_vars": {
    "BOT_TOKEN": "123:ABC",
    "DATABASE_URL": "postgresql://..."
  }
}
```

---

## Лимиты

### По умолчанию

| Лимит | Значение |
|-------|----------|
| Память | 256 MB |
| CPU | 0.5 cores |
| PIDs | 100 |
| Время работы | 24 часа |
| Ботов на пользователя | 3 |

### Конфигурация

```python
@dataclass
class ResourceLimits:
    memory_mb: int = 256
    cpu_cores: float = 0.5
    pids_limit: int = 100
    timeout_hours: int = 24
```

---

## API

### Создание/управление ботами

```json
// POST /jobs
{
  "blueprint": "bot_runner",
  "data": {
    "action": "start",
    "bot_id": "my-bot",
    "deployment_mode": "simple",
    "code": "...",
    "requirements": ["aiogram>=3.0"],
    "env_vars": {"BOT_TOKEN": "..."}
  }
}

// Остановка
{
  "blueprint": "bot_runner",
  "data": {
    "action": "stop",
    "bot_id": "my-bot"
  }
}

// Логи
{
  "blueprint": "bot_runner",
  "data": {
    "action": "logs",
    "bot_id": "my-bot",
    "lines": 100
  }
}

// Список
{
  "blueprint": "bot_runner",
  "data": {
    "action": "list"
  }
}
```

### Ответы

```json
// Успех
{
  "job_id": "...",
  "state": "completed",
  "data": {
    "result": {
      "status": "started",
      "container_id": "abc123",
      "container_name": "bot_user_mybot"
    }
  }
}

// Ошибка валидации
{
  "job_id": "...",
  "state": "failed",
  "data": {
    "error": {
      "code": "MISSING_REQUIRED_FIELD",
      "message": "Отсутствует обязательное поле 'deployment_mode'",
      "hint": "Выберите режим деплоя",
      "example": {...}
    }
  }
}
```

---

## CLI клиент

### Команды

```bash
# Запуск (simple)
avtomatika-bot start <bot_id> --simple <files...> [options]

# Запуск (custom)
avtomatika-bot start <bot_id> --custom <path> [options]
avtomatika-bot start <bot_id> --git <url> [--branch <branch>] [options]

# Запуск (image)
avtomatika-bot start <bot_id> --image <image> [options]

# Управление
avtomatika-bot stop <bot_id>
avtomatika-bot logs <bot_id> [-n <lines>]
avtomatika-bot status <bot_id>
avtomatika-bot list
```

### Опции

```
-e, --env KEY=VALUE     Переменная окружения (можно несколько)
-r, --requirements      Зависимости (файл или список через запятую)
--entrypoint            Точка входа (по умолчанию: bot.py)
--branch                Git ветка (для --git)
--registry-user         Логин registry (для --image)
--registry-pass         Пароль registry (для --image)
--url                   URL оркестратора
--token                 Токен авторизации
```

---

## План реализации

### Фаза 1: Core

- [x] ContainerManager
- [x] Worker с обработчиками
- [x] Blueprint для оркестратора
- [x] Валидатор запросов

### Фаза 2: CLI

- [x] Базовые команды
- [x] Обработка файлов
- [x] Rich вывод

### Фаза 3: Docker Compose

- [x] docker-compose.yml
- [x] Dockerfile для оркестратора
- [x] Dockerfile для воркера

### Фаза 4: Документация

- [x] README
- [x] Примеры ботов
- [x] Use cases

### Фаза 5: Тестирование

- [ ] Unit тесты ContainerManager
- [ ] Integration тесты
- [ ] E2E тесты

### Фаза 6: Улучшения

- [ ] Web UI
- [ ] Метрики
- [ ] Уведомления о падениях
