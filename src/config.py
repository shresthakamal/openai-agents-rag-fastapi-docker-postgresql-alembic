import logging
from pathlib import Path
from urllib.parse import quote_plus

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "local"
    app_version: str = "1.0.0"
    api_version: str = "api/v1"
    log_level: str = "INFO"

    # Database
    postgres_user: str = "akin_chat"
    postgres_password: str = "akin_chat"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "akin_chat"

    # OpenAI
    openai_api_key: str | None = None
    database_url: str | None = None

    # Pinecone
    pinecone_serverless_api_key: str | None = None
    pinecone_index: str = "ai4u"
    pinecone_host: str = "https://ai4u-jew04wr.svc.aped-4627-b74a.pinecone.io"
    pinecone_namespace: str = "global"

    # Voyage
    voyage_api_key: str | None = None
    voyage_embed_model: str = "voyage-3"
    voyage_rerank_model: str = "rerank-2.5"
    voyage_rerank_top_k: int = 5

    # RAG
    rag_top_k: int = 5
    rag_candidate_k: int = 20

    # Prompts
    prompts_dir: Path = Path(__file__).resolve().parent / "prompts"

    @property
    def is_local(self) -> bool:
        return self.environment.lower() in ("local", "test", "testing")

    def load_secrets_prefix(self) -> str:
        return f"akin/{self.environment}/chat"

    @model_validator(mode="after")
    def load_secrets_from_aws(self) -> "Settings":
        """Load secrets from AWS Secrets Manager in non-local environments."""
        if self.is_local:
            return self

        from utils.secrets import secrets_manager

        # Load database URL
        if not self.database_url:
            secret_name = f"{self.load_secrets_prefix()}/db_url"
            value = secrets_manager.get_secret_sync(secret_name=secret_name)
            if value:
                object.__setattr__(self, "database_url", value)
            else:
                logger.warning("Could not load %s from Secrets Manager", secret_name)

        # Load other secrets
        secret_mappings = {
            "openai_api_key": f"{self.load_secrets_prefix()}/openai_api_key",
            "pinecone_serverless_api_key": f"{self.load_secrets_prefix()}/pinecone_serverless_api_key",
            "voyage_api_key": f"{self.load_secrets_prefix()}/voyage_api_key",
        }

        for field_name, secret_name in secret_mappings.items():
            if getattr(self, field_name):
                continue

            value = secrets_manager.get_secret_sync(secret_name=secret_name)
            if value:
                object.__setattr__(self, field_name, value)
            else:
                logger.warning("Could not load %s from Secrets Manager", secret_name)

        return self

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
