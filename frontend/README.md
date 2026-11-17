# Frontend

Owner: Hemachandran. Run separately from Docker backends:

```bash
npm ci
npm run dev
```

Use Node 22 (`nvm install && nvm use`). Open http://127.0.0.1:3000. Vite proxies
`/api` and `/health` to VITE_API_URL from the root `.env`; no browser-side service
DNS, database credentials or direct AI-service calls. Keep environment settings
free of secrets: anything prefixed VITE_ can become browser-visible.

`src/services/api/client.ts` owns HTTP handling; `catalogue.ts` owns catalogue calls
and types. Components render state and call these services. Add feature directories
when real screens exist. TypeScript currently uses handwritten catalogue types;
generated OpenAPI clients are a future task. Review types and contracts together.

Optional container: `docker compose --profile frontend up -d --build frontend`.
It uses an internal proxy target provided by `infra/docker/frontend.env`.
This is a development server, not a production image. Cloud production should serve
a compiled static build and route API requests to the business backend.
