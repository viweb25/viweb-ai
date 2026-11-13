# VI Websync AI

Universal AI Vision & Industrial Intelligence Platform. Read CLAUDE.md first.

Quick start: `cp .env.example .env && make up && make install && make migrate && make seed && make dev`
Then open http://localhost:5173 and http://localhost:8000/docs. Start Claude Code with `claude` and type `/onboard`.

Folder owners: apps/web + backend + infra = Dev-1 | packages/vi_ml + services/worker + edge = Dev-2 |
labview = LabVIEW/PLC team | contracts = both developers.
