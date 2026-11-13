# VI WebSync Developer Handbook

GitHub handoff, local setup and repository reference

Prepared for Siva, Hemachandran and Akash · 2026-11-13

## 1. Repository identity and current handoff status

Account supplied by Siva: https://github.com/viweb25

Repository supplied by Siva: https://github.com/viweb25/viweb-ai.git

Siva created viweb25/viweb-ai. This PDF does not prove a push succeeded or establish repository visibility. Pushing requires authenticated GitHub access; check final push status separately. Do not paste access tokens into chats, source files or Git remote URLs.

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

Siva has created viweb25/viweb-ai. Use this existing repository; do not create a second one. Invite Hemachandran and Akash using their actual GitHub accounts. Confirm repository visibility in GitHub settings.

If using GitHub CLI on your own machine, authenticate with its browser flow. Do not enter secrets in this document. The following commands are for a normal writable Git checkout/export, NOT the supplied read-only .git folder:

```bash
gh auth login --hostname github.com --git-protocol https --web
git init -b main
git add .
git diff --cached --stat
git status --short
git commit -m "chore(T003): add platform foundation and developer handbook"
git remote add origin https://github.com/viweb25/viweb-ai.git
git ls-remote origin
# If the remote has no branches, publish the initial commit:
git push -u origin main
git branch develop
git push -u origin develop
```

If the remote already exists, clone it first, copy the clean source into that checkout, review differences and commit on an appropriate branch. Never force-push over existing history. Do not run gh repo create again for an existing repository.

After publication, check GitHub Actions; replace commented CODEOWNERS entries with actual handles. Protect main and develop against direct pushes and require CI plus reviews. Shared schemas need two reviewers under team policy; the current commented file does not enforce this. Private-repository rule availability depends on the GitHub plan. The first scaffold commit is not a production release.

## 5. Every developer: clone from GitHub

First accept Siva's repository invitation. Copy the actual clone URL from GitHub's Code menu. Use the actual repository URL below; a private repository also requires collaborator access.

```bash
git clone https://github.com/viweb25/viweb-ai.git
cd viweb-ai
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

### Root configuration

- `.dockerignore` — Excludes local credentials, dependencies and generated artifacts from Docker build contexts.

- `.editorconfig` — Shared whitespace, UTF-8 and newline settings; Python uses four spaces and Make recipes use tabs.

- `.env.example` — Committed local-development configuration template. make setup copies it to the ignored .env; contains sample credentials and service URLs, not production secrets.

- `.gitignore` — Excludes local secrets, agent/cloud metadata, dependency folders, caches, datasets/model binaries and runtime databases from Git.

- `.nvmrc` — Selects Node major version 22 for nvm install and nvm use.

- `.python-version` — Selects Python 3.11 for uv; developers need not replace their system Python.

- `AGENTS.md` — Active instructions for coding assistants: architecture boundaries, scope, tenant isolation and truthful implementation status.

- `CLAUDE.md` — Short assistant entry point linking to active instructions; archived two-developer rules are historical only.

- `CONTRIBUTING.md` — Branch, review, contract, migration, validation and commercial dependency-review conventions.

- `Makefile` — Root command interface for setup, dependency installation, infrastructure, processes, migrations, tests, lint, formatting, build and contract checks.

- `README.md` — Team entry point: product, workspace map, startup commands and current implementation limits.

- `package-lock.json` — Exact npm dependency graph and integrity metadata; npm ci reproduces it.

- `package.json` — npm workspace root connecting apps/web, requiring Node 22, and forwarding dev/build/typecheck scripts.

- `pyproject.toml` — Shared Python development dependencies, uv workspace behavior, pytest import/search paths and Ruff settings; no GPU framework is installed.

- `uv.lock` — Resolved Python dependencies with versions and artifact hashes, consumed by uv sync --locked.

### .github

- `.github/CODEOWNERS` — Commented ownership template awaiting real GitHub handles. It currently does not request or enforce owner reviews.

- `.github/pull_request_template.md` — PR prompts for task ID, resulting behavior, validation, contract/migration impact and review.

- `.github/workflows/ci.yml` — GitHub Actions jobs for Python checks, 17 current tests, OpenAPI drift, PostgreSQL migration, TypeScript and web build on main/develop pushes and PRs.

### ai

- `ai/LICENSES.md` — Checklist for reviewing model code, weights and training-data provenance before commercial selection.

- `ai/datasets/README.md` — Akash: dataset converters and validators only. Customer data belongs in object storage, never this directory. Status: extension point; production implementation is not included.

- `ai/tests/test_interface.py` — Ensures the incomplete abstract function cannot be instantiated.

- `ai/training/README.md` — Akash: reproducible recipes, frozen dataset splits, metrics, MLflow tracking, evaluation, export and promotion comparisons. Status: extension point; production implementation is not included.

- `ai/vi_ml/__init__.py` — Python package marker and short module description; enables imports for this service or shared package.

- `ai/vi_ml/common/README.md` — Akash: shared image/signal primitives. Keep per-function mutable state isolated. Status: extension point; production implementation is not included.

- `ai/vi_ml/export/README.md` — Akash: ONNX export, numerical parity, hardware benchmarks and package manifests. Status: extension point; production implementation is not included.

- `ai/vi_ml/functions/anomaly_detection/README.md` — Owner: Akash. Stage: core_vision; implementation not shipped. Add the processing adapter, function-specific configuration schema, training/evaluation recipe, commercial-use dependency review, and golden fixtures before enabling it. The current catalogue only declares a name field; it is not a complete function wizard. Never share mutable model state across configured customer functions.

- `ai/vi_ml/functions/assembly_verification/README.md` — Owner: Akash. Stage: industrial; implementation not shipped. Add the processing adapter, function-specific configuration schema, training/evaluation recipe, commercial-use dependency review, and golden fixtures before enabling it. The current catalogue only declares a name field; it is not a complete function wizard. Never share mutable model state across configured customer functions.

- `ai/vi_ml/functions/base.py` — Abstract FunctionAI interface requiring load, predict and health; no actual model implementation.

- `ai/vi_ml/functions/dimension_measurement/README.md` — Owner: Akash. Stage: industrial; implementation not shipped. Add the processing adapter, function-specific configuration schema, training/evaluation recipe, commercial-use dependency review, and golden fixtures before enabling it. The current catalogue only declares a name field; it is not a complete function wizard. Never share mutable model state across configured customer functions.

- `ai/vi_ml/functions/image_classification/README.md` — Owner: Akash. Stage: core_vision; implementation not shipped. Add the processing adapter, function-specific configuration schema, training/evaluation recipe, commercial-use dependency review, and golden fixtures before enabling it. The current catalogue only declares a name field; it is not a complete function wizard. Never share mutable model state across configured customer functions.

- `ai/vi_ml/functions/object_counting/README.md` — Owner: Akash. Stage: industrial; implementation not shipped. Add the processing adapter, function-specific configuration schema, training/evaluation recipe, commercial-use dependency review, and golden fixtures before enabling it. The current catalogue only declares a name field; it is not a complete function wizard. Never share mutable model state across configured customer functions.

- `ai/vi_ml/functions/object_detection/README.md` — Owner: Akash. Stage: core_vision; implementation not shipped. Add the processing adapter, function-specific configuration schema, training/evaluation recipe, commercial-use dependency review, and golden fixtures before enabling it. The current catalogue only declares a name field; it is not a complete function wizard. Never share mutable model state across configured customer functions.

- `ai/vi_ml/functions/ocr/README.md` — Owner: Akash. Stage: industrial; implementation not shipped. Add the processing adapter, function-specific configuration schema, training/evaluation recipe, commercial-use dependency review, and golden fixtures before enabling it. The current catalogue only declares a name field; it is not a complete function wizard. Never share mutable model state across configured customer functions.

- `ai/vi_ml/functions/predictive_maintenance/README.md` — Owner: Akash. Stage: prototype; implementation not shipped. Add the processing adapter, function-specific configuration schema, training/evaluation recipe, commercial-use dependency review, and golden fixtures before enabling it. The current catalogue only declares a name field; it is not a complete function wizard. Never share mutable model state across configured customer functions.

### apps

- `apps/web/README.md` — Owner: Hemachandran. React 18 + TypeScript + Vite, Node 22. From the repository root run `make web`; run `make api` in another terminal. The app currently displays the planned catalogue from the API and connectivity errors. No authentication, customer records or annotation workflows are implemented. Next: app navigation and identity integration (T016), project screens (T017), schema-driven function forms (T019), then dataset and annotation workflows. Add UI libraries when the relevant screen requires them; keep model/hardware logic out of browser code. Build with `make build`, type-check with `npm run typecheck`.

- `apps/web/index.html` — HTML document, page title and root mount node loading the React entry point.

- `apps/web/package.json` — React 18, Vite, TypeScript and React type dependencies; dev, typecheck and build commands.

- `apps/web/src/App.tsx` — Fetches API health and eight planned templates; shows connectivity/loading/failure state and the function roadmap. No customer CRUD or login.

- `apps/web/src/features/README.md` — Hemachandran: feature modules for auth, projects, assets, function-builder, datasets, annotation-studio, training, model-registry, deployments, monitoring, reports and administration. Add modules as tasks start. Status: extension point; production implementation is not included.

- `apps/web/src/main.tsx` — Mounts App inside React StrictMode and imports the stylesheet.

- `apps/web/src/shared/README.md` — Hemachandran: API client generated from OpenAPI, reusable UI, form rendering and WebSocket hooks. No model or PLC logic. Status: extension point; production implementation is not included.

- `apps/web/src/style.css` — Responsive visual styles for the current catalogue shell; no component library or Tailwind configuration yet.

- `apps/web/tsconfig.json` — Strict browser TypeScript checks, React JSX and bundler module resolution.

- `apps/web/vite.config.ts` — React Vite setup, port 5173 and /api plus /health proxy to the API URL from the root .env.

### docs

- `docs/architecture/ARCHITECTURE.md` — Architecture and boundaries. Maintained reference for the team; read it for the detailed policy or plan.

- `docs/architecture/DATA_MODEL.md` — Data model implementation guide. Maintained reference for the team; read it for the detailed policy or plan.

- `docs/decisions/0001-foundation.md` — ADR 0001: foundation and source reconciliation. Maintained reference for the team; read it for the detailed policy or plan.

- `docs/guides/GETTING_STARTED.md` — Developer setup. Maintained reference for the team; read it for the detailed policy or plan.

- `docs/guides/TEAM.md` — Team ownership and working agreements. Maintained reference for the team; read it for the detailed policy or plan.

- `docs/handbook/VI_WebSync_Developer_Handbook.md` — Editable source of this handbook; regenerated from the repository by the documentation script.

- `docs/handbook/VI_WebSync_Developer_Handbook.pdf` — Single shareable handbook: GitHub handoff, cloning, local setup, role commands, architecture and complete source inventory.

- `docs/handbook/file_descriptions.json` — Plain-language descriptions for important files, used by the automatically generated handbook inventory.

- `docs/handbook/handbook.template.md` — Editable narrative template for the PDF generator. The inventory is inserted automatically at the marked location.

- `docs/planning/CLEANUP.md` — Starter cleanup and migration map. Maintained reference for the team; read it for the detailed policy or plan.

- `docs/planning/SIVA_START_HERE.md` — Siva: repository lead starting checklist. Maintained reference for the team; read it for the detailed policy or plan.

- `docs/planning/SOURCE_REVIEW.md` — Review of the supplied development documents. Maintained reference for the team; read it for the detailed policy or plan.

- `docs/planning/VALIDATION.md` — Foundation validation. Maintained reference for the team; read it for the detailed policy or plan.

- `docs/planning/source-manifest.json` — Names, byte sizes and SHA-256 identifiers of the three original planning documents.

- `docs/planning/task-board.csv` — All 70 workbook tasks with owners, estimates, weeks, dependencies, acceptance criteria and unchanged source statuses.

- `docs/planning/workbook-snapshot.json` — Structured reference export of all 11 workbook sheets; cached formula values, not recalculated formulas or active assistant instructions.

- `docs/product/PRODUCT.md` — Product definition. Maintained reference for the team; read it for the detailed policy or plan.

- `docs/releases/README.md` — Release notes, signed-package references and acceptance evidence. No generated model binaries. Status: extension point; production implementation is not included.

- `docs/runbooks/README.md` — Operational procedures: incident response, backup/restore, deployment/rollback and offline recovery. Add tested procedures with each feature. Status: extension point; production implementation is not included.

- `docs/spikes/README.md` — Time-boxed experiments with owner, question, evidence and final decision. Status: extension point; production implementation is not included.

### Archived starter — historical only

- `docs/archive/starter/.claude/commands/daily.md` — Historical starter reference, preserved during cleanup. Not active configuration or instructions; do not run its old commands.

- `docs/archive/starter/.claude/commands/new-function-type.md` — Historical starter reference, preserved during cleanup. Not active configuration or instructions; do not run its old commands.

- `docs/archive/starter/.claude/commands/onboard.md` — Historical starter reference, preserved during cleanup. Not active configuration or instructions; do not run its old commands.

- `docs/archive/starter/.claude/commands/release-notes.md` — Historical starter reference, preserved during cleanup. Not active configuration or instructions; do not run its old commands.

- `docs/archive/starter/.claude/commands/review.md` — Historical starter reference, preserved during cleanup. Not active configuration or instructions; do not run its old commands.

- `docs/archive/starter/.env.example` — Historical starter reference, preserved during cleanup. Not active configuration or instructions; do not run its old commands.

- `docs/archive/starter/CLAUDE.md` — Historical starter reference, preserved during cleanup. Not active configuration or instructions; do not run its old commands.

- `docs/archive/starter/Makefile` — Historical starter reference, preserved during cleanup. Not active configuration or instructions; do not run its old commands.

- `docs/archive/starter/README.md` — Historical starter reference, preserved during cleanup. Not active configuration or instructions; do not run its old commands.

- `docs/archive/starter/bitbucket-pipelines.yml` — Historical starter reference, preserved during cleanup. Not active configuration or instructions; do not run its old commands.

- `docs/archive/starter/contracts/jobs/job.schema.json` — Historical starter reference, preserved during cleanup. Not active configuration or instructions; do not run its old commands.

- `docs/archive/starter/contracts/results/detection.schema.json` — Historical starter reference, preserved during cleanup. Not active configuration or instructions; do not run its old commands.

- `docs/archive/starter/docker-compose.local.yml` — Historical starter reference, preserved during cleanup. Not active configuration or instructions; do not run its old commands.

- `docs/archive/starter/infra/scripts/deploy.sh` — Historical starter reference, preserved during cleanup. Not active configuration or instructions; do not run its old commands.

- `docs/archive/starter/ml/base.py` — Historical starter reference, preserved during cleanup. Not active configuration or instructions; do not run its old commands.

- `docs/archive/starter/ml/object_detection/template.json` — Historical starter reference, preserved during cleanup. Not active configuration or instructions; do not run its old commands.

### infra

- `infra/docker-compose.yml` — Local PostgreSQL, Redis, source-built MinIO and MLflow with dedicated loopback host ports, named persistent volumes and health checks.

- `infra/docker/minio.Dockerfile` — Builds a pinned upstream MinIO release using Go, then runs it as a non-root user with health-check utilities. Development compatibility choice; production storage remains undecided.

- `infra/docker/mlflow.Dockerfile` — Builds MLflow 2.22.0 for local experiment tracking, pins SQLAlchemy 2.0.57 for compatibility and runs as a non-root user.

- `infra/observability/README.md` — Siva: structured logs, correlation IDs, metrics and alerts. No customer imagery or secrets in telemetry. Status: extension point; production implementation is not included.

- `infra/scripts/README.md` — Siva: deployment/backup helpers once hosting is chosen. No deployment is automated by the skeleton. Status: extension point; production implementation is not included.

- `infra/terraform/README.md` — Siva: provider-neutral placeholder until cloud ADR. Add environment modules and remote encrypted state only when selected. Status: extension point; production implementation is not included.

### packages

- `packages/core/vi_core/__init__.py` — Python package marker and short module description; enables imports for this service or shared package.

- `packages/core/vi_core/results.py` — Decision enum and conservative safe_decision helper. Simulation primitive, not a complete sequence-aware production rule engine.

- `packages/labview/bench/README.md` — Akash: documented camera/PLC test configurations and acceptance evidence; no site credentials. Status: extension point; production implementation is not included.

- `packages/labview/plc/README.md` — Akash: handshake signal mapping, sequence, ready/busy/complete/valid/error and acknowledgement protocol. Status: extension point; production implementation is not included.

- `packages/labview/sites/README.md` — Akash: sanitized site configuration templates. Keep customer-specific addresses and secrets outside Git. Status: extension point; production implementation is not included.

- `packages/labview/tests/README.md` — Akash: bench and hardware integration test definitions, including timeout and sequence mismatch. Status: extension point; production implementation is not included.

- `packages/labview/toolkit/README.md` — Akash: future real LabVIEW VIs. No placeholder binary VIs are generated. Status: extension point; production implementation is not included.

- `packages/schemas/README.md` — Owners: all three developers; Siva coordinates API contracts and Akash function schemas. - openapi/api.json: generated public API snapshot; `make contracts` checks drift. - functions/catalogue.json: eight planned templates with minimal name-only schemas. - functions/manifest.schema.json: initial package manifest shape; signature protocol remains future work. - results/inspection.schema.json: v1 result envelope with separate execution/decision. - jobs/job.schema.json: future domain job wire shape, not the Celery health-task payload. - examples/inspection.json: explicit error/HOLD example; not production inspection evidence. - edge/: extension 

- `packages/schemas/edge/README.md` — Shared: future device configuration, deployment commands, heartbeat and LabVIEW wire contracts. Status: extension point; production implementation is not included.

- `packages/schemas/examples/inspection.json` — Synthetic model-not-loaded error/HOLD example for schema validation; not an actual customer inspection.

- `packages/schemas/functions/catalogue.json` — Eight planned function entries with name-only configuration schemas; these are not trained packages or complete wizards.

- `packages/schemas/functions/manifest.schema.json` — Initial package manifest schema: identity, version, minimum platform, licence features and artifact SHA-256 hashes. Signing protocol is future work.

- `packages/schemas/jobs/job.schema.json` — Future domain job shape including tenant, function, dataset version, task kind and lifecycle status; separate from the health-task message.

- `packages/schemas/openapi/api.json` — Checked-in generated OpenAPI snapshot of the current public API; make contracts detects drift.

- `packages/schemas/results/inspection.schema.json` — Versioned inspection envelope with tenant/project/function/model/configuration IDs, sequence, time, execution status, decision and payload. Errors/timeouts require HOLD.

### scripts

- `scripts/build_developer_handbook.py` — Generates this PDF and its editable Markdown source, plus a current per-file inventory; ReportLab is documentation-only tooling.

- `scripts/doctor.py` — Read-only checks for Git, Docker Compose, Node 22, npm and uv; does not install tools or show secrets.

- `scripts/export_openapi.py` — Generates the API snapshot or checks it with --check. Requires services/api on PYTHONPATH (set automatically by Make).

### services

- `services/api/README.md` — Owner: Siva. Run from repository root after make install. ```bash make up make migrate make api ``` Public static catalogue and liveness are implemented. Authentication, tenant CRUD, audit and object uploads are future tasks. First migration creates only the organisation root. See docs/guides/TEAM.md for the work split and docs/architecture/ARCHITECTURE.md for target interfaces. Run make test before requesting review.

- `services/api/alembic.ini` — Points Alembic to its migration directory and makes API imports available.

- `services/api/alembic/env.py` — Runs online async PostgreSQL migrations or generates offline SQL from Settings and ORM metadata.

- `services/api/alembic/script.py.mako` — Template used by Alembic when generating future migration revision files.

- `services/api/alembic/versions/0001_organisations.py` — First migration: organisations table, primary key and version constraint; includes downgrade. Do not downgrade data-bearing databases casually.

- `services/api/app/__init__.py` — Python package marker and short module description; enables imports for this service or shared package.

- `services/api/app/api/v1/README.md` — Siva: routers for authenticated customer resources. Derive org_id from verified identity; never trust a request-supplied tenant ID. Status: extension point; production implementation is not included.

- `services/api/app/core/settings.py` — Loads API settings from environment/root .env with Pydantic Settings; ignores unrelated workspace settings.

- `services/api/app/db.py` — Creates the async SQLAlchemy engine and session factory from the configured PostgreSQL URL.

- `services/api/app/jobs/README.md` — Siva: durable job state, idempotency, cancellation and transactional enqueue/outbox. Not implemented by the health task. Status: extension point; production implementation is not included.

- `services/api/app/main.py` — FastAPI application, typed health/template responses, JSON error handlers, GET /health/live and GET /api/v1/function-templates. Catalogue is public static metadata.

- `services/api/app/models/base.py` — Declarative SQLAlchemy metadata base for future ORM models.

- `services/api/app/models/organisation.py` — Initial Organisation ORM model with UUID ID, name and version fields. No users, memberships or project tables yet.

- `services/api/app/schemas/README.md` — Siva: request/response types. Export OpenAPI after changes and have shared contracts reviewed. Status: extension point; production implementation is not included.

- `services/api/app/services/README.md` — Siva: domain use cases and transaction boundaries. Keep routers thin; check tenant access in every use case. Status: extension point; production implementation is not included.

- `services/api/tests/test_api.py` — Checks liveness, eight explicitly planned templates and the standard error envelope for missing routes.

- `services/edge-agent/README.md` — Owner: Siva / Akash. Run from repository root after make install. ```bash make edge-dev ``` One-shot no-hardware simulation prints HOLD. This is not a running HTTP edge agent. Siva owns sync/rules; Akash owns hardware adapters and inference coordination. See docs/guides/TEAM.md for the work split and docs/architecture/ARCHITECTURE.md for target interfaces. Run make test before requesting review.

- `services/edge-agent/deploy/README.md` — Siva and Akash: industrial-PC/Windows packaging and service installation after test-bench acceptance. Status: extension point; production implementation is not included.

- `services/edge-agent/tests/test_decisions.py` — Checks missing/error/timeout/unknown results hold and valid successful decisions are preserved.

- `services/edge-agent/vi_edge/__init__.py` — Python package marker and short module description; enables imports for this service or shared package.

- `services/edge-agent/vi_edge/__main__.py` — One-shot fake-camera/fake-PLC simulation; prints HOLD and exits without any physical output.

- `services/edge-agent/vi_edge/adapters/base.py` — Python Protocol interfaces for camera capture and PLC trigger/result operations. No vendor drivers are implemented.

- `services/edge-agent/vi_edge/capture/README.md` — Akash: trigger/frame sequencing and acquisition scheduling for shared cameras. Status: extension point; production implementation is not included.

- `services/edge-agent/vi_edge/deployments/README.md` — Akash with Siva: signature/digest checks, machine-bound entitlements, atomic activation and rollback. Status: extension point; production implementation is not included.

- `services/edge-agent/vi_edge/rules/README.md` — Siva: versioned decisions over typed observations. Unknown, stale or failed results must never pass. Status: extension point; production implementation is not included.

- `services/edge-agent/vi_edge/sync/README.md` — Siva: SQLite durable outbox, idempotent result uploads, retries, device heartbeat and outbound TLS identity. Status: extension point; production implementation is not included.

- `services/inference/README.md` — Owner: Akash. Run from repository root after make install. ```bash make inference ``` Health and a 503 model-not-loaded prediction response are implemented. No weights are included. Add package verification, load/unload and real predictions with golden tests. See docs/guides/TEAM.md for the work split and docs/architecture/ARCHITECTURE.md for target interfaces. Run make test before requesting review.

- `services/inference/tests/test_inference.py` — Ensures missing-model prediction cannot be reported as successful.

- `services/inference/vi_inference/__init__.py` — Python package marker and short module description; enables imports for this service or shared package.

- `services/inference/vi_inference/main.py` — Separate inference FastAPI service: process health and POST /v1/predict returning HTTP 503 while no approved package exists.

- `services/inference/vi_inference/runtime/README.md` — Akash: verified package loading, model caching, concurrency budgets and predict lifecycle. Add no dynamic code loading from untrusted packages. Status: extension point; production implementation is not included.

- `services/worker/README.md` — Owner: Siva. Run from repository root after make install. ```bash make up make worker ``` Celery health task is implemented. In another terminal run make worker-ping. Durable training jobs, dispatch outbox and cancellation are future tasks. See docs/guides/TEAM.md for the work split and docs/architecture/ARCHITECTURE.md for target interfaces. Run make test before requesting review.

- `services/worker/handlers/README.md` — Siva: dataset preparation, quality, training dispatch, evaluation and export handlers. Call ai/ code rather than embedding models here. Status: extension point; production implementation is not included.

- `services/worker/tests/test_worker.py` — Runs the smoke task eagerly without Redis to check its behavior.

- `services/worker/worker/__init__.py` — Python package marker and short module description; enables imports for this service or shared package.

- `services/worker/worker/app.py` — Celery application with JSON serialization, project Redis broker and vi.health.ping smoke task. Not a training pipeline.

- `services/worker/worker/enqueue.py` — Queues a health task and prints its ID; check worker logs to confirm execution.

### tests

- `tests/contracts/test_schemas.py` — Validates schema definitions, the example result, rejected error/PASS combinations and planned template configuration constraints.


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
