# Avtomatika

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7+-red?logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

State-Machine Orchestrator для распределённых workflow на Python.

## Возможности

- **State Machine** — декларативное описание бизнес-процессов
- **Distributed Workers** — масштабируемая обработка задач
- **Auto-Retry** — автоматические повторы при ошибках
- **Observability** — Prometheus метрики, OpenTelemetry
- **Security** — аутентификация клиентов и воркеров

## Архитектура

```
                              ┌─────────────────┐
                              │     Clients     │
                              │  (CLI, API, UI) │
                              └────────┬────────┘
                                       │
┌──────────────────────────────────────┴───────────────────────────────────┐
│                         AVTOMATIKA ORCHESTRATOR                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────┐    │
│  │  Blueprints  │  │   Executor   │  │  Dispatcher  │  │  Watcher  │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └───────────┘    │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Redis (States, Queues)  │  PostgreSQL (History)                 │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────┬───────────────────────────────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              ▼                        ▼                        ▼
     ┌──────────────┐         ┌──────────────┐         ┌──────────────┐
     │   Worker 1   │         │   Worker 2   │         │   Worker N   │
     └──────────────┘         └──────────────┘         └──────────────┘
```

---

## Сценарии использования

### Сценарий 1: Удалённый сервер + локальный клиент

Оркестратор и воркеры на сервере, пользователи подключаются через CLI.

```
┌──────────────────────────────────────────────────────────────┐
│                   СЕРВЕР (server.example.com)                │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │  Redis   │  │ Orchestrator │  │   Bot Runner Worker   │  │
│  │  :6379   │  │    :8000     │  │       (Docker)        │  │
│  └──────────┘  └──────┬───────┘  └───────────────────────┘  │
└───────────────────────┼──────────────────────────────────────┘
                        │ :8000
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
   ┌─────────┐     ┌─────────┐     ┌─────────┐
   │  CLI A  │     │  CLI B  │     │  CI/CD  │
   └─────────┘     └─────────┘     └─────────┘
```

#### Сервер: Оркестратор + Воркер

```bash
git clone https://github.com/avtomatika-ai/avtomatika.git && cd avtomatika

# Создать .env (или использовать значения по умолчанию из docker-compose)
cat > .env << 'EOF'
CLIENT_TOKEN=my-client-token
GLOBAL_WORKER_TOKEN=my-worker-token
EOF

docker-compose -f docker-compose.bot-runner.yml up -d

# Проверить
curl http://localhost:8000/_public/status
```

Токены по умолчанию (для тестирования): `test-client-token`, `test-worker-token`

#### Клиент: Локальный ПК

```bash
pip install avtomatika-bot-cli

export AVTOMATIKA_URL=http://server.example.com:8000
export AVTOMATIKA_TOKEN=my-client-token

avtomatika-bot status
avtomatika-bot start my-bot --simple bot.py -e "BOT_TOKEN=123:ABC"
avtomatika-bot logs my-bot -f
```

---

### Сценарий 2: Локальный оркестратор + удалённые воркеры

Оркестратор на вашем ПК, воркеры на удалённых серверах.

```
┌──────────────────────────────────────────────────────────────┐
│                  ВАШ ПК (192.168.1.100)                       │
│  ┌──────────┐  ┌──────────────┐  ┌─────────┐                 │
│  │  Redis   │  │ Orchestrator │  │   CLI   │                 │
│  │  :6379   │  │    :8000     │  │         │                 │
│  └──────────┘  └──────┬───────┘  └─────────┘                 │
└───────────────────────┼──────────────────────────────────────┘
                        │ :8000
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
   ┌─────────┐     ┌─────────┐     ┌─────────┐
   │  VPS    │     │ Server  │     │   RPi   │
   │ Worker  │     │ Worker  │     │ Worker  │
   └─────────┘     └─────────┘     └─────────┘
```

#### Локальный ПК: Оркестратор

```bash
git clone https://github.com/avtomatika-ai/avtomatika.git && cd avtomatika

# Запустить только Redis и оркестратор (без воркера)
docker-compose -f docker-compose.bot-runner.yml up -d redis orchestrator

# Узнать свой IP
ip addr show | grep "inet " | grep -v 127.0.0.1
```

#### Удалённый сервер: Воркер

```bash
# Клонировать и собрать воркер
git clone https://github.com/avtomatika-ai/avtomatika.git && cd avtomatika/bot_runner_worker

docker build -t bot-runner-worker .

docker run -d \
  -e ORCHESTRATOR_URL=http://192.168.1.100:8000 \
  -e WORKER_TOKEN=test-worker-token \
  -e WORKER_ID=remote-worker-1 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  bot-runner-worker
```

#### Локальный ПК: CLI

```bash
pip install avtomatika-bot-cli

export AVTOMATIKA_URL=http://localhost:8000
export AVTOMATIKA_TOKEN=test-client-token

avtomatika-bot status
avtomatika-bot start my-bot --simple bot.py
```

---

### Сценарий 3: Всё локально (демо)

```bash
git clone https://github.com/avtomatika-ai/avtomatika.git && cd avtomatika
docker-compose -f docker-compose.bot-runner.yml up -d

pip install avtomatika-bot-cli

export AVTOMATIKA_URL=http://localhost:8000
export AVTOMATIKA_TOKEN=test-client-token

avtomatika-bot status
avtomatika-bot start hello --simple examples/bots/echo_bot.py -r "aiogram>=3.0" -e "BOT_TOKEN=..."
```

---

## Установка

```bash
pip install avtomatika           # Базовая
pip install avtomatika[redis]    # С Redis (рекомендуется)
pip install avtomatika[all]      # Полная
```

---

## Быстрый старт

### Blueprint

```python
from avtomatika import StateMachineBlueprint, JobContext

workflow = StateMachineBlueprint("order_processing", api_endpoint="/jobs/orders")

@workflow.state("init", is_start=True)
async def init_order(ctx: JobContext):
    if ctx.initial_data.get("amount", 0) > 10000:
        ctx.actions.transition_to("pending_approval")
    else:
        ctx.actions.dispatch_task(
            task_type="process_payment",
            params={"order_id": ctx.initial_data["id"]},
            transitions={"success": "completed", "failure": "failed"}
        )

@workflow.state("completed", is_end=True)
async def done(ctx: JobContext):
    pass
```

### Оркестратор

```python
import asyncio
from avtomatika import OrchestratorEngine, Config
from avtomatika.storage.redis import RedisStorage
from redis.asyncio import Redis

async def main():
    config = Config()
    config.CLIENT_TOKEN = "test-client-token"
    config.GLOBAL_WORKER_TOKEN = "test-worker-token"
    
    storage = RedisStorage(Redis(host="localhost"))
    engine = OrchestratorEngine(config=config, storage=storage)
    engine.register_blueprint(workflow)
    
    await engine.start()

asyncio.run(main())
```

### API

```bash
curl -X POST http://localhost:8000/api/jobs/orders \
  -H "X-Avtomatika-Token: test-client-token" \
  -H "Content-Type: application/json" \
  -d '{"data": {"id": "order-123", "amount": 500}}'
```

---

## Workers

```python
from avtomatika_worker import Worker

worker = Worker(worker_type="my-worker", max_concurrent_tasks=10)

@worker.task("process_payment")
async def process_payment(params: dict) -> dict:
    return {"status": "success", "tx_id": "tx-123"}

asyncio.run(worker.main())
```

```bash
export ORCHESTRATOR_URL=http://localhost:8000
export WORKER_TOKEN=test-worker-token
```

---

## Конфигурация

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `REDIS_HOST` | Хост Redis | `localhost` |
| `REDIS_PORT` | Порт Redis | `6379` |
| `API_HOST` | Хост API | `0.0.0.0` |
| `API_PORT` | Порт API | `8000` |
| `CLIENT_TOKEN` | Токен клиентов | — |
| `GLOBAL_WORKER_TOKEN` | Токен воркеров | — |

---

## Мониторинг

```bash
curl http://localhost:8000/metrics        # Prometheus метрики
curl http://localhost:8000/_public/status # Health check
```

---

## Экосистема

| Компонент | Описание |
|-----------|----------|
| [avtomatika](https://github.com/avtomatika-ai/avtomatika) | Orchestrator |
| [avtomatika-worker](https://github.com/avtomatika-ai/avtomatika-worker) | Worker SDK |
| [avtomatika-bot-runner-worker](https://github.com/avtomatika-ai/avtomatika-bot-runner-worker) | Bot Runner |
| [avtomatika-bot-cli](https://github.com/avtomatika-ai/avtomatika-bot-cli) | CLI |

---

## Документация

- [Architecture](docs/architecture.md)
- [API Reference](docs/api_reference.md)
- [Deployment](docs/deployment.md)
- [Testing Guide](docs/guides/TESTING_GUIDE.md)

---

## Лицензия

MIT
