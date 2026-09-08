"""ORM-модели SQLAlchemy 2.0 (DeclarativeBase, типизированный стиль)."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей проекта."""


class Wallet(Base):
    """Кошелёк пользователя.

    Таблица `wallets`:
      - id          — UUID, первичный ключ (генерируется на стороне клиента/БД);
      - balance     — NUMERIC(20,4), точность при денежных операциях;
      - created_at  — момент создания записи (now() на стороне БД).
    """

    __tablename__ = "wallets"

    # UUID как первичный ключ; default=uuid4 — если клиент не передал id
    # (например, при ленивом создании кошелька на DEPOSIT).
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # NUMERIC(20,4) — денежный тип: без ошибок округления float.
    # server_default="0" — дефолт на стороне БД, также для миграций.
    balance: Mapped[Decimal] = mapped_column(
        Numeric(20, 4),
        nullable=False,
        server_default="0",
        default=Decimal(0),
    )

    # timestamptz с дефолтом now() на стороне БД.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
