"""Конкурентные тесты: параллельные операции на один кошелёк.

Ключевое требование задания: параллельные запросы на изменение
баланса одного кошелька обрабатываются корректно — без lost updates
и без отрицательного баланса (благодаря SELECT ... FOR UPDATE).
"""

import asyncio
from decimal import Decimal

import pytest

from tests.conftest import random_uuid

# Тесты выполняются в session-scoped петле asyncio (общей с фикстурами)
pytestmark = pytest.mark.asyncio(loop_scope="session")

API = "/api/v1/wallets"


async def test_50_parallel_deposits_balance_is_exact(client):
    """50 параллельных DEPOSIT по 10 на один кошелёк → баланс ровно 500."""
    w = random_uuid()

    async def deposit():
        r = await client.post(
            f"{API}/{w}/operation",
            json={"operation_type": "DEPOSIT", "amount": 10},
        )
        assert r.status_code == 200
        return r

    # Собираем корутины — httpx.AsyncClient можно звать конкурентно
    responses = await asyncio.gather(*(deposit() for _ in range(50)))
    assert all(r.status_code == 200 for r in responses)

    r = await client.get(f"{API}/{w}")
    assert Decimal(r.json()["balance"]) == 500


async def test_parallel_withdraws_no_negative_balance(client):
    """Параллельные WITHDRAW суммарно больше баланса:
    часть операций → 400, баланс >= 0 и равен ожидаемому."""
    w = random_uuid()
    # Кладём 1000, потом пробуем списать 60 раз по 50 (суммарно 3000)
    await client.post(
        f"{API}/{w}/operation",
        json={"operation_type": "DEPOSIT", "amount": 1000},
    )

    async def withdraw():
        return await client.post(
            f"{API}/{w}/operation",
            json={"operation_type": "WITHDRAW", "amount": 50},
        )

    responses = await asyncio.gather(*(withdraw() for _ in range(60)))

    ok = [r for r in responses if r.status_code == 200]
    rejected = [r for r in responses if r.status_code == 400]

    # Ровно 20 списаний прошли (20 × 50 = 1000), остальные 40 → 400
    assert len(ok) == 20
    assert len(rejected) == 40

    r = await client.get(f"{API}/{w}")
    # Баланс >= 0 и точно равен ожидаемому: ни копейки не потеряно
    assert Decimal(r.json()["balance"]) == 0


async def test_mixed_parallel_operations_deterministic_balance(client):
    """Смешанный параллельный сценарий DEPOSIT+WITHDRAW →
    финальный баланс детерминирован.

    Каждый воркер делает серию операций, суммарный вклад каждой
    операции известен: баланс = сумма всех эффектов.
    """
    w = random_uuid()

    async def worker(i: int):
        # Чередуем DEPOSIT (+30) и WITHDRAW (-10) — эффект +20 на воркера
        r1 = await client.post(
            f"{API}/{w}/operation",
            json={"operation_type": "DEPOSIT", "amount": 30},
        )
        r2 = await client.post(
            f"{API}/{w}/operation",
            json={"operation_type": "WITHDRAW", "amount": 10},
        )
        return r1.status_code, r2.status_code

    n = 30
    results = await asyncio.gather(*(worker(i) for i in range(n)))

    # Все операции прошли успешно (стартовый баланс хватает на любой WITHDRAW,
    # так как перед каждым WITHDRAW воркер уже сделал DEPOSIT +30)
    for s1, s2 in results:
        assert s1 == 200 and s2 == 200

    r = await client.get(f"{API}/{w}")
    # Детерминированный итог: 30 × (30 - 10) = 600
    assert Decimal(r.json()["balance"]) == 600
