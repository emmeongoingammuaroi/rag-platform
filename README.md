# RAG Platform

Production-ready Retrieval-Augmented Generation platform. Upload documents, chat with AI that retrieves relevant context from your files.

## Stack

| Layer           | Tech                                          |
| --------------- | --------------------------------------------- |
| API             | Python 3.12, FastAPI, Pydantic v2             |
| Database        | PostgreSQL, SQLAlchemy 2.0 (async)            |
| Background Jobs | Redis, Celery                                 |
| Vector DB       | Qdrant                                        |
| LLM             | OpenAI (gpt-4o-mini, text-embedding-3-small)  |
| Auth            | FastAPI-Users (JWT)                           |
| Frontend        | Vite + React + TypeScript + Tailwind          |

## Quick Start

```bash
# Clone and start all services
docker compose up

# API:      http://localhost:8000
# Docs:     http://localhost:8000/docs
# Frontend: http://localhost:3000
```

Requires Docker and a `.env` file (copy from `.env.example`).

## Architecture

```
backend/
  app/
    api/v1/          — Routers (auth, users, conversations, documents)
    core/            — Config, auth (FastAPI-Users), rate limiting, middleware
    services/        — Business logic (llm, conversation, document)
    tasks/           — Celery tasks (document ingestion pipeline)
    models/          — SQLAlchemy ORM models
    schemas/         — Pydantic request/response schemas
    utils/           — Vector DB client, document extractor
    db/              — Engine, session factory

web/                 — React SPA
infra/               — Terraform (AWS deployment)
```

## API Endpoints

### Auth (FastAPI-Users)

```
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/forgot-password
POST   /api/v1/auth/reset-password
POST   /api/v1/auth/verify
```

### Users

```
GET    /api/v1/users/me
PATCH  /api/v1/users/me
```

### Documents

```
POST   /api/v1/documents/upload       — upload file + async ingest
GET    /api/v1/documents              — list (paginated, user-scoped)
GET    /api/v1/documents/{id}
PUT    /api/v1/documents/{id}         — update + re-index
DELETE /api/v1/documents/{id}         — delete + remove vectors
```

### Conversations (RAG-powered)

```
POST   /api/v1/conversations
GET    /api/v1/conversations
GET    /api/v1/conversations/{id}     — with messages
PATCH  /api/v1/conversations/{id}     — update title
DELETE /api/v1/conversations/{id}
POST   /api/v1/conversations/{id}/messages  — send message (auto RAG retrieval)
```

### System

```
GET    /health                        — liveness
GET    /ready                         — readiness (DB + Redis + Qdrant)
```

## RAG Pipeline

```
Ingest:  upload → extract text (PDF/DOCX/TXT/MD) → chunk → embed → upsert to Qdrant
Chat:    query → embed → vector search (user-scoped) → top-5 context → LLM generate
```

## Development

```bash
cd backend

# Lint + format
ruff check app/ tests/
ruff format app/ tests/

# Tests
pytest

# Migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## Environment Variables

| Variable                 | Description                     | Default                 |
| ------------------------ | ------------------------------- | ----------------------- |
| `DATABASE_URL`           | PostgreSQL connection (asyncpg) | required                |
| `REDIS_URL`              | Redis connection                | required                |
| `SECRET_KEY`             | JWT signing key                 | required                |
| `OPENAI_API_KEY`         | OpenAI API key                  | required                |
| `OPENAI_MODEL`           | Chat model                      | `gpt-4o-mini`           |
| `QDRANT_URL`             | Qdrant endpoint                 | `http://localhost:6333` |
| `RATE_LIMIT_PER_MINUTE`  | Per-IP rate limit               | `60`                    |
| `MAX_UPLOAD_SIZE_MB`     | Max file upload size            | `20`                    |
| `ENVIRONMENT`            | `development` or `production`   | `development`           |

## License

MIT
