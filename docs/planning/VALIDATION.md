# Foundation validation

Verified locally on 13 November 2026 using temporary Node 22 and uv/Python 3.11 tools.
Install your own prerequisites as described in the setup guide; temporary tool paths
are not committed as a developer-machine dependency.

| Check | Outcome |
| --- | --- |
| `make check contracts` | Passed: Ruff lint/format, strict TypeScript, 17 Python tests, web production build, OpenAPI snapshot |
| npm dependency audit after Vite patch | Zero reported vulnerabilities at installation time |
| Compose configuration | Valid |
| Four-service local stack | PostgreSQL, Redis, MinIO and MLflow healthy |
| MinIO source build | Successful from pinned upstream release |
| `make migrate` | Initial migration applied to project PostgreSQL |
| PostgreSQL revision query | Verified revision 0001 |
| Real worker/broker smoke | Health task consumed and completed via project Redis; temporary worker stopped |
| Alembic offline SQL | Generated successfully |
| Edge simulation | HOLD, no hardware output |
| Documentation links / JSON files | Checked successfully |
| Workbook task dependency references | All referenced task IDs exist; no task starts in a week earlier than its listed prerequisite |

A third-party Starlette/AnyIO deprecation warning remains; it did not fail tests.
The sandbox prevented local database sockets and stalled the threaded API test client;
those checks passed when run with environment-approved execution outside the sandbox.
The first MLflow start exposed SQLAlchemy 2.1 incompatibility; its Dockerfile now pins
2.0.57 and the service passes health checks. Other projects occupied standard ports,
so this stack uses dedicated configurable host ports, leaving those services untouched.

These checks do not establish model accuracy, PLC timing, tenant isolation for future
endpoints, offline durability, production security, browser interaction coverage,
backup recovery, cloud deployment or real GitHub branch protection. Those features
remain on the task plan. No paid resources or external accounts were created.
