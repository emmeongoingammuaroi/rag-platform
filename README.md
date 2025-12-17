# AI RAG API

Production-ready FastAPI backend with AI capabilities, vector database integration, and RAG (Retrieval-Augmented Generation) support.

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
├── workers/        # Background tasks
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

API will be available at: http://localhost:8000

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

## Docker Deployment

### Build and Run

```bash
docker-compose up --build
```

### Production Build

```bash
docker build -t rag-platform-api .
docker run -p 8000:8000 --env-file .env rag-platform-api
```

## License

MIT
