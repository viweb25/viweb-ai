# Team ownership and working agreements

| Person | Primary ownership | Start commands | Next tasks |
| --- | --- | --- | --- |
| Siva | API, database, jobs/worker, infra, rules, edge sync, licensing | `make up`, `make migrate`, `make api`, `make worker` | T010, T012, T013, T014 |
| Hemachandran | frontend, schema-driven forms, annotations, dashboards | `make web` (and `make api` for catalogue) | T016, T017, T019 |
| Akash | ai, inference, camera/PLC/DAQ adapters, LabVIEW | `make inference`, `make edge-dev` | T011, T030, T031, T032 |
| All three | schemas, core, integration and acceptance | `make check`, `make contracts` | Review interfaces together |

Akash's title and skills are an assumption in the workbook, not confirmed staffing.
Siva manages repository integration, technical decisions and release readiness;
folder ownership guides reviews and does not prevent necessary coordinated changes.

## Siva

Run local infrastructure, migrations, API and a separate worker terminal. Define the
authentication provider and role matrix before tenant CRUD. Add organisation-scoped
queries, isolation tests and audit records with each feature. Own durable job state,
transactional dispatch and retries; do not execute GPU training in API request handlers.
Coordinate edge sync/rule boundaries with Akash. Replace commented CODEOWNERS entries
with actual account handles once the team repository exists.

## Hemachandran

Start the API for the static catalogue and the web dev server. Use OpenAPI to agree
request/response shapes with Siva before implementing forms; define explicit loading,
empty and failure states. Function-specific forms should eventually render from schemas,
not a separate hand-coded page per function. Do not infer that a displayed template means
a trained capability is available. Authentication and navigation are the next UI work.

## Akash

Start inference and run the no-hardware edge simulation. Implement one deterministic
sample plugin and golden-test harness before integrating a real model. Record both
code and weight licences. Add CUDA/PyTorch/ONNX/vendor SDK dependencies only in the
appropriate optional environment; the platform baseline does not install CUDA.
Measure export parity, per-function acceptance metrics and hardware latency.
Do not wire actual PLC outputs before bench tests cover timeout and sequence errors.

## Review workflow

Use feature/Txxx-short-name from develop; commits like feat(T014): add project API.
PRs link a task, explain resulting behavior and show validation. main is released code;
develop is integration. Require CI and at least one owner approval in repository settings.
Shared contracts need two reviewers by team agreement; basic CODEOWNERS alone does
not enforce two distinct approvals for one path. Configure an appropriate rule/check
when the real organisation supports it.

Use the workbook rhythm: stand-up 09:30, interface sync Wednesday 15:00, Friday demo
16:30, daily log before 18:00 (Asia/Kolkata). Dates and capacity are planning inputs,
not promises. The workbook is the authoritative task status; the exported CSV is a snapshot.
