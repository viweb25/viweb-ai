# AI integration and training plan

## Service contract and current state

`services/api` is the business backend; `services/inference` is the separate AI backend;
`ai/` holds function implementations and future training/dataset code. `services/worker`
runs asynchronous work. No trained weights or real training loop are included.
`POST /api/v1/predict` on the AI backend currently returns 503 `model_not_loaded`.
This is deliberate: an available HTTP server does not imply an available approved model.

The `FunctionAI` interface in `ai/vi_ml/functions/base.py` defines load, predict and
health. Keep each function's configuration, dataset snapshots, model versions and
runtime loading separate. An OCR update must not change a detection function's model.
Do not install CUDA/framework dependencies into the business API image; the current
shared Python baseline is temporary. GPU service images need separately pinned
framework/CUDA/driver compatibility and licence review before real model integration.

## First vertical slice

Build one deterministic sample plugin and a golden-test harness before selecting a
real detection model. The sample is a test fixture, never a production inspection model.
Then choose one detection dataset and acceptance target with the customer; complete
its full lifecycle before enabling all eight catalogue templates.

1. Authenticate and resolve organisation membership. Create a project and independent
   function instance. Record its immutable configuration version.
2. Issue short-lived upload URLs scoped to organisation/project/function. Validate size,
   type, checksum and ownership. Store immutable images outside Git and PostgreSQL.
3. Build a dataset snapshot containing explicit object versions, annotations and label
   schema. Freeze grouped train/validation/test splits. Keep frames from the same part,
   batch or acquisition session in one split to prevent leakage.
4. Create a durable training job with an outbox event as described in the distributed
   system guide. GPU workers download authorised snapshots and train reproducibly.
5. Record source commit, dependency/container digest, random seeds, hyperparameters,
   dataset/configuration hashes, base-model licence, hardware and artifact checksums.
   Experiment tracking helps comparison; PostgreSQL remains approval authority.
6. Evaluate candidate and parent on the same locked test set. Record per-class
   precision/recall, false accepts/rejects and relevant latency. Customers set thresholds;
   do not promise one universal accuracy percentage. Reject invalid/missing metrics.
7. An authorised reviewer approves a candidate with an audit record. Job success alone
   cannot approve it. Export the required runtime format and test export parity.
8. Package weights with model/function/configuration identity, input/output schemas,
   checksums, runtime compatibility, provenance and entitlement. Sign packages and verify
   signatures before loading. The signing/release pipeline is not implemented yet.
9. Deploy to a private inference service or factory agent. Stage and validate before an
   atomic activation. Keep the last approved compatible package for rollback.
10. Measure drift, customer acceptance, latency and failures. New data creates a new
    dataset/version cycle; never silently retrain or replace active weights.

## Future inference request

The final contract must include verified organisation context, function instance,
model version, configuration version, trigger sequence, input reference and deadline.
It must return validated observations, runtime status, matching identity/provenance
and timing. Choose a per-function payload schema with consumers before implementing
it. The existing generic result schema is a starting envelope, not a finished typed
AI API. Any new endpoint/types require OpenAPI and contract updates.

For cloud preview: browser -> business API -> private AI API. Business API authorises
the input and function. For factory inspection: local trigger -> capture -> local
inference -> approved rules -> validated hardware handshake -> durable local result
-> eventual cloud sync. Cloud preview must not become a safety-critical PLC control path.

Never pass arbitrary model paths or remote URLs from user input into model loaders.
Validate signed package manifests, checksums, file sizes and runtime compatibility.
Review serialization risks before loading third-party weights. Restrict training
network access and object permissions to the job's required tenant prefix.

## Release gates for real AI

Golden tests cover deterministic input/output, malformed input, absent/corrupt package,
wrong function/version and runtime failure. Model tests cover split leakage, missing
classes, invalid metrics, export parity and target-device latency. Integration tests
cover job retries, cancellation, tenant isolation and package approval/rollback.
Hardware acceptance covers timeout, freshness, sequence and disk-full HOLD behaviour.
No real PLC outputs until bench commissioning passes.
