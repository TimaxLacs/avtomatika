# Тест 03: Validation

## Информация

| Параметр | Значение |
|----------|----------|
| Статус | ✅ PASSED |
| Дата | 2026-01-18 |

## Описание

Проверка понятных сообщений об ошибках при неправильных запросах к API.

## Результаты тестов

| # | Тест | Запрос | Ответ | Статус |
|---|------|--------|-------|--------|
| 3.1 | Без токена | POST без header | `{"error": "Missing X-Avtomatika-Token header"}` | ✅ |
| 3.2 | Неверный токен | `X-Avtomatika-Token: wrong` | `{"error": "Unauthorized: Invalid token"}` | ✅ |
| 3.3 | Несуществующий endpoint | `/api/jobs/nonexistent` | `405: Method Not Allowed` | ⚠️ |
| 3.4 | Пустое тело | Пустой body | `{"error": "Invalid JSON body"}` | ✅ |
| 3.5 | Несуществующий Job | GET `/jobs/000...` | `{"error": "Job not found"}` | ✅ |

## Команды тестов

```bash
# 3.1 Без токена
curl -s -X POST http://localhost:8000/api/jobs/test \
  -H "Content-Type: application/json" \
  -d '{"input": "test"}'

# 3.2 Неверный токен
curl -s -X POST http://localhost:8000/api/jobs/test \
  -H "X-Avtomatika-Token: wrong-token" \
  -H "Content-Type: application/json" \
  -d '{"input": "test"}'

# 3.3 Несуществующий endpoint
curl -s -X POST http://localhost:8000/api/jobs/nonexistent \
  -H "X-Avtomatika-Token: test-client-token" \
  -H "Content-Type: application/json" \
  -d '{"input": "test"}'

# 3.4 Пустое тело
curl -s -X POST http://localhost:8000/api/jobs/test \
  -H "X-Avtomatika-Token: test-client-token" \
  -H "Content-Type: application/json" \
  -d ''

# 3.5 Несуществующий Job
curl -s http://localhost:8000/api/jobs/00000000-0000-0000-0000-000000000000 \
  -H "X-Avtomatika-Token: test-client-token"
```

## Выводы

- API возвращает понятные JSON-ошибки
- Аутентификация работает корректно
- Можно улучшить: добавить JSON-ответ для 404/405 ошибок
