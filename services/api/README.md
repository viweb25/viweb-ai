# api

Owner: Siva. Run from repository root after make install.

```bash
make up
make migrate
make api
```

Public static catalogue and liveness are implemented. Authentication, tenant CRUD, audit and object uploads are future tasks. First migration creates only the organisation root.

See docs/guides/TEAM.md for the work split and docs/architecture/ARCHITECTURE.md
for target interfaces. Run make test before requesting review.
