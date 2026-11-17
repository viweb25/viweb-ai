# Infrastructure

`../compose.yaml` is the supported developer backend stack. All application Dockerfiles
are under `docker/`. These are development definitions; cloud rollout requirements are
in `docs/runbooks/CLOUD_DEPLOYMENT.md`.

`compose.ai-tools.yaml` preserves the optional MinIO/MLflow development stack for future
AI work. It is separate from the normal backend stack and is not evidence that uploads,
training or tracking are integrated:

```bash
docker compose --env-file .env -f infra/compose.ai-tools.yaml up -d --build
```

Run from the repository root. This uses separate persistent object/tracking volumes.
No cloud resources are provisioned by the Terraform placeholder.
