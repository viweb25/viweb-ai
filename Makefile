SHELL := /bin/bash
UV ?= uv
COMPOSE := docker compose --env-file .env -f compose.yaml
export PYTHONPATH := services/api/src:services/worker:services/inference:services/edge-agent:ai:packages/core
.DEFAULT_GOAL := help

help:
	@echo "setup | install | up | tools | docker-check | docker-contracts | docker-test | docker-ping | down | api | web | dev | inference | worker | worker-ping | edge-dev | migrate | test | lint | format | build | check | doctor | contracts"
setup:
	@test -f .env || cp .env.example .env
install:
	$(UV) sync --locked
	npm ci
up: setup
	$(COMPOSE) up -d --build --wait
tools: setup
	$(COMPOSE) --profile tools up -d pgadmin
docker-test: setup
	$(COMPOSE) run --build --rm test
docker-check: docker-test
	$(COMPOSE) run --rm test ruff check --no-cache .
	$(COMPOSE) run --rm test ruff format --no-cache --check .
	$(COMPOSE) run --rm frontend npm run typecheck
	$(COMPOSE) run --rm frontend npm run build
docker-contracts: setup
	$(COMPOSE) run --rm test python scripts/export_openapi.py --check
docker-ping:
	$(COMPOSE) exec worker python -m worker.enqueue
down:
	$(COMPOSE) down
api:
	$(UV) run uvicorn vi_api.bootstrap:app --reload --host 127.0.0.1 --port 8000
web:
	npm run dev --workspace @vi/web
dev:
	$(MAKE) -j2 api web
inference:
	$(UV) run uvicorn vi_inference.main:app --reload --host 127.0.0.1 --port 8001
worker:
	$(UV) run celery -A worker.app:app worker --loglevel=info --pool=solo
worker-ping:
	$(UV) run python -m worker.enqueue
edge-dev:
	$(UV) run python -m vi_edge
migrate:
	$(UV) run alembic -c database/alembic.ini upgrade head
test:
	$(UV) run pytest -q
lint:
	$(UV) run ruff check .
	$(UV) run ruff format --check .
	npm run typecheck --workspace @vi/web
format:
	$(UV) run ruff check . --fix
	$(UV) run ruff format .
build:
	npm run build --workspace @vi/web
check: lint test build
export-contracts:
	$(UV) run python scripts/export_openapi.py
contracts:
	$(UV) run python scripts/export_openapi.py --check
doctor:
	python3 scripts/doctor.py
.PHONY: help setup install up down api web dev inference worker worker-ping edge-dev migrate test lint format build check doctor contracts export-contracts tools docker-test docker-ping docker-check docker-contracts
