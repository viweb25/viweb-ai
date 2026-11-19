# Run VI WebSync locally

Run the backend from this folder. The Compose entry point includes the repository's
shared topology, so root Make targets and this folder use the same containers and volumes.

```bash
cd deployment/docker-compose
docker compose up -d --build --wait
docker compose ps -a
docker compose logs -f api ai-api worker
```

Use `sudo docker compose` if your local Docker setup requires it. The stack starts
PostgreSQL, Redis, the one-shot Alembic migration, FastAPI, the inference service,
and the Celery worker. A migration container that exits with code 0 succeeded.

| Component | From the laptop | From another container |
|---|---|---|
| Business API and Swagger | http://127.0.0.1:8000/docs | `http://api:8000` |
| Inference Swagger | http://127.0.0.1:8001/docs | `http://ai-api:8001` |
| PostgreSQL | `127.0.0.1:15432` | `postgres:5432` |
| Redis | `127.0.0.1:16379` | `redis:6379` |
| Optional browser app | http://127.0.0.1:3000 | `frontend:3000` |
| Optional pgAdmin | http://127.0.0.1:15050 | `pgadmin:80` |

Use the repo-root `.env` for development overrides. Defaults also allow the backend
to start without an environment file. Published ports bind to loopback.

```bash
docker compose --profile frontend up -d --build --wait
docker compose --profile tools up -d pgadmin
docker compose exec -T worker python -m worker.enqueue
docker compose logs --tail=40 worker
docker compose exec -T redis redis-cli -n 1 --scan --pattern 'vi:catalogue:*'
```

To populate the cache, visit `http://127.0.0.1:8000/api/v1/function-templates` first.
For the camera demo and local model download, see the [root README](../../README.md).
For file-by-file execution flow, see the [backend guide](../../docs/guides/LOCAL_BACKEND.md).
