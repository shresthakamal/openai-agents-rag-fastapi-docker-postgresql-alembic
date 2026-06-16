import logging
from pathlib import Path
from urllib.parse import quote_plus

from pydantic import field_validator, model_validator
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

    # AWS / LocalStack
    aws_default_region: str = "us-east-1"
    aws_endpoint_url: str | None = None

    # Database
    postgres_user: str = "akin_chat"
    postgres_password: str = "akin_chat"
    postgres_host: str = "postgres"
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

    @field_validator("aws_endpoint_url", mode="before")
    @classmethod
    def normalize_aws_endpoint_url(cls, value: str | None) -> str | None:
        if value == "":
            return None
        return value

    @property
    def is_local(self) -> bool:
        return self.environment.lower() in ("local", "test", "testing")

    @model_validator(mode="after")
    def load_secrets_from_aws(self) -> "Settings":
        """Load secrets from AWS Secrets Manager in non-local environments."""
        if self.is_local:
            return self

        from utils.secrets import SecretNames, get_secrets_manager

        secrets = get_secrets_manager(
            region=self.aws_default_region,
            endpoint_url=self.aws_endpoint_url,
        )

        if not self.database_url:
            value = secrets.get_secret_or_env(
                SecretNames.db_url(),
                env_var="DATABASE_URL",
            )
            if value:
                object.__setattr__(self, "database_url", value)
            else:
                logger.warning("Could not load %s from Secrets Manager", SecretNames.db_url())

        secret_mappings = {
            "openai_api_key": (SecretNames.openai_api_key(), "OPENAI_API_KEY"),
            "pinecone_serverless_api_key": (
                SecretNames.pinecone_serverless_api_key(),
                "PINECONE_SERVERLESS_API_KEY",
            ),
            "voyage_api_key": (SecretNames.voyage_api_key(), "VOYAGE_API_KEY"),
        }

        for field_name, (secret_name, env_var) in secret_mappings.items():
            if getattr(self, field_name):
                continue

            value = secrets.get_secret_or_env(secret_name, env_var=env_var)
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
