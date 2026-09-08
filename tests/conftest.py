"""Конфигурация тестов: отдельная тестовая БД + async-клиент httpx.

Тесты ходят в тот же Postgres-контейнер, что и приложение
(порт 5432 проброшен наружу), но в отдельную базу wallets_test,
чтобы не трогать данные основного окружения.
"""

import asyncio
import os
import uuid

# Тесты идут в Postgres-контейнер через проброшенный порт localhost:5440,
# поэтому ПЕРЕД чтением настроек переопределяем хост/порт из .env (порт 5440)
# (в контейнере "db:5432"; снаружи — localhost:5440, т.к. 5432 часто занят
# локальным Postgres)
os.environ["POSTGRES_HOST"] = "localhost"
os.environ["POSTGRES_PORT"] = "5440"

import httpx  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings  # noqa: E402
from app.database import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402

# URL тестовой БД: хост localhost (порт проброшен из контейнера),
# база wallets_test — изолирована от основной
TEST_DB_URL = settings.database_url.replace(
    f"/{settings.postgres_db}", "/wallets_test"
)


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Создаёт тестовую БД (если её нет), схему и async engine.

    После всех тестов — дропает схему и закрывает engine.
    """
    # --- Создание базы wallets_test (если её ещё нет) ---
    admin_engine = create_async_engine(
        TEST_DB_URL.rsplit("/", 1)[0] + "/postgres",
        isolation_level="AUTOCOMMIT",
    )
    async with admin_engine.connect() as conn:
        exists = await conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = 'wallets_test'")
        )
        if exists.scalar() is None:
            await conn.execute(text("CREATE DATABASE wallets_test"))
    await admin_engine.dispose()

    # --- Создание таблиц через метаданные моделей ---
    engine = create_async_engine(TEST_DB_URL, pool_size=20, max_overflow=20)
    async with engine.begin() as conn:
        # drop_all перед create_all гарантирует чистую схему
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # --- Очистка после всех тестов ---
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(test_engine):
    """Async-клиент httpx поверх приложения FastAPI.

    Переопределяем зависимость get_db: КАЖДЫЙ HTTP-запрос получает
    СВОЮ сессию из тестового engine — как в реальной работе приложения.
    Это критично для конкурентных тестов: общая сессия из параллельных
    запросов дала бы InterfaceError (одно соединение — одна операция).
    """
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as ac:
        yield ac

    # Убираем переопределения после теста
    app.dependency_overrides.clear()


def random_uuid() -> uuid.UUID:
    """Случайный UUID для изоляции тестов друг от друга."""
    return uuid.uuid4()
