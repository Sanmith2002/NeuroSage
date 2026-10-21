# Feature 005 Data Model

**Scope:** Proposed Python records for [spec.md](spec.md) and [plan.md](plan.md). Names are design contracts, not implemented classes. Existing Feature 001–004 types remain unchanged. All accepted nested mappings/sequences are deep-frozen or defensively copied; `to_dict()` returns detached, privacy-filtered values.

## Input identities and trust

| Entity | Essential fields | Validation and privacy |
|---|---|---|
| `TrainingScope` | `model_id`, `model_version`, `label_id`, exact registered classifier/preprocessing/adapter compatibility references | One registered classifier-label scope. A component ID or shared label ID cannot replace exact contributor identity. Immutable. |
| `TrainingDatasetReference` | Feature 003 `dataset_id`, dataset version, `protocol_id`, protocol version, manifest reference/digest, builder version | Must exactly match independently admitted development result and Feature 004 dataset reference. Digest is an integrity comparison, not source proof. |
| `TrainingInputCheck` | Authority/method/evidence reference; actual dataset and feature-set content fingerprints; exact dataset/scope; Feature 004 run/method/reference identities; complete role-specific row inventory; per-record Feature 002 admission lineage | Returned only by an executed, injected independent verifier. Core checks every field against actual inputs; reject missing/stale/mismatch/extra/duplicate evidence. Check is internal and not itself a trust credential. No ordinary serialization of patient/row material. |
| `AdmittedTrainingExample` | Internal Feature 003 correctness example, aligned Feature 004 row, exact `TrainingScope`, opaque role/row association and restricted group reference | Internal only. `correctness_target` (0/1) is target `y`; group key only for trusted eligibility/disjointness; predictor builder sees `SignalResult` values but excludes target/group/role/verification/primary outputs. Never serialize as ordinary artifact. |

The input pair is `(DatasetBuildResult, SignalFeatureSet)`. Feature 003 train/validation/calibration and Feature 004 training/validation/calibration inventories must be exact bijections under the existing `SignalRowKey` derivation. Each embedded Feature 002 record requires independently checked admission. The verifier must establish that the Feature 004 run and its frozen reference states were generated for the exact admitted dataset/protocol/manifest/method scope; matching caller values alone are insufficient. The entire inventory is checked before any scope publishes fitted state or cohort support.

## Approved configuration and features

| Entity | Fields | Invariants |
|---|---|---|
| `TrainingProtocol` | `protocol_id`, `version`, exact allowed sources, per-source adequacy, feature declarations, non-value/omit policies, preprocessing policy, logistic configuration, candidate and metric requirements, safe aggregate policy | Accepted before reading validation outcomes; immutable/versioned. No fallback scientific parameters, alternate seeds or post-hoc schema changes. Missing required approval → `NOT_READY`. |
| `FeatureAvailabilityProfile` | Exact scope, each of six dimensions' supported states/method versions, approved selected/omitted features and safe omission reasons | Derived only after admission. No fake numeric value; cohort support separate from patient-time sufficiency. Safe summary does not include individual values or category names. |
| `FrozenFeatureSchema` | Schema version; ordered columns with source signal `(dimension, method_id, method_version, semantics)`, type, allowed states, required/optional status, encoding and missingness columns; omissions/reasons | Same column order for train/validation and artifact. Numeric values must be finite; only approved nominal `seen`/`unseen`; primary output and explanation provenance not columns. Each exact scope has its own schema. |
| `FrozenPreprocessingState` | Schema reference; train-fitted numeric medians, means/scales, zero-variance rule, fixed category/state one-hot order, omission decisions, software/version metadata | Fit from training predictor rows only; deeply immutable. Each imputed value retains a typed state indicator. No observed numeric values → predeclared omit/fail, never fabricated median. Applied unchanged to validation. |

All seven Feature 004 availability states are represented distinctly: `available`, `unsupported`, `missing`, `unavailable`, `insufficient_evidence`, `invalid`, `not_ready`. An `available` numeric feature requires a finite measurement; an available domain feature requires exactly an approved category. Invalid/unverified/not-ready measurements are not encoded. Other non-value states require explicit allowlisting. Universally unsupported dimensions are omitted with reason, not filled with zero. A required unconstructible feature yields `UNAVAILABLE_REQUIRED_EVIDENCE`; missing approval yields `NOT_READY`.

## Candidate comparison and artifact

| Entity | Fields | Invariants |
|---|---|---|
| `CandidateTrainingResult` | Exact scope; family (`prevalence_baseline`, `l2_logistic`); fixed configuration; fit status and safe reason; finite training-fitted state; optional safe training summaries | Baseline prevalence uses training `correctness_target` only. Logistic uses two-class train and approved support; convergence/numerical failure is explicit. No raw rows or per-patient scores. |
| `CandidateComparison` | Candidate IDs/status; validation Brier and direction; conditional AUROC/AP or undefined reasons; safe class support; selected family; exact tie rule; `validation_used_for_selection=True` | Same authorized validation rows for valid candidates. Brier `mean((p-y)^2)`, lower wins, exact tie baseline. Validation metrics labeled selection evidence, not independent performance. No validation refit. |
| `SafetyEstimatorArtifact` | Artifact schema/version/digest, `TrainingScope`, selected family/state, `FrozenFeatureSchema` and preprocessing, protocol and candidates, Feature 001 compatibility, Feature 003 reference, Feature 004 run/method/fitted-reference identities, dependency versions, reproducibility controls, safe training metrics, validation selection metrics, evidence lifecycle, safe limitations | Deeply immutable, detached safe export; always `uncalibrated=True`, `non_deployable=True`. No patient/group/row keys, correctness targets, raw predictor rows, restricted evidence, calibration or protected data. Aggregate metric suppression has a safe reason. Load checks shape/finiteness/integrity, exact compatibility and authorized source. No implied durable storage. |
| `TrainingOutcome` | Exact scope; status; optional successful artifact; safe reason/limitations and safe comparison summary | Success: `SELECTED_LOGISTIC` or `SELECTED_BASELINE` after valid comparison. Non-success: `INSUFFICIENT_EVIDENCE`, `NOT_READY`, `UNAVAILABLE_REQUIRED_EVIDENCE`, `INVALID_INPUT`, `INCOMPATIBLE_INPUT`, `COMPARISON_UNDEFINED`. Candidate fit failures are detailed only with safe codes. No artifact on non-success. |

### Estimator state shapes

- Baseline: one finite probability in `[0,1]`, derived only from eligible training targets. A single-class descriptive prevalence is kept outside a successful artifact.
- Logistic: two classes exactly `(0,1)`, finite coefficient vector of length equal to transformed schema width, finite intercept, declared feature count and convergence metadata. The fitted scikit-learn object itself is not an ordinary serialized payload.
- Candidate probabilities used for Brier must be finite in `[0,1]`; no undocumented clipping or threshold conversion.

## Lifecycle and state transitions

```text
UNVERIFIED INPUT
  → verified complete Feature 003/004/002 admission
  → exact scope and group/row eligibility
  → frozen train-derived schema/preprocessing
  → baseline and fixed logistic fit on train
  → single authorized validation comparison
  → selected uncalibrated artifact OR explicit non-success
```

Any admission failure blocks all affected scopes before feature construction. An exact-scope adequacy or feature failure affects that scope only. Validation becomes **spent for selection** if compared. Calibration stays reserved and protected final test is never accessed. Future independent calibration, policy selection and final evaluation are outside Feature 005. Neither an artifact export nor a digest means the result was durably stored or clinically validated.

## Cross-artifact compatibility key

An artifact is compatible only if all of the following match the intended later use: exact Feature 001 model/version/label and registered classifier/preprocessing/adapter identities; Feature 003 dataset/protocol/version/manifest provenance; Feature 004 run version, exact method IDs/versions/parameters, feature semantics, reference-state IDs and reference cohort; Feature 005 protocol/schema/preprocessing/estimator versions. A component name or label alone is insufficient. The compatibility check rejects mismatches; it never silently migrates an estimator or fitted signal state.
