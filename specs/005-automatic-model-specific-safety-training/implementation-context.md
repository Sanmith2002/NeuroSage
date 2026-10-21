# Feature 005 Implementation Context

**Purpose:** Compact implementation handoff for review and later feature work. Feature 005 T001–T047 is implemented. Normative source: [spec.md](spec.md), approved Decisions A–E. Detailed design: [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), [Python contract](contracts/training-python.md), and verified usage in [quickstart.md](quickstart.md).

## Existing contracts and code to reuse

- `src/safira/registry/`: immutable exact Feature 001 model/version/label and classifier/adapter/preprocessing compatibility. Do not change it.
- `src/safira/collection/records.py`: Feature 002 `PredictionRecord`, exact source/association and provenance. Constructible records need independently checked admission.
- `src/safira/dataset/records.py`: Feature 003 `DatasetBuildResult.development.{train,validation,calibration}` and `CorrectnessExample.correctness_target`, restricted `patient_group_ref`, source prediction and partition role. Protected rows/complete manifest are separately controlled. Never serialize the development result into an ordinary Feature 005 artifact.
- Feature 003 and Feature 004 expose no separate `dataset_version` field. Bind the exact dataset build using `dataset_id`, `manifest_reference` and independently verified manifest digest, `protocol_id`/`protocol_version`, `builder_version`, and the complete admitted row inventory. A digest alone is not provenance.
- `src/safira/signals/records.py`: Feature 004 `SignalFeatureSet`, `SignalFeatureRecord`, `SignalResult`, `SignalRunManifest`, dataset reference, fitted-state references and `SignalRowKey`. `SignalFeatureSet.to_dict()` can be copied by a caller; presence is not trusted origin.
- `src/safira/signals/validation.py`: existing prediction and dataset admission patterns, complete row inventory checks and fingerprints. `src/safira/signals/service.py` derives opaque row key from dataset ID, manifest reference and complete prediction fingerprint; it creates cross-fitted train and frozen-reference validation signals. Reuse semantics without altering Feature 004.
- Existing synthetic fixtures and tests under `tests/`, especially `tests/signals_fixtures.py`, `tests/dataset_fixtures.py`, `tests/test_signals_dataset_integration.py`, and acceptance tests for Features 001–004.
- `pyproject.toml`: Python >=3.11; Feature 005 uses the approved direct runtime pin `scikit-learn==1.7.1`.

## Implemented modules and dependency order

1. `records.py`, `exceptions.py`: immutable per-scope protocol, input/result records, safe typed outcomes and allowlisted estimator artifact.
2. `verification.py`: complete injected Feature 002/003/004 admission, exact registration, full inventories, row-key bijection and patient-group validation before any fitting.
3. `features.py`: protocol-approved predictor schema and training-only preprocessing; state indicators preserve non-value states without copying targets or identifiers.
4. `candidates.py`: fixed prevalence and L2 logistic fitting, Brier selection, exact baseline tie, conditional AUROC/AP and explicit failure states.
5. `service.py`: `prepare` eligibility and public `train` orchestration, fitting only on train and selecting once on validation per exact scope.
6. `artifacts.py`: canonical digest, exact compatibility and injected origin verification for JSON-compatible artifact loading; no pickle/joblib loading or durability claim.
7. `__init__.py`: exports the reviewed service, protocol/configuration and artifact-validation contracts, not candidate fitting, matrix or trust-gate helpers.

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

## External inputs still required for real use

- A versioned, research-owner-approved training protocol must provide exact source-specific feature/state rules, independent-group and correctness-class support, preprocessing, logistic `C`/`tol`/`max_iter`, validation feasibility, candidate failure behavior and safe aggregate disclosure. Missing settings produce `NOT_READY`.
- Host-operated independent evidence ledger/verifier for real Feature 003/004/002 admissions and an authorized artifact custodian if durable storage is desired. The repository provides no clinical integration or receipt guarantee.
- Later independent calibration, policy-selection and protected final evaluation designs. Feature 005 must not borrow validation already spent on estimator selection or protected data.

## Verified test checkpoints

Synthetic test-first checks cover adversarial trust/alignment, schema and train-only preprocessing, candidate metrics/feasibility/ties, independent scopes and lifecycle, artifact compatibility/immutability/privacy/safe loading, and protocol-readiness outcomes. The verified results are 93 Feature 005 tests, 566 relevant Feature 001–004/adapter/context/assessment regression tests, 659 full-suite tests, and a passing `git diff --check`. These are software checks only; no scientific or clinical validation is claimed.
