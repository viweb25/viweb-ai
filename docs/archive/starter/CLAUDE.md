# VI Websync AI - project guide for Claude Code

## What we are building
A universal AI vision & industrial intelligence platform for factories. One platform; each customer
creates many independent **AI functions** (object detection, classification, anomaly detection,
dimension measurement, OCR, counting, assembly verification, later time-series / predictive maintenance).
Every function has its own configuration, classes, dataset versions, model versions, validation and deployment.

Hierarchy: Organization -> Site -> Project -> AI Function -> Dataset versions / Model versions / Deployments.
Assets (cameras, PLCs, sensors, edge PCs) are reusable and can feed several functions.

Teaching approach ("80/20"): start every function from a pre-trained model (the 80% of knowledge it already has)
and teach it the customer's specifics with their own labeled images (the 20%). Datasets are split 80% train /
20% test by default (configurable, stratified, grouped by capture session to avoid leakage).

## Team
- Dev-1 Full-stack & Cloud: apps/web, backend/, infra/, pipeline, builds and deploys (release captain).
- Dev-2 AI & Edge: packages/vi_ml, services/worker, edge/.
- LabVIEW/PLC team: labview/ (toolkit VIs, PLC handshake, bench, site records).
Only touch folders owned by the person you are helping, plus contracts/ when a change is agreed by both developers.

## Architecture
- apps/web: React 18 + TypeScript + Vite + Tailwind + shadcn/ui + TanStack Query. Forms for AI functions are
  rendered from JSON Schema templates (react-jsonschema-form). Annotation canvas uses react-konva.
- backend: Python 3.11 FastAPI, SQLAlchemy 2 (async) + Alembic, Pydantic v2, PostgreSQL 16. Auth: JWT access
  token + rotating refresh token in httpOnly cookie, argon2 hashes. Roles: Owner, Admin, Engineer, Operator, Viewer.
- Jobs: `jobs` table; workers claim with `SELECT ... FOR UPDATE SKIP LOCKED` through `/internal/jobs/*` endpoints
  (workers connect OUTBOUND over HTTPS; no inbound ports at customers or office).
- packages/vi_ml: one plugin per function type in `vi_ml/functions/<type>/`
  (template.json, plugin.py with predict/train/evaluate, metrics.py, report.py). Registry in `vi_ml/functions/__init__.py`.
- services/worker: runs plugins for jobs (preview_detect, import_zip, quality, prelabel, train, evaluate, export).
  CPU image runs in Azure; GPU image runs on the office GPU PC.
- edge/vi_edge: runs approved models next to the camera; local REST + WebSocket for LabVIEW and the line screen;
  PLC handshake (ready/busy/complete/valid/error, sequence, timeout); SQLite outbox; sync when online.
- Storage: Azure Blob (Azurite locally). Raw data is immutable; derived data is versioned.
- Cloud: Azure Container Apps (api, worker-cpu, migrate job), Static Web Apps (web), PostgreSQL Flexible Server,
  Blob Storage, Container Registry, Key Vault, App Insights.

## Commands
- `make up` / `make down` / `make reset`  local Postgres, Azurite, Mailpit
- `make install`  pnpm install + uv sync
- `make migrate` / `make seed`  database
- `make dev`  API :8000 (/docs) + web :5173
- `make worker`  AI worker on this machine   |   `make edge-dev`  edge with fake camera + fake PLC
- `make test` / `make lint`  run before every push

## Rules (always)
1. Plan first: list files to change, API/DB changes and risks; wait for OK before editing.
2. Every table has `org_id`; every query is scoped to the current user's organization; add an isolation test.
3. A missing, failed or timed-out AI result is NEVER treated as PASS (edge, PLC handshake, API, UI).
4. Contracts in contracts/ are the source of truth between web, API, worker, edge and LabVIEW. Do not change
   them without saying so explicitly in the plan.
5. Alembic migrations must be backward compatible for one release (add first, remove later).
6. No secrets in code, logs, tests or prompts. Use settings + Key Vault.
7. Every change has tests. Keep functions small; follow the existing folder pattern.
8. New AI function type = new plugin folder + template.json + tests. No special-case UI code.
9. Use only libraries/models with licenses that allow commercial closed-source use; record new ones in
   packages/vi_ml/LICENSES.md (Ultralytics YOLO is AGPL: do not use without a commercial license).

## Git
Branches: d1/wNN-task, d2/wNN-task, lv/wNN-task, hotfix/vX.Y.Z. Commits: `feat(api): ...`, `fix(ml): ...`.
main is always deployable. Merge -> staging. Tag vX.Y.0 -> production (manual approval). Release every Friday.

## Definition of done
Code + tests green, works locally end-to-end, PR reviewed by the other developer, contracts updated if needed,
notes for the 4 PM daily connect, Excel row status = Done.
