# Web application

Owner: Hemachandran. React 18 + TypeScript + Vite, Node 22.
From the repository root run `make web`; run `make api` in another terminal.
The app currently displays the planned catalogue from the API and connectivity errors.
No authentication, customer records or annotation workflows are implemented.

Next: app navigation and identity integration (T016), project screens (T017),
schema-driven function forms (T019), then dataset and annotation workflows.
Add UI libraries when the relevant screen requires them; keep model/hardware logic
out of browser code. Build with `make build`, type-check with `npm run typecheck`.
