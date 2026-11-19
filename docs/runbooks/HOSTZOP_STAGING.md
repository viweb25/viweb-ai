# Hostzop staging for VI WebSync

One Hostzop GPU server can run a controlled staging environment for the UI,
business API, PostgreSQL, Redis, Celery, and inference. It is a single failure
domain. Take PostgreSQL backups to storage outside that server and test restoring
a copy before accepting customer data. Review the
[cloud release gates](CLOUD_DEPLOYMENT.md) for a customer deployment.

## Before ordering

Ask Hostzop for the exact GPU model and VRAM, CPU and RAM, usable storage, supported
Linux image and driver, SSH access, public IP, firewall support, backup options, and
monthly price. Benchmark the chosen model at expected resolution and concurrency.
Use those results and leave CPU, RAM, and disk I/O headroom for the API and database.
Reserve GPU access for inference or training containers.

## Deployment order

1. Create a staging DNS name such as `inspection.example.com`. Point it at the
   server IP, restrict SSH to your admin network, and expose only ports 80/443 for
   the HTTPS gateway. Keep PostgreSQL, Redis, Ollama and inference on private
   container networks. Leave pgAdmin disabled on the public host.
2. Set `APP_ORIGIN=https://inspection.example.com` in the server configuration.
   After the database migration, provision the first owner using the
   [password sign-in guide](../guides/SIGN_IN.md). Use the interactive password
   prompt and keep login request bodies out of logs.
3. Build the frontend with `npm ci` and `npm run build` in CI. Serve
   `frontend/dist` at the HTTPS origin and proxy the public auth, catalogue and
   status routes to the business API over the private network. Keep API routes
   same-origin. Protect login with request-size and rate limits at the gateway and
   configure the API to trust forwarded client IPs only from that gateway.
4. Start PostgreSQL on persistent storage. Run Alembic once with the migration
   account, then start the API and worker with their scoped runtime credentials.
   Build Python runtime images without dev dependencies or source bind mounts.
   Store credentials and model weights outside source control and public images.
5. With practice data and an authorised account, verify an HTTPS sign-in reaches the
   dashboard, a revoked session returns 401, and a second organisation cannot read
   another organisation's data. Verify migrations, backup restoration, and worker
   health. Keep `VI_DEMO_IMAGE_DIR` and the visual inspection demo route disabled
   at the public gateway. Opening cloud inspection requires authenticated,
   tenant-scoped routing and a model evaluated on the intended parts.

The development Compose file is for local work. This runbook describes staging
steps. A Hostzop server and domain are still required.
