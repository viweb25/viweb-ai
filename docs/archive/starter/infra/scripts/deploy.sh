#!/usr/bin/env bash
# Usage: deploy.sh <staging|production> <version-or-commit>
set -euo pipefail
ENV=$1; VER=$2; RG="rg-viws-$ENV"; REG="$ACR_NAME.azurecr.io"
az login --service-principal -u "$AZ_CLIENT_ID" -p "$AZ_CLIENT_SECRET" --tenant "$AZ_TENANT_ID" >/dev/null
az acr login -n "$ACR_NAME"
docker build -t "$REG/api:$VER" -f backend/Dockerfile .              && docker push "$REG/api:$VER"
docker build -t "$REG/worker-cpu:$VER" -f services/worker/Dockerfile.cpu . && docker push "$REG/worker-cpu:$VER"
docker build -t "$REG/edge:$VER" -f edge/deploy/Dockerfile .          && docker push "$REG/edge:$VER"
# 1) database migration runs as a Container Apps job inside Azure (next to the database)
az containerapp job update -n migrate -g "$RG" --image "$REG/api:$VER"
az containerapp job start  -n migrate -g "$RG"
./infra/scripts/wait-job.sh migrate "$RG"
# 2) API + CPU worker (new revisions; previous revisions kept for rollback)
az containerapp update -n api        -g "$RG" --image "$REG/api:$VER"
az containerapp update -n worker-cpu -g "$RG" --image "$REG/worker-cpu:$VER"
# 3) web
corepack enable && pnpm install --frozen-lockfile && pnpm --filter web build
npx @azure/static-web-apps-cli deploy apps/web/dist --deployment-token "$SWA_TOKEN" --env production
echo "Deployed $VER to $ENV"
