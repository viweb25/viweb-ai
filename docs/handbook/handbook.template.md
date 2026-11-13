# VI WebSync Developer Handbook

GitHub handoff, local setup and repository reference

Prepared for Siva, Hemachandran and Akash · 2026-11-13

## 1. Repository identity and current handoff status

Account supplied by Siva: https://github.com/viweb25

Intended private repository: {{REPOSITORY_URL}}

The repository name is the working choice from the development plan. This PDF does not prove the GitHub repository exists or that a push succeeded. Creation/push requires Siva's authenticated GitHub connection; final push status must be checked separately. Do not paste access tokens into chats, source files or Git remote URLs.

The supplied workspace has an unusable read-only .git directory. Its environment metadata is left untouched. A separate clean export can hold normal Git history for publication; future developers should clone the actual GitHub repository.

## 2. What this product does

VI WebSync is an industrial AI SaaS control plane plus a factory runtime. Customers configure independent inspection functions, collect/label their own data, train and evaluate candidates, approve versions and deploy packages beside cameras/PLCs. The target design keeps factory inspection operating locally during internet loss.

Hierarchy: Organisation → Project → Function → configuration/dataset/model versions → Deployment. Assets and class definitions are reusable; model state and customer datasets remain independent.

Current foundation: API health and static catalogue, React shell, initial organisation migration, Celery health task, separate inference stub, conservative edge simulator, schemas/tests and CI configuration.

Not implemented: login and tenant CRUD, complete function wizards, annotation, uploads, trained models, real training, package loading/signing, vendor hardware adapters, actual PLC outputs, durable edge sync, licensing, billing or production deployment.

## 3. Install prerequisites once

Use Linux/macOS or Ubuntu inside WSL2 on Windows. Run all project commands in a Linux/WSL terminal from the repository root. On Windows, enable Docker Desktop WSL integration and keep the clone in the Linux home directory.

Required tools: Git, GNU Make, Docker Engine/Desktop with Compose, Node 22 with npm, and uv. uv selects/downloads Python 3.11 from .python-version. A GPU is not needed for this scaffold; Akash configures CUDA and vendor SDKs separately when required.

Install Node with your preferred manager. With nvm already installed, run nvm install and nvm use after cloning; .nvmrc selects version 22. Install uv using its official installation page listed in References. On macOS install GNU Make if your normal make is unavailable/incompatible.

Verify tools:

```bash
git --version
docker compose version
docker info
node --version
npm --version
uv --version
make --version
```

## 4. Siva: initial GitHub publication

Create a private repository named vi-websync-ai under viweb25 if it does not exist. For a new empty remote, do not pre-create a README, .gitignore or licence: those files already exist here. Invite Hemachandran and Akash using their actual GitHub accounts.

If using GitHub CLI on your own machine, authenticate with its browser flow. Do not enter secrets in this document. The following commands are for a normal writable Git checkout/export, NOT the supplied read-only .git folder:

```bash
gh auth login --hostname github.com --git-protocol https --web
git init -b main
git add .
git diff --cached --stat
git status --short
git commit -m "chore(T003): add platform foundation and developer handbook"
gh repo create viweb25/vi-websync-ai --private --source=. --remote=origin --push
git branch develop
git push -u origin develop
```

If the remote already exists, clone it first, copy the clean source into that checkout, review differences and commit on an appropriate branch. Never force-push over existing history. Do not run gh repo create again for an existing repository.

After publication, check GitHub Actions; replace commented CODEOWNERS entries with actual handles. Protect main and develop against direct pushes and require CI plus reviews. Shared schemas need two reviewers under team policy; the current commented file does not enforce this. Private-repository rule availability depends on the GitHub plan. The first scaffold commit is not a production release.

## 5. Every developer: clone from GitHub

First accept Siva's repository invitation. Copy the actual clone URL from GitHub's Code menu. The intended URL below becomes usable only after the private repository is created and your account has access.

```bash
git clone {{REPOSITORY_URL}}
cd vi-websync-ai
git remote -v
git fetch origin
```

If Siva has published develop, switch to it before starting a feature:

```bash
git switch develop
git pull --ff-only origin develop
```

For private HTTPS access, use a credential manager, GitHub CLI browser authentication or a suitable personal access token through a secure credential prompt. Your GitHub account password is not used for Git HTTPS authentication. SSH is another option after configuring your own SSH key. Never embed a token in the clone URL.

## 6. First local setup

From the root containing Makefile, .env.example and pyproject.toml:

```bash
nvm install
nvm use
make doctor
make setup
make install
make up
make migrate
make dev
```

make setup creates .env only if it is missing. make install runs uv sync --locked and npm ci. make up builds/starts PostgreSQL, Redis, MinIO and MLflow, waiting for health. The initial MinIO source compilation and MLflow installation can take several minutes and require internet. make migrate applies the first organisation-table migration; it creates no user account. make dev runs API and web in the foreground.

Open http://127.0.0.1:5173 for the web shell and http://127.0.0.1:8000/docs for the API explorer. You should see the API-connected planned catalogue; there is no login yet. Ctrl-C stops the foreground web/API processes.

## 7. Terminals, services and exact ports

- Terminal A: make up, then make migrate. Infrastructure stays in Docker after the command exits.
- Terminal B: make api. API is http://127.0.0.1:8000, docs at /docs, liveness at /health/live.
- Terminal C: make web. Frontend is http://127.0.0.1:5173 and proxies /api plus /health to the API.
- Optional Terminal D: make inference. Separate runtime at http://127.0.0.1:8001/docs; prediction intentionally returns 503 while no model is loaded.
- Optional Terminal E: make worker. Keep running; in another terminal use make worker-ping and confirm the task succeeds in worker logs.
- One-shot edge check: make edge-dev. It prints simulation, fake camera/PLC and HOLD, then exits; no HTTP edge server or hardware output is started.
- PostgreSQL: 127.0.0.1:15432, database viws. Container-internal port is 5432.
- Redis: 127.0.0.1:16379. Container-internal port is 6379.
- MinIO S3 endpoint: http://127.0.0.1:19000; console: http://127.0.0.1:19001.
- MLflow: http://127.0.0.1:15000.

make dev combines terminals B and C. Do not also launch duplicate make api/make web processes on the same ports. Local sample credentials are in .env.example; they are not production credentials. MinIO bucket creation and upload APIs are future implementation.

## 8. Daily development workflow

```bash
git switch develop
git pull --ff-only origin develop
git switch -c feature/T014-project-api
# Implement the assigned task.
make check
make contracts
git status --short
git add path/to/changed-file
git commit -m "feat(T014): add project API"
git push -u origin feature/T014-project-api
```

Open a PR targeting develop. Link the task, explain resulting behavior and validation, and request the owner. Update the workbook after acceptance. main is for accepted releases; develop is integration. Do not commit .env, raw customer images, weights, local databases, node_modules or .venv.

After pulling a dependency change, rerun make install. After pulling a new migration, run make migrate before starting the API. No manual virtualenv activation is needed: Make uses uv run.

## 9. Who owns what and what to run

Siva — services/api, services/worker and infra; shared contract coordination; edge rules/sync, licensing and release readiness. Run make up, make migrate, make api and make worker. Next: auth/provider and permission matrix, tenant migrations and project/asset APIs. Test tenant isolation before exposing customer resources.

Hemachandran — apps/web, function forms, annotations and dashboards. Run make web and make api for the current catalogue. Next: navigation/identity integration, projects and schema-driven forms. Web code must not perform model inference or direct PLC communication.

Akash — ai, services/inference, hardware adapters in services/edge-agent and packages/labview. Run make inference and make edge-dev. Next: function-specific schemas, deterministic sample plugin, golden tests, then model/export/hardware work. The workbook assumes this role; confirm the actual assignment and skills.

All three — packages/schemas, packages/core, integration, reviews and acceptance. Run make check and make contracts. Changes to contracts must be coordinated with both producers and consumers.

## 10. How requests and data should flow

Current shell: Browser → Vite proxy → FastAPI catalogue/health. No database query is needed for catalogue rendering.

Target teaching: Browser → API → object storage and dataset snapshot → database job/outbox → Redis/Celery worker → AI training/evaluation → model registry → authorised approval → signed deployment.

Target inspection: PLC trigger/sequence → edge camera adapter → separate inference runtime → versioned rule decision → valid PLC handshake → durable local result/outbox → outbound cloud sync. Missing, failed, stale or timed-out results must not produce PASS. The included helper covers only basic simulation fallback, not the complete handshake.

PostgreSQL stores metadata. Object storage holds images/model packages. MLflow tracks experiments. Future edge SQLite holds the offline outbox. The scaffold creates only the organisation SQL table.

## 11. Configuration and persistence

.env.example is shareable; .env is local and ignored. DATABASE_URL, REDIS_URL, S3_ENDPOINT_URL and MLFLOW_TRACKING_URI describe host connections. *_PORT settings control Docker host mappings; update the matching URLs together if changing ports. VITE_API_URL controls Vite's API proxy; restart the dev server after editing it.

All Python paths required by the monorepo are exported by Makefile. Running a module directly may require PYTHONPATH; prefer make commands. For example, regenerate OpenAPI with:

```bash
PYTHONPATH=services/api uv run python scripts/export_openapi.py
make contracts
```

make down stops this project's containers and preserves named volumes. PostgreSQL, Redis, MinIO and MLflow data persist across normal stop/start. There is no destructive reset command. Deleting Docker volumes deletes local data; back up before doing that.

## 12. Troubleshooting and expected behavior

- Repository not found: confirm the repository was created, the URL is correct, your invitation is accepted and your authenticated account has access.
- fatal: not a git repository in the supplied folder: its .git metadata is read-only/unusable here. Use Siva's clean export or clone the published remote; do not delete protected metadata.
- Node engine error: run nvm use and confirm node --version reports v22.
- uv or make missing: install prerequisites, reopen the terminal and run make doctor.
- Docker unavailable: start Docker Desktop/Engine and verify Docker Compose support. Fix your OS/WSL Docker permissions; do not make its socket world-writable.
- Port already allocated: this stack uses dedicated ports. If still occupied, change the *_PORT variables and matching URLs in .env; leave other projects running.
- First make up is slow: MinIO compiles from a pinned source release; the image is cached after the first build. See its Dockerfile and the architecture decision for the upstream distribution change.
- MLflow fails to start: inspect its logs. Its Dockerfile pins SQLAlchemy 2.0.57 because the initial SQLAlchemy 2.1 resolution broke MLflow 2.22.0.
- Web reports API unavailable: run make api; check /health/live and the API terminal, then refresh the browser.
- Predict returns 503: expected, because there is no approved function package in this skeleton.
- Edge returns HOLD: expected, because there is no valid model result. It is not a fault to bypass.
- Worker task does not run: confirm Redis is healthy, make worker is running and REDIS_URL points to this project's port 16379.
- Migration fails: confirm Docker PostgreSQL is healthy and DATABASE_URL matches the local port and credentials.
- OpenAPI drift: regenerate the snapshot, review the API contract change, then run make contracts.

Useful diagnostics:

```bash
docker compose --env-file .env -f infra/docker-compose.yml ps
docker compose --env-file .env -f infra/docker-compose.yml logs --tail=80 mlflow
make doctor
make check
make contracts
```

## 13. Repository folder map

- apps/web: customer-facing browser shell; owner Hemachandran.
- services/api: control-plane API, settings, ORM, Alembic and API tests; owner Siva.
- services/worker: background task orchestration and smoke task; owner Siva.
- services/inference: independent model execution boundary; owner Akash.
- services/edge-agent: factory orchestration, adapters and future sync/rules; split ownership.
- ai: independent function implementations and training/data/export tooling; owner Akash.
- packages/schemas: shared wire formats and generated OpenAPI; shared review.
- packages/core: small runtime primitives without GPU/database/UI dependencies.
- packages/labview: future NI/LabVIEW toolkit and bench/site integration guides.
- infra: local Compose/images plus infrastructure extension-point READMEs.
- scripts: prerequisite checks, API snapshot export and this handbook generator.
- tests/contracts: cross-service schema/contract validation.
- docs/product: product scope and language.
- docs/architecture: runtime boundaries and planned data model.
- docs/guides: setup and named team responsibilities.
- docs/decisions: recorded working choices and unresolved architecture decisions.
- docs/planning: source review, workbook exports, cleanup and validation evidence.
- docs/handbook: the one PDF plus its editable source.
- docs/runbooks, docs/releases, docs/spikes: purpose-specific future operational records.
- docs/archive/starter: old configuration and instructions kept for history only.
- .github: CI and review templates; GitHub account settings are configured separately.

README-only extension folders deliberately contain no production implementation. In particular, infra/terraform has no Terraform resources, infra/observability has no monitoring deployment, packages/labview has no binary VIs, and the eight AI function folders have no trained models.

## 14. Complete current file inventory

The following inventory describes maintained source/configuration/documentation files, including hidden project configuration. It excludes local secrets, dependency installations, caches and runtime data. A README's description is derived from the actual README; these entries do not claim that future components already run.

{{INVENTORY}}

## 15. Local/generated things that are not source

- .env: your ignored machine-specific settings. Never commit it.
- .venv: uv-managed Python environment; regenerated by make install.
- node_modules and apps/web/node_modules: npm-installed packages; regenerated by npm ci.
- apps/web/dist: compiled static frontend output, generated by make build.
- __pycache__, .pytest_cache and .ruff_cache: disposable interpreter/test/lint caches.
- Docker named volumes: actual development metadata, broker state, objects and experiments; outside the source tree and not included by cloning.
- .git: Git history for a normal checkout. The supplied environment's read-only placeholder is not a usable checkout.
- .agents, .codex and .aws: environment-owned local metadata; excluded from GitHub export.

## 16. Acceptance and next steps

The foundation was verified with 17 tests, Ruff, strict TypeScript, frontend build and OpenAPI consistency. Its four local infrastructure services became healthy; the first PostgreSQL migration was queried and a real worker consumed a health task. These results do not prove customer workflows or industrial acceptance. See docs/planning/VALIDATION.md for details and limits.

Before onboarding is complete, Siva confirms a successful GitHub push, collaborator access, actual CODEOWNERS handles, branch rules and green hosted CI. Each developer then demonstrates clone → install → start → checks on their own machine. Pick one complete inspection vertical slice before broadening the function catalogue.

## 17. References and maintaining this PDF

Repository-specific source of truth: README.md, Makefile, .env.example, infra/docker-compose.yml, docs/guides/TEAM.md, docs/architecture/ARCHITECTURE.md and docs/planning/SOURCE_REVIEW.md. The original three planning documents remain unchanged outside this repository; their identities are in source-manifest.json.

GitHub cloning: https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository

GitHub HTTPS/SSH authentication: https://docs.github.com/en/get-started/git-basics/about-remote-repositories

uv installation: https://docs.astral.sh/uv/getting-started/installation/

MinIO upstream and source-build background: https://github.com/minio/minio

Regenerate after changing repository structure:

```bash
uv run --with reportlab==4.1.0 python scripts/build_developer_handbook.py
```

ReportLab is needed only to generate documentation, not to run the platform. The script updates this Markdown and the one PDF together. The inventory describes the current scaffold, not a future completed SaaS.
