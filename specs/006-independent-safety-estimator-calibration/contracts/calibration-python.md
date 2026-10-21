# Python Contract — Feature 006 Calibration

**Status**: Proposed implementation contract. It adds a narrow `safira.calibration` package and does not change Features 001–005, `ModelAdapter`, `AdapterCapabilities`, `SafetyContext`, or `SafetyAssessment`.

## Public orchestration surface

Reuse Feature 005 `TrainingScope`, `SafetyEstimatorArtifact`, and Feature 003/004 immutable record types when their current semantics fit. Do not create parallel model registration, correctness target, prediction, signal, dataset, or preprocessing contracts.

Conceptual API:

```python
class CalibrationService:
    def __init__(
        self,
        registry: ModelRegistry,
        protocol: CalibrationProtocol,
        input_verifier: CalibrationInputVerifier,
    ) -> None: ...

    def calibrate(
        self,
        dataset: DatasetBuildResult,
        signals: SignalFeatureSet,
        artifacts: Mapping[tuple[str, str, str], SafetyEstimatorArtifact],
    ) -> tuple[CalibrationOutcome, ...]: ...
```

The call has no prediction/`apply` method. It accepts one selected Feature 005 artifact per authorized exact scope, verifies all shared inputs once, then returns deterministic exact-scope outcomes. Shared trust or inventory failure raises a stable typed verification error before any scope result is published. After complete shared admission, an individual scope may return `INSUFFICIENT_EVIDENCE`, `NOT_READY`, or another typed non-success while independent scopes complete. No partial success is published before the shared check passes.

## Trusted verifier injection boundary

```python
class CalibrationInputVerifier(Protocol):
    def verify_bundle(
        self,
        dataset: DatasetBuildResult,
        signals: SignalFeatureSet,
        artifacts: Mapping[tuple[str, str, str], SafetyEstimatorArtifact],
        protocol: CalibrationProtocol,
    ) -> CalibrationInputCheck: ...

    def verify_prediction(self, record: PredictionRecord) -> SignalInputCheck: ...

    def verify_estimator_artifact(
        self, payload_digest: str, scope_key: tuple[str, str, str], artifact_version: str,
    ) -> ArtifactOriginCheck: ...
```

The host controls verifier construction and connects it to independently controlled evidence. There is no hidden global provider. `CalibrationService.calibrate` invokes verification; callers cannot pass a previously constructed `CalibrationInputCheck` as a bypass. A custom verifier implementation selected by untrusted request data is forbidden.

The complete verifier check binds: exact Feature 001 registrations; each embedded ordinary Feature 002 prediction's content and assessment association; Feature 003 dataset, manifest reference/digest, protocol/version, builder version and complete ordinary inventory; exact Feature 003 calibration target inventory; Feature 004 dataset/run/method/parameter/fitted-reference identities and exact calibration rows; and each Feature 005 artifact's canonical digest, exact scope, artifact version and host-ledger origin. Feature 003 does not define a separate `dataset_version` or builder ID. Digests are integrity comparisons, not origin proof.

The service recomputes fingerprints and exact inventories from submitted values. For every `CorrectnessExample` in calibration it derives exactly one matching Feature 004 `SignalFeatureRecord` using the existing dataset ID, manifest reference, prediction fingerprint/row-key construction, exact `source_key`, association and role. It rejects missing, extra, duplicate, changed, stale, cross-role and mismatched records. It also checks the full ordinary source inventory and admission lineage before any score reconstruction; only the exact calibration tuple reaches the numerical path. Protected test rows and outcomes do not enter this API.

Newly created in-memory Feature 005 artifacts require a fresh trusted-host ledger entry as well as loaded artifacts. An artifact object returned by `SafetyTrainingService.train`, its `digest`, or an `accepted` assertion does not establish origin. The host must independently record and resolve the exact artifact content/scope/version before Feature 006 accepts it. No production ledger is configured. The core cannot authenticate arbitrary malicious Python controlling the trusted host.

## Protocol and statuses

`CalibrationProtocol` is deeply immutable/versioned. It declares exact scopes, selected base family/version, method version, occurrence-weighted objective, per-scope unique-group/correctness-class support, score-variation/identifiability requirements, disclosure policy, solver settings, separation criterion/version, convergence behavior, deterministic expectations and slope-ambiguity rule. Required missing approval is `NOT_READY`, not a default.

`CalibrationStatus` values:

| Status | Meaning |
|---|---|
| `CALIBRATOR_FITTED_UNEVALUATED` | Approved exact-scope mapping fit; no independent performance estimate. |
| `NOT_READY` | Protocol approval, authority, origin check, or required verifier is absent or incomplete. |
| `INSUFFICIENT_EVIDENCE` | Protocol-approved unique-group/class support or identifiability requirement unmet. |
| `UNAVAILABLE_REQUIRED_EVIDENCE` | An admitted calibration row lacks a required compatible Feature 004 signal under the frozen Feature 005 schema. |
| `INVALID_INPUT` | Malformed, altered, duplicated, nonfinite, or internally inconsistent data/configuration. |
| `INCOMPATIBLE_INPUT` | Exact model/version/label, adapter/preprocessing, base artifact, dataset/manifest, signal method/reference or protocol mismatch. |
| `NUMERICAL_FAILURE` | Separation, rank/degeneracy, nonconvergence, nonfinite result, non-positive slope, or other approved numerical failure. |

Use privacy-safe typed exceptions for shared admission and compatibility failures, and stable safe outcome reason codes for scope-local feasibility. Never expose raw optimizer exceptions, raw data, or user-supplied identifiers in ordinary diagnostics. No artifact is present on non-success.

## Private frozen-score path

Internal `scores.py` is not exported from `safira.calibration.__init__` and exposes no public inference surface. After admission:

1. Validate schema/preprocessing fields, ordered columns, active indices, class order `(0,1)`, artifact scope/digest and finite coefficient/intercept shapes.
2. Reconstruct the typed `FrozenFeatureSchema` and `FrozenPreprocessingState` view from the artifact's allowlisted Feature 005 values without fitting or editing them.
3. Reuse Feature 005 production `build_feature_schema`, `encode_rows` and `transform_rows` semantics in `src/safira/training/features.py`. Adapt only the serialized-to-typed boundary. Do not duplicate encoding/preprocessing or call `src/safira/training/artifacts.py::_reproduce_probability_for_test`.
4. For logistic artifacts, calculate only the private score `z = intercept + dot(coefficients, transformed_row)`. Reject nonfinite values and shape/order mismatches. The primary classifier is never called.
5. For a baseline, read `p0`; require finite strict interior `0 < p0 < 1`.

The internal batch is ephemeral. Correctness targets are fit targets and patient-group references are support-only metadata. Neither is a predictor column or exported result.

## Fixed numerical fitting

### Logistic base

Fit only `q = sigmoid(a + b*z)` with scikit-learn 1.7.1 `LogisticRegression` configured explicitly as `penalty=None`, `solver="lbfgs"`, `fit_intercept=True`, `class_weight=None`, `warm_start=False`, protocol-declared `tol` and `max_iter`, binary class order `(0,1)`, and unit occurrence weights (`sample_weight=None`). Do not rely on library defaults for penalty. The scikit-learn object is temporary and is never serialized.

Before fitting, verify both target classes, protocol support, finite score values and a nonconstant/rank-valid scalar design. Let `[m0, M0]` and `[m1, M1]` be the represented score ranges for correctness classes 0 and 1. Complete or quasi-complete separation exists exactly when `M0 <= m1` or `M1 <= m0`; finite-MLE feasibility requires both `M0 > m1` and `M1 > m0`. Equality is quasi-separation. This exact test correctly permits a singleton class score strictly inside the other class's range; positive-width intersection of the two closed intervals is not required. Check rank degeneracy first so a constant score receives the distinct degeneracy result. The approved protocol records the criterion/version and any separate numerical ambiguity handling; do not add a tolerance to the mathematical equality test. Treat convergence warnings/iteration exhaustion, separation, invalid rank, non-finite coefficients, protocol-defined slope ambiguity, or `b <= 0` as a safe `NUMERICAL_FAILURE` or protocol-designated non-success. Do not retry with other parameters, regularize, clip, reverse score order, or use a fallback.

Use stable sigmoid/log-likelihood calculations as needed. Test same-environment reproducibility; record scikit-learn, NumPy, SciPy and relevant runtime metadata. Do not claim cross-platform bitwise identity.

### Baseline base

For unit occurrence weights and both target classes, use the closed-form MLE `p_cal = mean(y)` and `a = logit(p_cal) - logit(p0)`. Compute logit stably with `log(p)-log1p(-p)`. It is algebraically identical to minimizing the approved one-parameter Bernoulli likelihood `q=sigmoid(logit(p0)+a)`. No optimizer, slope, pseudo-count or clipping is required. Return a constant-output marker; `q=p_cal` for each occurrence. If either target class is absent or either probability is not strict-interior, return the specified non-success.

The objective weights each occurrence equally. Adequacy separately counts unique verified patient groups and class support according to the exact protocol. No universal patient count, class ratio, score threshold, or tolerance is added.

## Artifact, compatibility and serialization

`CalibratorArtifact` is a new deeply immutable record with exact scope, method/schema version, finite family-specific parameters, exact base Feature 005 artifact digest/family/version, schema/preprocessing digests, Feature 001 compatibility references, Feature 003 manifest-bound build/protocol/inventory references, Feature 004 run/method/fitted-reference identities, protocol/configuration, dependency versions, permitted convergence/aggregate adequacy metadata, and mandatory lifecycle fields.

`to_dict()` returns detached allowlisted JSON-compatible data. It must contain no patient, group, occurrence, assessment or row identifiers; targets/outcomes; raw Feature 002/004 values; calibration rows; fitted sklearn instance; protected data; or restricted verifier payload. Artifact validation recomputes canonical digest and compares exact expected compatibility. Digest validation does not establish origin or persistence. No loader uses pickle/joblib. This feature has no external persistence integration.

The frozen mapping is not applied to per-patient rows by any public method. No `predict`, `apply`, calibrated `SafetyContext`, `SafetyAssessment`, policy or deployment API is introduced.

## Proposed package responsibilities

| Path | Responsibility |
|---|---|
| `src/safira/calibration/records.py` | Protocol, status/outcome, verification check and immutable artifact records. |
| `src/safira/calibration/verification.py` | Explicit verifier protocol, complete inventory reconstruction, exact registry/partition/signal/artifact checks. |
| `src/safira/calibration/scores.py` | Private validated deserialization of frozen schema/preprocessing and one-row frozen score reconstruction. |
| `src/safira/calibration/fitting.py` | Fixed unpenalized logistic fitting, exact feasibility checks, baseline closed-form MLE. |
| `src/safira/calibration/service.py` | Atomic shared admission and exact-scope outcome orchestration. |
| `src/safira/calibration/exceptions.py` | Stable privacy-safe typed shared failures. |

No existing Feature 001–005 source module or public contract changes are planned. If code inspection proves a needed upstream helper is inaccessible, prefer a narrowly reasoned Feature 006 adapter and regression tests over changing an established contract.

## Synthetic test contract

- Each verifier fixture uses a separately controlled in-memory ledger. Positive cases create legitimate ledger entries independently; constructing a check object alone is a negative case.
- Admission tests mutate one field at a time and assert no private score or fit helper is reached before a complete check.
- Private numeric tests compare frozen logistic transformed rows/linear scores to synthetic scikit-learn training state; the comparison helper remains in test-only code.
- No test modifies an already admitted dataset and passes its old verification. To test fit independence, hold the admitted calibration inputs and frozen base artifact fixed and vary only non-consumed train/validation views in isolated internal helper tests, or freshly reauthorize complete fixtures.
- Group and occurrence identifiers exist only in restricted synthetic fixtures; exhaustive export/exception/representation scans verify they do not appear in ordinary outputs.

## Crosswalk

| Specification | Plan coverage |
|---|---|
| FR-001–FR-006 | Admission architecture, verifier contract and exact inventory tests. |
| FR-007–FR-010, FR-016 | Private score reconstruction and fixed family-specific fit. |
| FR-011–FR-015 | Occurrence/group support, error semantics and numerical feasibility. |
| FR-017, FR-022 | Explicit partition lifecycle and no protected-test access. |
| FR-018–FR-021, FR-025 | Immutable artifact, serialization, reporting and privacy. |
| FR-023–FR-024, FR-026 | Exact-scope configuration, reproducibility and synthetic/regression coverage. |
| SC-001–SC-009 | Admission, formula, support, adversarial input, numeric, lifecycle, artifact, privacy and full regression verification. |

## Sources

- Feature 006 [specification](../spec.md) and [approved decision record](../decision-record.md).
- Preserved [methodology review](../methodology-review.md) and [architecture-feasibility review](../architecture-feasibility.md).
- scikit-learn [LogisticRegression 1.7 API](https://scikit-learn.org/1.7/modules/generated/sklearn.linear_model.LogisticRegression.html) and [1.7.1 implementation](https://github.com/scikit-learn/scikit-learn/blob/1.7.1/sklearn/linear_model/_logistic.py).
- Albert & Anderson (1984), [logistic MLE existence and separation](https://doi.org/10.1093/biomet/71.1.1).
