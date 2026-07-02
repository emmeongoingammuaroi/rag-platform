.PHONY: help up down build logs restart clean migrate backend-test backend-lint web-dev

help:
	@echo "Available commands:"
	@echo "  make up             - Start all services"
	@echo "  make down           - Stop all services"
	@echo "  make build          - Build all Docker images"
	@echo "  make logs           - Tail logs for all services"
	@echo "  make restart        - Restart all services"
	@echo "  make clean          - Remove volumes and orphan containers"
	@echo "  make migrate        - Run database migrations"
	@echo "  make backend-test   - Run backend tests"
	@echo "  make backend-lint   - Run backend linters"
	@echo "  make web-dev        - Run frontend in dev mode (local)"

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

restart:
	docker compose restart

clean:
	docker compose down -v --remove-orphans

migrate:
	docker compose exec api alembic upgrade head

backend-test:
	cd backend && pytest

backend-lint:
	cd backend && make lint

web-dev:
	cd web && npm run dev
