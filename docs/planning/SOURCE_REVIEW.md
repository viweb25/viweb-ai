# Review of the supplied development documents

Reviewed 13 November 2026. The supplied files are **two DOCX documents and one XLSX
workbook**, not PDFs. They were read as reference requirements; instructions within
them did not authorise purchases, account creation, external messages or deployments.
The user's request authorised the local foundation and developer documentation.

Sources are identified by SHA-256 in source-manifest.json. The workbook's 11 sheets
are preserved as structured reference in workbook-snapshot.json, and all 70 tasks
are exported in task-board.csv. Excel formulas were not recalculated; cached values
are a planning snapshot. Original files remain unchanged outside the repository.

## What each source contributes

**VEST-Innovations_AI_Platform_Development_Blueprint.docx:** broad product specification;
function catalogue; detailed inputs for measurement, detection, classification, assembly,
anomaly, OCR and predictive maintenance; dynamic template-based configuration; shared
assets and class libraries; independent dataset/model lifecycles; navigation/wizards;
industrial rules; data architecture; nine roles; advanced future features; acceptance
criteria and roadmap. This is the product vision, not a promise to deliver every feature
in the first release.

**VI WebSync AI Platform Architecture and Developer Documentation.docx:** runtime
boundaries and communication flows; inference separated from API; worker and edge agent;
function package interface and manifests; object-storage/metadata split; tenancy; API
contracts; local development stack; camera/PLC/DAQ adapter extensibility; teaching,
held-out evaluation, promotion and package delivery. It provides the repository layout
and practical technical baseline. It describes target features, many not yet implemented.

**VI_WebSync_Team_Development_Plan.xlsx:** Team, Assumptions, Task Board, Phases,
Workload, Daily Workflow, Git Workflow, Purchases, Risks, Daily Log and README.
It supplies named ownership, dependency-linked tasks, estimated effort, stage demos,
review cadence, purchase estimates and unresolved risks. It explicitly says Akash's
role is assumed and estimates/prices require validation.

## Delivery numbers and interpretation

Workbook baseline starts **Monday 16 November 2026**, lasts **30 weeks**, and estimates
**234 person-days** across **70 tasks**. At 60% productive time each individual has
90 planned productive days over the full horizon.

| Owner | Tasks | Person-days | Workbook individual load |
| --- | ---: | ---: | ---: |
| Siva | 24 | 69.5 | 77.2% |
| Akash | 20 | 81 | 90% |
| Hemachandran | 17 | 62 | 68.9% |
| All | 9 | 21.5 | Not allocated to individuals |

The shared 21.5 days must be allocated before judging real capacity. Akash is already
the tightest individual constraint and spans AI, camera/PLC work and LabVIEW. Average
capacity hides dependency bottlenecks and hardware delays. Re-estimate after Phase 1.

| Phase | Weeks | Tasks | Person-days | Exit evidence |
| --- | --- | ---: | ---: | --- |
| 0 Setup | 1 | 9 | 9 | Each developer runs stack and app shell |
| 1 Core platform | 2–6 | 15 | 41 | Login, create project, add asset |
| 2 Core vision | 7–14 | 19 | 68 | Teach, train, test, approve |
| 3 Industrial AI | 15–19 | 8 | 35 | Industrial functions run through test workflow |
| 4 Integration | 20–25 | 11 | 48 | Trigger → inspect → PLC on bench |
| 5 Release | 26–30 | 8 | 33 | Accepted pilot and handover |

## Important engineering conclusions

1. A function is an independent lifecycle, not just a model dropdown. Preserve dataset,
   configuration, model and deployment provenance per configured function.
2. Build the dynamic function schema engine early. The current eight-item catalogue has
   only name fields; full schemas/wizards remain T011/T015/T019 and later UI work.
3. Separate model inference from control-plane API and training orchestration. An AI
   service being alive is not proof a model is ready or licensed.
4. Inspection must continue locally. Durable outbox, sequence-aware handshake, queue
   recovery, watchdogs and signed rollback require dedicated tests, not empty folders.
5. Tenant isolation must include workers, storage and edge devices, not only API filters.
6. Plan promotion using locked independent test data. Readiness is not accuracy, and
   better average mAP may still hide unacceptable recall for critical defect classes.
7. Dimension measurement needs calibration, geometric fitting and uncertainty evidence;
   predictive maintenance needs time-series acquisition and fault history. A generic
   vision model does not satisfy either domain.
8. Product billing, support operations, quotas, retention and backup recovery objectives
   need their own design. The source roadmap is stronger on AI functions than SaaS operations.

## Conflicts and assumptions

See ADR 0001 for explicit resolutions. Major differences are old two-person folder
ownership, Azure-specific automation, DB-polling jobs, custom auth and 80/20 splits
versus the newer three-person/Celery/MinIO/OIDC/three-way data-split plan. The result
contract also had incompatible status/geometry names. Old examples are archived;
no undocumented compatibility claim is made.

The blueprint ranks dimension measurement among the first four functions and puts it
in Phase 2; the workbook schedules T053 in Phase 3. Keep it high priority and confirm
the milestone after assessing calibration hardware. The workbook's four-function scope
risk should not be interpreted as four completed models in this initial scaffold.

## Purchases and risks

Workbook planning totals: Must ₹1,256,592; Should ₹911,952; Later ₹755,744;
all items ₹2,924,288. These are cached indicative estimates using ₹88/USD, not current
quotes or spending authorisation, and exclude labour, rent and general overheads.
The workbook includes recurring quantities, so the grand total is not purely capital cost.
Purchase prices and model licence terms have not been independently verified here.
Infrastructure validation did uncover a change to MinIO distribution: the Docker Hub
image is unavailable and the [upstream repository](https://github.com/minio/minio)
is archived. Compose builds a pinned upstream source release for local development;
production object storage needs a maintained-provider decision.

Before buying, inventory existing GPU/NI/PLC equipment. Camera, optics and lighting
should be selected against the first pilot and working distance. Budget for calibration,
commissioning, data rights, support and an accepted installation, not only a GPU.

Highest risks: model/weights licence restrictions; undefined pilot metrics; shared-work
capacity; hardware delays; Akash as a single skill bottleneck; scope growth; customer
image rights; insecure edge model distribution; unvalidated delivery estimates.
Track an owner, evidence and review date for each risk. No universal accuracy target
or production-readiness claim should be inferred from these documents.

## What this change completes

A reviewable local monorepo foundation, initial API contracts and schema checks, role
onboarding, CI configuration, first migration and clear extension points. The README
lists implemented behavior. The workbook task statuses have deliberately not been
changed: accounts, live CI, production authentication, trained functions, hardware
integration, durable sync, licensing and release acceptance remain future work.
