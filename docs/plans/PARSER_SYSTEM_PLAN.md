# План системы парсинга VK/Telegram

Этот документ описывает архитектуру и план реализации системы парсинга контента из VK и Telegram с использованием Avtomatika.

## Содержание

1. [Обзор системы](#обзор-системы)
2. [Архитектура](#архитектура)
3. [Компоненты](#компоненты)
4. [Режимы работы](#режимы-работы)
5. [API](#api)
6. [План реализации](#план-реализации)

---

## Обзор системы

Система позволяет:
- Парсить посты из VK сообществ
- Парсить сообщения из Telegram каналов
- Пересылать контент подписчикам через Telegram бота
- Работать в режиме непрерывного мониторинга

### Основные сценарии

1. **Одноразовый парсинг**: Получить последние N постов из указанных источников
2. **Непрерывный мониторинг**: Постоянно отслеживать новые посты и пересылать их

---

## Архитектура

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ПОЛЬЗОВАТЕЛИ                                 │
│                    (Telegram Bot Interface)                          │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      TELEGRAM BOT WORKER                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   aiogram    │  │   SQLite     │  │   Commands   │              │
│  │   Bot        │  │   Storage    │  │   Handlers   │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         ОРКЕСТРАТОР                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │  Blueprints  │  │  Scheduler   │  │  Dispatcher  │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        PARSER WORKERS                                │
│  ┌──────────────┐  ┌──────────────┐                                │
│  │   Telegram   │  │      VK      │                                │
│  │   Parser     │  │    Parser    │                                │
│  └──────────────┘  └──────────────┘                                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Компоненты

### 1. Telegram Bot Worker

Отвечает за взаимодействие с пользователями:

```python
# Команды бота
/start          # Начало работы
/subscribe      # Подписаться на обновления
/unsubscribe    # Отписаться
/sources        # Список источников
/add <url>      # Добавить источник
/remove <id>    # Удалить источник
/status         # Статус мониторинга
/start_monitor  # Запустить мониторинг
/stop_monitor   # Остановить мониторинг
```

### 2. Parser Workers

#### Telegram Parser Worker

```python
@worker.task("parse_telegram")
async def parse_telegram(params: dict) -> dict:
    channel = params["channel"]
    limit = params.get("limit", 50)
    since_id = params.get("since_id")
    
    parser = TelegramParser(...)
    messages = await parser.get_channel_messages(
        channel, 
        limit=limit,
        min_id=since_id
    )
    
    return {
        "status": "success",
        "data": {
            "messages": [m.to_dict() for m in messages],
            "last_id": messages[0].id if messages else since_id
        }
    }
```

#### VK Parser Worker

```python
@worker.task("parse_vk")
async def parse_vk(params: dict) -> dict:
    group = params["group"]
    limit = params.get("limit", 50)
    since_id = params.get("since_id")
    
    parser = VKParser(...)
    posts = await parser.get_wall(
        group,
        count=limit,
        filter_after=since_id
    )
    
    return {
        "status": "success",
        "data": {
            "posts": posts,
            "last_id": posts[0]["id"] if posts else since_id
        }
    }
```

### 3. Оркестратор Blueprints

#### One-shot Parsing Blueprint

```python
blueprint = StateMachineBlueprint("parse_once")

@blueprint.state("init")
async def init(data, actions):
    actions.dispatch_parallel([
        ("parse_telegram", {"channel": ch}) 
        for ch in data.get("telegram_channels", [])
    ] + [
        ("parse_vk", {"group": g}) 
        for g in data.get("vk_groups", [])
    ])
    actions.transition_to("collecting")

@blueprint.state("collecting")
async def collecting(data, actions, task_results):
    data["results"] = task_results
    actions.transition_to("completed")
```

#### Continuous Monitoring Blueprint

```python
blueprint = StateMachineBlueprint("monitor_sources")

@blueprint.state("init")
async def init(data, actions):
    # Инициализация: загрузка last_ids из БД
    actions.transition_to("parsing")

@blueprint.state("parsing")
async def parsing(data, actions):
    # Параллельный парсинг всех источников
    actions.dispatch_parallel(...)
    actions.transition_to("forwarding")

@blueprint.state("forwarding")
async def forwarding(data, actions, task_results):
    # Пересылка новых постов подписчикам
    new_posts = extract_new_posts(task_results)
    
    if new_posts:
        actions.dispatch_task(
            "forward_to_subscribers",
            params={"posts": new_posts, "subscribers": data["subscribers"]}
        )
    
    # Планируем следующую итерацию
    actions.schedule_self(delay_seconds=60)
    actions.transition_to("waiting")

@blueprint.state("waiting")
async def waiting(data, actions):
    # Ожидание следующей итерации
    pass
```

---

## Режимы работы

### 1. Одноразовый парсинг

```
Пользователь → /parse @channel1 @channel2 vk.com/group1
                     │
                     ▼
               Оркестратор создаёт Job
                     │
                     ▼
               Параллельный dispatch задач
              ┌──────┴──────┐
              ▼             ▼
        TG Parser     VK Parser
              │             │
              └──────┬──────┘
                     ▼
               Сбор результатов
                     │
                     ▼
               Отправка пользователю
```

### 2. Непрерывный мониторинг

```
Пользователь → /start_monitor
                     │
                     ▼
               Создание scheduled job
                     │
        ┌────────────┴────────────┐
        ▼                         │
   Парсинг источников             │
        │                         │
        ▼                         │
   Сравнение с last_ids           │
        │                         │
        ▼                         │
   Пересылка новых постов         │
        │                         │
        ▼                         │
   Обновление last_ids            │
        │                         │
        ▼                         │
   schedule_self(60s) ────────────┘
```

---

## API

### Telegram Bot API

```python
# SQLite схема
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,  -- 'telegram' or 'vk'
    identifier TEXT NOT NULL,  -- channel/group
    last_parsed_id INTEGER,
    added_by INTEGER REFERENCES users(user_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE subscriptions (
    user_id INTEGER REFERENCES users(user_id),
    source_id INTEGER REFERENCES sources(id),
    PRIMARY KEY (user_id, source_id)
);

CREATE TABLE monitor_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT,  -- Avtomatika job_id
    status TEXT,  -- 'running', 'stopped'
    started_by INTEGER REFERENCES users(user_id),
    started_at TIMESTAMP,
    stopped_at TIMESTAMP
);
```

### Orchestrator API

```json
// POST /jobs - создание задачи парсинга
{
  "blueprint": "parse_once",
  "data": {
    "telegram_channels": ["@channel1", "@channel2"],
    "vk_groups": ["group1", "group2"],
    "limit": 50
  }
}

// POST /jobs - создание мониторинга
{
  "blueprint": "monitor_sources",
  "data": {
    "sources": [
      {"type": "telegram", "id": "@channel1"},
      {"type": "vk", "id": "group1"}
    ],
    "subscribers": [123456789, 987654321],
    "interval_seconds": 60
  },
  "scheduled": true,
  "cron": "* * * * *"  // Каждую минуту
}
```

---

## План реализации

### Фаза 1: Базовые компоненты

- [ ] Интеграция sno_parser в Worker
- [ ] Blueprint для одноразового парсинга
- [ ] Тестирование парсинга через API

### Фаза 2: Telegram Bot

- [ ] Базовый бот с командами
- [ ] SQLite для хранения данных
- [ ] Интеграция с оркестратором

### Фаза 3: Мониторинг

- [ ] Blueprint для continuous monitoring
- [ ] Логика определения новых постов
- [ ] Пересылка подписчикам

### Фаза 4: Улучшения

- [ ] Фильтрация контента
- [ ] Форматирование постов
- [ ] Медиа-файлы
- [ ] Админ-панель

---

## Использование

### Быстрый старт

```bash
# 1. Запуск Redis
docker run -d -p 6379:6379 redis

# 2. Запуск оркестратора
python -m avtomatika.server

# 3. Запуск Parser Worker
python parser_worker.py

# 4. Запуск Bot Worker
BOT_TOKEN=your_token python bot_worker.py
```

### Конфигурация

```env
# .env
ORCHESTRATOR_URL=http://localhost:8000
WORKER_TOKEN=secret

# Telegram Parser
TG_API_ID=your_api_id
TG_API_HASH=your_api_hash

# VK Parser
VK_TOKEN=your_vk_token

# Bot
BOT_TOKEN=your_bot_token
```
