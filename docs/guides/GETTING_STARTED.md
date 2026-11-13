# Developer setup

Run all commands from the repository root. Windows developers: use Ubuntu on WSL2
with Docker Desktop WSL integration and keep the checkout inside the Linux filesystem.

## Prerequisites

Git, GNU Make, Docker Engine/Desktop with Compose, Node **22**, npm, and **uv**.
The workspace selects Python **3.11** through .python-version; uv can download it.
Install uv using the official instructions at https://docs.astral.sh/uv/getting-started/installation/.
Install Node 22 with your preferred manager; if using nvm, `nvm install` then `nvm use`
reads .nvmrc. You do not need a GPU for platform work or the edge simulator.

```bash
make doctor
make setup
make install
make up
make migrate
make dev
```

`make setup` copies .env.example only if .env does not already exist.
`make install` uses uv.lock and package-lock.json for reproducibility.
`make up` starts four persistent infrastructure services and waits for health.
MLflow and MinIO build local images on the first run; MinIO compiles from a pinned
upstream release and can take several minutes. Docker needs network access for
images; MinIO's bucket is intentionally not created until object-upload implementation.
`make migrate` creates the organisation table; it does not create fake users or tenants.
`make dev` runs API and web in the foreground. Ctrl-C stops them.

## Terminals and ports

| Process | Command | Address / check |
| --- | --- | --- |
| Web | `make web` | http://127.0.0.1:5173 |
| API | `make api` | http://127.0.0.1:8000/docs |
| Inference | `make inference` | http://127.0.0.1:8001/docs |
| Worker | `make worker` | Logs; Redis must be running |
| Worker smoke task | `make worker-ping` | Confirm task execution in worker terminal |
| Edge simulator | `make edge-dev` | Prints HOLD and exits; touches no hardware |
| PostgreSQL | `make up` | 127.0.0.1:15432, viws database |
| Redis | `make up` | 127.0.0.1:16379 |
| MinIO API / console | `make up` | http://127.0.0.1:19000 / :19001 |
| MLflow | `make up` | http://127.0.0.1:15000 |

Local credentials are in .env.example. They are not production credentials.
The Vite dev server proxies /api and /health to VITE_API_URL from the root .env;
restart it after changing that value. The browser does not call inference directly.
A deployment will need a reverse proxy for the same paths.

## Daily checks

```bash
make check
make contracts
```

Python tests run without Docker/GPU. CI additionally runs the migration against a
PostgreSQL service. Regenerate a changed API snapshot with:

```bash
PYTHONPATH=services/api uv run python scripts/export_openapi.py
```

Formatting: `make format`; TypeScript is strict and type-checked. ESLint/Prettier,
Tailwind, component libraries, schema form renderer, canvas annotations, browser tests
and generated clients can be added with the corresponding UI tasks; they are not
pretended to be configured here.

## Shut down and troubleshooting

`make down` stops containers and preserves named volumes. There is intentionally no
one-command destructive reset. Back up local data before manually removing volumes.

- Missing uv/Node: install prerequisites and rerun `make doctor`.
- Docker socket permission error: check Docker Desktop integration or your OS Docker
  group permissions; do not solve it by making the socket world-writable.
- Port collision: stop the conflicting local service or deliberately update Compose,
  .env and the relevant dev command together.
- Web says API unavailable: start `make api`, inspect /health/live and the API logs.
- Predict returns 503: expected until Akash implements approved package loading.
- Migration connection failure: run `make up`, check .env, then retry `make migrate`.
- Source folder itself is not a working Git repository: clone the real team remote or
  initialise it during T001; .git metadata supplied by this environment is not writable.

Infrastructure uses project-specific host ports (15432, 16379, 19000, 19001, 15000)
to coexist with other development stacks. Override the *_PORT variables in .env if
needed and update the corresponding URL settings. Container-internal ports remain standard.
