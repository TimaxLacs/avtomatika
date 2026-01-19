# Чеклист тестирования Bot Runner

## Сводка (2026-01-19)

| # | Тест | Статус | Комментарий |
|---|------|--------|-------------|
| 1 | Базовый бот | ✅ Пройден | Бот работает напрямую |
| 2 | Orchestrator + Worker | ✅ Пройден | После исправлений |
| 3 | Валидация | ✅ Пройден | API ошибки корректны |
| 4 | CLI (start/list/status/logs/stop) | ✅ Пройден | Все команды работают |
| 5 | Docker Compose | ✅ Пройден | Полная инфраструктура |
| 6 | Update бота | ✅ Пройден | stop + start с новым кодом |
| 7 | Лимиты | ✅ Пройден | 4-й бот → QUOTA_EXCEEDED |
| 8 | Логи ошибок | ✅ Пройден | Traceback отображается |
| 9 | Git режим | ✅ Пройден | Клонирование + сборка + запуск |

**Итого:** 9 из 9 пройдено ✅

---

## Подготовка

```bash
cd ~/projects/avtomatika
source venv/bin/activate
export BOT_TOKEN="8466887146:AAFn-N0w0MLMYQlMetAq_4IU5xdrq_Bj9kw"
export AVTOMATIKA_TOKEN=test-client-token
export AVTOMATIKA_URL=http://localhost:8000
```

---

## Пройденные тесты

### ✅ Тест 1: Базовый бот

```bash
python test_bot.py
```

**Результат:** Бот @testTimax_bot работает, отвечает на /start, /ping, эхо.

---

### ✅ Тест 2: Orchestrator + Worker

```bash
python local_test/orchestrator_server.py &
python local_test/worker_client.py &
curl -X POST http://localhost:8000/api/jobs/test ...
```

**Результат:** Job создаётся → Task отправляется Worker → Результат возвращается → completed

---

### ✅ Тест 3: Валидация

| Запрос | Ответ |
|--------|-------|
| Без токена | 401 Unauthorized |
| Неверный токен | 401 Invalid token |
| Несуществующий job | 404 Not found |

---

### ✅ Тест 4: CLI (все команды)

| Команда | Результат |
|---------|-----------|
| `avtomatika-bot start bot-name --simple file.py` | ✅ Бот запущен в Docker |
| `avtomatika-bot list` | ✅ Таблица ботов (1/3) |
| `avtomatika-bot status bot-name` | ✅ 🟢 RUNNING, container info |
| `avtomatika-bot logs bot-name` | ✅ Логи контейнера |
| `avtomatika-bot stop bot-name` | ✅ Бот остановлен |

**Ответ бота на /start:**
```
👋 Привет, [Имя]!
Я Echo-бот. Отправь мне любое сообщение, и я его повторю.
```

---

### ✅ Тест 5: Docker Compose

```bash
docker-compose -f docker-compose.bot-runner.yml up -d
# → Redis: healthy
# → Orchestrator: healthy  
# → Bot Runner Worker: running

avtomatika-bot start docker-test-bot --simple examples/bots/echo_bot.py ...
# → Бот запущен и работает в полной Dockerized инфраструктуре
```

**Исправленные проблемы:**
- `decode_responses=True` убрано из Redis (конфликт с бинарными данными)
- `asyncio.create_task(run_in_executor())` → `run_in_executor()` напрямую

---

### ✅ Тест 7: Лимиты

```bash
# Создаём 3 бота (успех)
avtomatika-bot start limit-bot-1 --simple echo_bot.py ...
avtomatika-bot start limit-bot-2 --simple echo_bot.py ...
avtomatika-bot start limit-bot-3 --simple echo_bot.py ...

# 4-й бот (ошибка)
avtomatika-bot start limit-bot-4 --simple echo_bot.py ...
# → Task failed: Maximum 3 bots per user
```

---

### ✅ Тест 8: Логи ошибок

```bash
# Бот с ошибкой
avtomatika-bot start error-bot --simple error_bot.py

# Логи показывают traceback
avtomatika-bot logs error-bot
# → ValueError: TEST ERROR
# → Traceback (most recent call last):
```

---

### ✅ Тест 6: Update бота

```bash
avtomatika-bot start update-test-bot --simple echo_bot.py -e "TEST_NUMBER=V1"
# → Бот V1 запущен

avtomatika-bot update update-test-bot --simple echo_bot_v2.py -e "BOT_VERSION=V2"
# → Шаг 1/2: Остановка текущего бота...
# → ✓ Остановлен
# → Шаг 2/2: Запуск с новым кодом...
# → Бот успешно обновлён!

avtomatika-bot logs update-test-bot
# → Starting Echo Bot V2...
```

---

### ✅ Тест 9: Git режим

```bash
avtomatika-bot start git-test \
  --git https://github.com/deep-assistant/telegram-bot \
  --entrypoint "__main__.py" \
  -e "TOKEN=$BOT_TOKEN" \
  -e "IS_DEV=True" ...

# → Репозиторий клонирован
# → Docker образ собран
# → Бот запущен
# → Логи доступны
```

**Исправленный баг:** `bool(data.get("git_repo"))` вместо `data.get("git_repo")`

---

## Полная документация тестов

📁 [tests/manual/README.md](../tests/manual/README.md) — сводка всех тестов с логами

📁 Отдельные тесты:
- [test_01_basic_bot](../tests/manual/test_01_basic_bot/README.md)
- [test_02_orchestrator_worker](../tests/manual/test_02_orchestrator_worker/README.md)
- [test_03_validation](../tests/manual/test_03_validation/README.md)
- [test_04_cli](../tests/manual/test_04_cli/README.md)
- [test_05_docker_compose](../tests/manual/test_05_docker_compose/README.md)
- [test_06_update_bot](../tests/manual/test_06_update_bot/README.md)
- [test_07_limits](../tests/manual/test_07_limits/README.md)
- [test_08_error_logs](../tests/manual/test_08_error_logs/README.md)
- [test_09_git_mode](../tests/manual/test_09_git_mode/README.md)
