# RAG Platform API

Production-ready FastAPI backend with AI capabilities, vector database integration, and Retrieval-Augmented Generation (RAG) support.

## Features

- ✅ **FastAPI** with async/await architecture
- ✅ **SQLAlchemy 2.0** ORM with Alembic migrations
- ✅ **Pydantic v2** schemas and validation
- ✅ **JWT Authentication** with OAuth2
- ✅ **PostgreSQL** database
- ✅ **Redis** for caching and background jobs
- ✅ **OpenAI & Anthropic** integration
- ✅ **Qdrant** vector database for embeddings
- ✅ **RAG Pipeline** (chunking, embeddings, semantic search)
- ✅ **Streaming** chat responses
- ✅ **Docker & Docker Compose** setup
- ✅ **Pre-commit hooks** for code quality
- ✅ **Structured logging** (JSON format)

## Architecture

```
app/
├── core/           # Core configurations
├── db/             # Database setup
├── models/         # SQLAlchemy models
├── schemas/        # Pydantic schemas
├── api/            # API routes
├── services/       # Business logic
├── tasks/          # Background tasks (Celery)
└── utils/          # Utilities
```

## Quick Start

### 1. Clone and Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your credentials
```

### 2. Start Services with Docker

```bash
docker-compose up -d
```

This starts:
- PostgreSQL (port 5432)
- Redis (port 6379)
- Qdrant (port 6333)

### 3. Run Migrations

```bash
alembic upgrade head
```

### 4. Start Application

```bash
uvicorn app.main:app --reload
```

Or use Makefile shortcuts:

```bash
make run
make celery-worker
```

API will be available at: http://localhost:8000 (default)

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login and get JWT token
- `POST /api/v1/auth/refresh` - Refresh access token

### Users
- `GET /api/v1/users/me` - Get current user
- `PUT /api/v1/users/me` - Update current user

### AI Chat
- `POST /api/v1/ai/chat` - Chat completion (streaming supported)
- `POST /api/v1/ai/chat/rag` - RAG-enhanced chat

### Embeddings
- `POST /api/v1/ai/embeddings` - Generate embeddings
- `POST /api/v1/ai/embeddings/search` - Semantic search

### Documents
- `POST /api/v1/documents/upload` - Upload and process document
- `GET /api/v1/documents` - List documents
- `DELETE /api/v1/documents/{id}` - Delete document

Document ingestion runs asynchronously via Celery:

- `documents.ingest` - Extract text from uploaded file and trigger indexing
- `documents.index` - Chunk, embed, and upsert to Qdrant
- `documents.delete_vectors` - Delete vectors for a document

## Development

### Install Pre-commit Hooks

```bash
pre-commit install
```

### Run Tests

```bash
pytest
```

### Code Formatting

```bash
# Format code
black app/
isort app/

# Lint
flake8 app/
mypy app/
```

### Create Migration

```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## Environment Variables

See `.env.example` for all available configuration options.

Key variables:
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `SECRET_KEY` - JWT secret key
- `OPENAI_API_KEY` - OpenAI API key
- `QDRANT_URL` - Qdrant vector DB URL
- `BACKEND_CORS_ORIGINS` - Comma-separated list or JSON array of allowed origins (e.g. `http://localhost:3000,http://127.0.0.1:3000`)

## Docker Deployment

### Build and Run

```bash
docker-compose up --build
```

### CI/CD (GitHub Actions)

This repository includes a sample GitHub Actions pipeline at `.github/workflows/ci-cd.yml`:

- **CI**: runs `pytest` on pull requests.
- **CD** (on push to `main`): builds and pushes a Docker image to **GHCR**, then deploys via SSH by running `docker compose pull`, `docker compose up -d`, and `alembic upgrade head`.

#### Required GitHub Secrets

- `SSH_HOST` - Server hostname/IP
- `SSH_USER` - SSH username
- `SSH_PRIVATE_KEY` - SSH private key
- `SSH_PORT` - SSH port (e.g. `22`)
- `APP_DIR` - Absolute path on the server containing `docker-compose.yml`

#### Deployment image variables

The `docker-compose.yml` supports pulling a registry image via environment variables:

- `RAG_PLATFORM_IMAGE` (e.g. `ghcr.io/<owner>/rag-platform-api`)
- `RAG_PLATFORM_TAG` (e.g. a git SHA)

If not set, it falls back to a `latest` tag.

### Production Build

```bash
docker build -t rag-platform-api .
docker run -p 8000:8000 --env-file .env rag-platform-api
```

## License

MIT
