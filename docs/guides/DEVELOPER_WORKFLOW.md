# Developer workflow

## Clone and start

Install Docker Engine with Compose, Git and Node 22. Docker daemon access is required;
follow your machine's policy rather than copying sudo commands from other projects.
Python/uv are optional if backend development and testing stay inside containers.

```bash
git clone <repository-url>
cd viweb-ai
cp .env.example .env
docker compose up -d --build --wait
npm ci
npm run dev
```

Frontend: http://127.0.0.1:5173. API docs: http://127.0.0.1:8000/docs.
AI docs: http://127.0.0.1:8001/docs. PostgreSQL: `127.0.0.1:15432`.
Redis: `127.0.0.1:16379`. All published ports bind to loopback for local work.
The migration container runs before API/worker startup; no manual table creation.
The stack intentionally avoids PostgreSQL 5432 and Redis 6379 used by other local stacks.

The default backend stack contains six services: postgres, redis, migrate (one-shot),
api, ai-api and worker. A completed migration container is expected to exit with code 0.
MinIO and MLflow are not required for this public-catalogue foundation.

```bash
make tools                         # optional pgAdmin on port 15050
make docker-ping                   # submit health task; inspect worker logs
make docker-test                   # Python + live PostgreSQL checks
make docker-check                  # broad foundation checks via Docker
make docker-contracts              # business + AI OpenAPI snapshots
npm run typecheck
npm run build
docker compose logs -f api worker
```

Optional all-Docker frontend:

```bash
docker compose --profile frontend up -d --build frontend
```

Do not start a host frontend at the same port simultaneously. Frontend source changes
reload; API source changes reload; restart the worker after modifying task code.
Rebuild images after dependency changes. The AI API is separately restartable.
`docker compose down` preserves data; deleting volumes deletes local data.

## Host backend development

Install uv, run `make install`, then start only dependencies:

```bash
docker compose up -d postgres redis
make migrate
make api
# separate terminals
make inference
make worker
```

Stop corresponding Docker application containers before using the same host ports.
`make check` and `make contracts` are the broad local gates. To run them without host
Python, use the test service image:

```bash
docker compose run --rm test ruff check .
docker compose run --rm test ruff format --check .
docker compose run --rm test python scripts/export_openapi.py --check
```

## Working agreements

Hemachandran owns frontend screens/API calls; Siva owns API/database/jobs/deployment;
Akash owns AI/inference/hardware. Shared schemas require coordinated review and snapshot
regeneration. Keep dependencies per application and review interfaces before consumers.

Each feature should include a usable workflow, failure behaviour, relevant tests and
honest documentation. No login/customer tables/training are implemented by this folder
reorganisation. Follow the v0.1 checklist for the remaining release work.

## Troubleshooting

Run `docker compose ps -a` and inspect the failing service logs. If migration fails,
fix/re-run it before restarting dependants. Check `.env` credentials against the initial
PostgreSQL volume: changing environment variables does not change existing DB users.
For port conflicts, change both published ports and the corresponding host URL settings.
Inside containers use service names and container ports, never localhost for another service.
Do not delete volumes as a first response to a startup error.
