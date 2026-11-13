# Shared contracts

Owners: all three developers; Siva coordinates API contracts and Akash function schemas.

- openapi/api.json: generated public API snapshot; `make contracts` checks drift.
- functions/catalogue.json: eight planned templates with minimal name-only schemas.
- functions/manifest.schema.json: initial package manifest shape; signature protocol remains future work.
- results/inspection.schema.json: v1 result envelope with separate execution/decision.
- jobs/job.schema.json: future domain job wire shape, not the Celery health-task payload.
- examples/inspection.json: explicit error/HOLD example; not production inspection evidence.
- edge/: extension point for device and LabVIEW protocols.

Current tests validate schemas, examples, planned configs and unsafe status combinations.
Add typed payload schemas and real examples with every function. No one claims generic
payload objects already validate detection boxes, OCR text or measurement uncertainty.
Shared contracts require two human approvals; configure enforcement in the real remote.
