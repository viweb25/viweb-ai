# VI WebSync AI Platform

Industrial AI SaaS and factory runtime. Customers create independent inspection
functions, teach them using their own datasets, approve model versions, and deploy
approved packages to a factory PC. Inspection continues locally when the cloud is unavailable.

**Start here:** [Product](docs/product/PRODUCT.md) · [Developer setup](docs/guides/GETTING_STARTED.md) ·
[Team ownership](docs/guides/TEAM.md) · [Siva's first steps](docs/planning/SIVA_START_HERE.md) ·
[Document review](docs/planning/SOURCE_REVIEW.md)

## Workspace

```text
apps/web/                 React + TypeScript web shell — Hemachandran
services/api/             FastAPI control plane + Alembic — Siva
services/worker/          Celery orchestration — Siva
services/inference/       Separate model execution service — Akash
services/edge-agent/      Factory runtime — Siva (sync/rules), Akash (hardware)
ai/                       Function plugins, dataset tooling, training — Akash
packages/schemas/         Versioned OpenAPI + JSON Schema — shared
packages/core/            Small shared Python primitives — shared
packages/labview/         LabVIEW integration extension points — Akash
infra/                    Local infrastructure, future hosting — Siva
tests/contracts/          Cross-service schema checks
docs/                     Product, architecture, onboarding, decisions, task plan
.github/                  CI and review templates
scripts/                  Read-only doctor and OpenAPI exporter
```

## Run locally

Use Linux/macOS or Windows WSL2, Docker Compose, Node 22, uv and Make.
From this root directory:

```bash
nvm install
nvm use
make setup
make install
make up
make migrate
make dev
```

Open http://127.0.0.1:5173 and http://127.0.0.1:8000/docs.
In separate terminals, `make inference`, `make worker`, or `make edge-dev`.
`make check` runs formatting/lint, Python tests and the web production build.
`make contracts` checks that OpenAPI matches the API.
See the setup guide for tool installation, ports and role-specific commands.

## What works today

API liveness, eight planned function templates, API-connected web shell, a first
organisation migration, Celery health task, explicit model-unavailable inference
response, edge simulation with HOLD, JSON Schema checks and CI definitions.
There are no trained models, customer endpoints, login, annotation, actual training,
PLC outputs, durable edge sync, billing or production deployment yet.
This is a Phase 0 foundation, not a production-ready SaaS.

The original starter automation is preserved under `docs/archive/starter/`.
Source documents remain untouched. See [cleanup mapping](docs/planning/CLEANUP.md).

Local check results and limits: [Validation](docs/planning/VALIDATION.md).

Shareable onboarding and complete file inventory: [Developer handbook (PDF)](docs/handbook/VI_WebSync_Developer_Handbook.pdf).
