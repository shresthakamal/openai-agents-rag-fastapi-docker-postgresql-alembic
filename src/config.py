from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str | None = None
    log_level: str = "INFO"
    port: int = 8000

    database_url: str | None = None

    postgres_user: str = "akin_chat"
    postgres_password: str = "akin_chat"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "akin_chat"

    api_version: str = "v1"
    app_version: str = "1.0.0"

    def build_database_url(self, *, hide_password: bool = False) -> str:
        if self.database_url:
            return self.database_url

        password = "****" if hide_password else self.postgres_password

        return (
            f"postgresql+asyncpg://{quote_plus(self.postgres_user)}:{quote_plus(password)}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    def build_sync_database_url(self, *, hide_password: bool = False) -> str:
        """Sync driver URL for Alembic and other blocking SQLAlchemy tools."""
        url = self.build_database_url(hide_password=hide_password)
        if url.startswith("postgresql+asyncpg://"):
            return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url


settings = Settings()
