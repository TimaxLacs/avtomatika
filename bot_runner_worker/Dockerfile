FROM python:3.11-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем файлы зависимостей
COPY pyproject.toml .
COPY README.md .

# Копируем исходный код
COPY src/ src/

# Устанавливаем пакет
RUN pip install --no-cache-dir -e .

# Переменные окружения по умолчанию
ENV PYTHONUNBUFFERED=1

# Запуск воркера
CMD ["python", "-m", "bot_runner_worker.worker"]
