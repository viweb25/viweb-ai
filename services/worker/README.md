# worker

Owner: Siva. Run from repository root after make install.

```bash
make up
make worker
```

Celery health task is implemented. In another terminal run make worker-ping. Durable training jobs, dispatch outbox and cancellation are future tasks.

See docs/guides/TEAM.md for the work split and docs/architecture/ARCHITECTURE.md
for target interfaces. Run make test before requesting review.
