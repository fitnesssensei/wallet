"""Pydantic-схемы: валидация входных данных и формат ответов API."""

import uuid
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class OperationType(str, Enum):
    """Допустимые типы операций с кошельком."""

    DEPOSIT = "DEPOSIT"  # пополнение
    WITHDRAW = "WITHDRAW"  # списание


class OperationRequest(BaseModel):
    """Тело запроса POST /api/v1/wallets/{wallet_uuid}/operation.

    Валидация:
      - operation_type — только значения enum (иначе 422);
      - amount — строго > 0 (gt=0), иначе 422.
    """

    operation_type: OperationType
    amount: Decimal = Field(
        ...,
        gt=0,
        description="Сумма операции, строго больше нуля",
        # Ограничиваем количество знаков после запятой — деньги
        decimal_places=4,  # соответствует NUMERIC(20, 4) в БД
    )


class BalanceResponse(BaseModel):
    """Ответ с балансом кошелька (для обоих эндпоинтов)."""

    # model_config разрешает создание схемы из ORM-объектов
    model_config = ConfigDict(from_attributes=True)

    wallet_uuid: uuid.UUID
    balance: Decimal
