# ADR 0001: foundation and source reconciliation

Status: working baseline for scaffold; 13 November 2026. Owner: Siva.

## Decision

Follow the 12 November architecture document's monorepo paths and the workbook's
three-person ownership. One modular FastAPI control plane, a worker, independent
inference and edge runtimes, shared schemas, React/TypeScript frontend.
Use Celery/Redis and MinIO locally as described by the newer documents. Use npm
workspaces for the single web app, uv for Python. Node 22 and Python 3.11 are the
baseline; versions are locked in dependency lockfiles. Keep production hosting open.

## Conflicts resolved for scaffolding

| Topic | Sources differ | Working baseline |
| --- | --- | --- |
| Layout | Starter backend/edge/vi_ml vs architecture services/ai/packages | Architecture section 7 paths |
| Team | Starter Dev-1/Dev-2 vs named three-person workbook | Siva/Hemachandran/Akash; Akash role still assumed |
| Jobs | Starter DB polling vs document Celery/Redis | Celery; durable DB jobs/outbox still required |
| Storage | Starter Azure Blob/Azurite vs document S3/MinIO | Local MinIO; provider adapter later |
| Cloud | Starter Azure vs newer provider-neutral options | No provider chosen or provisioned |
| Identity | Starter custom passwords vs Keycloak/Auth0 workbook | OIDC provider decision pending; no fake login |
| Splits | Starter 80/20 vs newer train/validation/locked test | Grouped three-way split with leakage checks |
| Result | Starter OK/NOT_OK vs document PASS and rule separation | v1 execution_status plus PASS/FAIL/HOLD/REINSPECT |
| Measurement | Blueprint top four/Phase 2 vs workbook Phase 3 | High priority, provisionally Phase 3 pending bench readiness |
| Git | Starter main staging/Bitbucket vs workbook develop/GitHub | GitHub CI template and develop integration; no remote changes |

## Open decisions

Brand (VI WebSync is a working name); Akash role/skills; real Git handles and hosting
organisation; cloud/region and data residency; OIDC provider and role matrix; model
and weight licences; package signing/activation design; initial function acceptance
thresholds; customer data-use terms; dimension-measurement milestone; billing and
subscription metering boundaries; recovery targets and support/operating model.

Do not introduce Kubernetes, MQTT brokers or an extra time-series database merely
for an advanced folder tree. Add them when measurements and a recorded decision
justify the operational cost. Local HTTP and demo credentials are development-only.

## Validation finding: MinIO distribution changed

The documented Docker Hub image failed to pull. Upstream's repository is archived
and recommends source builds: https://github.com/minio/minio . Local Compose now
builds release RELEASE.2025-10-15T17-29-55Z from upstream source. It is a development
compatibility choice, not a production storage recommendation. Review a maintained
S3-compatible service and its licence before customer deployment. MinIO itself is
AGPL-3.0; review obligations for any distribution, just as for model dependencies.
