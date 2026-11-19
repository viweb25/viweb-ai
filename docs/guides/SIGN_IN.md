# Email and password sign-in

VI WebSync verifies passwords against salted scrypt hashes in PostgreSQL. Account
creation is an administrator action. There is no public registration endpoint.

From the repository root, start the app and apply Alembic migrations:

```bash
make setup
docker compose --profile frontend up -d --build --wait
```

Create an owner account for a new organisation:

```bash
docker compose exec api python -m vi_api.infrastructure.identity.create_owner \
  --email you@example.com --organisation "Your Company"
```

Enter and confirm a password of 15 to 128 characters at the hidden prompt. For an
existing organisation, replace `--organisation "Your Company"` with
`--org-id YOUR_ORGANISATION_UUID`. Open http://127.0.0.1:3000 and use the same email
and password. On a successful login the browser loads the session from
`GET /api/v1/auth/me` and opens the dashboard.

`POST /api/v1/auth/login` accepts JSON with `email` and `password`. It checks the
same-origin browser request and applies PostgreSQL-backed attempt limits per email
and source address. PostgreSQL stores session token hashes. HTTPS deployments use a
host-only Secure, HttpOnly, SameSite=Strict cookie. Configure `APP_ORIGIN` with the
dashboard's HTTPS origin in staging. Configure trusted proxy headers so the API
sees real client addresses at the gateway. Only trust headers from that gateway.
Do not log login request bodies.

The application uses the existing user and organisation membership tables.
Migration `0005` adds password credentials and sign-in attempt counters. Historical
external identity rows are preserved. The current sign-in path uses password
credentials. See the [pgAdmin walkthrough](../../database/README.md#identity-in-pgadmin).

For a hosted workspace, keep the shared demo storage and raw inspection endpoint
private. See the [staging runbook](../runbooks/HOSTZOP_STAGING.md).
