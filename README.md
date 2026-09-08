# Wallet REST API

Асинхронное REST API для операций с кошельками пользователей (тестовое задание Python Dev).

## Стек технологий

| Назначение | Выбор |
|---|---|
| Язык | Python 3.12 |
| Веб-фреймворк (async) | FastAPI + uvicorn |
| ORM (async) | SQLAlchemy 2.0 (asyncpg) |
| Миграции | Alembic |
| БД | PostgreSQL 16 (контейнер) |
| Валидация | Pydantic v2 + pydantic-settings |
| Тесты | pytest + pytest-asyncio + httpx |
| Линтер / формат | ruff + black (PEP8) |
| Инфраструктура | Docker, docker-compose |

## API

### Изменение баланса
`POST /api/v1/wallets/{wallet_uuid}/operation`

```json
{
  "operation_type": "DEPOSIT",   // DEPOSIT | WITHDRAW
  "amount": 1000                 // строго > 0
}
```

Ответ `200`: `{ "wallet_uuid": "...", "balance": 1000.0 }`
Ошибки: `404` (кошелёк не найден для WITHDRAW), `400` (недостаточно средств), `422` (ошибка валидации).

### Получение баланса
`GET /api/v1/wallets/{wallet_uuid}` → `200` с текущим балансом или `404`.

**Правила существования кошелька:**
- `DEPOSIT` на несуществующий UUID — кошелёк создаётся (ленивое создание);
- `WITHDRAW` на несуществующий UUID — `404`;
- `GET` несуществующего кошелька — `404`.

## Конкурентность (ключевое требование)

- Каждая операция изменения баланса — одна транзакция;
- Перед изменением строка кошелька блокируется `SELECT ... FOR UPDATE` (row-level lock) — исключает lost updates;
- Проверка достаточности средств выполняется **внутри** заблокированной транзакции — нет гонки «проверили-списали»;
- Недостаток средств → откат транзакции и `400`.

## Структура проекта

```
wallet/
├── app/
│   ├── main.py            # создание FastAPI, подключение роутеров
│   ├── config.py          # настройки через pydantic-settings (.env)
│   ├── database.py        # async engine, sessionmaker, get_db-зависимость
│   ├── models.py          # модель Wallet
│   ├── schemas.py         # OperationRequest, BalanceResponse
│   ├── services.py        # бизнес-логика (FOR UPDATE)
│   └── routers/wallets.py # эндпоинты /api/v1/wallets
├── alembic/               # миграции (env.py под async engine)
├── tests/                 # базовые и конкурентные тесты
├── docker-compose.yml     # db + app, подъём одной командой
├── Dockerfile
├── requirements.txt / requirements-dev.txt
└── .env.example
```

## Запуск

Вся система поднимается одной командой (БД в контейнере, миграции применяются автоматически):

```bash
cp .env.example .env
docker-compose up --build
```

Приложение будет доступно на http://localhost:8000 (Swagger UI: `/docs`).

### Локальный запуск тестов

Тесты идут в Postgres-контейнер через порт `localhost:5440` (в compose проброшен из контейнера):

```bash
pip install -r requirements-dev.txt
pytest          # 12 тестов: базовые сценарии + конкурентность
```

Проверка стиля кода:

```bash
ruff check .
black --check .
```

### Примеры запросов (curl)

```bash
W=aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee
B=http://localhost:8000/api/v1/wallets

# Пополнить кошелёк (несуществующий кошелёк создаётся автоматически)
curl -X POST $B/$W/operation -H 'Content-Type: application/json' \
     -d '{"operation_type":"DEPOSIT","amount":1000}'
# → {"wallet_uuid":"...","balance":"1000"}

# Списать
curl -X POST $B/$W/operation -H 'Content-Type: application/json' \
     -d '{"operation_type":"WITHDRAW","amount":300}'
# → {"wallet_uuid":"...","balance":"700"}

# Узнать баланс
curl $B/$W
# → {"wallet_uuid":"...","balance":"700.0000"}

# Ошибки: 400 (недостаточно средств), 404 (WITHDRAW/GET по несуществующему), 422 (валидация)
```

## Модель данных

Таблица `wallets`:
- `id` — UUID, primary key;
- `balance` — `NUMERIC(20,4)`, NOT NULL, DEFAULT 0 (точность денежных операций);
- `created_at` — timestamptz, NOT NULL, DEFAULT now().

## Статус выполнения

- [x] Изучить задание, составить план (`plan.md`)
- [x] Каркас проекта: структура каталогов, `requirements*.txt`, `.gitignore`, `.env.example`
- [x] Конфиг, БД-слой, модель Wallet
- [x] Alembic-миграции (async env.py, первая миграция, автоприменение при старте)
- [x] Схемы Pydantic + сервисный слой (FOR UPDATE, savepoint для гонки ленивого создания)
- [x] Роутер и сборка приложения
- [x] Dockerfile + docker-compose (healthcheck, подъём одной командой)
- [x] Тесты: 12 тестов — базовые сценарии + конкурентность (`pytest`)
- [x] Прогон тестов и ручная проверка (`docker-compose up --build` + curl, 50 параллельных операций → баланс ровно как сумма)
- [x] Финализация README, проверка PEP8 (ruff + black — все проверки пройдены)
- [ ] Публикация на GitHub (репозиторий создан, финальный пуш после коммитов)
