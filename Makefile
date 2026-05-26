.PHONY: help up down restart logs shell migrate migrate-down test lint fmt check fresh

help:
	@echo "ExoCortex — available commands:"
	@echo "  up           Start all services"
	@echo "  down         Stop all services"
	@echo "  restart      Restart API service"
	@echo "  logs         Tail API logs"
	@echo "  shell        Open Python shell in API container"
	@echo "  migrate      Run pending migrations"
	@echo "  migrate-down Rollback last migration"
	@echo "  test         Run test suite with coverage"
	@echo "  lint         Run ruff + mypy"
	@echo "  fmt          Auto-fix formatting"
	@echo "  check        lint + test (CI equivalent)"
	@echo "  fresh        Destroy volumes and rebuild from scratch"

up:
	docker compose up -d
	@echo "Services started. API: http://localhost:8000/api/docs | Grafana: http://localhost:3001 | Keycloak: http://localhost:8080"

down:
	docker compose down

restart:
	docker compose restart api

logs:
	docker compose logs -f api

shell:
	docker compose exec api python

migrate:
	docker compose exec api alembic upgrade head

migrate-down:
	docker compose exec api alembic downgrade -1

test:
	docker compose exec api pytest tests/ -v --cov=app --cov-report=term-missing --cov-fail-under=80

lint:
	docker compose exec api ruff check app/ tests/
	docker compose exec api mypy app/

fmt:
	docker compose exec api ruff check --fix app/ tests/
	docker compose exec api ruff format app/ tests/

check: lint test

fresh:
	docker compose down -v
	docker compose up -d --build
	@echo "Waiting for services..."
	@sleep 15
	docker compose exec api alembic upgrade head
