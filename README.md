# VI WebSync AI Platform

Industrial AI SaaS and factory-runtime foundation for a three-person team. The target
workflow is configure -> collect -> annotate -> train -> evaluate -> approve -> deploy
-> monitor, with independent models per inspection function and local factory operation.

This repository is a developer foundation, not a production-ready inspection system.

## Start development

Run backend services in Docker and the frontend separately. Requires Docker Compose
and Node 22; Python/uv are optional for host backend development.

```bash
cp .env.example .env
docker compose up -d --build --wait
npm ci
npm run dev
```

Frontend: http://127.0.0.1:5173. Business API: http://127.0.0.1:8000/docs.
AI API: http://127.0.0.1:8001/docs. PostgreSQL: `127.0.0.1:15432`.
`make tools` starts optional pgAdmin at http://127.0.0.1:15050.
The migration job completes before the API and worker start. Development ports bind
only to loopback. See [developer workflow](docs/guides/DEVELOPER_WORKFLOW.md).

## Repository layout

```text
frontend/                      React + TypeScript, independent development server
  src/services/api/            HTTP client and API-specific calls
services/
  api/app/
    api/v1/controllers/        HTTP routes and dependency injection
    services/                  Use cases
    interfaces/                Dependency protocols
    repositories/              Storage implementations
    schemas/                   Typed wire contracts
    models/                    SQLAlchemy persistence models
    core/                      Settings
  inference/                   Separate AI inference backend
  worker/                      Celery jobs and Redis messaging
  edge-agent/                  Factory runtime simulation and future adapters
database/
  alembic.ini                  Migration entry point
  migrations/versions/         Ordered schema changes
  functions/                   Versioned PostgreSQL diagnostic functions
  tests/                       Live-database checks
ai/                            Function interfaces and future training implementations
packages/schemas/              Shared OpenAPI and JSON Schema contracts
packages/core/                 Small shared runtime primitives
packages/labview/              Integration extension points
infra/docker/                  Application Dockerfiles and development proxy settings
compose.yaml                   Backend stack; optional tools/frontend/test profiles
tests/contracts/               Cross-service schema checks
docs/                          Architecture, workflow, AI, deployment and release gates
```

Keep one repository for compatible contracts and easy onboarding. Applications remain
separate processes/images. Heavy AI dependencies must remain outside the business API.

## Validation

```bash
make docker-check
make docker-contracts
make docker-ping
npm run typecheck
npm run build
```

Host development: `make install`, `make check`, `make contracts`.
CI checks Python, frontend, API snapshot, migrations and database functions.
Actual results and limitations: [validation](docs/releases/FOUNDATION_VALIDATION.md).

## What exists

The API exposes a public static catalogue through controller/service/repository layers,
process liveness and migration-aware DB readiness. The frontend calls the API through
service modules. Compose defines PostgreSQL, Redis, migration, API, AI API and worker
containers. Celery has a health task. Ten SQL diagnostics support database inspection.
The AI API explicitly returns model-unavailable; edge simulation preserves HOLD.

There is no login, tenant resource workflow, durable customer-job/outbox implementation,
annotation, real training, approved model package, PLC output, durable edge sync,
billing or provisioned cloud environment. Catalogue entries are planned capabilities.

## Design and delivery guides

- [Distributed system, service boundaries and reliable jobs](docs/architecture/DISTRIBUTED_SYSTEM.md)
- [AI integration, training, evaluation and deployment](docs/guides/AI_LIFECYCLE.md)
- [Database, migrations, SQL functions and pgAdmin](database/README.md)
- [Cloud deployment plan and release gates](docs/runbooks/CLOUD_DEPLOYMENT.md)
- [v0.1 foundation checklist](docs/releases/V0_1_FOUNDATION.md)
- [Product](docs/product/PRODUCT.md), [architecture](docs/architecture/ARCHITECTURE.md),
  [team ownership](docs/guides/TEAM.md)

Imported source documents and archived starter instructions are preserved as reference.
Historical handbook/planning exports can describe the previous layout; this README
and the current developer workflow are the active setup instructions.
