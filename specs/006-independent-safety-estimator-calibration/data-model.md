# Feature 006 Data Model — Independent Safety Estimator Calibration

This document defines proposed immutable records and their invariants. Names are planning contracts; exact Python signatures are in [calibration-python.md](contracts/calibration-python.md). Existing Feature 001–005 record types are referenced rather than redefined.

## Identity and scope

### CalibrationScope

The scope key is exactly `(model_id, model_version, label_id)`. Reuse Feature 005 `TrainingScope` where possible so classifier artifact SHA-256, adapter ID/version/fingerprint, preprocessing identity, task kind and registered source identity remain attached. A scope is never inferred from a component name or label alone.

**Invariants**: scope values match one exact Feature 001 registration, one Feature 005 selected artifact and all Feature 003/004 records for the calibration fit. Overlapping label IDs from different contributors remain separate. No cross-version or cross-label parameter pooling.

### CalibrationProtocol

An immutable, versioned declaration approved before reading calibration outcomes. It binds:

- protocol ID, version and canonical configuration digest;
- the authorized exact scopes and per-scope selected Feature 005 artifact versions/families;
- approved method identity/version (`logistic_recalibration_v1` family-specific rule);
- per-scope unique patient-group support and correctness-class criteria;
- per-scope logistic score-variation/identifiability criteria;
- fixed scikit-learn 1.7.1 `lbfgs` solver settings: explicit unpenalized penalty, tolerance, max iterations, convergence policy, separation check/version, deterministic expectations and slope-ambiguity rule;
- allowed aggregate metadata disclosure;
- the occurrence-weighted objective and lifecycle/access policy.

**Invariants**: no implicit defaults for required approval; no universal sample minimum or hidden tolerance; protocol is deeply immutable. Incomplete approval yields `NOT_READY`. All method or support decisions are fixed before calibration outcomes are examined.

## Input and trust records

### CalibrationInputBundle

An orchestration value composed of existing types:

- Feature 003 `DatasetBuildResult`, with ordinary development train/validation/calibration rows;
- Feature 004 `SignalFeatureSet`, with the calibration feature tuple;
- exact Feature 001 registry handle and approved `CalibrationProtocol`;
- one Feature 005 `SafetyEstimatorArtifact` per protocol-authorized exact scope.

The bundle is not itself verified. No caller-set state on this object is accepted as admission evidence.

### CalibrationInputVerifier and CalibrationInputCheck

The trusted host injects a verifier that independently resolves the evidence ledgers for Feature 002 prediction admission, Feature 003 dataset/manifest, Feature 004 run, and Feature 005 artifact origin. Feature 006 invokes that verifier and compares its results with canonical fingerprints and inventory recomputed from the actual bundle.

`CalibrationInputCheck` carries only restricted verification references, exact dataset/manifest/protocol/builder identity, complete ordinary dataset and feature-set fingerprints, exact role/scope inventories, signal method/fitted-reference identities, Feature 005 artifact digest/scope/version origin checks, and authority/method/time/version information. It must not carry patient IDs, target values, raw records, raw verifier payloads, or protected test data into a normal outcome or artifact.

**Required binding**: dataset ID + manifest reference + manifest digest + protocol ID/version + builder version + complete authorized inventory; Feature 004 dataset reference/run/method configuration/fitted-state references and exact row alignment; artifact canonical payload digest + exact source key + artifact version. The model does not invent a separate dataset-version or builder-ID field.

**Trust invariants**:

- The verifier is explicitly injected by trusted host configuration; no global lookup or caller-selected request provider.
- The service executes verification on every call. It does not accept a constructed check, Boolean, status string, digest, or receipt as a substitute for that execution.
- Every embedded ordinary Feature 002 prediction is verified against exact content and association. The full ordinary dataset inventory and manifest authorization are checked before any scope is processed.
- The core independently checks registry identity, complete calibration prediction/feature pairing, one-to-one row keys, exact source/label/version, associations, roles, and Feature 004 method/reference compatibility.
- Every Feature 005 object, whether newly created in memory or loaded, must have an independent host-ledger origin record bound to its digest, scope and artifact version. Without that record the call is not ready.
- The library cannot authenticate arbitrary malicious code controlling the trusted host. No production verifier/ledger is configured in this repository.

## Frozen score reconstruction (internal, ephemeral)

### ReconstructedFeatureState

A short-lived, non-exported typed view of the Feature 005 artifact's allowlisted ordered feature schema and frozen preprocessing mappings, reconstructed only after admission. It contains the artifact digest and schema/preprocessing digests, typed Feature005 transform objects, and exact active-column order.

**Invariants**: parsed fields exactly match the artifact and compatibility reference; all arrays have declared dimensions and finite values; preprocessing is never fitted or mutated; no extra categories, columns or missingness policies are introduced. Transform uses the existing Feature 005 production encoding/transform semantics.

### FrozenScoreRow (restricted ephemeral record)

One exact source/occurrence reference, frozen score `z` (or baseline `p0`), binary Feature 003 correctness target `y`, and opaque patient-group reference for protocol support only. No raw primary input, raw Feature 004 evidence, explanation, outcome, patient identifier or group key enters the design matrix or output artifact.

**Invariants**: only matching Feature 003/004 calibration records produce these internal rows. Scores and target are finite and binary. `patient_group_ref` is excluded from all predictors, mapping fit inputs except the separate support accounting, serialization and ordinary diagnostics. Rows are discarded after fitting; they are not a public result type.

## Fit configuration and mapping state

### LogisticCalibrationState

Stores only finite intercept `a`, finite slope `b > 0`, input semantics (“Feature 005 frozen logistic linear predictor”), method/version, and protocol reference. `b <= 0` is non-success. The state does not contain the Feature 005 coefficient vector again; its base-artifact binding points to that immutable artifact by digest/version.

### BaselineOffsetState

Stores finite offset `a`, finite interior `p0`, method/version, and constant-output marker. The MLE is `p_cal = mean(y)`, `a = logit(p_cal) - logit(p0)`, and `q = p_cal` for every occurrence. It has no fitted slope and no individualized discrimination. Both target classes are required; no clipping, prior or pseudo-count is allowed.

### NumericalFitRecord (restricted summary)

Contains protocol-approved convergence code, solver/version, iteration/convergence metadata, method feasibility state and only explicitly allowed aggregate adequacy values. It excludes calibration rows, outcome vectors, scores, optimizer messages that may echo input, patient IDs and group IDs.

## Outcomes and state transitions

### CalibrationStatus

- `CALIBRATOR_FITTED_UNEVALUATED`: mapping fitted under the approved protocol, with no independent performance claim.
- `NOT_READY`: required protocol approval, trusted authority, verifier, artifact-origin record, or evidence authorization is absent.
- `INSUFFICIENT_EVIDENCE`: approved unique-group/class support or identifiability requirement is unmet.
- `UNAVAILABLE_REQUIRED_EVIDENCE`: a required Feature 004 signal cannot be formed under the frozen Feature 005 schema/state policy.
- `INVALID_INPUT`: malformed, altered, duplicated or internally inconsistent records/configuration.
- `INCOMPATIBLE_INPUT`: exact model/version/label, adapter, preprocessing, artifact, dataset/manifest, method, fitted reference or protocol mismatch.
- `NUMERICAL_FAILURE`: separation, rank/degenerate score, nonconvergence, non-finite estimate, invalid slope or other approved numerical feasibility failure.

Every non-success contains no calibrator artifact and only stable privacy-safe reason codes. A shared verification/inventory failure aborts the request before returning per-scope outcomes. Once shared admission completes, an individual scope's insufficiency does not invalidate other independent scopes.

### CalibrationOutcome

One immutable result per exact protocol scope: `TrainingScope`, status, optional `CalibratorArtifact`, safe reason code, permitted limitations and permitted aggregate fit status. Successful status requires the artifact; non-success prohibits it. No patient-level outputs, calibrated row scores, performance metrics, raw exceptions or restricted verifier data.

## Calibrator artifact

### CalibratorArtifact

Allowlisted frozen fields:

- schema version, calibrator method ID/version and exact `(model_id, model_version, label_id)` plus compatible Feature 001 identity;
- base Feature 005 artifact digest/version/family, exact ordered schema digest and preprocessing digest;
- mapping family and finite parameters only: logistic `(a,b)` or baseline `(p0,a,constant_output=True)`;
- Feature 003 dataset ID, manifest reference/digest, protocol ID/version, builder version, verified ordinary inventory identity;
- Feature 004 dataset reference, run version/fingerprint, exact method/parameter identities and fitted-reference IDs;
- calibration protocol ID/version/digest and fixed solver/weighting/adequacy configuration reference;
- dependency/reproducibility metadata, allowed convergence/support summaries, and safe verification provenance references;
- lifecycle: `CALIBRATOR_FITTED_UNEVALUATED`, `not_independently_evaluated=True`, `non_deployable=True`, `not_clinically_validated=True`, `calibration_partition_spent=True`, `protected_test_accessed=False`.

**Serialization invariant**: deeply immutable/defensively detached nested values, canonical allowlisted JSON-compatible export, no pickle/joblib. Exclude all patient, group, assessment, occurrence and row IDs; targets, outcomes, features, raw predictions or signals; source rows; full restricted verifier records; protected-test content. A digest supports integrity checking only and proves neither origin nor persistence.

## Relationships and lifecycle

```text
Feature001 exact registration ──────────────────────┐
Feature002 admitted prediction lineage ─────────────┤
Feature003 manifest + calibration CorrectnessExample├─> shared trust/inventory gate
Feature004 aligned calibration SignalFeatureRecord ┤           │
Feature005 compatible selected frozen artifact ────┘           v
                                               private z/p0 reconstruction
                                                 ├─ support and numerical gate
                                                 ├─ fixed mapping fit per exact scope
                                                 └─ immutable unevaluated artifact/status
```

No train/validation observation is used as a calibrator row. Calibration records are consumed only for fitting and become spent. Protected final test is absent from the ordinary bundle. Independent evaluation and policy selection require distinct future authorization.
