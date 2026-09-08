"""Базовые сценарии эндпоинтов /api/v1/wallets."""

import pytest

from decimal import Decimal

from tests.conftest import random_uuid

# Тесты выполняются в session-scoped петле asyncio (общей с фикстурами)
pytestmark = pytest.mark.asyncio(loop_scope="session")

API = "/api/v1/wallets"


async def test_deposit_increases_balance(client):
    """Успешный DEPOSIT → баланс увеличился."""
    w = random_uuid()

    r1 = await client.post(
        f"{API}/{w}/operation",
        json={"operation_type": "DEPOSIT", "amount": 1000},
    )
    assert r1.status_code == 200
    assert Decimal(r1.json()["balance"]) == 1000

    r2 = await client.post(
        f"{API}/{w}/operation",
        json={"operation_type": "DEPOSIT", "amount": 250.5},
    )
    assert r2.status_code == 200
    assert Decimal(r2.json()["balance"]) == Decimal("1250.5")


async def test_withdraw_decreases_balance(client):
    """Успешный WITHDRAW → баланс уменьшился."""
    w = random_uuid()
    await client.post(
        f"{API}/{w}/operation",
        json={"operation_type": "DEPOSIT", "amount": 500},
    )
    r = await client.post(
        f"{API}/{w}/operation",
        json={"operation_type": "WITHDRAW", "amount": 200},
    )
    assert r.status_code == 200
    assert Decimal(r.json()["balance"]) == 300


async def test_withdraw_more_than_balance_returns_400(client):
    """WITHDRAW больше баланса → 400, баланс не изменился."""
    w = random_uuid()
    await client.post(
        f"{API}/{w}/operation",
        json={"operation_type": "DEPOSIT", "amount": 100},
    )
    r = await client.post(
        f"{API}/{w}/operation",
        json={"operation_type": "WITHDRAW", "amount": 150},
    )
    assert r.status_code == 400

    # Баланс не изменился
    r2 = await client.get(f"{API}/{w}")
    assert Decimal(r2.json()["balance"]) == 100


async def test_withdraw_nonexistent_wallet_404(client):
    """WITHDRAW по несуществующему кошельку → 404 (без ленивого создания)."""
    r = await client.post(
        f"{API}/{random_uuid()}/operation",
        json={"operation_type": "WITHDRAW", "amount": 100},
    )
    assert r.status_code == 404


async def test_get_nonexistent_wallet_404(client):
    """GET несуществующего кошелька → 404."""
    r = await client.get(f"{API}/{random_uuid()}")
    assert r.status_code == 404


async def test_negative_amount_422(client):
    """Отрицательный amount → 422."""
    r = await client.post(
        f"{API}/{random_uuid()}/operation",
        json={"operation_type": "DEPOSIT", "amount": -100},
    )
    assert r.status_code == 422


async def test_zero_amount_422(client):
    """Нулевой amount → 422 (amount строго > 0)."""
    r = await client.post(
        f"{API}/{random_uuid()}/operation",
        json={"operation_type": "DEPOSIT", "amount": 0},
    )
    assert r.status_code == 422


async def test_unknown_operation_type_422(client):
    """Неизвестный operation_type → 422."""
    r = await client.post(
        f"{API}/{random_uuid()}/operation",
        json={"operation_type": "ROB_THE_BANK", "amount": 100},
    )
    assert r.status_code == 422


async def test_invalid_uuid_422(client):
    """Невалидный UUID в пути → 422."""
    r = await client.post(
        f"{API}/not-a-uuid/operation",
        json={"operation_type": "DEPOSIT", "amount": 100},
    )
    assert r.status_code == 422
