.PHONY: help install dev-install format lint test clean migrate run celery-worker

help:
	@echo "Available commands:"
	@echo "  make install       - Install production dependencies"
	@echo "  make dev-install   - Install development dependencies"
	@echo "  make format        - Format code with ruff"
	@echo "  make lint          - Run linters (ruff, mypy)"
	@echo "  make test          - Run tests"
	@echo "  make clean         - Clean cache and build files"
	@echo "  make migrate       - Run database migrations"
	@echo "  make run           - Run development server"
	@echo "  make celery-worker - Run Celery worker (document indexing)"

install:
	pip install -r requirements.txt

dev-install:
	pip install -r requirements.txt
	pre-commit install

format:
	ruff format app/ tests/
	ruff check --fix app/ tests/

lint:
	ruff check app/ tests/
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

migrate:
	alembic upgrade head
