SHELL := /bin/bash
UV ?= uv
COMPOSE := docker compose --env-file .env -f infra/docker-compose.yml
export PYTHONPATH := services/api:services/worker:services/inference:services/edge-agent:ai:packages/core
.DEFAULT_GOAL := help

help:
	@echo "setup | install | up | down | api | web | dev | inference | worker | worker-ping | edge-dev | migrate | test | lint | format | build | check | doctor | contracts"
setup:
	@test -f .env || cp .env.example .env
install:
	$(UV) sync --locked
	npm ci
up: setup
	$(COMPOSE) up -d --wait
down:
	$(COMPOSE) down
api:
	$(UV) run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
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
	$(UV) run alembic -c services/api/alembic.ini upgrade head
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
contracts:
	$(UV) run python scripts/export_openapi.py --check
doctor:
	python3 scripts/doctor.py
.PHONY: help setup install up down api web dev inference worker worker-ping edge-dev migrate test lint format build check doctor contracts
