# Data model implementation guide

Owner: Siva, reviewed with Akash and Hemachandran. This is the target model, not
implemented database schema. Migration 0001 contains only organisations.

## Add tables with the feature that uses them

| Domain | Planned entities | Important relationship |
| --- | --- | --- |
| Identity | organisations, users, memberships, roles, role_bindings | A user may join multiple organisations; selected org must be verified against membership |
| Project | projects, production_lines, assets, asset_channels | Asset sharing is explicit and constrained by organisation and acquisition capacity |
| Function | function_templates, functions, function_configurations | Template type is separate from configured instance; configurations append versions |
| Class library | classes, class_attributes, function_classes | Reusing a class definition must not share labels or model state |
| Dataset | datasets, dataset_versions, dataset_images, annotations | Snapshot is immutable; labels and split membership must be reproducible |
| Training | training_jobs, training_metrics, dispatch_outbox | Persist job and dispatch event atomically; broker delivery alone is not durable domain state |
| Model | models, model_versions, approval_events | Every candidate references parent release, dataset snapshot and reproducibility metadata |
| Deployment | devices, deployments, deployment_events | Only approved/licensed packages may activate; keep previous approved target for rollback |
| Operations | inference_results, events_alarms, rules, reports, audit_logs | Store rule/config/model provenance, trigger sequence, device and timestamp |
| SaaS operations | subscriptions, entitlements, usage_events, retention_policies | Billing state must not silently change industrial commissioning or inspection semantics |

## Tenant invariants

The organisation root has id. Every tenant-owned resource carries org_id, including
jobs and audit entries. Use tenant-scoped unique constraints and foreign keys (for
example org_id plus project_id) or equally explicit transaction-level enforcement.
Avoid a cross-tenant relationship even when both identifiers are otherwise valid.

Resolve org_id from validated identity and membership. A body parameter, URL ID or
worker payload does not prove authorisation. Scope list/detail/update/delete,
object signed URLs, model downloads, job cancellation, reports and WebSocket streams.
Super-admin access must be explicit and audited, not an accidental missing filter.

## Concurrency and history

Use version numbers/ETags for mutable resources. Check expected version on update
and return a conflict rather than overwriting another editor. Dataset snapshots,
configuration versions, model versions, approvals and deployment events append history.
Do not mutate the dataset used to produce a released model.

## Storage keys and provenance

Example object-key convention (not yet implemented):

```text
orgs/{org_id}/projects/{project_id}/functions/{function_id}/datasets/{version}/...
orgs/{org_id}/projects/{project_id}/functions/{function_id}/models/{version}/...
```

Keep content hash, object size, media type, capture session and provenance metadata.
Validate uploads server-side, constrain presigned operations, enforce quotas, and
sweep abandoned uploads. Never embed model weights or image blobs in SQL rows.
A time-series store should follow a measured sensor volume/retention decision.

## Before merging tenant CRUD

Add tests for two organisations and verify read/write/delete/list isolation,
cross-tenant parent references, storage URL scope, job dispatch scope and audit org.
Add forward migration tests against PostgreSQL and document one-release compatibility.
For data-bearing changes, define backup/restore and rollback behavior before release.
