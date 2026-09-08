"""Сервисный слой: бизнес-логика операций с кошельками.

Ключевое требование — корректность в конкурентной среде:
  - каждая операция изменения баланса выполняется в одной транзакции;
  - перед изменением строка кошелька блокируется SELECT ... FOR UPDATE
    (row-level lock) — исключает lost updates при параллельных запросах;
  - проверка достаточности средств выполняется ВНУТРИ заблокированной
    транзакции — нет гонки «проверили-списали».
"""

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Wallet
from app.schemas import OperationType


class WalletNotFoundError(Exception):
    """Кошелёк не найден (для WITHDRAW и GET) → маппится в 404."""


class InsufficientFundsError(Exception):
    """Недостаточно средств при WITHDRAW → маппится в 400."""


async def get_balance(db: AsyncSession, wallet_uuid: uuid.UUID) -> Decimal:
    """Получить баланс кошелька. Несуществующий кошелёк → 404.

    FOR UPDATE здесь не нужен: чтение баланса не изменяет данные,
    а_seq блокировка только снизила бы пропускную способность.
    """
    wallet = await db.get(Wallet, wallet_uuid)
    if wallet is None:
        raise WalletNotFoundError(f"Wallet {wallet_uuid} not found")
    return wallet.balance


async def process_operation(
    db: AsyncSession,
    wallet_uuid: uuid.UUID,
    operation_type: OperationType,
    amount: Decimal,
) -> Decimal:
    """Выполнить DEPOSIT/WITHDRAW и вернуть новый баланс.

    Схема конкурентной безопасности:
      1. Начинаем транзакцию (сессия уже в транзакции, commit — ниже);
      2. SELECT ... FOR UPDATE — блокируем строку кошелька (или убеждаемся,
         что её нет);
      3. Внутри блокировки проверяем достаточность средств;
      4. Применяем изменение и коммитим.

    Если одновременно прилетают N операций по одному кошельку, они
    выстраиваются в очередь на row-level lock — итоговый баланс
    равен сумме операций ровно, без lost updates.
    """
    # --- Шаг 1-2: SELECT ... FOR UPDATE ---
    # with_for_update() блокирует строку до конца транзакции.
    query = select(Wallet).where(Wallet.id == wallet_uuid).with_for_update()
    result = await db.execute(query)
    wallet = result.scalar_one_or_none()

    # --- Ленивое создание: DEPOSIT на несуществующий кошелёк ---
    if wallet is None:
        if operation_type == OperationType.DEPOSIT:
            # Возможна гонка: два параллельных DEPOSIT одновременно видят,
            # что кошелька нет, и оба делают INSERT. Обрабатываем через
            # SAVEPOINT: при нарушении уникальности (второй INSERT) откатываемся
            # к savepoint, перечитываем строку с FOR UPDATE и работаем дальше.
            async with db.begin_nested():  # SAVEPOINT
                try:
                    wallet = Wallet(id=wallet_uuid, balance=Decimal(0))
                    db.add(wallet)
                    await db.flush()  # INSERT в текущей транзакции
                except IntegrityError:
                    # Кошелёк уже создан параллельным запросом
                    wallet = None
            if wallet is None:
                # Перечитываем уже существующую строку с блокировкой
                result = await db.execute(query)
                wallet = result.scalar_one()
        else:
            # WITHDRAW на несуществующий кошелёк → 404
            raise WalletNotFoundError(f"Wallet {wallet_uuid} not found")

    # --- Шаг 3: проверка средств ВНУТРИ заблокированной транзакции ---
    if operation_type == OperationType.WITHDRAW and wallet.balance < amount:
        # Недостаток средств → откат транзакции (rollba­ck в роутере) → 400
        raise InsufficientFundsError(
            f"Insufficient funds: balance={wallet.balance}, requested={amount}"
        )

    # --- Шаг 4: применяем операцию ---
    if operation_type == OperationType.DEPOSIT:
        wallet.balance += amount
    else:
        wallet.balance -= amount

    # Фиксируем транзакцию: снимается и FOR UPDATE блокировка.
    await db.commit()
    return wallet.balance
