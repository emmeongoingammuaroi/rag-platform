# RAG Platform

## Project Overview

Production-ready RAG (Retrieval-Augmented Generation) platform. Users upload documents (PDF/DOCX/TXT/MD), documents are processed asynchronously (extract → chunk → embed → store in vector DB), then users chat with AI that retrieves relevant context from their documents.

**Stack:** Python 3.12 + FastAPI | PostgreSQL + SQLAlchemy 2.0 | Redis + Celery | Qdrant | OpenAI API

**Run:** `make up` (or `docker compose up`) → 7 services (postgres, redis, qdrant, api, celery_worker, celery_beat, web)

**Monorepo:** `backend/` (Python/FastAPI) | `web/` (Vite + React SPA) | `infra/` (Terraform placeholder)

---

## Architecture Rules

### Layered Responsibility

```
app/
  api/          → FastAPI routers. Thin — validate input, call service, return response.
  services/     → Business logic. Orchestrate between models, external APIs, tasks.
  models/       → SQLAlchemy ORM models. DB schema only, no business logic.
  schemas/      → Pydantic models. Request/response validation.
  tasks/        → Celery async tasks. Heavy processing (document ingestion, indexing).
  rag/          → RAG pipeline modules. Chunking, embedding, retrieval, reranking.
  utils/        → Shared utilities. Vector DB client, document extractor.
  core/         → App config, auth, logging, Celery setup.
  db/           → Database engine, session factory, base model.
  eval/         → Evaluation pipeline. Metrics, dataset, runner.
```

### Key Principles

- **Async everywhere** — FastAPI + async SQLAlchemy (asyncpg) + async OpenAI client
- **Heavy work → Celery** — Document extraction, chunking, embedding run in Celery workers, not in request cycle
- **User data isolation** — Vector search MUST filter by user_id. Users only see their own documents.
- **RAG pipeline is modular** — Each stage (chunk, embed, rerank, hyde) is toggleable via config flags
- **Auth via FastAPI-Users** — Don't write custom JWT logic

### What Goes Where

- **User auth, registration, password reset** → `app/core/users.py` (FastAPI-Users config)
- **Document CRUD** → `app/services/document.py` (service) + `app/api/v1/documents.py` (router)
- **Document processing** → `app/tasks/` (Celery) calling `app/rag/ingest.py`
- **Text extraction (PDF/DOCX/TXT)** → `app/utils/document_extractor.py`
- **RAG retrieval pipeline** → `app/rag/retriever.py` (orchestrate: hyde → embed → search → rerank)
- **LLM chat calls** → `app/services/ai.py`
- **Vector DB operations** → `app/utils/vector_db.py`
- **Conversation/message CRUD** → `app/services/chat.py`
- **Config/env vars** → `app/core/config.py` (single Pydantic Settings class)

### Do NOT

- Write custom JWT auth logic (use FastAPI-Users)
- Do heavy processing in request handlers (use Celery tasks)
- Search vectors without user_id filter (data leak)
- Auto-commit in DB session dependency (explicit commit in service/router)
- Connect to external services on module import (use lazy init)
- Leak exception details in production responses (`detail=str(e)` → generic message)
- Use `datetime.utcnow()` (use `datetime.now(timezone.utc)`)
- Use `@app.on_event()` (use `lifespan` context manager)

---

## Coding Conventions

### Python

- **Python 3.12**, type hints on all function signatures
- **Pydantic v2** for all schemas (BaseModel, Field, validators)
- **SQLAlchemy 2.0** mapped_column style (not legacy Column)
- **No classes for simple services** — use static methods or plain functions
- **Imports:** absolute from project root (`from app.services.document import DocumentService`)
- **Error handling:** HTTPException in routers, raise/return in services
- **Tests:** pytest + pytest-asyncio, files in `tests/`
- **Formatting:** ruff (line-length=100, replaces black+isort+flake8), mypy for type checking

### Async Patterns

- DB sessions: `async with session` (context manager)
- OpenAI calls: `await client.chat.completions.create()`
- Celery tasks: sync function wrapping `asyncio.run()` for async logic
- Embeddings: batch up to 20 texts per API call

### Docker

- Python image: `python:3.12-slim`, multi-stage build, non-root user
- All env vars via `.env` + docker-compose `env_file`
- Healthchecks on all services
- Pin image versions (no `latest` tag)

---

## RAG Pipeline

### Ingest (async via Celery)
```
upload → extract text (PDF/DOCX/TXT/MD) → chunk → embed → upsert to Qdrant
```

### Retrieval
```
query → [HyDE expand] → embed → Qdrant search (filtered by user_id)
  → top-20 → [rerank] → top-5 → inject as context → LLM generate
```

- **Chunker:** Recursive text splitter, chunk_size=512, overlap=50. Sentence-aware.
- **Embedder:** OpenAI text-embedding-3-small (1536d), batch up to 20.
- **Reranker:** cross-encoder/ms-marco-MiniLM-L-6-v2, lazy-loaded. Toggle: `RERANKER_ENABLED`
- **HyDE:** LLM generates hypothetical answer, embed that instead of raw query. Toggle: `HYDE_ENABLED`
- **Hybrid search:** Dense + sparse (BM25) via Qdrant. Toggle: `HYBRID_SEARCH_ENABLED`

---

## Environment Variables

```
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/ai_rag_db
DB_ECHO=false

# Redis
REDIS_URL=redis://redis:6379/0

# Security
SECRET_KEY=<random-string>

# OpenAI
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_MAX_TOKENS=2000

# Vector DB
QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION_NAME=documents
VECTOR_DIMENSION=1536

# RAG Toggles
RERANKER_ENABLED=true
HYDE_ENABLED=true
HYBRID_SEARCH_ENABLED=false

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60

# Storage
STORAGE_DIR=storage
STORAGE_BACKEND=local

# Observability
OBSERVABILITY_PROVIDER=none
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=

# App
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
LOG_FORMAT=json
```

---

## Project Structure

```
backend/                — Python/FastAPI backend
  app/
    core/              — config, auth, logging, celery
    db/                — SQLAlchemy engine, session, base model
    models/            — ORM models (user, document, conversation, message)
    schemas/           — Pydantic request/response models
    api/v1/            — FastAPI routers (auth, users, documents, ai)
    services/          — business logic (document, ai, chat)
    tasks/             — Celery tasks (document ingestion, indexing)
    rag/               — RAG pipeline (chunker, embedder, reranker, hyde, retriever, ingest)
    utils/             — vector_db client, document_extractor
    eval/              — evaluation pipeline (metrics, dataset, runner)
  alembic/             — DB migrations
  tests/               — pytest
  Dockerfile
  requirements.txt
  pyproject.toml       — ruff, mypy, pytest config
  Makefile             — backend-specific commands (lint, test, run)

web/                   — Vite + React SPA (TypeScript, Tailwind)
  src/
  Dockerfile           — multi-target (dev / prod)

infra/                 — Terraform placeholder (AWS: ECS, RDS, ElastiCache, ALB, S3)

docker-compose.yml     — orchestrates all services from root
Makefile               — root shortcuts (make up/down/build/migrate)
```

---

## API Endpoints

```
# Auth (FastAPI-Users)
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
POST   /api/v1/auth/forgot-password
POST   /api/v1/auth/reset-password

# Users
GET    /api/v1/users/me
PUT    /api/v1/users/me

# Documents
POST   /api/v1/documents/upload      — upload + async ingest
GET    /api/v1/documents              — list (paginated, user-scoped)
GET    /api/v1/documents/{id}         — get single
PUT    /api/v1/documents/{id}         — update + re-index
DELETE /api/v1/documents/{id}         — delete + remove vectors

# AI / Chat
POST   /api/v1/ai/chat               — direct LLM chat (streaming optional)
POST   /api/v1/ai/chat/rag           — RAG-enhanced chat
POST   /api/v1/ai/embeddings         — generate embeddings
POST   /api/v1/ai/embeddings/search  — semantic search

# Conversations
POST   /api/v1/ai/conversations                        — create
GET    /api/v1/ai/conversations                        — list
GET    /api/v1/ai/conversations/{id}                   — get with messages
PATCH  /api/v1/ai/conversations/{id}                   — update title
DELETE /api/v1/ai/conversations/{id}                   — delete
POST   /api/v1/ai/conversations/{id}/messages          — send message (RAG optional)

# System
GET    /health                        — liveness check
GET    /ready                         — readiness check (verify DB, Redis, Qdrant)
```
