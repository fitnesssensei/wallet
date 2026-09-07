# --- Образ приложения: python:3.12-slim (по плану) ---
FROM python:3.12-slim

# Отключаем интерактив и буферизацию вывода (логи сразу видны в docker logs)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Сначала только зависимости — слой кэшируется, пересобирается
# только при изменении requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения и миграции
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

# Скрипт запуска: миграции → uvicorn
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Контейнер слушает порт приложения
EXPOSE 8000

# При старте контейнера: применяем миграции Alembic, затем поднимаем uvicorn
ENTRYPOINT ["./entrypoint.sh"]
