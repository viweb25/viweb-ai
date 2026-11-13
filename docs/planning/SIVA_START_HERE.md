# Siva: repository lead starting checklist

The foundation is prepared locally. This checklist is future work, not a claim that
accounts, permissions or cloud resources have already been created.

## First day

1. Read docs/product/PRODUCT.md and docs/planning/SOURCE_REVIEW.md; walk the team through ownership and ADR 0001.
2. Set up tools, run `make check` and `make contracts`, then the local stack and migration.
3. Create the real private organisation/repository and invite the team (T001).
   This supplied folder does not have usable Git metadata; initialise/clone deliberately
   and preserve this work. No remote or repository has been created automatically.
4. Add real CODEOWNERS handles. Create main/develop, require PRs and CI, prohibit direct
   pushes, and configure shared-contract review rules (T002).
5. Agree brand, Akash's role, OIDC provider and first pilot inspection. Do not order from
   spreadsheet prices without current quotes. Record decisions in docs/decisions.

## First week / next engineering sequence

- T003: review/merge this structure and onboarding.
- T004: run and verify Compose on each developer machine, including MLflow and MinIO.
- T005: enable and observe the supplied CI in the real repository.
- T006: Akash validates the GPU workstation separately; no CUDA is required for Siva/UI.
- T007/T016: Hemachandran extends the shell with navigation and real identity flow.
- T008/T009: agree standards and ownership, then demonstrate all three local setups.
- T010/T011: review auth/projects/assets/classes OpenAPI and full function schemas.
- T012/T013: verified identity, permission matrix, tenant model and remaining migrations.
- T014/T015: organisation-scoped project/asset APIs and full function-template engine.

## First useful vertical slice

Authenticated organisation → create project → create function → upload immutable
sample images → annotate → snapshot dataset → queue training → evaluate → approve →
manual test → edge bench deployment. Finish a coherent slice before broadening catalogue.

## Track management work

Use docs/planning/task-board.csv as an accessible export; update actual progress in the
original workbook or a linked team board. Do not mark a full workbook task Done just
because a partial scaffold exists. Record daily blockers, review contracts Wednesday,
demo Friday, re-estimate after Phase 1. The 30-week plan has 234 estimated person-days,
including shared work; a spare-looking individual load is not proof of schedule safety.
