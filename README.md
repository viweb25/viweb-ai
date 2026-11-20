# VI WebSync business backend

This tree is the backend-only cutover candidate for the existing viweb-ai repo.
It owns FastAPI, identity, catalogue, database access queries and Celery. The
database and AI repos build the independent images used by Compose.

Build vi-websync/db:staging and vi-websync/inference:staging from the matching
repositories on the AI server, or set DB_MIGRATION_IMAGE and AI_RUNTIME_IMAGE
to their published image references in .env. Copy .env.example to .env and set
the HTTPS hostnames, gateway key and database credentials.

```bash
docker compose up -d --build --wait
docker compose exec api python -m vi_api.infrastructure.identity.create_owner \
  --email owner@example.test --organisation "Staging Company"
```

Deploy the frontend from its own repository. APP_ORIGIN must match the frontend's
HTTPS origin, and both gateways must use the same VI_GATEWAY_KEY. The business API,
database, Redis and inference containers use private Docker networking. The public
gateway permits sign-in, session checks, logout, signup, catalogue, liveness and inspection. Hosted
inspection requires an active workspace membership. Example uploads use company-scoped backend access.

Use the backend's OpenAPI snapshot in packages/schemas/openapi/api.json to
coordinate frontend releases. Track the migration revision and image tags together.

## Account signup and camera inspections

In the backend server's `.env`, set `SIGNUP_CODE` to a random value generated
with `openssl rand -hex 24`. Share it privately with users authorised to
create a workspace. Each registration creates a new workspace and its owner.
The code is reusable until rotated. Clear it and recreate the API container
to disable registration.

For YOLO, build the inference image from the standalone inference repository.

```bash
docker build --target yolo -t vi-websync/inference:staging /path/to/viweb-inference
```

Put the trained `best.pt` in a directory readable by container UID 10001.
Set `YOLO_MODEL_DIR` to that absolute host directory and `VI_YOLO_WEIGHTS` to
`/models/best.pt` in the backend `.env`. Restart the inference container after replacing
weights. Use the `vision` Compose profile with the configured Ollama model for Qwen.
Both gateways route JPEGs through the business API, which checks the session and origin
before forwarding them to private inference.
