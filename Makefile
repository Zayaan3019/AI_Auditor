.PHONY: help install dev test lint format clean run docker-build docker-run deploy

help:
	@echo "AI Auditor - Makefile Commands"
	@echo "================================"
	@echo "install      - Install production dependencies"
	@echo "dev          - Install development dependencies"
	@echo "test         - Run tests with coverage"
	@echo "lint         - Run linters (flake8, mypy)"
	@echo "format       - Format code (black, isort)"
	@echo "security     - Run security checks"
	@echo "clean        - Clean build artifacts"
	@echo "run          - Run the application locally"
	@echo "docker-build - Build Docker image"
	@echo "docker-run   - Run with Docker Compose"
	@echo "docker-down  - Stop Docker Compose"
	@echo "benchmark    - Run performance benchmarks"

install:
	poetry install --only main

dev:
	poetry install --with dev

test:
	poetry run pytest tests/ -v --cov=app --cov-report=html --cov-report=term

test-fast:
	poetry run pytest tests/ -v -x

lint:
	poetry run flake8 app/ tests/
	poetry run mypy app/

format:
	poetry run black app/ tests/
	poetry run isort app/ tests/

security:
	poetry run bandit -r app/ -ll
	poetry run safety check

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ htmlcov/ .coverage

run:
	poetry run python -m app.main

docker-build:
	docker build -t ai-auditor:latest .

docker-run:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f ai-auditor

benchmark:
	poetry run python scripts/benchmark.py

migrate:
	@echo "Running migrations (if any)..."

env-example:
	cp .env.example .env
	@echo "Created .env file. Please edit with your configuration."

# CI/CD targets
ci-test: lint test security

ci-build: docker-build
	docker tag ai-auditor:latest ai-auditor:$(shell git rev-parse --short HEAD)

# Development helpers
watch:
	poetry run watchmedo auto-restart --directory=./app --pattern=*.py --recursive -- python -m app.main

shell:
	poetry shell

update:
	poetry update

lock:
	poetry lock

check:
	@echo "Checking code quality..."
	@make lint
	@echo "Running tests..."
	@make test
	@echo "Running security checks..."
	@make security
	@echo "✅ All checks passed!"
