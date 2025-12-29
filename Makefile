.PHONY: help install dev-install format lint test clean docker-build docker-up docker-down migrate run celery-worker

help:
	@echo "Available commands:"
	@echo "  make install       - Install production dependencies"
	@echo "  make dev-install   - Install development dependencies"
	@echo "  make format        - Format code with black and isort"
	@echo "  make lint          - Run linters (flake8, mypy)"
	@echo "  make test          - Run tests"
	@echo "  make clean         - Clean cache and build files"
	@echo "  make docker-build  - Build Docker images"
	@echo "  make docker-up     - Start Docker services"
	@echo "  make docker-down   - Stop Docker services"
	@echo "  make migrate       - Run database migrations"
	@echo "  make run           - Run development server"
	@echo "  make celery-worker - Run Celery worker (document indexing)"

install:
	pip install -r requirements.txt

dev-install:
	pip install -r requirements.txt
	pre-commit install

format:
	black app/ tests/
	isort app/ tests/

lint:
	flake8 app/ tests/
	mypy app/

test:
	pytest

run:
	uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

celery-worker:
	celery -A app.core.celery_app.celery_app worker -l info

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	rm -rf htmlcov/
	rm -rf dist/
	rm -rf build/

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

migrate:
	alembic upgrade head

run:
	uvicorn app.main:app --reload --port 8080
