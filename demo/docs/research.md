# Repository research and integration decision

## Verified baseline and evidence quality

Inspected the repository at closure `4f31886f12f6df09cd3dc688b48fb9e20329a3ee`, parent implementation `40768110eeb16c07574d3a7432805233db86af4c`. Source worktree was clean. Requested target was absent but registered as a prunable missing worktree on `demo/feature-008-closure`. `git worktree prune --dry-run --verbose --expire now` identified only that stale registration; pruning removed its Git metadata, then `git worktree add -b demo/safira-fyp-showcase <target> <closure>` succeeded. No existing directory, branch or file was deleted. The old branch reference is retained.

Constitution [v3.0.0](../../.specify/memory/constitution.md) and Features 001–008 specifications/contracts were reviewed alongside actual modules and synthetic fixtures. Older specification headings retain planning-era statuses; do not use those headings alone as current completion evidence.

| Feature | Closure/completion evidence at baseline | Presentation qualification |
|---|---|---|
| 001 | [quickstart](../../specs/001-model-registration-registry/quickstart.md), all amendment tasks T024–T028 checked; commits `a8cfeae`, `0c35e6e` | Verified completed research software; no standalone `closure.md` present |
| 002 | [quickstart](../../specs/002-prediction-evidence-collection/quickstart.md), checked tasks; final acceptance commit `9a51025` | Completion evidence, not a standalone closure record |
| 003 | [implementation checkpoints](../../specs/003-patient-grouped-safety-dataset/implementation-checkpoints.md), post-audit F1–F6 and commit `d7e7dd4` | Post-audit record supersedes earlier limitations/counts |
| 004 | [implementation context](../../specs/004-safety-signal-extraction/implementation-context.md), checked tasks and targeted remediation `7828096` | Completed software; no dedicated closure file |
| 005 | [spec status](../../specs/005-automatic-model-specific-safety-training/spec.md), implementation context, 47 checked tasks, closure commit `d880310` | Frozen intermediate estimator, not complete deployment package |
| 006 | [closure](../../specs/006-independent-safety-estimator-calibration/closure.md) | `CALIBRATOR_FITTED_UNEVALUATED` |
| 007 | [closure](../../specs/007-selective-safety-policy/closure.md), `c62b4d0` | `SELECTED_UNEVALUATED` |
| 008 | [closure](../../specs/008-runtime-safety-assessment/closure.md), exact baseline | Closed synthetic-only scope |

Feature 008 closure reports historical **839 passed, zero failures/skips**, partitioned 794 Features 001–007 plus 45 runtime tests; audit A–J passed. Historical audit environment: Python 3.11.0, pytest 9.1.1, scikit-learn 1.7.1. Those counts are not new full-suite verification or clinical performance. Earlier cumulative snapshots include 265 (001), 401 (002), 461 after 003 remediation, 659 (005), 751 (006), 794 (007); never add cumulative totals together. For 004 use its completion evidence without inventing a separate count.

Fresh Phase 1 checks: editable installation succeeded; the eight existing `test_runtime_*.py` files produced **45 passed in 33.59 s**. Import path resolved to this demo worktree's `src/safira/__init__.py`. Python 3.11.17, pytest 9.1.1, sklearn 1.7.1; NumPy 2.4.6 and SciPy 1.17.1. The full 839 suite was not rerun. The focused suite includes isolated monkeypatched behavior tests; its passing count does not prove every proposed scenario is an unmocked end-to-end run.

A separate one-off research probe then used fresh temporary test registries and the existing fixture builders with unmodified service calls. Both default baseline and logistic recipes returned TRUST / `cutoff_satisfied`. Seven predeclared synthetic primary-query recipes were collected and separately admitted to prediction and synthetic ledgers under the same frozen logistic artifacts: recipes 0/1/5/6 returned CAUTION / `cutoff_not_satisfied`; 2/3/4 returned TRUST. Recipe inputs remain host-private; recipe 0 uses the deterministic synthetic adapter's primary output 0.01, not a Safira correctness score or policy threshold. This provides a concrete natural CAUTION recipe without changing any estimator, calibration or policy artifact. One existing boundary test also passed in that final probe invocation (2.36 s); it overlaps the 45 and must not be added to the unique count.

Two earlier diagnostic harness attempts failed: first by reusing a registry and attempting duplicate registration, then during Windows temporary SQLite cleanup because the registry was still open. Neither was a framework-suite regression; the corrected probe used separate registries and explicit close before cleanup, and exited zero. No source changes or production app code were introduced by the probe. Direct pytest fixture-wrapper use was confined to this disposable research diagnostic; it is prohibited in the running demo host.

## Actual integration, not a hypothetical public API

`pyproject.toml`: distribution `safira-clinical==0.1.0`, setuptools src layout, Python >=3.11, dependency `scikit-learn==1.7.1`. Use editable installation from the new checkout; import `safira`, not `safira-clinical`. No absolute path into the source worktree and no `sys.path` modification.

Confirmed entry point in [runtime service](../../src/safira/runtime/_service.py):

```python
from safira.runtime._service import simulate_synthetic_assessment
result = simulate_synthetic_assessment(request, registry=registry, verifier=verifier)
```

`SyntheticRuntimeRequest` in `_records.py` requires exactly: `prediction`, `scope`, `original_dataset`, `original_reference`, `original_signal_protocol`, `original_signal_set`, `estimator`, `calibrator`, `policy_protocol`, `policy`. Exact type checks require existing PredictionRecord, PolicyScope, DatasetBuildResult, Feature003DatasetReference, SignalProtocol, SignalFeatureSet, SafetyEstimatorArtifact, CalibratorArtifact, PolicySelectionProtocol and SelectivePolicyArtifact. Missing policy is not a constructible valid request. Do not invent a `SafetyAssessment` runtime constructor or public `assess` method. Legacy `SafetyContext` and `SafetyAssessment` retain patient-bearing fields and individual scores; neither belongs in this HTTP boundary. `ModelAdapter.predict(patient_data, label)` remains mandatory; evidence capabilities are explicit in `AdapterCapabilities`.

The service performs admission outside the readiness handler, derives one private signal record, applies Feature 005/006 frozen state, then exact Feature 007 comparison. Only `RuntimeReadinessFailure` during admitted processing becomes DEFER. `RuntimeAdmissionRejected` can also occur after initial admission during reference/scoring checks and must remain a rejection. Unexpected exceptions propagate to a sanitized HTTP 500.

## Trusted dependencies

| RuntimeVerifier operation | Host evidence required |
|---|---|
| `verify_prediction(prediction)` | Exact Feature 002 admission ledger: canonical content fingerprint, scope, association, provenance mode and input scope |
| `verify_synthetic_fixture(prediction)` | Exact host-created fixture membership; separate from prediction admission |
| `verify_original_predictors(reference, source_key, predictor_fingerprints, dataset_fingerprint, inventory_digest)` | Independently retained original training predictor inventory, reference identity and artifact inventory |
| `verify_signal_protocol(protocol, feature_set_digest, reference, source_key)` | Approved frozen protocol and feature manifest bindings |
| `verify_artifact(payload_digest, scope_key, artifact_version)` | Exact estimator/calibrator/policy origin entries; digests alone are insufficient |
| `verify_protocol(protocol)` | Feature 007 protocol approval recorded before outcomes |

All typed receipts are exact-scope checks executed by the configured host. No provider/receipt/authority is selected from an HTTP payload. HMAC `association_fingerprint` is process-local integrity binding, not synthetic-origin proof or independent artifact provenance; do not export it. Python private imports cannot defend against hostile code controlling the same process.

## Fixture reuse decision

[runtime_fixtures.py](../../tests/runtime_fixtures.py) `build_runtime_fixture(registered_collection, *, force_logistic=False)` delegates to `policy_fixtures.make_end_to_end_case`, which prepares real Feature 003 data, Feature 004 entropy features, trains/selects Feature 005, fits Feature 006 and selects Feature 007 using a distinct policy cohort. The runtime builder preapproves synthetic cutoff candidates `(0.25, 0.75)` before selection; these are test protocol settings, not caller/runtime threshold knobs. It registers query admission and synthetic membership separately.

The factory is not installed application API: `registered_collection` is a pytest generator fixture; its helpers include bare test-module imports, `tests.training_fixtures`, and `OriginLedger` from `test_calibration_bundle_gate`. Do not import pytest test modules in the running web app or call a fixture's private wrapper. Smallest compliant adaptation in Batch A: implement a **demo-owned synthetic host assembly** with equivalent explicit registration, synthetic row recipes and separately held ledgers, using real Safira services for every algorithm. Reuse recipe data and trust-contract ideas, not copied algorithm implementations. Keep all adapter/ledger classes under `demo/backend/app/fixtures/`; the synthetic primary adapter is deliberately deterministic and must be labeled as such. Safira scoring is real. Differential tests compare this assembly with the existing factory in pytest only.

Preparation happens once before readiness, outside `/run`, using synthetic development/selection data; freeze artifacts and ledger membership afterward. Each run gets an isolated registry/verifier view to prevent negative cases contaminating later runs. No new patient memberships can be added by the run request. Runtime must not train, recalibrate or reselect. Keep protected content absent from host preparation; do not configure a protected apply custodian or enumerate protected rows.

## Signal/reference nuance and trace feasibility

Runtime reconstructs kNN/domain references from original train predictors and patient-group references, checks exact frozen state digests, and applies them. This is deterministic recovery of approved state, not learning from the query. No original correctness/outcome or validation/calibration targets are consumed at runtime. The existing default end-to-end factory configures **only `bernoulli_entropy`**; its reference-state map is empty. Separate unit tests demonstrate kNN/domain reconstruction using isolated admitted helper objects, not a complete reference-based service scenario. Do not advertise all six signals as executed by this factory.

No step-level service telemetry exists. Use a request-local forwarding RuntimeVerifier decorator that delegates every operation, records only method alias/completed-or-rejected state, and never captures arguments or returned payloads. A completed callback alone means provider check returned, not that the whole admission passed. Only a returned final result establishes complete admission and frozen processing success. For DEFER, exact internal failing stage is unavailable. For rejection, preserve only actual host observations and the safe rejection code; later stages remain unobserved. No monkeypatch, global instrumentation, alternate orchestrator or duplicated scoring is needed. Detailed semantics are in [data model](data-model.md).

## Decision and remaining gates

Genuine integration is feasible without upstream contract changes. No blocking framework defect was found. Fixture adaptation and unmocked scenario qualification are normal Batch A implementation gates. TRUST and a natural CAUTION recipe have direct diagnostic evidence; DEFER still lacks an unmocked full-service fixture. Missing-policy and unsupported-explanation categories may remain educational-only; see [inventory](scenario-inventory.md). No mocks may replace the private service if a category proves infeasible.
