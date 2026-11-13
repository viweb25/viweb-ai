# Contributing

Read README, docs/guides/GETTING_STARTED.md and docs/guides/TEAM.md.

1. Pick a workbook task with satisfied dependencies; branch feature/Txxx-short-name
   from develop. Keep one task per PR where practical.
2. Agree shared contracts with the producer and consumer owners before implementation.
3. Keep domain logic out of routers/UI, AI execution out of API, and hardware code
   behind edge adapter interfaces. Add migrations for database changes.
4. Verify relevant behavior and run `make check` and `make contracts` before review.
   Add isolation tests with every tenant-resource feature and golden tests for AI changes.
5. Link the task and validation in the PR. Request the folder owner; shared schemas
   need two human approvals. Update the workbook/log when work is accepted.

Never commit secrets, customer data or weights. Use immutable data/model references.
Database releases use additive migrations first; defer destructive changes to a later
release with a migration/rollback plan. Unknown or invalid inspection results cannot PASS.

Formatting is Ruff for Python, strict TypeScript for frontend. Dependencies are locked;
update manifests and lockfiles together. Review model-code AND weights licences.
There is no production deployment pipeline yet; cloud selection and release acceptance
must precede it. See docs/decisions/0001-foundation.md.
