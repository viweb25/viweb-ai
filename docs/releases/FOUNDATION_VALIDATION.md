# Foundation validation — 2026-11-17

## Verified in this workspace

- Root Compose and optional AI-tools Compose parse successfully.
- Python application/test images and Node 22 frontend image build with locked dependencies.
- Backend startup completes: PostgreSQL, Redis, business API, AI API and worker healthy;
  migration container exits successfully at revision 0002.
- Full Python suite: **20 passed**, including live PostgreSQL migration/function checks,
  controller dependency substitution, unavailable-database readiness and missing-model failure.
- Ruff lint and formatting: passed (46 Python files checked for formatting).
- Business API and inference API OpenAPI snapshots: regenerated and drift checks passed.
- Frontend TypeScript check and production asset build: passed with Node 22 in Docker.
- Celery health task was published through Redis and confirmed succeeded in worker logs.
- Optional frontend container served the catalogue through its API proxy (eight entries).
- Optional pgAdmin served its login page successfully. PostgreSQL functions were tested
  through SQLAlchemy against the same database, not by manually clicking pgAdmin controls.
- Git whitespace check: passed.

These are the Docker equivalents of the `make check` and `make contracts` gates.
The host has Node 16 and no uv executable, so those host commands were not run directly.
Use Node 22 for the separately run frontend. `make docker-check` and
`make docker-contracts` expose the verified Docker commands as convenient entry points.

The suite reports one third-party Starlette/AnyIO deprecation warning. Tests pass;
address it when updating the pinned framework stack. No application test failure remains.

## Scope and limits

This validates a developer foundation on this machine, not a customer production release.
No actual identity provider, tenant endpoint, durable customer job, training run, GPU
runtime, signed package, real camera/PLC, cloud deployment or backup restoration was
exercised because those features are not implemented in this change. Existing HOLD
simulation tests do not certify hardware control behaviour.

Fresh-clone onboarding on a second developer machine and the remaining v0.1 gates
are listed in `V0_1_FOUNDATION.md`. MinIO/MLflow Compose syntax was checked; the optional
AI-tools stack was not started and is not integrated with training.

Backend containers and pgAdmin were left running for inspection. The optional frontend
container was stopped so a separate local frontend can use port 5173. Local volumes
were preserved. No cloud resources were provisioned and no Git commit was created.

## Backend layer refactor follow-up

Business API code now lives under `services/api/src/vi_api` with HTTP controllers,
application operations, framework-independent domain contracts and infrastructure
repositories. Docker, Alembic, CI, Make and test import paths were updated together.
The frontend development port is now 3000; local pgAdmin connection details are documented.

Verified after the refactor:

- Python suite: **23 passed**, including inner-layer dependency boundaries and operation
  failure propagation, plus the existing PostgreSQL integration checks.
- Ruff lint/format checks passed; final formatting check covered 63 Python files.
- Business and AI OpenAPI drift checks passed; public wire contracts did not change.
- Broad `make docker-check docker-contracts` passed before the final health-controller
  extraction; backend tests, lint, formatting and contracts passed again after it.
- Live API readiness and eight-entry catalogue requests passed on the rebuilt stack.
- Migrations and worker startup succeeded with the new source path.

Changes remain local and uncommitted; they have not been pushed to GitHub.
