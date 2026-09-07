"""Слой доступа к базе данных: async engine, фабрика сессий, зависимость get_db."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

# Async engine SQLAlchemy 2.0 (драйвер asyncpg).
# echo=False — не логировать SQL-запросы в продакшене.
engine = create_async_engine(
    settings.database_url,
    echo=False,
    # Пул соединений рассчитан на конкурентную нагрузку:
    # параллельные запросы не должны ждать освобождения соединений дольше timeout.
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
    pool_pre_ping=True,  # проверка живости соединения перед использованием
)

# Фабрика сессий: каждая операция получает свою сессию (и свою транзакцию).
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # не сбрасывать атрибуты объектов после commit
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI-зависимость: выдаёт сессию БД на время запроса.

    Транзакцию коммитит сам сервисный слой (контроль над
    откатами при ошибках бизнес-логики остаётся в сервисе).
    """
    async with async_session_factory() as session:
        yield session
