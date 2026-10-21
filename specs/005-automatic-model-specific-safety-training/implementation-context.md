# Feature 005 Implementation Context

**Purpose:** Compact handoff for later `$speckit-tasks` and implementation sessions. Normative source: [spec.md](spec.md), approved Decisions A–E. Detailed design: [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), [Python contract](contracts/training-python.md).

## Existing contracts and code to reuse

- `src/safira/registry/`: immutable exact Feature 001 model/version/label and classifier/adapter/preprocessing compatibility. Do not change it.
- `src/safira/collection/records.py`: Feature 002 `PredictionRecord`, exact source/association and provenance. Constructible records need independently checked admission.
- `src/safira/dataset/records.py`: Feature 003 `DatasetBuildResult.development.{train,validation,calibration}` and `CorrectnessExample.correctness_target`, restricted `patient_group_ref`, source prediction and partition role. Protected rows/complete manifest are separately controlled. Never serialize the development result into an ordinary Feature 005 artifact.
- Feature 003 and Feature 004 expose no separate `dataset_version` field. Bind the exact dataset build using `dataset_id`, `manifest_reference` and independently verified manifest digest, `protocol_id`/`protocol_version`, `builder_version`, and the complete admitted row inventory. A digest alone is not provenance.
- `src/safira/signals/records.py`: Feature 004 `SignalFeatureSet`, `SignalFeatureRecord`, `SignalResult`, `SignalRunManifest`, dataset reference, fitted-state references and `SignalRowKey`. `SignalFeatureSet.to_dict()` can be copied by a caller; presence is not trusted origin.
- `src/safira/signals/validation.py`: existing prediction and dataset admission patterns, complete row inventory checks and fingerprints. `src/safira/signals/service.py` derives opaque row key from dataset ID, manifest reference and complete prediction fingerprint; it creates cross-fitted train and frozen-reference validation signals. Reuse semantics without altering Feature 004.
- Existing synthetic fixtures and tests under `tests/`, especially `tests/signals_fixtures.py`, `tests/dataset_fixtures.py`, `tests/test_signals_dataset_integration.py`, and acceptance tests for Features 001–004.
- `pyproject.toml`: Python >=3.11; current runtime dependencies empty. Implementation adds direct `scikit-learn==1.7.1` pin only for Feature 005.

## Proposed modules and order

1. `src/safira/training/records.py`, `exceptions.py`: frozen protocol, exact scope, schema, outcome/artifact and safe codes. Test nested mutation and serialization privacy first.
2. `verification.py`: explicit injected host verifier; independent Feature 003/004/002 evidence checks, exact registration, full inventories, row-key bijection, group disjointness. No public fit/cohort claim before this gate. Test forged/missing/mismatched ledgers first.
3. `features.py`: six-dimension availability profile, protocol allowlist, finite numeric and nominal seen/unseen, typed state indicators, training-only median/optional scaling and frozen order. No copied primary output or explanation metadata as predictors.
4. `candidates.py`: training-prevalence baseline; pinned scikit-learn L2 `lbfgs` logistic with fixed protocol-approved `C`/`tol`/`max_iter`; Brier comparison, exact tie baseline, conditional AUROC/AP, explicit convergence/numeric failure.
5. `service.py` and `__init__.py`: deterministic per-scope orchestration and privacy-safe artifact. Integrate and run focused plus full regressions. No new service/database, plugin registry or runtime assessment.

## Research-critical invariants

1. Exact `(model_id, model_version, label_id)` scope throughout; same label in another contributor/version never shares rows, schema, support or artifact.
2. Feature 003's verified `correctness_target` is the only target. Feature 004 validated predictor results are the only feature source. No threshold, target rebuild, signal recomputation or primary classifier retraining.
3. Neither typed objects nor caller digests prove authority. An independently controlled, injected verifier checks the actual complete dataset, feature set/run and every embedded Feature 002 admission. The trusted host is the operational trust root, and no real ledger is configured here.
4. Feature 003 patients remain grouped across visits, labels and contributors. Group keys are used only for trusted disjointness/adequacy, never candidate fitting, preprocessing, scoring or ordinary output.
5. Train fits candidate/preprocessing; validation compares once and is spent; calibration reserved; protected test unavailable. No second CV over Feature 004 cross-fitted training signals, no seed/parameter search or validation refit. For fit-isolation tests, changed validation/calibration data must either be independently reauthorized or passed only to isolated train-only helpers; unauthorized mutations fail full-service admission.
6. Six dimensions are optional families, not six separate estimators. Explanation reliability has no generic numerical V1 measurement. Unavailable evidence never becomes measured zero; all seven signal states retain meaning.
7. A valid two-class Brier comparison can select baseline or logistic; single-class baseline-only description is non-success. Selection metrics are not independent final estimates.
8. Artifact is deeply immutable, exact-compatible, privacy-safe, uncalibrated and non-deployable. JSON export/digest is not trusted provenance or durable persistence. No untrusted pickle/joblib load.
9. Synthetic software tests do not establish empirical generalization, calibration, clinical safety or authenticated external integrations.

## Inputs still requiring approval or integration

- Versioned protocol: exact source-specific feature/state/optional rules, independent-group and class support, preprocessing, logistic numeric `C`/`tol`/`max_iter`, metric feasibility and safe aggregate disclosure. Missing approval means `NOT_READY`.
- Host-operated independent evidence ledger/verifier for real Feature 003/004/002 admissions and an authorized artifact custodian if durable storage is desired. The repository provides no clinical integration or receipt guarantee.
- Later independent calibration, policy-selection and protected final evaluation designs. Feature 005 must not borrow validation already spent on estimator selection or protected data.

## Test checkpoints

Focused synthetic tests should cover (a) adversarial trust/alignment, (b) schema and train-only preprocessing, (c) candidate numeric/feasibility/tie behavior, (d) independent scopes and evidence lifecycle, and (e) artifact compatibility, immutability, privacy and safe load. Then run all Feature 005 tests, relevant Features 001–004 tests, full pytest and `git diff --check`. Use test-first red/green evidence; no test count is claimed yet.
