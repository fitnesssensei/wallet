"""Alembic: асинхронное окружение миграций (работает через async engine)."""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Импортируем настройки и метаданные моделей, чтобы Alembic
# видел таблицы (target_metadata) и строку подключения.
from app.config import settings
from app.models import Base

# Объект конфигурации Alembic (заполняется из alembic.ini)
config = context.config

# Настройка логирования из alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Подставляем строку подключения из настроек приложения
# (в alembic.ini она намеренно не хранится, чтобы не дублировать секреты).
config.set_main_option("sqlalchemy.url", settings.database_url)

# Метаданные моделей: для autogenerate-миграций
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Режим 'offline': генерация SQL-скрипта без подключения к БД."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Настройка контекста и запуск миграций на переданном соединении."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # compare_type=True — autogenerate отслеживает изменения типов колонок
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Запуск миграций через async engine (asyncpg)."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # для миграций пул не нужен
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Режим 'online': подключение к БД и применение миграций."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
