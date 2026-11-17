# v0.1 developer foundation acceptance

This change is a foundation improvement, not completion of the first customer release.

## Included in this change

- Frontend in `frontend/`; HTTP calls under `src/services/api/`.
- Business API catalogue through controller/application-operation/domain/infrastructure layers.
- Separate AI backend with an explicit 503 when no approved model is loaded.
- Database migrations in `database/`, ten diagnostic SQL functions and database checks.
- Docker definitions for API, AI API, PostgreSQL, Redis, Celery worker and migration job.
- Optional pgAdmin and frontend profiles; frontend runs separately by default.
- Developer setup, distributed jobs design, AI lifecycle and cloud deployment plan.

See `FOUNDATION_VALIDATION.md` for actual checks and environment limitations.

## Remaining v0.1 release gates

- Select identity provider and implement verified identity, membership and role checks.
- Deliver one tenant-scoped project workflow through frontend/API/database.
- Prove tenant isolation and concurrent update behaviour.
- Implement the deterministic AI plugin and golden tests; no production weights needed.
- Decide whether durable customer jobs belong in v0.1; if exposed, implement job rows,
  transactional outbox, idempotency, leases, cancellation and recovery tests first.
- Run fresh-clone Docker startup on another developer machine and record acceptance.
- Review shared contracts and CI evidence with owners before tagging the release.

Actual training, signed model deployment, hardware commissioning, billing and production
cloud hosting remain later deliveries. The target design does not make them implemented.

## Cleanup decisions

Moved existing frontend and migrations rather than creating duplicate applications.
Removed replaced source-directory README placeholders. Preserved archived starter
instructions, imported references, planning workbook snapshots and handbook artifacts
for traceability. Those artifacts may describe the previous layout and are not current
setup instructions; use the root README and developer workflow instead.
