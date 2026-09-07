#!/bin/sh
# Entrypoint контейнера приложения:
# 1) ждём готовности Postgres (на случай, если healthcheck ещё не прошёл);
# 2) применяем миграции Alembic;
# 3) запускаем uvicorn.

set -e

echo "Waiting for database to be ready..."
until python -c "
import asyncio, asyncpg, os
async def check():
    conn = await asyncpg.connect(
        host=os.environ['POSTGRES_HOST'],
        port=int(os.environ.get('POSTGRES_PORT', 5432)),
        user=os.environ['POSTGRES_USER'],
        password=os.environ['POSTGRES_PASSWORD'],
        database=os.environ['POSTGRES_DB'],
    )
    await conn.close()
asyncio.run(check())
" 2>/dev/null; do
  sleep 1
done
echo "Database is ready."

echo "Applying migrations..."
alembic upgrade head

echo "Starting uvicorn..."
exec uvicorn app.main:app --host "${APP_HOST:-0.0.0.0}" --port "${APP_PORT:-8000}"
