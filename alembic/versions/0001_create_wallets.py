"""create wallets table

Создание таблицы `wallets`:
  - id         — UUID, первичный ключ;
  - balance    — NUMERIC(20,4), NOT NULL, DEFAULT 0 (денежная точность);
  - created_at — timestamptz, NOT NULL, DEFAULT now().

Revision ID: 0001_create_wallets
Revises:
Create Date: 2026-09-07

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# Идентификаторы ревизий
revision: str = "0001_create_wallets"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Применение миграции: создание таблицы wallets."""
    op.create_table(
        "wallets",
        # UUID-первичный ключ; серверный дефолт gen_random_uuid() —
        # на случай вставок вне приложения (ленивое создание на DEPOSIT)
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "balance",
            sa.Numeric(20, 4),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    """Откат миграции: удаление таблицы wallets."""
    op.drop_table("wallets")
