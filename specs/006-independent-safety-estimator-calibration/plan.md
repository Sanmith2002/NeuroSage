# Implementation Plan: Independent Safety Estimator Calibration

**Branch**: `feature-06/Independent-calibration` | **Date**: 2026-10-21 | **Spec**: [spec.md](spec.md)

**Input**: Finalized Feature 006 specification, decisions A–G, methodology review and architecture-feasibility research.

## Summary

Implement a narrow Python-library stage that independently verifies exact-scope Feature 001–005 inputs, privately reconstructs the frozen Feature 005 score from the matched Feature 004 calibration features, fits exactly one approved family-specific calibration mapping per `(model_id, model_version, label_id)`, and produces a deeply immutable, privacy-safe `CALIBRATOR_FITTED_UNEVALUATED` artifact. The service does not train or execute the primary classifier, refit the Feature 005 estimator or preprocessing, access protected test data, expose calibrated per-patient inference, or evaluate calibration performance.

## Technical Context

**Language/Version**: Python 3.11+ (project target).
**Primary Dependencies**: Existing project dependency `scikit-learn==1.7.1`; NumPy/SciPy versions are recorded from the exact Feature 005 artifact/runtime dependency metadata. No new dependency is planned.
**Storage**: No new database or storage service. Artifacts are constructed in memory and exported as allowlisted JSON-compatible values; export is not a persistence guarantee.
**Testing**: `pytest`, using synthetic Feature 001–005 records and independently controlled trusted test ledgers.
**Target Platform**: Existing Python package runtime; no new platform target.
**Project Type**: Python research library.
**Performance Goals**: No latency or throughput target is specified. Process only the exact authorized calibration inventory in memory; no real-time path.
**Constraints**: No universal support minima, score-variation cutoffs, solver tolerances, iteration limits or slope ambiguity thresholds. These are exact-scope, versioned-protocol settings approved before outcome access. No Features 001–005 contract changes. No patient-level inference API, safety assessment, policy, protected-test use or clinical claim.
**Scale/Scope**: One independent result per exact model/version/label scope in the admitted calibration set; multiple contributors and overlapping labels remain separate.

### Implementation Dependencies and Verified Repository Facts

- `pyproject.toml` already pins scikit-learn 1.7.1; the inspected Python environment reports 1.7.1. No dependency installation is needed for planning.
- Feature 001 `ModelRegistry` resolves exact registrations and adapter/classifier/preprocessing identity.
- Feature 003 `DatasetBuildResult.development.calibration` contains `CorrectnessExample` records with `correctness_target`, partition role and restricted patient-group reference. Protected rows are outside ordinary results. Its verified build identity uses dataset ID, manifest reference/digest, protocol ID/version, `builder_version` and complete inventory; no independent `dataset_version` field exists.
- Feature 004 `SignalFeatureSet.calibration` holds immutable `SignalFeatureRecord` rows under a matching `Feature003DatasetReference`, with a run manifest, method configuration and fitted-reference identities.
- Feature 005 `SafetyEstimatorArtifact` is deeply immutable and stores its exact source scope, selected family, ordered schema, frozen preprocessing, baseline probability or logistic coefficients/intercept/classes, Feature 003 manifest-bound identity, Feature 004 run/method/reference identity, dependency versions and lifecycle flags. `validate_artifact` applies an injected origin verifier to safely loaded allowlisted content. `src/safira/training/features.py` contains production feature encoding/transformation functions. `src/safira/training/artifacts.py::_reproduce_probability_for_test` is explicitly test-only and must not be used by production Feature 006.
- There is no configured production dataset ledger, Feature 002/003/004 evidence service, Feature 005 artifact ledger/custodian, Feature 006 verifier, or durable calibrator storage integration. A real authorized host must inject and control those providers.

## Constitution Check — Before Design

| Principle | Gate | Plan response |
|---|---|---|
| I. Post-hoc reliability, not disease prediction | PASS | Target is correctness of the exact existing classifier prediction; no primary prediction or diagnosis is generated. |
| II. Classifier-scoped labels and patient isolation | PASS | Independent exact `(model_id, model_version, label_id)` outcomes; group references are used only for trusted support checks, never predictors. |
| III. Preserve existing adapter and assessment contracts | PASS | Compose existing registry, dataset, signal and training records; no existing contract changes are planned. |
| IV. Exactly six safety dimensions | PASS | Consume the frozen Feature 005 schema derived from Feature 004; add no dimension or signal. |
| V. Model-specific packages and version compatibility | PASS | Bind each calibrator to exact registered classifier/version/label and selected estimator compatibility. |
| VI–IX. Evidence, held-out boundaries and safe failures | PASS | Use only Feature 003 calibration correctness targets and aligned Feature 004 calibration rows; preserve train, spent validation, calibration-spent and protected-test boundaries. |
| X. Privacy and claim discipline | PASS | Restricted identifiers/rows/targets stay out of ordinary outputs; artifacts are non-deployable and not independently evaluated or clinically validated. |
| XI. Automated verification and reproducibility | PASS | Test-first synthetic tests, stable reason codes, pinned dependency metadata and deterministic same-environment checks. |
| XII. Specification-driven change | PASS | This plan follows the approved spec and introduces no implementation outside Feature 006. |
| XIII. Research prototype boundary | PASS | No clinical, deployment-readiness, reliability-policy or safety claims. |

**Pre-design gate**: PASS. All research decisions A–G are approved. Exact numerical settings and scope adequacy criteria are delegated to a versioned protocol and are prerequisites to a run, not open feature-method decisions.

## Architecture

### Admission and orchestration

`CalibrationService` receives a registry, immutable `CalibrationProtocol`, and explicitly injected `CalibrationInputVerifier`. It performs a complete shared admission before returning any outcome or starting score reconstruction. Admission verifies exact Feature 001 registration; every embedded Feature 002 prediction's independently controlled lineage; Feature 003 dataset/manifest authorization, complete ordinary inventory and calibration targets; Feature 004 exact aligned calibration rows, methods and fitted-state identities; and Feature 005 artifact compatibility and independently accepted origin. The core independently compares content fingerprints, source keys, associations, partition roles, row inventory, schema/order and exact scope to the verifier response.

The service does not accept a preconstructed `verified=True` result in place of executing the verifier. It has no module-global provider. A shared inventory/trust failure rejects the whole call before publishing per-scope outcomes. After shared admission succeeds, exact-scope inadequacy is returned only for that scope; independent eligible scopes may complete separately.

Both freshly produced in-memory and loaded Feature 005 artifacts require a host-ledger-backed origin check bound to the canonical artifact payload digest, exact source key and artifact version. For a fresh in-memory artifact, the authorized host must independently record and verify the artifact before Feature 006 admission. The Feature 006 library cannot authenticate arbitrary hostile Python controlling its trusted process. No production verifier or custodian is present in the repository.

### Private frozen-score application

For each admitted calibration `SignalFeatureRecord`, a private `FrozenScoreReconstructor`:

1. Validates the Feature 005 artifact's safe schema, preprocessing, estimator family, class order `(0, 1)`, finite parameter shapes, exact scope and compatibility.
2. Reconstructs the typed frozen Feature 005 schema/preprocessing from the allowlisted artifact values without refitting them.
3. Uses a Feature 006-private serialized-to-typed adapter to reconstruct the exact `FrozenFeatureSchema` and `FrozenPreprocessingState` exclusively from the already validated Feature 005 artifact's allowlisted representation. The adapter validates the supported existing `artifact_version` and corresponding schema/preprocessing field shapes (Feature 005 defines no separate `schema_version` field), dimensions, ordered columns, active indices, categorical/state mappings, finite preprocessing values, and exact artifact compatibility. It MUST NOT call `build_feature_schema` or `fit_preprocessing` while consuming calibration data: the former learns a schema from supplied training rows, and the latter fits learned state. After reconstruction, Feature 006 may call Feature 005's production `encode_rows` and `transform_rows` only with those validated frozen objects and their actual signatures. No schema, column order, active index, category mapping, missingness policy, imputation value, or scaling parameter is learned or refitted from calibration observations.
4. For `l2_logistic`, calculates the private frozen score `z = intercept + dot(coefficients, transformed_row)` after checking active-column order and finite values. The calibrator consumes `z`, not the primary classifier score. A stable sigmoid is used only where needed for internal parity/validation.
5. For `prevalence_baseline`, reads the artifact's constant `p0`, requiring finite `0 < p0 < 1`.

If an admitted, exactly aligned signal record contains an unavailable non-value that the already frozen Feature 005 state is approved to handle, apply that state unchanged. Do not relabel every non-value as unavailable. If a required predictor cannot be formed under the validated frozen schema/state policy, produce the affected scope's `UNAVAILABLE_REQUIRED_EVIDENCE` without fitting that scope. Batch A may inspect admitted evidence states and approved frozen-policy metadata to identify this outcome when determinable without transformation; it MUST NOT construct or learn a schema, fit preprocessing, or reconstruct numerical scores. If the condition is discoverable only during frozen transformation, the private Batch B path must return a typed scope-local non-success for the Batch C service to report. A missing, extra, forged, malformed, or incompatible row remains an admission failure, not an unavailable-signal outcome.

The implementation MUST NOT use Feature 005's test-only probability helper and MUST NOT expose an apply/predict method to callers. Synthetic parity tests compare the internal reconstructed scores to a test-only use of the original selected estimator without storing test inputs in artifacts.

### Approved calibration fitting

For logistic base estimator, fit only the two mapping parameters in `q = sigmoid(a + b*z)` with Bernoulli maximum likelihood. Use scikit-learn 1.7.1 `LogisticRegression(penalty=None, solver="lbfgs", fit_intercept=True, class_weight=None, warm_start=False, max_iter=protocol.max_iter, tol=protocol.tol)` with binary target order `(0,1)` and unit per-occurrence weights. Do not inherit the default L2 penalty. Store no sklearn estimator object.

Before fitting, require both classes, protocol group/class support and finite varying `z`. For the one-dimensional score plus intercept, reject complete or quasi-complete separation exactly when `max(z0) <= min(z1)` or `max(z1) <= min(z0)`; finite-MLE feasibility requires both strict cross-endpoint inequalities `max(z0) > min(z1)` and `max(z1) > min(z0)`. Do not require positive-width intersection of the two closed class ranges: a singleton score strictly inside the other class's range can be a finite-MLE case. First test full rank of the intercept-plus-score design so an all-constant score is reported as degenerate, separately from separation. The protocol pins this exact criterion/version and any separate numeric ambiguity policy; no tolerance is added to the mathematical equality check. Treat warning/nonconvergence, protocol-defined separation/identifiability failure, non-finite estimate, invalid rank, or fitted `b <= 0` as an explicit non-success. Do not switch solvers, regularize, clip, reverse ordering, retry under altered settings, or fall back.

For baseline, compute the unique unit-occurrence MLE analytically: `p_cal = mean(correctness_target)` and `a = logit(p_cal) - logit(p0)`. Both classes and `0<p0<1` ensure finite strict-interior values. Use `log`/`log1p`; do not use pseudo-counts or clipping. `q = p_cal` is the same for every occurrence and is explicitly non-individualized. Protocol adequacy is independently assessed on unique patient groups.

All protocol parameters (unique group/class support, logistic score variation criteria, solver tolerance/iterations, convergence and separation criteria, deterministic expectations, disclosure, and slope ambiguity policy) are frozen before calibration outcomes are examined. No universal threshold is introduced.

### Artifact and privacy boundary

Each successful exact-scope outcome contains an immutable `CalibratorArtifact` with the family-specific finite mapping state, method/schema version, exact Feature 005 artifact digest/family/version, schema/preprocessing digests, exact model/version/label and registry compatibility, Feature 003 dataset/manifest/protocol/builder/inventory references, Feature 004 calibration run/method/fitted-reference IDs, approved calibration protocol/configuration, dependency versions, permitted convergence and aggregate adequacy metadata, and lifecycle status. Baseline artifacts record constant output and no individualized discrimination.

Serialization is detached allowlisted JSON-compatible data; no pickle/joblib or fitted sklearn object. No patient/group/occurrence/row IDs, correctness targets, outcomes, source observations, raw signal rows, verification payloads or protected values are serialized. A digest detects content changes but is not origin authentication or persistence proof. Output creation is in-memory; durable storage needs a separately authorized custodian integration and is not part of this feature.

### Failure semantics and lifecycle

Public service flow: full shared admission → exact per-scope compatibility → protocol readiness → exact calibration row alignment → support/evidence feasibility → private frozen score reconstruction → one fixed mapping → immutable artifact or non-success outcome. A scope with a preflight non-success short-circuits before score reconstruction and fitting; a scope-local `UNAVAILABLE_REQUIRED_EVIDENCE` discovered during frozen transformation also short-circuits before fitting. Neither condition blocks an independently eligible scope after shared admission succeeds. Shared admission does not partially publish outcomes. Per-scope `NOT_READY`, `INSUFFICIENT_EVIDENCE`, `UNAVAILABLE_REQUIRED_EVIDENCE`, `INVALID_INPUT`, `INCOMPATIBLE_INPUT` and `NUMERICAL_FAILURE` remain distinct. No artifact accompanies a non-success.

Only `DatasetBuildResult.development.calibration` and `SignalFeatureSet.calibration` can affect fitting. Train is not reread as fitting evidence; validation is spent and not reused; calibration is spent after fit; protected final-test is unavailable to this feature. There is no independent calibrator evaluation result, per-patient application, safety assessment or policy selection.

## Project Structure

### Documentation

```text
specs/006-independent-safety-estimator-calibration/
├── spec.md
├── decision-record.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/calibration-python.md
├── quickstart.md
├── implementation-context.md
└── tasks.md                  # Later $speckit-tasks stage; not created here
```

### Source Code (proposed only)

```text
src/safira/calibration/
├── __init__.py              # Narrow public protocol/service/artifact exports
├── records.py               # Frozen protocol, scope, check, outcome, artifact
├── verification.py          # Host verifier interface; exact inventory rechecks
├── scores.py                # Private frozen Feature 005 score reconstruction
├── fitting.py               # Fixed logistic MLE and baseline offset MLE
├── service.py               # Atomic shared admission and per-scope orchestration
└── exceptions.py            # Safe typed admission/compatibility/numerical failures

tests/
├── calibration_fixtures.py  # Synthetic registry, data, signals, artifacts, ledgers
├── test_calibration_records.py
├── test_calibration_admission.py
├── test_calibration_scores.py
├── test_calibration_fitting.py
├── test_calibration_artifacts.py
├── test_calibration_acceptance.py
└── test_calibration_regression.py
```

**Structure Decision**: Add one cohesive `safira.calibration` package consistent with existing Feature 003/004/005 package conventions. Keep parsing/transforms, fitting and verification in small modules so privacy and method boundaries can be tested independently. Do not create a database, service, CLI, REST endpoint, or new Feature 001–005 package abstraction.

## Test Strategy and Acceptance Mapping

1. **Records and immutability**: nested mutation, detached export, exact source keys, valid lifecycle and prohibited sensitive-field rejection (FR-018–FR-020; SC-007–SC-008).
2. **Admission first**: independently controlled ledgers for Feature 001–005; forged or missing host evidence; all record lineages; wrong/stale manifest, artifact, protocol, method, fitted reference, scope, association and role; missing/extra/duplicate inventory. Assert no score helper or fitter executes on failure (FR-002–FR-006; SC-001, SC-004).
3. **Score parity**: reconstruct ordered raw and transformed vectors and logistic `z` from persisted artifact state; compare against the original frozen test estimator. Verify baseline constant and reject malformed dimensions, nonfinite values, class order or incompatible schema (FR-007, FR-009, FR-016; SC-002, SC-007).
4. **Formula and weighting**: synthetic known cases for `sigmoid(a+b*z)` and baseline closed-form offset; occurrence repetitions affect objective as approved, while unique group support counts repeated visits once. Independent calculations are test-only (FR-008–FR-012; SC-002–SC-003).
5. **Numerical failures**: absent classes, baseline boundary probability, exact constant score, one-dimensional separation/touching ranges, rank deficiency, convergence warning/nonconvergence, non-finite output and non-positive/ambiguous slope. Verify typed states and absence of fallback or changed parameters (FR-012–FR-015; SC-005).
6. **Lifecycle, scopes and privacy**: standalone binary, multilabel, independent contributors with overlapping labels, multiple versions; shared admission fails atomically, scope insufficiency remains isolated; alter train/validation while holding admitted calibration inputs and frozen artifact fixed; no access to protected rows; inspect every ordinary result, repr, error and serializer (FR-011, FR-017, FR-021–FR-026; SC-003, SC-006, SC-008).
7. **Regression**: run relevant Features 001–005 tests and final full `pytest` suite. Confirm no upstream source/contracts changed (SC-009).

All test data are synthetic. Passing pytest demonstrates software behavior only, not scientific effectiveness or clinical validation.

## Constitution Check — Post-Design

| Principle | Result | Design evidence |
|---|---|---|
| I. Post-hoc correctness reliability | PASS | A frozen correctness estimator is recalibrated; no disease inference is generated. |
| II. Exact classifier-label scope and isolation | PASS | Each model/version/label is independent; unique group IDs are restricted to support verification. |
| III. Preserve contracts | PASS | Existing registry, collection, dataset, signals, context, assessment and training types are consumed unchanged. |
| IV. Six dimensions | PASS | Only Feature 004's frozen approved predictor schema is consumed. |
| V. Exact version package compatibility | PASS | Calibrator binds to registration, adapter, preprocessing, selected estimator and all source references. |
| VI–IX. Sufficient evidence, privacy-safe failures, no arbitrary threshold or policy | PASS | Exact protocol readiness, typed non-success, no threshold/policy/assessment logic. |
| X. Privacy and claims | PASS | Allowlisted output omits identifiers, targets, rows and restricted content; non-deployable/not evaluated/not clinically validated. |
| XI. Automated verification | PASS | Focused adversarial synthetic tests plus full regression suite are planned. |
| XII. Specification-driven development | PASS | Follows finalized Feature 006 spec; implementation tasks remain deferred. |
| XIII. Research prototype boundary | PASS | No clinical effectiveness, safety or deployment claims. |

**Post-design gate**: PASS. The only operational prerequisites are a versioned approved protocol and actual trusted-host integrations. No production trust ledger or durable custodian is available in the repository. These are documented integration limitations, not architecture approval for an absent service.

## Open Integration Risks (not specification blockers)

- A trusted deployment host must independently establish ledger-backed admission for Feature 002/003/004 evidence and both in-memory and loaded Feature 005 artifact origin. Synthetic fixture verifiers are not production integrations.
- Feature 005 persists its transform state as allowlisted mappings; Feature 006 must parse and validate those fields and reuse Feature 005's production transform behavior without changing Feature 005 contracts. Parity tests are a release gate.
- Exact solver numerical settings, support criteria, score-variation feasibility, separation protocol identifier/version, slope ambiguity handling and disclosure require approved protocol values before a run. The code must return `NOT_READY` when required values are absent.
- Numerical results can depend on platform BLAS/SciPy runtime despite deterministic same-environment settings; artifact metadata and quickstart must limit claims accordingly.
- There is no independent evaluation set, policy-selection evidence, clinical source system, or durable artifact custodian configured.

## Complexity Tracking

No Constitution violations are proposed. No additional project, service, database, dependency or external API is required.
