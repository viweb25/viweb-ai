# Cloud deployment design and release gates

This is a provider-neutral deployment plan, not provisioned infrastructure or a tested
production runbook. No provider/account/domain has been selected. Provider-specific
commands, sizing and prices require a separate verified deployment task.

Hostzop staging steps are in [HOSTZOP_STAGING.md](HOSTZOP_STAGING.md).

## Deployment layout

Serve the built frontend from static hosting/CDN behind TLS. Route `/api/v1` and
required health probes to a private-container business API through a gateway/load
balancer. Run AI inference and workers as separate private workloads. Use GPU workers
only for workloads that need them; training workers scale separately from inference.
Deploy long-running GPU training on an appropriate job runner after capacity testing.

Use managed PostgreSQL with backups and point-in-time recovery, a private managed
Redis deployment compatible with the selected Celery transport, immutable object
storage, secrets management and a private image registry. Keep model binaries/data
out of Git and container build contexts. Experiment tracking needs a durable database,
artifact storage and authenticated access if enabled. It is not the model-approval database.

Only the frontend/gateway should be internet reachable. Keep PostgreSQL, Redis,
inference, workers, pgAdmin and experiment tracking private. pgAdmin is a local tool;
use audited administrative access for production operations. Production containers
must have no source bind mounts, reload server, example credentials or developer tools.

## Before first staging deployment

1. Complete verified identity, roles, tenant isolation and audit logging. Decide the
   permission matrix with the team. Test cross-tenant reads, writes and background jobs.
2. Split runtime dependencies and create production API, AI, worker and static frontend
   images. The supplied `python.Dockerfile` base is a starting point; Compose targets
   the development stage. Add resource budgets, shutdown handling and production probes.
3. Select region, data residency, domains, identity provider and object retention policy.
   Define expected load, maximum queue age, availability target, recovery time and data
   loss tolerance. Choose infrastructure from these requirements rather than a service count.
4. Provision infrastructure as code with distinct staging/production state and secrets.
   No Terraform resources are currently implemented. Use short-lived CI credentials.
5. Create separate migration-owner and least-privilege runtime database roles. Configure
   private networking, TLS validation, object-prefix permissions and service identities.
6. Build/test images in CI, scan dependencies/images, publish immutable digests, and
   retain a release manifest linking code, migration head, contracts and model packages.

## Release sequence

Back up and verify recovery capability. Review migration locking and expected runtime.
Run one migration job per environment before application rollout; do not let every
replica race migrations. Use expand/contract schema changes so previous and next app
versions can coexist. Do not run destructive schema contraction in the same release
that stops using a column.

Deploy compatible workers and APIs, then frontend assets. Gate rollout on readiness
and smoke tests: authentication, tenant rejection, database access, job completion,
private inference failure behaviour and rollback. Canary AI packages independently of
application code. An application rollback does not automatically roll back the database.

Observe request errors/latency, database connections, queue depth/age, job failures,
object errors, GPU utilisation and model rejection/HOLD rates. Keep runbooks for broker
loss, expired leases, bad model activation, failed migration and object-storage outage.
A failed candidate must not replace an approved active package.

## Recovery and acceptance

Restore a backup into an isolated staging environment and verify data/artifacts before
claiming recovery works. Exercise broker loss and duplicate delivery once durable jobs
exist. Verify that edge inspection continues during a simulated cloud outage after
local runtime and sync are implemented. Test controlled shutdown during a job and
mid-rollout compatibility. Record measured outcomes and unresolved limits.

The local Docker stack is not a production deployment. v0.1 foundation completion is
separate from customer production release approval.
