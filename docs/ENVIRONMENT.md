# Environment & Secrets Configuration

This document explains how akin-chat loads configuration across three modes: **local**, **LocalStack (prod simulation)**, and **real AWS production**.

---

## Overview

| Mode | Env file(s) | `ENVIRONMENT` | Where secrets come from | AWS client config |
|------|-------------|---------------|-------------------------|-------------------|
| Local development | `.env.local` | `local` | Directly from env vars | Secrets Manager **not used** |
| LocalStack prod simulation | `.env.prod` + `.env.localstack` | `prod` | AWS Secrets Manager via LocalStack | Region + endpoint + test credentials |
| Real AWS production | Task/instance env | `prod` | AWS Secrets Manager | Region only (IAM role) |

---

## 1. LocalStack prod simulation

Use this when you want the app to behave like production (fetch secrets from Secrets Manager) while running everything on your machine with Docker.

### How it works

There are **two env files**, each serving a different container:

#### `.env.localstack` → LocalStack container

Used by `docker-compose.localstack.yml` to seed Secrets Manager on startup via `scripts/localstack/init-aws.sh`.

```dotenv
ENVIRONMENT=prod

DATABASE_URL=postgresql+asyncpg://akin_chat:akin_chat@postgres:5432/akin_chat
OPENAI_API_KEY=sk-...
PINECONE_SERVERLESS_API_KEY=pcsk_...
VOYAGE_API_KEY=pa-...
```

The init script reads these values and creates secrets under:

```
akin/prod/chat/db_url
akin/prod/chat/openai_api_key
akin/prod/chat/pinecone_serverless_api_key
akin/prod/chat/voyage_api_key
```

#### `.env.prod` → Application container

Used by `docker-compose.yml` when simulating production. It sets **how the app talks to AWS**, not the application secrets themselves:

```dotenv
ENVIRONMENT=prod

AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_DEFAULT_REGION=us-east-1
AWS_ENDPOINT_URL=http://localstack:4566
```

Because `ENVIRONMENT=prod`, the app skips `.env` credentials for OpenAI/Pinecone/Voyage and instead loads them from Secrets Manager — exactly like real production.

### Why the AWS vars in `.env.prod` are required

LocalStack is not real AWS. The boto3 client still needs:

| Variable | Purpose |
|----------|---------|
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | LocalStack accepts dummy values (`test` / `test`) |
| `AWS_DEFAULT_REGION` | Required by boto3 (`NoRegionError` without it) |
| `AWS_ENDPOINT_URL` | Tells boto3 to call LocalStack instead of `secretsmanager.us-east-1.amazonaws.com` |

In `src/utils/secrets.py`, when `AWS_ENDPOINT_URL` is set the client is created in **LocalStack mode**:

```python
if self.endpoint_url:
    client_kwargs["endpoint_url"] = self.endpoint_url
    client_kwargs["aws_access_key_id"] = os.environ.get("AWS_ACCESS_KEY_ID", "test")
    client_kwargs["aws_secret_access_key"] = os.environ.get("AWS_SECRET_ACCESS_KEY", "test")
```

In `src/config.py`, settings pass these into the secrets manager at startup:

```python
secrets = get_secrets_manager(
    region=self.aws_default_region,
    endpoint_url=self.aws_endpoint_url,
)
```

### Run LocalStack prod simulation

Point the app at `.env.prod` in `docker-compose.yml`:

```yaml
env_file:
  - .env.prod
```

Then start both stacks:

```bash
docker compose -f docker-compose.localstack.yml up -d
docker compose up --build
```

---

## 2. Real AWS production

On ECS, EC2, or Lambda with `ENVIRONMENT=prod` and **no** `AWS_ENDPOINT_URL`.

### What you set in deployment

```dotenv
ENVIRONMENT=prod
AWS_DEFAULT_REGION=us-east-1
# Do NOT set AWS_ENDPOINT_URL
# Do NOT set AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY
```

### How authentication works

When `AWS_ENDPOINT_URL` is **not** set, `SecretsManager` creates the boto3 client **without** explicit credentials:

```python
else:
    auth_method = "IAM role (instance profile)"
    # boto3 uses the task/instance IAM role automatically
    self._client = boto3.client(**client_kwargs)
```

boto3 resolves the real AWS Secrets Manager endpoint for the region on its own. The task role must allow `secretsmanager:GetSecretValue` on:

```
akin/prod/chat/db_url
akin/prod/chat/openai_api_key
akin/prod/chat/pinecone_serverless_api_key
akin/prod/chat/voyage_api_key
```

If `AWS_ACCESS_KEY_ID` is present in a non-local environment, it is **ignored** and a warning is logged — production must use IAM roles.

### Config loading flow (`src/config.py`)

1. Pydantic reads env vars into `Settings`.
2. Because `ENVIRONMENT=prod`, `is_local` is `False`, so `load_secrets_from_aws` runs.
3. For each secret field not already set in env, `get_secret_or_env()` fetches from Secrets Manager.
4. Loaded values are stored on `settings` (e.g. `settings.openai_api_key`).
5. At startup, `app.py` registers the key with the Agents SDK via `set_default_openai_key(settings.openai_api_key)`.

Secret names are built by `SecretNames` in `src/utils/secrets.py`:

```python
def prefix() -> str:
    return f"akin/{get_secret_environment()}/chat"
```

`get_secret_environment()` maps `ENVIRONMENT=prod` → secret namespace `prod`.

---

## 3. Local development

The simplest mode — no AWS involved.

### `.env.local`

```dotenv
ENVIRONMENT=local

OPENAI_API_KEY=sk-...
PINECONE_SERVERLESS_API_KEY=pcsk_...
VOYAGE_API_KEY=pa-...
```

### What happens in code

When `ENVIRONMENT=local`, `Settings.is_local` is `True` and the secrets validator returns immediately:

```python
if self.is_local:
    return self
```

All credentials are read directly from environment variables by pydantic-settings. Secrets Manager is never called.

Use this for day-to-day development:

```yaml
# docker-compose.yml
env_file:
  - .env.local
```

```bash
docker compose up --build
```

---

## Quick reference: decision tree

```
ENVIRONMENT=local?
  └─ Yes → use .env.local, no Secrets Manager

ENVIRONMENT=prod + AWS_ENDPOINT_URL set?
  └─ Yes → LocalStack simulation
           • Seed secrets: .env.localstack
           • App AWS config: .env.prod (region + endpoint + test keys)
           • App secrets: fetched from LocalStack Secrets Manager

ENVIRONMENT=prod + no AWS_ENDPOINT_URL?
  └─ Yes → Real AWS
           • Set AWS_DEFAULT_REGION only
           • IAM role provides credentials
           • Secrets fetched from real Secrets Manager
```

---

## Files

| File | Committed | Purpose |
|------|-----------|---------|
| `.env.local` | No (gitignored) | Local dev credentials |
| `.env.prod` | No (gitignored) | App AWS client config for LocalStack simulation |
| `.env.localstack` | No (gitignored) | Secret values seeded into LocalStack |
| `.env.example` | Yes | Template for local dev |

---

## Related code

| File | Role |
|------|------|
| `src/config.py` | Settings model, skips AWS when local, loads secrets when not |
| `src/utils/secrets.py` | boto3 client, LocalStack vs IAM auth, `SecretNames` |
| `src/app.py` | Registers `settings.openai_api_key` with Agents SDK at startup |
| `scripts/localstack/init-aws.sh` | Creates secrets in LocalStack from `.env.localstack` |
| `docker-compose.localstack.yml` | LocalStack service |
| `docker-compose.yml` | App + Postgres |
