# Akin Chat

A multi-agent AI platform built on the [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/), serving a chat agent, a RAG-backed knowledge assistant, and a multi-phase web research pipeline through a single FastAPI application.

## Documentation

| Doc | Description |
|-----|-------------|
| [Setup & Running Guide](docs/README.md) | Docker setup, environment variables, database schema, full stack overview |
| [API Endpoints](docs/API_ENDPOINTS.md) | All HTTP endpoints, request/response shapes, and SSE streaming events |
| [RAG Pipeline](docs/RAG.md) | How the assistant agent retrieves and reranks knowledge base documents |
| [Environment & Secrets](docs/ENVIRONMENT.md) | Local, LocalStack prod simulation, and real AWS configuration |

## Quick Start

Two ways to run locally with Docker. See [Environment & Secrets](docs/ENVIRONMENT.md) for how configuration is loaded in each case.

### Option 1 — LocalStack prod simulation (Secrets Manager)

Simulates production: the app loads secrets from LocalStack with `ENVIRONMENT=prod`.

**1. Create env files**

`.env.localstack` — seeds LocalStack Secrets Manager:

```dotenv
ENVIRONMENT=prod
DATABASE_URL=postgresql+asyncpg://akin_chat:akin_chat@postgres:5432/akin_chat
OPENAI_API_KEY=sk-...
PINECONE_SERVERLESS_API_KEY=pcsk_...
VOYAGE_API_KEY=pa-...
```

`.env.prod` — app AWS client config only:

```dotenv
ENVIRONMENT=prod
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_DEFAULT_REGION=us-east-1
AWS_ENDPOINT_URL=http://localstack:4566
```

**2. Point the app at `.env.prod`** in `docker-compose.yml`:

```yaml
env_file:
  - .env.prod
```

**3. Start LocalStack, then the app**

```bash
docker compose -f docker-compose.localstack.yml up -d
docker compose up --build
curl http://localhost:8000/health
```

LocalStack creates secrets under `akin/prod/chat/*` on startup. The app fetches them via boto3 using the AWS vars in `.env.prod`.

---

### Option 2 — Local only (no LocalStack)

Simplest setup: credentials come directly from env vars with `ENVIRONMENT=local`. No Secrets Manager.

**1. Create `.env.local`**

```bash
cat > .env.local <<'EOF'
ENVIRONMENT=local
OPENAI_API_KEY=sk-...
PINECONE_SERVERLESS_API_KEY=pcsk_...
VOYAGE_API_KEY=pa-...
EOF
```

**2. Point the app at `.env.local`** in `docker-compose.yml`:

```yaml
env_file:
  - .env.local
```

**3. Start the app**

```bash
# Create the shared Docker network once if LocalStack has never been run
docker network create network 2>/dev/null || true

docker compose up --build
curl http://localhost:8000/health
```

---

See [docs/README.md](docs/README.md) for the full setup guide.
