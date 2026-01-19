# Пример кастомного Dockerfile для бота
FROM python:3.11-slim

# Установка системных зависимостей (при необходимости)
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем файлы зависимостей отдельно для кэширования
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY . .

# Опционально: создаём непривилегированного пользователя
RUN useradd --create-home --shell /bin/bash botuser
USER botuser

# Запуск
CMD ["python", "bot.py"]
