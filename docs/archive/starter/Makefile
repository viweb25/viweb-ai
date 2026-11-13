COMPOSE = docker compose -f docker-compose.local.yml

up: ; $(COMPOSE) up -d
down: ; $(COMPOSE) down
reset:
	$(COMPOSE) down -v
	$(MAKE) up
	sleep 3 && $(MAKE) migrate seed
install:
	corepack enable && pnpm install
	uv sync --all-packages
migrate: ; cd backend && uv run alembic upgrade head
seed: ; cd backend && uv run python -m app.seed
api: ; cd backend && uv run uvicorn app.main:app --reload --port 8000
web: ; pnpm --filter web dev
dev: ; $(MAKE) -j2 api web
worker: ; uv run python -m worker --mode $${WORKER_MODE:-cpu}
edge-dev: ; cd edge && uv run python -m vi_edge --config config.local.yaml
test:
	cd backend && uv run pytest -q
	uv run pytest -q packages/vi_ml services/worker edge
	pnpm --filter web test
lint:
	uv run ruff check .
	pnpm --filter web lint
.PHONY: up down reset install migrate seed api web dev worker edge-dev test lint
