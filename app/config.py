"""Конфигурация приложения через pydantic-settings.

Все настройки читаются из переменных окружения и/или файла .env,
что позволяет использовать один и тот же код локально и в Docker.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Основные настройки приложения.

    Значения берутся из окружения (.env / docker-compose), при отсутствии
    используются значения по умолчанию, указанные ниже.
    """

    # --- Подключение к PostgreSQL ---
    postgres_host: str = "db"          # в docker-compose хост = имя сервиса
    postgres_port: int = 5432
    postgres_db: str = "wallets"
    postgres_user: str = "wallet_user"
    postgres_password: str = "wallet_password"

    # --- Настройки приложения ---
    app_host: str = "0.0.0.0"          # адрес, на котором слушает uvicorn
    app_port: int = 8000

    # --- Пул соединений (настроен под конкурентную нагрузку) ---
    db_pool_size: int = 20             # базовый размер пула
    db_max_overflow: int = 20          # доп. соединения при пиках нагрузки
    db_pool_timeout: int = 30          # сек. ожидания свободного соединения

    model_config = SettingsConfigDict(
        # читаем .env из корня проекта; extra="ignore" — не падать
        # на лишних переменных окружения (например, docker-специфичных)
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        """Строка подключения для async engine (драйвер asyncpg)."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    """Возвращает singleton настроек (кэшируется через lru_cache)."""
    return Settings()


# Глобальный экземпляр настроек, используется остальными модулями приложения
settings = get_settings()
