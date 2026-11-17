# Business API

Owner: Siva. Docker: `make up`. Optional host development: `make install`, run only
infrastructure, then `make api`. Do not run host API on a port already used by Docker.

Request path:

```text
api/v1/controllers -> services -> interfaces <- repositories
                         |
                       schemas
```

Controllers own HTTP input, response codes and dependency injection. Services own
use cases and transaction boundaries. Protocol interfaces describe dependencies;
repositories implement storage access. Schemas define the wire contract; models
define persistence. `api/dependencies.py` composes implementations. The public static
catalogue is the first working example. Python services do not require an abstract
class for every class; use a protocol where a boundary needs substitution.

`/health/live` checks the process. `/health/ready` checks DB access and migration head.
`/api/v1/function-templates` returns public planned templates. Customer endpoints,
authentication, roles, durable jobs and inference orchestration remain unimplemented.

For each future customer use case, resolve verified membership, pass a tenant context
to the service and require that context in repository methods. Add cross-tenant
rejection tests. The repository never commits; the use case owns the transaction.
Do not put SQL in controllers or GPU work in this service. Keep internal inference
URLs server-controlled. Review shared contracts and regenerate OpenAPI together.
