# Feature 006 Implementation Context

Reusable handoff for implementation sessions. Authority order: Constitution v3.0.0, [spec.md](spec.md), [decision-record.md](decision-record.md), then [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), and [contracts/calibration-python.md](contracts/calibration-python.md).

## Existing contracts to reuse

- **Feature 001**: `ModelRegistry` exact model/version registration, label, classifier artifact, adapter identity and preprocessing compatibility. Never pool independently registered contributors.
- **Feature 002**: `PredictionRecord` and independent admission lineage. Constructing a record, matching digest, Boolean, or asserted status does not establish origin.
- **Feature 003**: `DatasetBuildResult.development.calibration` contains `CorrectnessExample` with exact prediction, binary `correctness_target`, partition role, target/protocol context, and restricted patient group reference. Protected final-test observations remain outside ordinary API. Identity is the existing manifest-bound tuple `(dataset_id, manifest_reference, manifest_digest, protocol_id, protocol_version, builder_version, complete inventory)`; no separate dataset-version or builder-ID field exists.
- **Feature 004**: `SignalFeatureSet.calibration`, `Feature003DatasetReference`, `SignalFeatureRecord` row/source keys, run manifest, method configuration and fitted-reference identity. Align exactly to Feature 003 calibration examples; do not recompute signals or refit reference states.
- **Feature 005**: `TrainingScope`, frozen `SafetyEstimatorArtifact`, safe schema/preprocessing and family state, `ArtifactCompatibility`, `ArtifactOriginCheck`, and `validate_artifact` pattern. For newly created and loaded base artifacts, require an independently ledger-backed host verification of payload digest, exact scope and artifact version. Existing transforms live in `src/safira/training/features.py`; `_reproduce_probability_for_test` in `src/safira/training/artifacts.py` is test-only and must not be imported by production code.

`pyproject.toml` pins scikit-learn 1.7.1; installed environment was also 1.7.1 at planning time. No production dataset/evidence/artifact ledger, artifact custodian, or durable output store is configured. A trusted host must supply verifiers; the library cannot authenticate malicious Python controlling that host.

## Intended package

```text
src/safira/calibration/
  __init__.py       # Narrow protocol/service/outcome/artifact exports; no apply/predict
  records.py        # Deeply immutable protocol, checks, outcomes and calibrator artifact
  verification.py   # Explicit injected verifier + local fingerprint/inventory rechecks
  scores.py         # Private artifact schema/preprocessing reconstruction and frozen z
  fitting.py        # Fixed logistic MLE, feasibility checks, baseline closed-form offset
  service.py        # Complete shared admission then independent exact-scope outcomes
  exceptions.py     # Stable privacy-safe shared failures
tests/
  calibration_fixtures.py
  test_calibration_records.py
  test_calibration_admission.py
  test_calibration_scores.py
  test_calibration_fitting.py
  test_calibration_artifacts.py
  test_calibration_acceptance.py
  test_calibration_regression.py
```

Keep Features 001–005 unchanged. Do not add dependencies, services, databases, CLI/REST endpoints, per-patient inference or `SafetyAssessment` behavior.

## Dependency order

1. Test and implement immutable protocols, exact scopes, status records and allowlisted artifacts.
2. Test and implement injected host verification, exact dataset/manifest and Feature 002/003/004 inventory admission, registry compatibility, Feature 005 artifact origin, atomic shared rejection and scope isolation.
3. Test and implement a Feature 006-private parser that reconstructs the exact typed frozen schema/preprocessing exclusively from the validated Feature 005 artifact's allowlisted representation. Validate its supported existing `artifact_version` and corresponding schema/preprocessing field shapes (there is no separate Feature 005 `schema_version` field), dimensions, ordered columns/active indices, categorical/state mappings, finite parameters, and compatibility. Never call `build_feature_schema` or `fit_preprocessing` on calibration data. Reuse only `encode_rows(schema, rows)` and `transform_rows(state, schema, rows)` with those reconstructed objects. Establish synthetic score parity and baseline `p0` validation.
4. Test logistic class support, one-dimensional score variation/separation, stable likelihood fitting, convergence and positive-slope rules; test the baseline MLE `a=logit(mean(y))-logit(p0)` and constant output.
5. Test complete service lifecycle, failure distinctions, multi-configuration/exact-scope independence, serialization privacy, compatibility and no protected/train/validation leakage.
6. Run focused suites, relevant Feature 001–005 regression tests, then full pytest; update quickstart only with commands/results actually verified.

## Research-critical invariants

- Decisions A–G are fixed. One calibrator per exact `(model_id, model_version, label_id)`; no algorithm comparison, isotonic, successful identity map, retraining, retuning, or pooling.
- Logistic: `q=sigmoid(a+b*z)`, unpenalized MLE, explicit scikit-learn 1.7.1 `penalty=None`, `solver='lbfgs'`, unit occurrence weights and protocol-fixed settings. Non-positive slope or numerical failure is non-success; no fallback or changed-parameter retry.
- Baseline: strict `0<p0<1`; fit only offset; `q` stays constant. With both classes and unit occurrence weights, `p_cal=mean(y)` and `a=logit(p_cal)-logit(p0)`. No pseudo-counts or clipping.
- Score `z` comes from Feature 004 calibration signals under the exact frozen Feature 005 schema/preprocessing and stored coefficients/intercept. No transform is fit or changed; no primary model is called; no public score application exists.
- Occurrences have equal objective weight. Unique verified patient groups determine independent support; group/occurrence IDs are restricted support metadata only, never predictors or artifact fields.
- Only fully authorized Feature 003 calibration targets + exactly aligned Feature 004 calibration rows affect fit. Feature 005 validation is spent. Protected final test is inaccessible. Calibration is spent after fitting.
- Shared admission checks run before any score/fitter and fail closed. A per-scope inadequacy may coexist with another scope's result only after shared inputs have been completely verified.
- Distinguish missing/extra/forged or malformed/incompatible records from an admitted aligned record whose required predictor cannot be formed under the frozen Feature 005 state. Permitted non-value states use existing frozen handling. Batch A may inspect evidence-state and frozen-policy metadata only; Batch B can detect a transformation-time `UNAVAILABLE_REQUIRED_EVIDENCE`; Batch C reports it for that scope without fitting while preserving independent eligible scopes.
- Distinct outcomes: `NOT_READY`, `INSUFFICIENT_EVIDENCE`, `UNAVAILABLE_REQUIRED_EVIDENCE`, `INVALID_INPUT`, `INCOMPATIBLE_INPUT`, `NUMERICAL_FAILURE`, `CALIBRATOR_FITTED_UNEVALUATED`. No non-success artifact.
- Artifacts are deeply immutable, allowlisted JSON-compatible, non-deployable, not independently evaluated and not clinically validated. No patient/row/target/raw evidence/restricted verifier/protected content. Digests do not prove origin or persistence.
- Passing tests demonstrate software behavior only. No independent calibration performance, clinical safety, transportability or effectiveness is established.
