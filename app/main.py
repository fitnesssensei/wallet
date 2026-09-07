"""Точка входа приложения: создание FastAPI и подключение роутеров."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import engine
from app.routers import wallets


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Жизненный цикл приложения.

    На старте проверяем доступность БД, при завершении —
    корректно закрываем пул соединений.
    """
    from sqlalchemy import text

    async with engine.connect() as conn:
        # Простейшая проверка соединения с БД (упадёт с понятной ошибкой,
        # если Postgres недоступен, — например, при старте раньше контейнера)
        await conn.execute(text("SELECT 1"))
    yield
    await engine.dispose()


app = FastAPI(
    title="Wallet REST API",
    description="Асинхронное API для операций с кошельками (FastAPI + PostgreSQL)",
    version="1.0.0",
    lifespan=lifespan,
)

# Подключаем роутер с эндпоинтами /api/v1/wallets
app.include_router(wallets.router)


@app.get("/health", tags=["service"])
async def health_check() -> dict:
    """Простейший health-check эндпоинт (полезен для docker healthcheck)."""
    return {"status": "ok"}
