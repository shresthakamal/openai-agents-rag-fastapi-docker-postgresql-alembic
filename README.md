# Akin Chat

A multi-agent AI platform built on the [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/), serving a chat agent, a RAG-backed knowledge assistant, and a multi-phase web research pipeline through a single FastAPI application.

## Documentation

| Doc | Description |
|-----|-------------|
| [Setup & Running Guide](docs/README.md) | Docker setup, environment variables, database schema, full stack overview |
| [API Endpoints](docs/API_ENDPOINTS.md) | All HTTP endpoints, request/response shapes, and SSE streaming events |
| [RAG Pipeline](docs/RAG.md) | How the assistant agent retrieves and reranks knowledge base documents |

## Quick Start

```bash
cp .env.example .env   # fill in API keys
docker compose up --build
curl http://localhost:8000/health
```

See [docs/README.md](docs/README.md) for the full setup guide.
