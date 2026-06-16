class SecretsManager:
    def __init__(self) -> None:
        import boto3

        self._client = boto3.client("secretsmanager")

    def get_secret_sync(self, secret_name: str) -> str | None:
        try:
            response = self._client.get_secret_value(SecretId=secret_name)
            secret = response.get("SecretString")
            return secret if secret else None
        except self._client.exceptions.ResourceNotFoundException:
            return None
        except Exception:
            return None


secrets_manager = SecretsManager()
