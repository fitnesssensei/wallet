"""Эндпоинты /api/v1/wallets: операции с балансом и получение баланса."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import services
from app.database import get_db
from app.schemas import BalanceResponse, OperationRequest

router = APIRouter(prefix="/api/v1/wallets", tags=["wallets"])


@router.post(
    "/{wallet_uuid}/operation",
    response_model=BalanceResponse,
    summary="Изменение баланса (DEPOSIT / WITHDRAW)",
)
async def wallet_operation(
    wallet_uuid: uuid.UUID,
    operation: OperationRequest,
    db: AsyncSession = Depends(get_db),
) -> BalanceResponse:
    """Выполнить операцию над кошельком.

    Коды ответов:
      - 200 — операция успешна, возвращён новый баланс;
      - 404 — WITHDRAW по несуществующему кошельку;
      - 400 — недостаточно средств при WITHDRAW;
      - 422 — невалидное тело запроса (проверяет Pydantic автоматически).
    """
    try:
        balance = await services.process_operation(
            db=db,
            wallet_uuid=wallet_uuid,
            operation_type=operation.operation_type,
            amount=operation.amount,
        )
    except services.InsufficientFundsError as exc:
        # Недостаток средств → откат транзакции и 400.
        # rollback нужен, чтобы вернуть соединение в пул в чистом состоянии.
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except services.WalletNotFoundError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return BalanceResponse(wallet_uuid=wallet_uuid, balance=balance)


@router.get(
    "/{wallet_uuid}",
    response_model=BalanceResponse,
    summary="Получение баланса кошелька",
)
async def get_wallet_balance(
    wallet_uuid: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> BalanceResponse:
    """Вернуть текущий баланс. Несуществующий кошелёк → 404."""
    try:
        balance = await services.get_balance(db, wallet_uuid)
    except services.WalletNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return BalanceResponse(wallet_uuid=wallet_uuid, balance=balance)
