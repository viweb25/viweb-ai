# Product definition

VI WebSync is an industrial AI vision and intelligence platform with two delivery
modes: a managed multi-tenant SaaS control plane and an on-premise factory runtime.
A function package can also be licensed as a standalone product. The distinguishing
workflow is configure → collect → annotate → train → evaluate → approve → deploy → monitor.

A manufacturer can inspect an assembly for missing bolts, detect surface defects,
read a batch label, count products, or measure a calibrated dimension. Each function
instance has its own configuration, datasets, training runs, model versions,
acceptance criteria and deployments. Updating one function must not alter another.

## Domain hierarchy

Organisation → Project → Function → Configuration versions / Dataset versions /
Model versions → Deployments. Production lines and sites may group projects;
site hierarchy is not fixed by this scaffold. Assets and class definitions are reusable
within an organisation, while acquisition schedules and mutable model state remain isolated.

A function template describes configuration and output schemas. A function instance
is the customer's configured task. A function package is a versioned released model
or processing pipeline. A deployment assigns an approved package to an execution target.
These are separate entities and must not collapse into one database table.

## First delivery

Build the function builder and independent data/model lifecycle first. Prove one
complete detection workflow before multiplying function types. Classification and
anomaly detection follow. Dimension measurement is a high-priority fourth capability,
but must have calibration, reference instruments and an uncertainty budget.
The workbook schedules it in Phase 3; the blueprint prioritises it earlier. Retain
that schedule provisionally and review at the first planning meeting.

Later: assembly verification, OCR/label inspection, counting and a predictive
maintenance prototype. Cosmetic 3D, audio, marketplace, AI-assisted configuration,
advanced analytics and international billing are future scope. SaaS billing and
entitlements are separate from model accuracy and hardware commissioning.

## User groups

Platform Super Administrator; Organisation Administrator; Project Manager; AI Engineer;
Production Engineer; Quality Inspector; Maintenance Engineer; Operator; Viewer.
The blueprint names these roles but does not define a complete permission matrix.
Siva must define and test the matrix before exposing customer resources.

## Product boundaries

The API manages state and authorisation; it does not run neural networks.
AI returns observations; versioned customer-approved rules make operational decisions.
PLC/camera/DAQ adapters run beside the machine. Emergency stops and certified safety
interlocks remain in their certified control systems.

Customer raw data is immutable; dataset snapshots and configuration versions are
traceable. No cross-customer shared training by default. Accuracy is measured per
application with a named dataset and metric, never as one universal percentage.
