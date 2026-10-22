# Eight-stage educational catalog

Source of truth for Explorer content. All eight stages are independently selectable. The default runtime fixture measures entropy only; these cards describe framework capabilities and historical preparation, not an assertion that all stages execute on RUN.

## 001 — Model registry

- **Purpose:** associate every prediction/artifact with exact classifier, model version and label, including separate contributors sharing a label.
- **Input:** RegisteredModelVersion metadata, loaded classifier/adapter pair, loader-owned IdentityProvider evidence, output semantics and preprocessing identity.
- **Operation:** validate single-label binary or multi-label task/cardinality, fingerprint classifier/adapter artifacts, check loaded association, persist immutable metadata in SQLite and retain live bindings separately.
- **Output:** exact registration and usable binding; no trained safety package or assessment.
- **Verification:** identity provider checks actual pair; digests alone are insufficient; resolve exact version and label, never substitute nearest version.
- **Failure:** unsupported task, wrong label count, contradictory output mapping, duplicate conflicting version, missing attachment or identity mismatch.
- **Lifecycle:** offline registration; runtime checks exact usable registry compatibility without registering/retraining.
- **Dependencies:** adapter contracts precede 001; 002 and every later artifact preserve this source identity.

Visual: model → version → label chips plus independent contributor lanes; show synthetic public aliases only.

## 002 — Prediction admission / evidence collection

- **Purpose:** admit a primary prediction with source-qualified association and meaningful evidence states.
- **Input:** exact registry, opaque patient/assessment/occurrence association, live adapter request or configured precomputed source contract and trusted provenance check.
- **Operation:** collect/normalize primary output, enforce declared score/class mapping, independently check source linkage and preserve optional evidence states.
- **Output:** PredictionRecord with primary semantics, provenance and available/unsupported/missing/unavailable/invalid evidence; optional context projection remains internal.
- **Verification:** real configured source integration or loaded live binding; exact content/scope checks, no incoming `verified` flag.
- **Failure:** invalid primary, model/version/label mismatch, missing/unauthorized association, stale/replayed precomputed evidence; valid primary may retain incomplete optional evidence.
- **Lifecycle:** fixture prediction collection occurs in host preparation; runtime rechecks admitted prediction ledger and synthetic membership rather than rerunning the primary model.
- **Dependencies:** 001 exact metadata; output feeds 003/004 and runtime 008.

Visual: synthetic admission gate separating retained incomplete evidence from request rejection; no raw record browser.

## 003 — Patient-grouped safety dataset

- **Purpose:** establish reliable correctness supervision and leakage-safe evidence roles.
- **Input:** admitted predictions, independently checked outcomes and target definitions, linkage/independence/timing evidence, versioned split protocol and controlled handoffs.
- **Operation:** compare predicted class to verified binary outcome; group all visits/labels/contributors for one patient; enforce approved assignments, independence and lifecycle.
- **Output:** development train/validation/calibration DatasetBuildResult, readiness/exclusions and controlled manifest reference; protected final-test content remains outside ordinary outputs.
- **Verification:** exact prediction admission, ground-truth association, patient linkage, data lineage, split/history and role constraints. No universal split percentages or minima.
- **Failure:** uncertain outcome/linkage, overlap, missing provenance, unsupported constraints or inadequate scope support; no fabricated target.
- **Lifecycle:** offline preparation; runtime reads only original train predictors/grouping required for approved reference recovery, not supervision. Estimator validation, calibration fitting and later separate policy-selection evidence are spent for their respective purposes.
- **Dependencies:** 001/002; supplies 004–006; a separately authorized patient-disjoint selection cohort supports 007. Future final evaluation is outside this demo.

Visual: synthetic patient grouping tokens contained wholly in one partition; five distinct roles with final-test box locked. Tokens are educational symbols, not fixture identities/counts.

## 004 — Safety signals

- **Purpose:** derive explicit capability-aware evidence within exactly six dimensions, not six mandatory numeric scores.
- **Input:** verified PredictionRecord, exact registration, SignalProtocol and approved original training reference where needed.
- **Operation:** SignalExtractor performs exact admission/semantics checks, stateless extraction and train-only grouped cross-fitting/reference preparation. Runtime uses its existing private bridge.
- **Output:** SignalResult/SignalFeatureRecord and privacy-safe manifest; cohort adequacy is separate metadata, not a patient predictor.
- **Verification:** exact source, method/version/parameters, schema/preprocessing, original reference digest and Feature 002 admission.
- **Failure:** preserve `unsupported`, `missing`, `unavailable`, `invalid`, `insufficient_evidence`, `not_ready`; none means numeric zero. `available` means measured, not clinically validated.
- **Lifecycle:** offline reference preparation; runtime frozen reference recovery/check plus query extraction/application. Default demo candidate only executes configured entropy.
- **Dependencies:** 001–003; only approved typed schema fields feed 005 and runtime frozen application.

| Exact dimension ID / display name | Purpose and prerequisites | Approved general method | Unavailable behavior and estimator contribution |
|---|---|---|---|
| `data_sufficiency` / Data sufficiency | Explain which declared evidence prerequisites are present; immutable evidence states and prerequisite profile | Structured evidence coverage; separate protocol-scoped unique-group/cohort support | No scalar sufficiency score. Missing approvals/support remain non-ready/insufficient. Only explicitly approved state indicators can enter 005; cohort counts never do. |
| `distribution_conformity_ood` / Distribution conformity / OOD | Compare a compatible feature representation to approved training-only reference | `knn_distance`: protocol-declared k-th nearest distance, supported metric; grouped cross-fitted train features and frozen full-train apply | Unsupported capability, missing/invalid vector, incompatible schema or insufficient neighbours remain non-value states. Approved finite distance may enter 005; no invented OOD cutoff. |
| `prediction_uncertainty` / Prediction uncertainty | Describe uncertainty of registered binary probability; optional verified same-input repeats | `bernoulli_entropy`: −p log(p)−(1−p) log(1−p), declared base; optional repeated-output descriptive variance | Non-probability has no invented conversion; repeats require compatible provenance. Approved finite entropy/variance may enter schema; neither alone means correctness probability. |
| `modality_agreement` / Modality agreement | Compare at least two semantically aligned modality probabilities for the same contributor/label/input/timing | Pairwise Jensen–Shannon divergence with approved aggregation and log base | Unsupported/missing modalities or incompatible output semantics remain unavailable/invalid. Approved numeric JSD may enter 005; never compare separate component classifiers. |
| `domain_familiarity` / Domain familiarity | Check approved domain-category membership against training-only vocabulary | `domain_familiarity`: cross-fitted train membership, frozen apply returning `seen`/`unseen` | Schema/approval/reference absence remains explicit; raw category/site never displayed. Approved categorical encoding may enter 005; no domain probability or reassuring zero. |
| `explanation_reliability` / Explanation reliability | Check explanation method, target label/output, output space, calibration relation and provenance applicability | Structured explanation metadata/scope validation; V1 has no generic numeric reliability or stability metric | Unsupported/missing/invalid explanation stays explicit. Explanation applicability and raw content are non-predictive in 005; no numeric reliability contribution. |

Visuals: six expandable evidence-family cards; equation illustration for entropy, abstract training-reference sketch, state legend and domain membership diagram. Any toy drawing is labeled educational and contains no runtime/private numeric values. Do not present toy entropy as an observed Safira result.

## 005 — Automatic model-specific safety estimator

- **Purpose:** automatically choose a correctness estimator per exact model/version/label; never retrain the primary classifier.
- **Input:** independently admitted aligned Feature 003/004 data and TrainingProtocol, support and frozen candidate/preprocessing rules.
- **Operation:** fit prevalence baseline and fixed L2 logistic candidate on train; compare on validation by lower Brier score, exact tie favouring baseline; report AUROC/AP only when defined. No unrestricted parameter/seed search or validation refit.
- **Output:** immutable SafetyEstimatorArtifact with selected family, schema/preprocessing, state and compatibility provenance; uncalibrated, non-deployable intermediate artifact.
- **Verification:** row alignment, train-only learned transforms, group disjointness, allowed finite features/categories/state indicators, trusted targets and origin.
- **Failure:** unverified/invalid/not-ready input, inadequate two-class support, missing essential predictors or no eligible candidate; no pretend training success.
- **Lifecycle:** offline fitting/selection only; runtime reconstructs and applies frozen state. Validation is spent selection evidence, not independent final performance.
- **Dependencies:** 001–004; selected artifact feeds 006, then 007/008. Separate exact scopes never pool compatibility or targets.

Visual: train → two candidate cards → validation selection → frozen artifact. No progress animation suggesting per-run fitting.

## 006 — Calibration

- **Purpose:** map frozen estimator output toward correctness probability using separate calibration evidence.
- **Input:** exact selected Feature 005 artifact, aligned calibration partition/signals and approved CalibrationProtocol/origin verifier.
- **Operation:** fixed unpenalized positive-slope logistic calibration for logistic base; prevalence-offset baseline mapping produces a constant probability. Raw logistic estimator output is a linear score, not calibrated correctness probability.
- **Output:** immutable CalibratorArtifact bound to base digest/family/schema, `CALIBRATOR_FITTED_UNEVALUATED`; calibration partition spent.
- **Verification:** original artifact origin, independent partition, rank/separation/feasibility/support and finite approved mapping; no fallback clipping/tuning.
- **Failure:** inadequate support, unidentified/separated fit, nonpositive slope, incompatible base or numerical failure; no invented mapping.
- **Lifecycle:** offline fitting only; runtime applies exact frozen mapping privately, never recalibrates and never returns the individual probability.
- **Dependencies:** 001–005; 007 selection and 008 application consume frozen calibrated state.

Visual: abstract raw-score → frozen mapping → private calibrated-score box. No synthetic calibration-quality curve or performance claim without actual authorized evaluation.

## 007 — Selective policy

- **Purpose:** select one frozen TRUST cutoff under a prespecified empirical risk ceiling and support protocol.
- **Input:** separate authorized selection cohort, verified correctness and patient disjointness/history, original train reference, frozen estimator/calibrator and approved policy protocol.
- **Operation:** choose one index assessment per patient/scope; evaluate all approved candidates, maximise TRUST coverage among feasible nonempty selections, deterministic tie rule. Risk is incorrect selected / selected; coverage is selected / eligible. Empty risk is undefined.
- **Output:** SelectivePolicyArtifact with selected cutoff and exact `>=` or `>` comparison; `SELECTED_UNEVALUATED`, selection evidence spent. Aggregate statistics are disclosed only when approved.
- **Verification:** full shared admission and origin, pre-outcome protocol approval, patient history completeness, untouched protected-test boundary and exact reconstruction.
- **Failure:** no feasible nonempty cutoff, insufficient support, missing reference, incomplete history or invalid shared trust. Shared rejection is not a scope success.
- **Lifecycle:** offline selection; runtime only applies the frozen cutoff. At equality, `>=` gives TRUST and `>` gives CAUTION for valid scores. Selection-cohort empirical risk is not a future-risk guarantee.
- **Dependencies:** 001–006; 008 uses frozen policy. Independent evaluation remains absent, not supplied by this application.

Visual: schematic cutoff with inclusive/exclusive marker; no caller-editable threshold and no displayed individual runtime score. Selection metrics, if later shown, must be approved aggregate artifact fields, separately labeled; MVP omits them.

## 008 — Synthetic runtime assessment

- **Purpose:** demonstrate frozen software behavior for admitted controlled synthetic predictions.
- **Input:** exact SyntheticRuntimeRequest, usable registry and injected RuntimeVerifier, all server-owned.
- **Operation:** verify shared trust and synthetic membership, recover/check configured Feature 004 state, derive private signals, apply frozen 005/006 and 007. Drop private intermediates before returning.
- **Output:** InternalResearchAssessmentResult: TRUST/CAUTION or admitted DEFER with fixed reason; lifecycle `SYNTHETIC_TEST_ONLY` / `SELECTED_UNEVALUATED`. HTTP emits a smaller allowlist, not the result's full `to_dict()`.
- **Verification:** all six trusted host operations, exact artifact/manifest/source bindings and actual service return. HMAC is not independent origin evidence.
- **Failure:** RuntimeAdmissionRejected means no assessment; admitted RuntimeReadinessFailure yields scoreless DEFER; unexpected programming failures are server errors. Missing policy is rejected during host construction, not DEFER.
- **Lifecycle:** only runtime application executes per RUN; all historical preparation remains frozen. No primary model invocation or original ground-truth access is needed by this service.
- **Dependencies:** all earlier identities/artifacts; no production or clinical authorization follows.

Visual: observed host checks and final outcome beside expandable historical cards. Detail unavailable is a legitimate trace state.
