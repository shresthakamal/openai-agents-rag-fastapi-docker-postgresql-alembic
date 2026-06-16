"""AWS Secrets Manager client for akin-chat.

Supports:
- AWS Secrets Manager in staging/production (IAM roles)
- LocalStack Secrets Manager in local development
- Environment variable fallback in local development
"""

import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)


def get_secret_environment() -> str:
    """Map ENVIRONMENT to the secret namespace (dev, staging, prod)."""
    env = os.environ.get("ENVIRONMENT", "dev").lower()
    if env in ("local", "test", "testing", "development", "dev"):
        return "dev"
    if env in ("staging", "stage"):
        return "staging"
    if env in ("production", "prod"):
        return "prod"
    return "dev"


def _is_running_on_aws() -> bool:
    if os.environ.get("AWS_EXECUTION_ENV"):
        return True
    if os.environ.get("ECS_CONTAINER_METADATA_URI") or os.environ.get(
        "ECS_CONTAINER_METADATA_URI_V4"
    ):
        return True
    if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        return True

    try:
        import urllib.request

        token_request = urllib.request.Request(
            "http://169.254.169.254/latest/api/token",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "21600"},
            method="PUT",
        )
        with urllib.request.urlopen(token_request, timeout=1) as response:
            token = response.read().decode()

        metadata_request = urllib.request.Request(
            "http://169.254.169.254/latest/meta-data/instance-id",
            headers={"X-aws-ec2-metadata-token": token},
        )
        with urllib.request.urlopen(metadata_request, timeout=1) as response:
            if response.status == 200:
                return True
    except Exception:
        pass

    return False


class SecretsManagerError(Exception):
    pass


class SecretsManager:
    """Secrets Manager client with environment-aware authentication."""

    def __init__(
        self,
        *,
        region: str | None = None,
        endpoint_url: str | None = None,
        use_env_fallback: bool = True,
        cache_ttl: int = 300,
    ) -> None:
        self.region = (
            region
            or os.environ.get("AWS_DEFAULT_REGION")
            or os.environ.get("AWS_REGION", "us-east-1")
        )
        self.cache_ttl = cache_ttl
        self.environment = os.environ.get("ENVIRONMENT", "local").lower()
        self.is_local = self.environment in ("local", "test", "testing")
        self.is_on_aws = _is_running_on_aws()

        localstack_endpoint = endpoint_url or os.environ.get("AWS_ENDPOINT_URL") or None
        if localstack_endpoint == "":
            localstack_endpoint = None

        if localstack_endpoint:
            # LocalStack integration testing (including ENVIRONMENT=prod against local AWS)
            self.endpoint_url = localstack_endpoint
            self.use_env_fallback = use_env_fallback
        elif self.is_local:
            self.endpoint_url = None
            self.use_env_fallback = use_env_fallback
        else:
            self.endpoint_url = None
            self.use_env_fallback = False
            if not self.is_on_aws:
                logger.warning(
                    "Non-local environment (%s) detected but not running on AWS. "
                    "Secrets Manager requires IAM roles on EC2/ECS/Lambda.",
                    self.environment,
                )

        self._cache: dict[str, Any] = {}
        self._cache_timestamps: dict[str, float] = {}
        self._client = None

    @property
    def client(self):
        if self._client is None:
            if not self.endpoint_url and self.is_local:
                logger.info(
                    "Local environment without LocalStack endpoint — using environment variables only"
                )
                return None

            try:
                import boto3
                from botocore.config import Config

                client_kwargs: dict[str, Any] = {
                    "service_name": "secretsmanager",
                    "region_name": self.region,
                    "config": Config(retries={"max_attempts": 3, "mode": "standard"}),
                }

                if self.endpoint_url:
                    client_kwargs["endpoint_url"] = self.endpoint_url
                    client_kwargs["aws_access_key_id"] = os.environ.get("AWS_ACCESS_KEY_ID", "test")
                    client_kwargs["aws_secret_access_key"] = os.environ.get(
                        "AWS_SECRET_ACCESS_KEY", "test"
                    )
                    auth_method = "LocalStack"
                    logger.info("Using LocalStack at %s", self.endpoint_url)
                else:
                    auth_method = "IAM role (instance profile)"
                    if os.environ.get("AWS_ACCESS_KEY_ID") and not self.is_local:
                        logger.warning(
                            "AWS_ACCESS_KEY_ID found in environment but ignored. "
                            "Non-local environments must use IAM roles."
                        )

                self._client = boto3.client(**client_kwargs)
                logger.info(
                    "Initialized Secrets Manager client (region=%s, env=%s, auth=%s)",
                    self.region,
                    self.environment,
                    auth_method,
                )
            except ImportError:
                if self.is_local:
                    logger.warning("boto3 not installed — using environment variables only")
                else:
                    logger.error("boto3 not installed — required for non-local environments")
                self._client = None
            except Exception as exc:
                if self.is_local:
                    logger.warning("Failed to initialize Secrets Manager: %s", exc)
                else:
                    logger.error(
                        "Failed to initialize Secrets Manager: %s. "
                        "Ensure an IAM role is attached.",
                        exc,
                    )
                self._client = None

        return self._client

    def _is_cache_valid(self, key: str) -> bool:
        if self.cache_ttl == 0 or key not in self._cache_timestamps:
            return False
        return (time.time() - self._cache_timestamps[key]) < self.cache_ttl

    def _set_cache(self, key: str, value: Any) -> None:
        if self.cache_ttl > 0:
            self._cache[key] = value
            self._cache_timestamps[key] = time.time()

    def _get_cache(self, key: str) -> Any | None:
        if self._is_cache_valid(key):
            return self._cache.get(key)
        return None

    def _secret_name_to_env_var(self, secret_name: str) -> str:
        parts = secret_name.split("/")
        if len(parts) > 2 and parts[1] in ("dev", "staging", "prod"):
            secret_name = "/".join([parts[0]] + parts[2:])
        return secret_name.replace("/", "_").upper()

    def get_secret_sync(
        self,
        secret_name: str,
        *,
        default: str | None = None,
    ) -> str | None:
        cache_key = f"{secret_name}:AWSCURRENT"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        if self.is_local and self.use_env_fallback:
            env_var = self._secret_name_to_env_var(secret_name)
            env_value = os.environ.get(env_var)
            if env_value:
                logger.debug("Loaded %s from environment variable %s", secret_name, env_var)
                self._set_cache(cache_key, env_value)
                return env_value

        if self.client is None:
            if self.use_env_fallback:
                env_var = self._secret_name_to_env_var(secret_name)
                return os.environ.get(env_var, default)
            return default

        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            if "SecretString" in response:
                value = response["SecretString"]
            else:
                import base64

                value = base64.b64decode(response["SecretBinary"]).decode("utf-8")

            self._set_cache(cache_key, value)
            return value
        except self.client.exceptions.ResourceNotFoundException:
            logger.warning("Secret not found: %s", secret_name)
        except Exception as exc:
            logger.error("Error retrieving secret %s: %s", secret_name, exc)

        if self.use_env_fallback:
            env_var = self._secret_name_to_env_var(secret_name)
            return os.environ.get(env_var, default)

        return default

    def get_secret_or_env(
        self,
        secret_name: str,
        *,
        env_var: str,
        default: str | None = None,
    ) -> str | None:
        value = self.get_secret_sync(secret_name, default=default)
        if value:
            return value
        return os.environ.get(env_var, default)


_secrets_manager: SecretsManager | None = None


def get_secrets_manager(
    *,
    region: str | None = None,
    endpoint_url: str | None = None,
    **kwargs: Any,
) -> SecretsManager:
    global _secrets_manager

    if _secrets_manager is None:
        _secrets_manager = SecretsManager(
            region=region,
            endpoint_url=endpoint_url,
            **kwargs,
        )

    return _secrets_manager


def reset_secrets_manager() -> None:
    global _secrets_manager
    _secrets_manager = None


class SecretNames:
    """Environment-aware secret names for akin-chat."""

    @staticmethod
    def prefix() -> str:
        return f"akin/{get_secret_environment()}/chat"

    @staticmethod
    def db_url() -> str:
        return f"{SecretNames.prefix()}/db_url"

    @staticmethod
    def openai_api_key() -> str:
        return f"{SecretNames.prefix()}/openai_api_key"

    @staticmethod
    def pinecone_serverless_api_key() -> str:
        return f"{SecretNames.prefix()}/pinecone_serverless_api_key"

    @staticmethod
    def voyage_api_key() -> str:
        return f"{SecretNames.prefix()}/voyage_api_key"
