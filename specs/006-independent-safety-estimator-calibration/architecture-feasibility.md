# Feature 006 Architecture and Integration Feasibility Review

**Stage:** Pre-specification research. This document proposes a small implementation boundary; it is not an approved plan or contract.
**Proposed feature directory:** `specs/006-independent-safety-estimator-calibration/`
**Proposed code boundary:** a new calibration package consuming existing records and artifacts without changing Features 001–005.

## Finding

Feature 006 is technically feasible as a small library feature if it is limited to: (1) exact, trusted input admission; (2) internal application of an already frozen Feature 005 estimator to Feature 004 calibration signals; (3) fitting one approved exact-scope calibration mapping on Feature 003 calibration correctness targets; and (4) returning an immutable, non-deployable, explicitly unevaluated calibrator artifact and privacy-safe outcome.

The key limitation is not numerical implementation. The repository has no production trusted Feature 002/003/004 evidence ledger, Feature 005 artifact origin store, or custodian. Tests can prove that the library rejects missing, forged, stale or mismatched evidence when configured with an independently controlled verifier. The library cannot authenticate malicious code that controls its trusted Python host, nor claim durable storage from a digest or ordinary in-memory artifact.

## Existing interfaces and actual capability

| Existing component | Available capability | Feature 006 implication |
|---|---|---|
| Feature 001 `ModelRegistry` | Exact registered model ID, version, label, classifier/adapter and preprocessing compatibility; registration objects are immutable. | Each calibration artifact and operation must bind to one exact source key. Same label names across models/versions do not share evidence. No registry change is needed. |
| Feature 002 prediction records | Source-qualified predictions and explicit admission lineage are verified through host-owned integrations. | Calibration must admit the entire underlying dataset/signal inventory and the embedded source predictions; a constructed record or caller digest is insufficient. |
| Feature 003 `DatasetBuildResult` | Immutable development partitions `train`, `validation`, `calibration`; correctness examples include exact prediction, correctness target, target/outcome and restricted patient group. Protected-test rows are outside the ordinary result; full manifests and protected handoffs are separately controlled. | Consume only `development.calibration` after independent trusted verification. Do not accept protected-test rows or expose target/group/partition content in outputs. |
| Feature 004 `SignalFeatureSet` | Separate `training`, `validation`, `calibration` `SignalFeatureRecord` tuples, exact source keys and opaque row keys; frozen reference states, method identities and dataset/run manifests are represented. | Use already-generated calibration signals. Do not recompute signals, refit Feature 004 references, or change evidence-state handling. Align each calibration feature row to its exact Feature 003 prediction row. |
| Feature 005 `SafetyEstimatorArtifact` | Frozen family (`prevalence_baseline` or `l2_logistic`), exact scope, ordered feature schema, frozen preprocessing state, coefficients/intercept/classes or constant probability, dependency/provenance references, lifecycle flags and canonical digest. Safe JSON-compatible `to_dict`/`validate_artifact` path with injected origin verifier; no pickle/joblib loading. | Feature 006 can reconstruct the uncalibrated score without retraining. Artifact object/digest alone does not prove authorized origin. The existing artifact remains unchanged and uncalibrated. |
| Feature 005 training service | Public `train` and eligibility-only `prepare`; no public inference method. Full trusted admission verifies Feature 003/004 and embedded Feature 002 records. Training reads train and validation for its purposes; calibration is verified but not used for fitting/selection. | Feature 006 needs a minimal private application routine. Do not add a public inference method to Feature 005 or mutate its selected estimator or preprocessing. |
| Feature 005 dependency | `scikit-learn==1.7.1` is pinned and was verified in the completed environment; NumPy/SciPy support exists as transitive dependencies. | A logistic recalibration solver may reuse the pinned stack if approved. No additional runtime dependency is presently necessary. A numerical implementation detail and pin must still be confirmed in planning. |

### Internal application of the frozen estimator

Feature 005 intentionally serializes coefficients and transforms instead of a Python estimator object. A minimal Feature 006-private helper can:

1. Require an already validated and origin-checked `SafetyEstimatorArtifact` (or validate its allowlisted payload against exact compatibility and an injected origin verifier).
2. Require exact agreement between requested `(model_id, model_version, label_id)`, artifact scope and current Feature 001 registration.
3. Check that Feature 003 dataset/manifest/protocol identity and Feature 004 run/method/fitted-reference identity match those recorded in the Feature 005 artifact and independent admission receipt.
4. Project only the exact Feature 004 calibration `SignalFeatureRecord`s through the stored ordered Feature 005 schema and stored `FrozenPreprocessingState`. Apply no fit, inference-time feature extraction, imputation-policy change or reference refit.
5. Compute the exact frozen correctness score: `sigmoid(intercept + coefficients · transformed_row)` for `l2_logistic`; the stored constant probability for `prevalence_baseline`.
6. Retain the logistic margin directly for recalibration where possible, so the implementation need not take `logit` of a rounded probability. Verify finite shapes, finite parameters and output range; use stable sigmoid/log-likelihood math.
7. Keep this helper private to Feature 006. It does not call the registered primary classifier and cannot become a `SafetyAssessment`, public runtime scoring or policy API.

The current `_reproduce_probability_for_test` in Feature 005 is explicitly test-only. Feature 006 should not import a test-only function as a production dependency. It can implement the small numerical application in its own internal module, with synthetic parity tests against the Feature 005 frozen coefficients and test-only reproduction. Feature 001–005 contracts remain unchanged.

## Proposed minimal workflow

```text
Feature 001 exact registration ─────────┐
Feature 005 selected frozen artifact ────┼──> injected artifact/data verifier
Feature 003 calibration partition ──────┤              │
Feature 004 calibration SignalFeatureSet ┘              v
                              exact row/source/role alignment
                                              │
                              apply stored schema + preprocessing
                                              │
                              frozen Feature 005 correctness score
                                              │
                              protocol-specific support/feasibility
                                              │
                              fixed logistic-recalibration fit
                                              │
                              immutable calibrator artifact (unevaluated)
```

Recommended orchestration is independent per exact source scope. The service should fail closed on a shared admission failure before it publishes any scope result that implies trusted admission. If one individually authorized exact scope lacks calibration support, return `INSUFFICIENT_EVIDENCE` for it without pooling data or settings from other scopes. Whether a shared verifier failure rejects all scopes or yields per-scope errors should follow Feature 005's established boundary: the complete source inventory must verify before results are emitted.

### Admission requirements

Compose the existing verifier concepts rather than inventing a new trust infrastructure:

- Feature 005 `ArtifactCompatibility`/`ArtifactOriginVerifier` semantics for the exact estimator artifact and selected family. A valid digest is integrity information only, not origin evidence.
- Feature 005 `TrainingInputVerifier` or a narrowly typed Feature 006 wrapper that executes the underlying Feature 002 prediction admission and Feature 003/004 complete-content checks. It must bind actual inputs to the exact Feature 003 dataset ID, manifest reference/digest, protocol ID/version, builder version, complete inventory, Feature 004 run, method parameters, fitted references and calibration row assignments.
- Independent local comparisons against the actual data: `readiness == ready`; each Feature 003 calibration example has exactly one Feature 004 calibration record derived from the same prediction fingerprint/source/association; no duplicate, extra, missing, cross-role or changed rows; exact registered classifier/version/label and adapter/preprocessing identity; no patient group crossing existing Feature 003 roles.
- Calibration outcomes are the already verified `correctness_target` values. Feature 006 does not reconstruct targets, inspect protected artifacts, or accept a primary score threshold as correctness.
- The verifier is injected by an authorized trusted host. Caller-supplied Boolean values, constructed “verified” records or digest assertions alone do not establish admission. There is no real integration configured in this repo.

### Feature 005 and Feature 004 compatibility

The calibration operation must reject, not migrate, any mismatch in:

- model ID, exact model version, label ID, registered classifier artifact identity, adapter identity/version/fingerprint or preprocessing identity;
- base Feature 005 artifact digest/version/family, training protocol, schema order/digest, frozen preprocessing digest, binary class order or dependency compatibility;
- Feature 003 dataset ID/manifest reference/digest/protocol/version/builder version and admitted inventory;
- Feature 004 dataset reference, calibration run/version, source key, method/version/parameters and fitted reference-state identities; and
- calibration row identity, partition role, completeness, source or correctness target lineage.

Feature 005 does not define a separate dataset-version field. Use the existing independently verified manifest-bound tuple, not an invented field. Feature 003's complete manifest and protected test remain controlled outside development-facing results.

## Proposed immutable calibrator artifact

The artifact is a new Feature 006 object, not a modified Feature 005 estimator. A research-review-level field proposal is:

| Field group | Proposed contents |
|---|---|
| Artifact identity | Artifact schema/version, calibrator method ID/version, canonical payload digest. |
| Exact model scope | `(model_id, model_version, label_id)` and registered classifier/adapter/preprocessing compatibility references. |
| Base estimator binding | Exact Feature 005 artifact digest/version/family; base lifecycle remains `uncalibrated_non_deployable`; feature-schema and preprocessing digests. |
| Calibration mapping | For logistic base: finite intercept/slope and input score semantics. For baseline: finite offset, fixed slope-one semantics, constant-output marker. Store no fitted estimator pickle. |
| Calibration protocol | Protocol ID/version/digest; method configuration, optimizer/tolerance/termination semantics, weighting rule, exact adequacy criteria and status. Every choice is fixed before observing calibration outcomes. |
| Data provenance | Feature 003 dataset/manifest/protocol/builder identities and verified inventory reference/digests; Feature 004 calibration run/method/fitted-reference identities; verifier authority/method/evidence references as permitted. |
| Fit record | Role `calibration_fit`; successful/non-success state; permitted unique-group and correctness-class support summary only if approved for disclosure; convergence code. No row values or group identifiers. |
| Lifecycle and limitations | Calibration partition is spent for fitting and in-sample diagnostics, not an independent estimate. Validation is already spent; protected final-test not accessed; future policy evidence required; `not_independently_evaluated`; `not_clinically_validated`; `non_deployable`. |

All nested values are deeply immutable/defensively detached. Serialize an allowlisted JSON-compatible representation. Do not include patient, assessment, occurrence, group, row, target, outcome, raw signal, raw prediction, protected-test or restricted verification content. A canonical digest provides change detection, not origin authentication or durable persistence. A host-controlled artifact custodian is needed for durable storage claims; none is configured here.

The calibrated probability is defined as estimated correctness for the exact primary classifier prediction under the verified target and target-population scope. It is not a disease probability, independent validation result, policy decision or clinical safety conclusion. The fitted mapping can be retained for future authorized internal application, but Feature 006 should not publish a patient-facing runtime `apply` or assessment interface unless the reviewed specification explicitly authorizes it.

## Proposed error/result states

Use Feature 005/003 safe-state vocabulary where semantically compatible; add no error text containing raw rows, group IDs, categories or numerical input values.

- `NOT_READY`: missing/unapproved protocol, required trust provider, origin verifier or evidence authorization.
- `INSUFFICIENT_EVIDENCE`: approved exact-scope unique-patient/correctness support unmet, a needed target class absent, or approved score variation/identifiability inadequate.
- `UNAVAILABLE_REQUIRED_EVIDENCE`: a required frozen Feature 005 predictor cannot be formed from an already admitted Feature 004 calibration record under the stored schema/state policy.
- `INVALID_INPUT`: malformed or altered data, nonfinite score/targets/parameters, duplicate/missing row or protocol inconsistency.
- `INCOMPATIBLE_INPUT`: exact classifier/version/label/adapter/preprocessing/base artifact/dataset/manifest/signal-run/fitted-reference mismatch. Existing code may raise a typed compatibility exception rather than return a status; preserve a single documented public behavior.
- `NUMERICAL_FAILURE` (proposed): optimization fails, nonfinite coefficient, singular/rank-deficient score design, complete separation without finite unpenalized MLE, or unexpected solver behavior. Do not silently switch methods or return an identity transform.
- `CALIBRATOR_FITTED_UNEVALUATED` (proposed success): mapping fits under the approved protocol; no independent performance claim.

## Evaluation boundary

Feature 005 validation selected the base estimator, so it is spent. Feature 006 calibration rows fit the calibrator, so diagnostics on them are apparent/in-sample. Feature 003 protected final-test is not accessible to Feature 006. Therefore current Features 001–005 provide no permitted independent performance set for the calibrated artifact. A later separately authorized evidence source is necessary to evaluate it; future threshold/policy selection needs distinct authorization as well. The software may verify this lifecycle and report “not independently evaluated,” but must not claim independent reliability or clinical calibration.

## Implementation-context handoff (for the later plan)

- Keep new code in a Feature 006 calibration package. Likely cohesion: immutable records/protocols and safe errors; verifier/completeness alignment; private frozen-score calculation; fixed calibrator fitting and outcome service; allowlisted artifact compatibility/export. These are proposals only, not implementation tasks.
- Reuse Feature 001 registrations, Feature 003 `DatasetBuildResult.development.calibration`, Feature 004 `SignalFeatureSet.calibration`, and Feature 005 serialized state. Do not modify established contracts.
- Dependency order: approve methodology/estimand; define immutable exact-scope contracts; test trusted admission and row alignment; test private frozen-score parity; test calibration formula/degenerate cases; implement support gates and fit; test artifact privacy/compatibility; end-to-end synthetic calibration and Features 001–005 regression.
- Synthetic tests should cover each base family, exact per-label and per-version independence, row order and deterministic fit, independently admitted calibration evidence, forged/altered target/signal/artifact rejection, missing required evidence, one-class targets, constant/near-constant logistic margins, rank deficiency/separation, repeated-patient weighting, output bounds, privacy, immutable artifacts, and explicit proof that train/validation/protected rows cannot affect fit.
- Do not expose API or successful artifact until the complete verifier gate passes. Train only the calibrator; never refit the Feature 005 base estimator, Feature 005 preprocessing or Feature 004 references.

## Research questions for clarification

1. Approve the recommended fixed method family and baseline intercept-only rule, or select a different one-method design.
2. Approve the calibration unit/weighting rule for repeated predictions from one patient and what adequacy counts as independent support.
3. Decide whether to use unpenalized logistic MLE with explicit failure on separation/degeneracy, or approve a specific regularized estimator and fixed penalty in advance.
4. Decide the response to an estimated negative logistic slope and whether calibrator output may reverse base-score ordering.
5. Confirm Feature 006 output is an immutable, non-deployable calibrator artifact plus fit-only diagnostics, with no public per-patient application endpoint.
6. Confirm no calibration-fit-set performance claim is allowed and that independent evaluation and policy selection require later separately authorized evidence.
7. Define how a newly produced Feature 005 in-memory artifact gains independently verifiable origin before Feature 006 accepts it, given no production artifact ledger.

## Proposed worktree, branch and Spec Kit setup

Verified repository state during this review:

- Active worktree: `C:\Users\User\Desktop\NeuroSage-Workspace\safira-auto-training`.
- Active branch: `feature-06/Independent-calibration`.
- Base commit: `d8803107cb566fccb1f2a0b10db0e0cca33727af` (`Feature 005 closure`); its parent is the final adversarial verification commit. `feature-05/Automatic-Safety-Training` resolves to the same base commit. The Feature 005 closure change is committed, and the worktree was clean before this review.
- Feature directory: `specs/006-independent-safety-estimator-calibration/`.
- Spec Kit resolver reads `.specify/feature.json` before inferring from branch names. The local ignored file initially targeted Feature 005. It now points to `specs/006-independent-safety-estimator-calibration/` so later Feature 006 commands target the right directory. This directory contains research documents only; it deliberately has no official `spec.md` pending decision approval.
- `check-prerequisites.ps1 -RequireSpec` is expected to fail until the reviewed research questions are approved and the user invokes `$speckit-specify`. Do not run plan/tasks/implementation commands yet.

