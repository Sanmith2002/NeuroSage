# Feature Specification: Automatic Model-Specific Safety Training

**Feature Branch**: `[005-automatic-model-specific-safety-training]`

**Created**: 2026-10-21

**Status**: Draft — ready for scientific and technical clarification

**Input**: User description: automatic model-specific supervised safety-estimator training using trusted Feature 003 correctness supervision and Feature 004 safety features.

## Context and Scope

Safira is a post-hoc reliability research framework, not a disease-prediction model. Feature 005 specifies how Safira automatically learns an estimator of whether a registered primary classifier's prediction is correct, using independently verified correctness supervision and supported evidence from the six constitutional safety dimensions. It does not retrain the primary classifier. The six dimensions are feature families; they do not imply six separately trained meta-models or six numeric predictors.

Feature 001 provides immutable registration and exact classifier/version/label identity. Feature 002 provides admitted primary predictions and evidence. Feature 003 provides independently verified binary correctness targets, patient-grouped partitions, dataset identity, and protected final-test isolation. Feature 004 provides admitted, predictor-only safety feature records, explicit availability states, and compatible fitted-reference provenance. Feature 005 MUST consume these existing outputs without weakening or changing their public contracts. Its trusted integration must verify exact dataset and feature-record scope before using values; caller-constructed values or self-asserted provenance alone are not sufficient.

Training is conducted independently for each eligible exact `(model_id, model_version, label_id)` scope. Multiple independently registered contributors with the same label remain separate. A successful training result is an immutable, non-deployable estimator artifact for later calibration and policy work; it is not a complete safety package, reliability score, or clinical decision.

No separate original proposal or research-direction document was found in the repository. This user-provided feature request is treated as the proposal of record. Candidate estimator families, multi-label estimator architecture, feature encoding, model-selection design, and the handoff to later calibration and policy work remain research decisions for clarification; this specification does not silently approve them.

## User Scenarios & Testing

### User Story 1 — Establish an eligible model-specific training scope (Priority: P1)

A research user submits a Feature 003 dataset and its aligned Feature 004 predictor records. Safira verifies that both inputs refer to the same approved dataset, protocol, manifest, exact registered classifier/version/label, and admitted row lineage. It reports whether training is eligible for each exact scope and explains any exclusions or readiness limitation without exposing protected information.

**Why this priority**: Estimator results are meaningless if the target, prediction, signal row, or model identity is mismatched, or if protected evaluation data enter development.

**Independent Test**: Use synthetic verified and forged dataset/feature inputs for standalone binary, multi-label, and independently composed classifiers. Assert exact row alignment, exact per-source eligibility, target/feature separation, privacy-safe outcomes, and fail-closed behavior for invalid or incomplete verification.

**Acceptance Scenarios**:

1. **Given** a ready Feature 003 development result and Feature 004 feature set with matching verified dataset, protocol, manifest, row lineage, and exact source scope, **when** training preparation is requested, **then** only corresponding eligible training rows are used and each retains its exact model, version, and label identity.
2. **Given** correctness targets, verification values, patient/group references, partition roles, or protected-test data, **when** predictor inputs are prepared, **then** none of those values is included as a predictor; only the Feature 003 correctness target is used as the supervised target.
3. **Given** a forged, altered, duplicated, missing, stale, wrong-scope, or unverified Feature 003/004 input, **when** a training scope is prepared, **then** the affected scope fails closed and no estimator artifact is published from it.
4. **Given** contributors with the same label ID but distinct model IDs or versions, **when** eligible training scopes are determined, **then** each contributor is evaluated separately and no support or feature rows are pooled across those scopes.

### User Story 2 — Automatically train and select a correctness estimator (Priority: P2)

A research user requests automatic training for eligible exact model/version/label scopes under an approved, versioned training protocol. Safira assesses the available six-dimension features, trains and compares approved candidate estimators using patient-grouped development evidence, and reports the selected candidate or a specific non-ready outcome.

**Why this priority**: This is the feature's central value: learning a model-specific correctness estimator from supported safety evidence, while avoiding manual per-dimension model training and leakage.

**Independent Test**: Use synthetic balanced and imbalanced datasets with multiple available and unavailable signal dimensions. Verify the protocol's candidates and comparison rules are followed, every exact source scope is independent, patient groups do not cross fit/selection roles, and failed feasibility produces no artifact.

**Acceptance Scenarios**:

1. **Given** an eligible exact scope and an approved candidate/selection protocol, **when** automatic training runs, **then** Safira trains only the declared estimator candidates against Feature 003 correctness targets and uses only permitted patient-grouped development partitions.
2. **Given** six signal dimensions with a subset unsupported or unavailable, **when** feature availability is assessed, **then** only evidence supported by the approved feature schema is considered and absent values are not fabricated or treated as reassuring values.
3. **Given** standalone binary, multi-label, or multi-model inputs, **when** training scopes are formed, **then** each classifier-label scope preserves its original identity and no architecture or contributor is assumed compatible by label name alone.
4. **Given** too few independent patient groups, absent required correctness-class support, unusable feature variation, or an infeasible approved comparison, **when** training is requested, **then** Safira reports `INSUFFICIENT_EVIDENCE` or `NOT_READY` with a safe reason and does not manufacture data or silently change the protocol.
5. **Given** a candidate protocol that requests calibration or protected final-test observations for fitting or selection, **when** training is requested, **then** the request is rejected and no candidate is fit or selected using those observations.

### User Story 3 — Preserve reproducibility and model-specific estimator artifacts (Priority: P3)

A research user reviews a completed or failed training run and can determine its exact scope, feature schema, data provenance, method, configuration, selection evidence, reproducibility controls, limitations, and readiness. A completed estimator remains frozen and cannot be silently transferred to an incompatible classifier, version, label, preprocessing, signal schema, or fitted-reference cohort.

**Why this priority**: Future calibration and policy work can use a training result only if its identity, evidence, and limitations remain reproducible and explicit.

**Independent Test**: Train synthetic scopes repeatedly under the same approved inputs and protocol, inspect detached immutable artifacts, and attempt incompatible model/version/label/schema/reference applications. Confirm deterministic results to the extent promised by the declared methods and explicit failure otherwise.

**Acceptance Scenarios**:

1. **Given** a successful training run, **when** its result is frozen, **then** its artifact records exact primary model/version/label scope, estimator and configuration, feature schema and missingness treatment, dataset/protocol/manifest provenance, candidate-selection method, grouped validation design, metrics, random-state/reproducibility controls, associated Feature 004 fitted-reference identities, readiness, and limitations.
2. **Given** a caller mutates source values or a returned serialization after an artifact is accepted, **when** the artifact is read again, **then** accepted artifact content is unchanged.
3. **Given** an artifact is requested for a different model, version, label, preprocessing identity, feature schema, or incompatible Feature 004 reference cohort, **when** compatibility is checked, **then** use is rejected with a safe, actionable reason.
4. **Given** training cannot proceed because evidence is invalid, unavailable, incompatible, insufficient, or not ready, **when** the run completes, **then** its outcome state and reasons distinguish that condition and no successful estimator artifact is implied.
5. **Given** a successful estimator artifact, **when** it is reported, **then** it is explicitly uncalibrated and not a deployable safety package; it contains no reliability probability, TRUST/CAUTION/DEFER policy, protected-test outcome, patient identifier, or unsupported clinical claim.

## Edge Cases

- One exact model/version/label scope has no eligible examples, only one correctness class, conflicting scope metadata, or too few independent patient groups for the approved protocol.
- A multi-label classifier has different feature availability, outcome balance, or feasibility for each label.
- Several independent contributors produce the same label ID, or one component mixes classifier types and versions.
- A signal is valid for one row but missing, unavailable, invalid, unsupported, or method-specifically insufficient for another; explanation metadata may be non-numeric.
- A feature is constant, non-finite, malformed, or unsupported for a candidate estimator or training protocol.
- A training example contains an outcome-derived field, patient/group identifier, partition role, verification evidence, or protected-test information in its predictor map.
- Feature 003 and Feature 004 references match by dataset name but differ in manifest, protocol, version, row inventory, contributor, or occurrence.
- The same patient appears across visits, labels, or contributors and could cross a training/selection fold if grouping is incomplete.
- Hyperparameter selection is infeasible under the single approved grouped split or candidate comparison rule; no alternate split or seed is silently searched.
- A candidate metric is undefined for an imbalanced or single-class evaluation partition.
- A dependency or fitted reference changes after training, making the saved feature schema or provenance incompatible.
- Calibration or protected-test records are present in an input object but are not authorized for Feature 005 development use.
- A successful estimator has not yet undergone the independent calibration, policy selection, or final evaluation required for any later package.

## Requirements

### Functional Requirements

- **FR-001**: The feature MUST accept only trusted, exact-scope Feature 003 supervision and aligned Feature 004 predictor feature records for training.
- **FR-002**: The feature MUST verify dataset, dataset version, protocol, manifest, row alignment, source lineage, and exact `(model_id, model_version, label_id)` scope before using any target or predictor row.
- **FR-003**: The feature MUST use the Feature 003 `correctness_target` as the supervised binary target and MUST NOT reconstruct it from a score, prediction threshold, raw outcome, or a new correctness rule.
- **FR-004**: The correctness target, raw/verified outcome, target-verification material, patient/group identity, partition role, and protected-test information MUST NOT enter predictor features, candidate selection inputs, or learned preprocessing.
- **FR-005**: The feature MUST preserve exact model ID, model version, label ID, contributor identity, and source-qualified provenance for each training scope and resulting artifact.
- **FR-006**: The feature MUST form and assess independent training scopes for each exact model/version/label combination. It MUST NOT pool unrelated contributors or versions solely because label IDs match.
- **FR-007**: The feature MUST support registered standalone supervised single-label binary classifiers, supervised multi-label classifiers, and independently composed multi-model components without changing Features 001–004 contracts.
- **FR-008**: For each exact scope, the feature MUST assess which of the six approved signal dimensions and which feature values/states are actually available in the admitted training evidence.
- **FR-009**: The feature MUST consume only the predictor features and provenance made available by Feature 004 and MUST NOT recalculate, relabel, bypass, or weaken Feature 004 signal validation or provenance.
- **FR-010**: The feature MUST NOT train one mandatory estimator per safety dimension merely because six dimensions exist. Candidate estimators MUST use an explicitly approved scope-level feature schema; estimator sharing across labels is subject to clarification and approval.
- **FR-011**: The feature MUST define and validate a stable feature schema covering numeric values, categorical values, structured availability states, missing values, and non-value states before estimator fitting. The encoding and missingness treatment MUST be explicit in the approved training protocol and artifact.
- **FR-012**: Unsupported, missing, unavailable, invalid, or insufficient signal evidence MUST NOT be fabricated, silently converted to zero, or treated as reassuring evidence. Any permitted encoding or exclusion behavior MUST be declared and traceable.
- **FR-013**: The feature MUST evaluate training feasibility per exact source scope using the approved cohort adequacy, independent patient-group support, correctness-class representation, feature usefulness, and candidate-method requirements. It MUST NOT introduce universal sample minima or arbitrary thresholds.
- **FR-014**: The feature MUST train only estimator families and configurations approved for the relevant research protocol; algorithm candidates and comparison criteria remain subject to clarification.
- **FR-015**: Candidate comparison and hyperparameter selection MUST follow a declared, reproducible patient-grouped design and MUST keep every patient's visits, labels, and contributor records in one group for every fit and evaluation split.
- **FR-016**: Training-row values from Feature 004 MUST preserve its patient-grouped cross-fitted reference signals and MUST NOT be replaced with optimistic in-sample reference scores.
- **FR-017**: Any learned Feature 005 preprocessing, feature selection, or other transformation MUST be fitted only on the training partition or training fold used for the corresponding candidate and then applied without refitting to its evaluation fold.
- **FR-018**: Estimator fitting and candidate selection MUST use only Feature 003 training and protocol-authorized development validation evidence. The calibration and protected final-test partitions MUST NOT be used for feature fitting, preprocessing fitting, candidate comparison, hyperparameter selection, or training decisions.
- **FR-019**: The protocol MUST define the permitted role of validation evidence for estimator selection and MUST document how selection evidence remains separate from later calibration, policy selection, and final evaluation. Reuse of validation evidence for a later decision requires an explicitly approved research protocol and MUST NOT be silent.
- **FR-020**: The feature MUST NOT search alternative seeds, change patient grouping, relax adequacy requirements, or alter candidate criteria to obtain a favorable result when an approved design is infeasible.
- **FR-021**: The feature MUST report distinct outcomes for successful estimator training, insufficient evidence, incompatible inputs, unavailable required evidence, invalid input, and not-ready verification or approval prerequisites.
- **FR-022**: A successful result MUST create an immutable, versioned estimator artifact scoped to the exact primary model/version/label, approved feature schema, preprocessing identity, training protocol, dataset/protocol/manifest provenance, and compatible Feature 004 reference state(s).
- **FR-023**: Each artifact MUST record the selected estimator type and configuration, candidate-selection method, grouped development design, training/evaluation metrics, reproducibility controls, source and fitted-reference identities, readiness, limitations, and evidence lineage needed to reproduce its research result.
- **FR-024**: Artifact compatibility MUST be checked against exact model/version/label identity and all declared feature-schema, preprocessing, protocol, and Feature 004 fitted-reference compatibility requirements. Incompatible artifacts MUST NOT transfer silently.
- **FR-025**: Accepted training configurations and artifacts MUST be immutable or defensively detached so later caller mutation cannot alter their approved values or provenance.
- **FR-026**: The feature MUST keep routine diagnostics, summaries, artifacts, and serialized outputs free of identifiable patient data, raw protected records, patient/group identifiers, protected-test observations, and protected outcomes.
- **FR-027**: Tests and examples MUST use synthetic or appropriately approved de-identified research fixtures and MUST NOT commit restricted patient datasets.
- **FR-028**: The feature MUST provide reproducible training and comparison behavior under the declared protocol, including seeds, data and software/method versions, configuration, and applicable nondeterminism limitations.
- **FR-029**: The feature MUST NOT infer primary-model correctness from probability thresholds, predictor confidence, calibration status, or signal values; only Feature 003's verified target is authoritative.
- **FR-030**: The feature MUST NOT retrain or modify primary disease-prediction classifiers, recalculate safety signals, construct Feature 003 targets, calibrate final Safira reliability probabilities, select TRUST/CAUTION/DEFER policies or thresholds, access protected final-test outcomes, or create runtime `SafetyAssessment` decisions.
- **FR-031**: A successful Feature 005 artifact MUST be identified as an uncalibrated estimator-training result and MUST NOT be represented as a complete/deployable safety package, validated clinical method, clinical safety claim, or final reliability score.
- **FR-032**: Automated synthetic acceptance tests MUST cover exact source scope, all supported classifier configurations, per-label feasibility, missing evidence, imbalanced/insufficient data, patient-grouped leakage, deterministic candidate selection, artifact compatibility and immutability, privacy, and all failure outcomes.
- **FR-033**: Implementation and verification MUST confirm that Features 001–004 public contracts and existing adapter, context, and assessment behavior remain unchanged unless a separately approved change is made.

### Key Entities

- **Training Protocol**: Versioned, approved rules for eligible source scopes, candidate families/configurations, feature schema and missingness treatment, patient-grouped fitting and comparison, metrics, reproducibility, and permitted data partitions.
- **Training Scope**: One exact `(model_id, model_version, label_id)` classifier-label scope with its own eligible examples, feature schema, feasibility result, and candidate comparison. Component composition does not combine scopes.
- **Admitted Training Example**: An exact, trusted alignment between a Feature 003 correctness target and a Feature 004 predictor-only feature record, retaining safe source and dataset provenance while excluding patient identity and protected data from predictors.
- **Feature Availability Profile**: The per-scope inventory of supported signal dimensions, feature fields, missing/value states, and method-specific limitations that may be considered under an approved schema.
- **Candidate Estimator**: A protocol-approved supervised binary classifier trained to estimate the Feature 003 correctness target from the approved predictor feature schema; it is not a primary disease classifier.
- **Candidate Evaluation**: A patient-grouped comparison result using only protocol-authorized training/development evidence, with its metric definitions, feasibility, and limitations.
- **Safety Estimator Artifact**: An immutable, versioned, exact-scope, uncalibrated estimator result with feature schema, provenance, selected configuration, reproducibility details, validation evidence, and limitations. It is not a complete safety package.
- **Training Outcome**: A privacy-safe result distinguishing completed training from insufficient evidence, incompatibility, unavailable evidence, invalid inputs, and not-ready prerequisites.

## Success Criteria

### Measurable Outcomes

- **SC-001**: In synthetic positive and adversarial tests, 100% of training rows used by a successful run have matching independently verified Feature 003 target and Feature 004 predictor lineage for the same exact dataset, protocol, manifest, model, version, label, and row association; every mismatch or unverified input is rejected from the affected scope.
- **SC-002**: For all synthetic classifier configurations, successful scope formation retains exact model/version/label provenance, and zero examples are pooled across different contributors or versions solely due to a shared label ID.
- **SC-003**: Synthetic target/predictor isolation tests confirm that correctness, outcomes, patient/group identity, partition assignments, and verification records do not occur in predictor features or learned preprocessing inputs; changing only a target cannot change its predictor record.
- **SC-004**: Under an approved synthetic grouped protocol, no patient's visits, labels, or contributor records cross any candidate fitting and evaluation fold; no calibration or protected-test observation influences preprocessing, fitting, candidate comparison, or selection.
- **SC-005**: Repeated training with identical eligible synthetic inputs and protocol reproduces identical declared deterministic selections, configurations, and artifact provenance; any nondeterministic result is identified with its permitted reproducibility limitation.
- **SC-006**: Synthetic cases for every required feasibility condition and each non-success outcome produce the protocol-appropriate explicit result, with no fabricated samples, values, thresholds, or silent protocol changes.
- **SC-007**: Every successful synthetic artifact is immutable, records all required exact-scope and provenance fields, and is rejected for each tested incompatible model/version/label, feature schema, preprocessing, protocol, or fitted-reference scope.
- **SC-008**: Synthetic privacy inspection finds zero patient-identifying values, patient/group identifiers, protected-test rows/outcomes, or restricted records in ordinary results, diagnostics, artifact serialization, or committed fixtures.
- **SC-009**: Regression verification passes for Features 001–004 and existing adapter/context/assessment contracts; no primary-model prediction, safety signal extraction, calibration, policy, or assessment is invoked during Feature 005 training tests.

## Open Research Decisions for Clarification

These decisions are intentionally not made by this specification. The approved clarification and subsequent plan must record the evidence and limitations supporting each selected option.

**A. Candidate estimator families and selection criteria**: Which established binary-correctness estimators should be candidates for the first research version, what scientifically meaningful baseline is required, and which metrics and comparison rules are suitable for the available cohort and class balance? No universal best estimator, threshold, or performance bar is assumed.

**B. Multi-label estimator architecture**: Should the system train an independent estimator per exact label scope, or may it use a shared label-aware estimator while preserving separate per-label outputs, evaluation, model/version compatibility, and no pooling across independent contributors? Evidence is needed to justify sample-efficiency claims and avoid cross-label leakage.

**C. Missing and heterogeneous feature treatment**: Which numeric, categorical, and structured Feature 004 availability values may enter candidate estimators, and should a scope exclude rows/features, use a declared missingness representation, or be marked infeasible? Explanation metadata is currently non-numeric and is not automatically a predictor. No missing value may become an invented zero or implicitly reassuring value.

**D. Grouped selection and small-cohort feasibility**: Which patient-grouped training/selection design and permitted metric set are defensible under small or imbalanced cohorts? How should the protocol establish adequate independent groups and class support without universal minima, favorable-seed search, or patient leakage?

**E. Frozen estimator and later workflow boundary**: What constitutes a frozen, versioned but uncalibrated estimator artifact, and how must its compatibility and provenance connect to later calibration, policy selection, and final evaluation? Specifically, may validation evidence used to select the estimator be reused for later policy selection, or must later work reserve independent evidence? Feature 005 does not answer this by assumption.

## Assumptions

- Features 001–004 remain the authoritative sources for classifier identity, prediction admission, verified correctness targets, patient-grouped dataset roles, safety features, availability states, and fitted-reference compatibility.
- The Feature 003 training partition is the only source for fitting candidate estimators and any Feature 005 learned preprocessing. Feature 003 validation may be used only as explicitly authorized development evidence. Calibration and protected final-test roles remain unavailable to Feature 005.
- Research owners approve candidate families, study metrics, feature encoding, class-support criteria, partition use, and reproducibility rules through a versioned protocol before training.
- Every exact source scope can have a different eligible feature set or a different training outcome. No requirement makes all six signal dimensions available or numeric.
- Synthetic software verification does not establish scientific effectiveness, clinical validity, or performance on real patients.
- A trained estimator is an intermediate research artifact. Later calibration, policy selection, final evaluation, and runtime assessment require separately specified and validated work.

## Scope Boundaries

**Included**: trusted exact-scope joining of Feature 003 supervision and Feature 004 predictor records; automatic per-scope feasibility assessment; training and leakage-safe comparison of approved binary correctness-estimator candidates; patient-grouped reproducibility; immutable uncalibrated estimator artifacts; explicit readiness and failure outcomes; synthetic acceptance and compatibility tests.

**Excluded**: primary classifier retraining or modification; rebuilding Feature 003 correctness targets; recalculating or bypassing Feature 004 signals; training six mandatory estimators by dimension; Safira reliability calibration; TRUST/CAUTION/DEFER policy or threshold selection; use of calibration or protected final-test outcomes for Feature 005; protected-test handoff or access; runtime `SafetyAssessment`; clinical diagnosis, treatment, or safety claims; changes to Features 001–004 or existing adapter/context/assessment contracts; unsupervised learning, regression, or other classifier task expansion.
