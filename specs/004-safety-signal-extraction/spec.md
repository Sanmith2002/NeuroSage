# Feature Specification: Safety Signal Extraction and Feature Engineering

**Feature Branch**: Not created (no branch hook configured)  
**Created**: 2026-10-18  
**Status**: Draft — research clarified; ready for technical planning
**Input**: Specify model-agnostic extraction of traceable safety signals from validated primary predictions, evidence, and patient-grouped safety datasets.

## Context and Scope

Safira is a post-hoc reliability research framework, not a disease-prediction model. Constitution v3.0.0 defines exactly six safety dimensions: data sufficiency, distribution conformity/out-of-distribution (OOD), prediction uncertainty, modality agreement, domain familiarity, and explanation reliability. The dimensions are evidence families; they do not imply six mandatory numeric values or an already approved calculation for every family.

The repository has no operational signal algorithms or signal-specific tests. `src/safira/signals/base.py` is empty. Existing `ModelAdapter` and `AdapterCapabilities` expose optional primary probabilities, feature representations, repeated outputs, modality outputs, domain metadata, explanations, input metadata, and available modalities. Those capabilities establish possible evidence collection, not the scientific validity or applicability of a signal.

Feature 001 supplies immutable registrations and exact model/version/label score semantics. Feature 002 supplies validated, source-qualified `PredictionRecord` values, evidence provenance and explicit evidence states. Feature 003 supplies patient-grouped correctness examples and train, validation, and calibration datasets through its ordinary development result. Protected-test rows are transferred only through a separate custodian-controlled handoff. Feature 003 has no configured real verification or storage integrations; its manifest handoff can bind a receipt to an exact manifest but does not by itself prove durable storage. Feature 004 MUST honor these limits and MUST NOT weaken any of these contracts.

Feature 004 specifies WHAT signal extraction and feature preparation must guarantee. The clarification session approves candidate V1 method scopes recorded below, but does not establish their empirical or clinical validity, choose study-specific parameters or thresholds, or require a universal signal vector. Feature 004 does not train a safety estimator or create a safety assessment.

## Clarifications

### Session 2026-10-18

- Q: Should Feature 004 clarify the proposed V1 methods below as the research team’s candidate scope? → A: Adopt the six-dimension candidate set: separate prediction-time evidence coverage from cohort adequacy; use raw k-th-neighbour distance only with compatible representations and a Feature 003 training reference; binary entropy only for registered probability outputs; pairwise Jensen–Shannon divergence only for comparable modality probabilities; declared seen/unseen domain-category support against an approved training reference; and explanation method/target/output-space metadata without a generic numeric reliability score. A method remains unavailable when its prerequisites fail, and literature does not establish clinical validity.
- Q: How should reference-based training features avoid scoring a patient against that patient’s own records? → A: Use patient-grouped cross-fitting. The versioned research protocol declares fold design and seed; all records for a patient group remain together, each scored group is excluded from its reference, and no alternative-seed search is allowed. Report infeasibility instead of weakening grouping.
- Q: Should Feature 004 use distinct availability-state meanings and protocol-specific adequacy? → A: Yes. `unsupported` means the method/capability is not supplied; `missing` means expected evidence is absent; `unavailable` means supported evidence could not be obtained; `invalid` means supplied evidence fails validation; `insufficient_evidence` means valid evidence fails the method’s declared support requirements; and `not_ready` means required compatible reference, approval, or provenance is not ready. Adequacy is method- and protocol-specific, with unique patient-group counts and any required correctness-class support evaluated per exact model/version/label; no universal minimum is introduced.
- Q: How should Feature 004 align rows with Feature 003 and handle protected final-test data? → A: Bind extraction to exact Feature 003 dataset, protocol, and manifest references, with opaque row-alignment keys separate from predictors. Define a separate custodian-controlled apply-only boundary for frozen signal state on protected-test data; it cannot refit, select, tune, or expose protected rows, outcomes, correctness targets, or their distributions through ordinary APIs. The required real custodian integration is not currently configured, and the boundary does not claim persistence or verification that an integration does not provide.

## User Scenarios & Testing

### User Story 1 - Extract Applicable Safety Signals (Priority: P1)

A research user supplies a validated prediction and its permitted evidence and receives traceable signal results for the exact contributing model version and label. Each result says what was measured, what evidence supports it, and when the signal cannot be produced.

**Why this priority**: Future model-specific safety training depends on predictor features whose meaning, provenance, and availability are explicit. A fabricated value or an ambiguous contributor would invalidate later analysis.

**Independent Test**: Use synthetic records for standalone binary, multi-label, and independently composed multi-model configurations. Exercise all six dimensions with supported, missing, unsupported, invalid, and insufficient-evidence cases. Check exact contributor identity and verify no unsupported numeric result is emitted.

**Acceptance Scenarios**:

1. **Given** a valid live or admitted precomputed prediction for an exact registered model version and label, **when** applicable signal extraction is requested, **then** each result is bound to that exact source key and preserves the primary score's declared meaning and evidence provenance.
2. **Given** a component containing independently registered contributors, including contributors with overlapping label IDs, **when** signal results are produced, **then** each contributor's results remain distinct by `(model_id, model_version, label_id)` and no component-level aggregation or compatibility transfer is implied.
3. **Given** a signal prerequisite is unsupported, missing, unavailable, invalid, insufficient, or not ready, **when** extraction runs, **then** the result reports the applicable non-value state and a safe reason without inventing a numeric value or treating absence as reassuring evidence.
4. **Given** multiple supported and unsupported dimensions for one record, **when** extraction completes, **then** valid signals are retained independently while unusable signals remain explicitly unavailable; the system does not require all six dimensions to be measurable.

### User Story 2 - Prepare Comparable Features from Approved References (Priority: P1)

A research user applies reference-based signal methods using a justified training population and later applies the resulting compatible state to permitted records. The state identifies which model, version, label, preprocessing, cohort scope, and evidence definition it represents.

**Why this priority**: Distribution, domain, and other reference-dependent measurements can be misleading if fitted with evaluation data or reused across incompatible classifiers.

**Independent Test**: Fit synthetic reference states using only a Feature 003 training partition, then apply them to eligible synthetic records. Change validation, calibration, and protected-test inputs and confirm the fitted state is unchanged. Attempt mismatched model versions, labels, preprocessing identities, evidence schemas, and cohort scopes and confirm the state is rejected or reported not ready.

**Acceptance Scenarios**:

1. **Given** a method that requires a fitted reference, **when** its state is created, **then** only protocol-approved training-partition predictor evidence contributes to that state; outcomes, correctness targets, validation/calibration data, and protected-test data do not.
2. **Given** a fitted state for one exact model/version/label and evidence definition, **when** it is requested for a different or materially changed identity or scope, **then** the incompatibility is explicit and the state is not silently reused.
3. **Given** an accepted state and unchanged eligible input, method version, configuration, and seed where applicable, **when** extraction is repeated, **then** deterministic methods return identical values and provenance; methods that are not deterministic report their reproducibility limits.
4. **Given** a stateless method whose approved definition needs only the current prediction/evidence, **when** it is applied, **then** it does not create hidden fitted state or consult another partition.

### User Story 3 - Keep Predictor Features Separate from Supervision and Evaluation (Priority: P1)

A research user prepares feature rows aligned with Feature 003 examples while keeping correctness supervision and protected evaluation information outside predictor values and ordinary development outputs.

**Why this priority**: Including outcomes, grouping, or evaluation information in a predictor can make later safety-estimator results invalid even when the signal calculation itself is reproducible.

**Independent Test**: Build paired synthetic datasets with identical allowed predictions/evidence but altered ground truth, correctness targets, patient-group references, and protected outcomes. Confirm none of those values is emitted as a predictor feature or used to fit signal state. Confirm changes to protected data do not change development feature values or fitted state.

**Acceptance Scenarios**:

1. **Given** a Feature 003 correctness example, **when** predictor features are produced, **then** the primary outcome, correctness target, patient-group identity, partition assignment, and protected-test membership remain outside the feature vector. Opaque references needed to align rows are carried separately under the applicable data controls.
2. **Given** training, validation, calibration, and protected-test roles, **when** signal state is fitted, **then** only permitted training evidence is used. Validation/calibration evidence may be transformed by the frozen state only where the approved protocol allows; protected-test rows and outcomes are not exposed through ordinary development APIs.
3. **Given** an attempt to supply an outcome, correctness target, patient-group reference, or protected-test value as signal input, **when** predictor-feature validation runs, **then** the value is rejected or excluded with a safe reason rather than accepted as a predictor.
4. **Given** restricted or identifiable values in an input or failure, **when** extraction is performed or rejected, **then** ordinary logs, errors, and reports do not expose patient data, protected rows, outcomes, or raw evidence payloads.

### User Story 4 - Review Signal Meaning and Limitations (Priority: P2)

A researcher can determine how an available value was derived, which evidence and reference it used, whether it is calibrated or uncalibrated, and why another signal could not be calculated.

**Why this priority**: Downstream training and research reports require signals with documented semantics rather than unlabeled numbers.

**Independent Test**: Inspect synthetic results and manifests for every dimension, score kind, evidence state, and supported fitting mode. Verify that results retain method/configuration provenance, interpretation and safe limitations, and that no signal is presented as a reliability score or clinical conclusion.

**Acceptance Scenarios**:

1. **Given** a primary probability, a non-probability score, and an explanation that may refer to a different output space, **when** signal results are recorded, **then** the source semantics and explanation target space remain distinct; score magnitude or explanation presence is not silently reinterpreted as uncertainty or reliability.
2. **Given** a signal calculation using repeated outputs, modalities, explanations, or domain metadata, **when** results are recorded, **then** the evidence identities, scope, timing, interpretation, and any known limitations are traceable to the source record.
3. **Given** no scientifically justified method or adequate evidence for a dimension in the declared scope, **when** extraction is requested, **then** it returns an explicit non-value state rather than a placeholder algorithm or unsupported safety claim.

### Edge Cases

- A standalone single-label classifier has a binary probability but no class-conditional output vector; an approved method requiring more than that output is unavailable rather than inferred from an undocumented transform.
- A model provides a finite non-probability score with a registered primary class mapping. The score is not assumed to be a calibrated probability or comparable with another model's score.
- A representation is empty, constant, malformed, dimensionally different from its reference, or created under a different preprocessing identity.
- A small or imbalanced training cohort cannot support a proposed reference method, including a method that requires both correctness classes. No samples, classes, modalities, or explanations are fabricated to meet a minimum.
- Repeated outputs are absent, have too few observations for a declared method, or originate from incompatible seeds, stochastic settings, or model versions.
- One modality is missing or unsupported, modality-specific outputs use different scales or target meanings, or a modality was not available for the assessment.
- An explanation targets an uncalibrated score while the delivered primary probability is calibrated, or its method, output space, target, or perturbation semantics are unknown.
- Domain/cohort metadata is missing, too broad, contains patient identifiers, or refers to a population outside the approved reference scope.
- A component has any number of independent contributors, overlapping labels, mixed classifier forms, or different evidence capabilities; one contributor's signal must not stand in for another's.
- A fitted state is stale, corrupt, lacks verifiable provenance, or is requested for a new model version, label, preprocessing identity, evidence schema, or cohort scope.
- An extractor cannot distinguish a missing measurement from an actual numeric zero or receives non-finite values.
- Only protected-test observations or outcomes are available for a requested fitted operation.

## Requirements

### Functional Requirements

- **FR-001**: The feature MUST accept only predictions and evidence validated under Feature 002, with an exact compatible Feature 001 registration for each `(model_id, model_version, label_id)` source.
- **FR-002**: The feature MUST preserve standalone supervised single-label binary, supervised multi-label, and independently composed multi-model configurations. It MUST NOT infer a classifier's task type from a component's total label count.
- **FR-003**: Results for overlapping labels from different contributors MUST remain independent and source-qualified; the feature MUST NOT fuse predictions or transfer signal values or fitted state across contributors.
- **FR-004**: The feature MUST organize signal definitions under exactly the six constitutional dimensions and MUST NOT add an undeclared seventh dimension.
- **FR-005**: Before a method is treated as an available signal, its purpose, input prerequisites, output semantics, units or representation, applicability, limitations, and provenance requirements MUST be declared and testable. Unapproved or scientifically unsupported methods MUST remain unavailable/not ready.
- **FR-006**: Every signal result MUST identify the exact model ID, model version, label ID, dimension, method and method version, evidence sources, and applicable reference-state identity. Component identity alone MUST NOT qualify a result.
- **FR-007**: Signal results MUST preserve primary score kind, value, scale, direction, class mapping, and calibration meaning. The primary classifier score MUST NOT be relabeled as a Safira reliability score.
- **FR-008**: Signal results MUST retain evidence provenance, applicable timing/observation scope, source assurance, and safe references to the evidence used. They MUST distinguish the signal's provenance from the prediction's source provenance.
- **FR-009**: A signal result MUST contain either a validated value with declared semantics or an explicit non-value state and safe reason. Feature 004 signal-state codes MUST distinguish `unsupported` (method/capability not supplied), `missing` (expected evidence absent), `unavailable` (supported evidence could not be obtained), `invalid` (supplied evidence fails validation), `insufficient_evidence` (valid evidence does not meet the method's declared support requirements), and `not_ready` (required approval, compatible reference, or provenance is not ready). These signal states MUST preserve rather than rewrite Feature 002's underlying five-state evidence values. They MUST NOT be replaced with fabricated measurements such as zero.
- **FR-010**: Extraction MUST be capability-aware. It MUST NOT call unsupported adapter operations, and MUST NOT assume that every classifier or assessment can supply all six signal dimensions.
- **FR-011**: Data sufficiency MUST expose prediction-time evidence coverage/validity against an explicitly declared method prerequisite profile. This record-level profile MUST preserve underlying evidence states and MUST NOT imply clinical eligibility, correctness, or safety. Cohort sample adequacy MUST be reported separately using protocol-specific criteria and MUST NOT enter patient predictor features by default.
- **FR-012**: The V1 distribution-conformity/OOD candidate is raw k-nearest-neighbour reference distance for a current feature representation against compatible representations from the approved Feature 003 training partition. For vector `z`, metric `d`, and declared integer `k`, the value is the distance from `z` to its k-th nearest reference vector. It is a distance, not a probability or thresholded decision. The result MUST identify feature space, metric, `k`, preprocessing and reference scope. Missing or incompatible representations make the method unavailable/not ready; the result MUST NOT imply diagnosis, abnormality, error probability, or safety.
- **FR-013**: For registered binary probability `p`, the V1 predictive-uncertainty candidate is Bernoulli entropy `H(p) = -p log(p) - (1-p) log(1-p)`, with log base recorded and `0 log(0)` defined as zero; its range is `[0, log(2)]` for the selected base. It describes ambiguity in the declared probability output, not correctness or calibrated reliability. Non-probability scores MUST NOT be transformed into probabilities. Optional repeated-output dispersion is the descriptive variance `R⁻¹ Σᵣ(pᵣ−p̄)²` over the exact declared set of `R` same-input probability outputs, where `p̄` is their arithmetic mean; it is available only when repeat identity, same-input scope, stochastic mechanism and compatible probability semantics are declared and validated. It MUST NOT automatically be interpreted as epistemic or aleatoric uncertainty, and no universal minimum `R` is set.
- **FR-014**: The V1 modality-agreement candidate is pairwise Jensen–Shannon divergence for Bernoulli distributions formed from modality-specific probabilities for the same exact contributor, label, target, assessment occurrence and compatible time scope. For distributions `P_i`, `P_j`, it is `H((P_i+P_j)/2) - (H(P_i)+H(P_j))/2`; log base and any multi-modality aggregation must be declared. At least two valid, semantically comparable probabilities are required. Missing or incomparable modalities are missing/unavailable, not agreement/disagreement. Different component classifiers MUST NOT be compared as modalities.
- **FR-015**: The V1 domain-familiarity candidate reports whether a privacy-permitted, declared domain category occurs in a versioned reference vocabulary built from the approved Feature 003 training partition (`seen`, `unseen`, or an explicit evidence state). It MUST identify category semantics and reference population/scope. Category identifiers or support counts MUST NOT expose patient/site identity or become predictors without an explicitly approved privacy and feature-use definition. This category-coverage result is not a population-level distribution-shift test.
- **FR-016**: V1 explanation reliability MUST preserve explanation method, target, output space, calibration relationship and provenance, and report applicability/availability states. It MUST NOT emit a generic numeric explanation-reliability score. Perturbation sensitivity, infidelity/fidelity, stability and model/data randomization checks are deferred unless a later approved method defines the explainer, target, perturbation distribution, model access, scope and validation. Explanation availability alone MUST NOT be treated as reliability; stability MUST NOT replace the broader dimension.
- **FR-017**: Stateless calculations MUST use only the current approved prediction/evidence record and declared configuration; they MUST NOT fit or update hidden state.
- **FR-018**: Any fitted extractor or reference distribution MUST be fit only from permitted predictor evidence in the approved Feature 003 training partition. It MUST record the exact dataset, protocol and manifest references available to the authorized integration; exact model/version/label; preprocessing and evidence schema; method version and parameters; and provenance needed to assess compatibility and reproduce the state. Parameter choices (including distance metric, `k`, entropy/JSD log base, modality aggregation, domain-category definition, fold design and adequacy criteria) MUST be documented and approved by the research owner in a versioned protocol before extraction. Choices MUST NOT be tuned against protected-test outcomes.
- **FR-019**: Fitted state MUST NOT use verified outcomes, primary correctness targets, patient-group identifiers, partition assignments as predictor values, validation/calibration observations for fitting, or protected-test observations/outcomes. Partition roles may gate access but MUST NOT become predictor features. For training-row values from reference-fitted methods, the implementation MUST use deterministic patient-grouped cross-fitting declared in the versioned protocol; all visits, labels and records for a patient group MUST be assigned to one fold, and that group's records MUST be excluded from the reference used to score it. Infeasible folds yield `insufficient_evidence`; the implementation MUST NOT split a patient group or search alternative seeds.
- **FR-020**: Fitted state MUST be rejected or explicitly not ready when its model/version/label, preprocessing identity, evidence definition, reference cohort/scope, method version, or required provenance is missing or incompatible. State MUST NOT be reused automatically across incompatible identities or scopes.
- **FR-021**: Applying a fitted state outside its training partition MUST respect the approved Feature 003 protocol and exact dataset/protocol/manifest references. Validation/calibration transforms use frozen state only. A protected-test apply-only path MAY operate only through a separately injected, authorized custodian boundary after signal definitions and fitted state are frozen. It MUST validate exact scope, MUST NOT refit, select, tune or expose protected rows, outcomes, correctness targets or their distributions, and MUST return no protected values through ordinary development-facing objects, APIs, logs or serialization. The custodian integration is external and not currently configured; no access, persistence or verification guarantee is implied.
- **FR-022**: Predictor feature values MUST be separated from outcome/supervision records. Patient, assessment, occurrence, linkage-group, split-assignment, target, verified outcome, and correctness-target references/values MUST NOT enter the predictor feature vector. Any opaque keys needed for row alignment MUST remain separate from feature values and be handled under the approved privacy controls.
- **FR-023**: Repeated observations, modalities, explanations and domain fields MUST retain their own source, timing, scope, interpretation, and preprocessing provenance. Non-comparable evidence MUST NOT be combined into one signal value.
- **FR-024**: For the same input, state, method version, and deterministic configuration, extraction MUST produce reproducible outputs. Any method with unavoidable nondeterminism MUST declare it and retain the controls and provenance needed to reproduce or characterize the run; it MUST NOT silently retry with alternative seeds to obtain a favorable result.
- **FR-025**: Invalid input, incompatible identity, unavailable reference state, or an extraction failure MUST produce a typed, privacy-safe outcome. Errors MUST NOT echo patient input, raw explanation content, identifiers, or restricted values.
- **FR-026**: Accepted signal outputs and fitted-state metadata MUST be immutable or defensively detached so caller changes cannot alter recorded features or their provenance.
- **FR-027**: The feature MUST NOT change Feature 001, Feature 002, Feature 003, `ModelAdapter`, `AdapterCapabilities`, `SafetyContext`, or `SafetyAssessment` contracts without a separately justified and approved contract change.
- **FR-028**: This feature MUST stop at signal extraction and predictor-feature preparation. It MUST NOT train a safety estimator, calibrate Safira reliability, select policy or operating points, produce reliability scores, generate TRUST/CAUTION/DEFER, make diagnoses, or claim clinical validation.
- **FR-029**: Verification MUST use synthetic data and include positive, negative, leakage, determinism, model/version compatibility, all three classifier configurations, and evidence-availability coverage. No restricted or identifiable patient data may be committed or printed in routine output.

### Safety Dimension Requirements

| Dimension | Required meaning and purpose | Evidence prerequisites and applicability | Limits |
|---|---|---|---|
| Data sufficiency | Prediction-time evidence coverage/validity for declared method prerequisites; separately, protocol-scoped cohort support. | Record profile uses Feature 002 states and declared requirements. Cohort support uses Feature 003 training partition, unique patient groups and exact model/version/label scope. | Cohort counts/class support are controlled adequacy metadata, not patient predictors. Criteria are protocol-specific; no universal minimum. |
| Distribution conformity / OOD | Raw k-th-neighbour distance in a named feature space against an approved training reference. | Requires compatible finite representations, preprocessing, declared metric and `k`, and exact model/version/label scope. | Reference-fitted. Distance is not probability or clinical abnormality. Use patient-grouped cross-fitting for training-row values. |
| Prediction uncertainty | Bernoulli entropy of an explicitly registered probability; optional repeated-output variation with validated stochastic provenance. | Entropy requires valid binary `p`; repeated variation additionally requires same-input repeats and declared stochastic settings. | Entropy is not correctness or calibration. Stateless for entropy; repeated-output semantics remain conditional. |
| Modality agreement | Pairwise Jensen–Shannon divergence between comparable modality-specific Bernoulli probabilities. | At least two outputs for same contributor, label, target, occurrence and compatible timing/calibration semantics; log base and aggregation declared. | Stateless. No comparisons across independent component classifiers; missing or incomparable modalities yield explicit states. |
| Domain familiarity | Whether a privacy-permitted declared category occurs in an approved training-reference vocabulary. | Requires source-qualified category semantics and exact compatible reference scope. | Reference-fitted, with patient-grouped cross-fitting for training-row values. Not equivalent to OOD or cohort-shift testing; category exposure is privacy-limited. |
| Explanation reliability | Preserve method/target/output-space/calibration metadata and applicability; no generic numeric V1 score. | Feature 002 explanation metadata may support traceability, but numeric fidelity/stability needs additional model and perturbation evidence. | Stateless metadata. Perturbation-based and model/data randomization methods are deferred until separately justified and validated. |

### Applicability by Classifier Configuration

| Configuration | Applicability rule |
|---|---|
| Standalone supervised single-label binary classifier | A signal is eligible only when the exact label's registered primary semantics and required evidence support its approved method. One binary probability may support some uncertainty definitions, but MUST NOT be assumed to support every distributional or uncertainty calculation. |
| Supervised multi-label classifier | Evaluate each label independently using that label's exact registered score semantics and evidence. A signal for one label MUST NOT be substituted for another label merely because the outputs share a model. Shared representations are usable only when a method explicitly defines and validates that scope. |
| Multi-model component | Evaluate each contributor independently using its exact model/version/label and evidence. Different contributors may have different applicable dimensions and fitted states. Component-level composition does not establish modality agreement; agreement across modalities requires comparable outputs from modalities of the same declared prediction target, while agreement/fusion across separate classifiers is outside this feature. |

No classifier form is required to provide all six signals. Missing probability vectors, modality outputs, representations, repeats, explanations, or domain metadata make only the dependent operation unavailable, subject to its approved definition.

### Stateless and Reference-Fitted Operations

Stateless extraction calculates a declared value from the current validated prediction/evidence record and fixed, versioned method configuration. V1 stateless candidates are evidence coverage, binary entropy, pairwise modality JSD, and explanation metadata/applicability. Reference-fitted candidates are kNN OOD distance and the domain-category vocabulary. Fitted state uses only permitted Feature 003 training-partition predictor evidence and is bound to exact dataset/protocol/manifest references, model/version/label, preprocessing, evidence schema, method version and parameters.

For training-row values from reference-fitted methods, deterministic patient-grouped cross-fitting is required. A patient group’s all visits, labels and related records remain in one fold and are excluded from the reference used to score that group. Fold design and seed are approved in the versioned research protocol; no alternative-seed search is permitted. Validation and calibration rows may be transformed by full frozen training state, subject to protocol. Protected-test transformation is apply-only under the separate custodian boundary in FR-021.

Method parameters and support criteria are not universal constants. The research owner records and approves each method’s parameters, rationale, method version, preprocessing, reference scope, fold design, and adequacy criteria in a versioned protocol before extraction. A parameter cannot be selected or revised using protected-test outcomes. Software tests establish implementation behavior; empirical validation on appropriately independent data is still required before claiming usefulness for a research population.

### Remaining Research Limitations

The clarified candidate methods are not clinically validated for Safira’s intended populations. Actual evidence availability varies by adapter and precomputed source contract. The repository has no configured real Feature 003 verification/custodian integration, so protected-test application cannot currently be exercised against real controlled artifacts. The owner must establish compatible representations, source-valid domain categories, comparable modality probability semantics, repeat provenance, and an empirically justified perturbation protocol before any conditional/deferred method can be treated as operational. No universal sample minimum, cutoff, confidence claim or clinical interpretation is defined.
## Key Entities

- **SignalDefinition**: A versioned research definition within one of the six dimensions, including purpose, prerequisites, applicability, value semantics, method, limitations, and required evidence provenance.
- **SignalResult**: A value or explicit non-value state for one exact model/version/label and assessment occurrence, with evidence lineage, method/configuration identity, interpretation, and safe reason.
- **SignalFeatureRecord**: A set of independently traceable signal results aligned with one eligible Feature 003 example using opaque row-alignment keys kept separate from predictor values. It carries exact Feature 003 dataset, protocol and manifest references available through the authorized integration; patient-group identity is never a predictor.
- **FittedSignalState**: Immutable, versioned parameters or reference data learned only from approved Feature 003 training predictor evidence, with exact compatibility scope, cross-fitting fold/seed provenance, and reproducibility lineage.
- **SignalRunManifest**: A privacy-safe record of exact input dataset/protocol/manifest references, signal definitions and method versions, deterministic configuration, fitted-state references, exclusions, and output lineage, without restricted rows or identifying content.
- **AvailabilityState**: Feature 004 signal-result state, separate from its value and from Feature 002's preserved evidence state: `available`, `unsupported`, `missing`, `unavailable`, `invalid`, `insufficient_evidence`, or `not_ready`. It is separate from safety assessment.

## Success Criteria

### Measurable Outcomes

- **SC-001**: All six constitutional dimensions have an explicit definition record identifying the clarified V1 candidate scope, purpose, evidence prerequisites, applicable configurations, limitations, deferred methods, and conditions that yield a non-value state; the record does not claim empirical or clinical validation.
- **SC-002**: In synthetic acceptance cases, every emitted signal value is traceable to one exact registered `(model_id, model_version, label_id)` and its source/evidence lineage; overlapping-label contributors remain distinct.
- **SC-003**: In tests covering standalone binary, multi-label and multi-model inputs, each signal either produces a contract-valid result when its approved prerequisites hold or an explicit non-value state when they do not; no test requires all six signals to be available.
- **SC-004**: Altering only ground truth, correctness targets, patient-group identifiers, split assignments, validation/calibration values, or protected-test values cannot change training-fitted signal state or ordinary development predictor features, and none of those supervision/partition values may appear in a predictor feature. Protected-test transformations, if authorized, remain in the separate custodian-controlled artifact.
- **SC-005**: A fitted reference created from synthetic training data is unchanged when validation, calibration or protected-test records are changed, and it is rejected for an incompatible model version, label, preprocessing identity, evidence schema or scope.
- **SC-006**: Repeating deterministic extraction with the same approved inputs, state and configuration produces identical signal values and lineage; nondeterministic methods identify their reproducibility limitations.
- **SC-007**: Tests for unsupported, missing, unavailable, invalid and insufficient evidence confirm that no fabricated measurement is emitted and that valid independent signal results are not discarded solely because another optional signal is unavailable.
- **SC-008**: Privacy and compatibility tests confirm that routine outputs contain no patient-identifying data, restricted manifest contents or protected-test rows, and that Features 001–003 and existing adapter/context/assessment behavior remain unchanged.
- **SC-009**: No Feature 004 output or documentation presents a signal value as a Safira reliability score, TRUST/CAUTION/DEFER decision, diagnosis, or clinical safety claim.
- **SC-010**: Synthetic cross-fitting tests confirm that every training patient group is excluded from the reference used to score it, all related visits/labels stay in one fold, and the approved deterministic fold configuration is used without alternate-seed search.
- **SC-011**: Synthetic custodian-boundary tests confirm that protected transforms use only exact-scope frozen state, do not refit/tune, and expose no protected rows, outcomes, correctness targets, or distributions through ordinary objects, APIs, logs, or serialization.

## Assumptions

- Feature 001 exact registrations, Feature 002 validated records and Feature 003 grouped datasets remain authoritative and are consumed without contract changes.
- Feature 003's ordinary development dataset can supply train, validation and calibration examples. This specification defines an apply-only custodian boundary for protected-test transformation after state is frozen, but does not implement or configure that integration or expose protected data through ordinary Feature 003/004 APIs. A manifest reference or receipt alone is not proof of durable storage or protected-artifact access.
- Feature 004 may define a small set of justified methods after research clarification. It does not need to produce a numeric value for every dimension or every record.
- Research owners provide lawful, privacy-preserving inputs and authorized reference data. Passing synthetic tests establishes software behavior only, not the validity of a method or clinical safety.
- Fitted states are scoped to exact model/version/label, preprocessing, evidence schema, reference population and method version unless a separately justified compatibility decision is approved.
- No numerical threshold, minimum cohort size, universal algorithm, signal ranking, or clinical meaning is assumed.

## Scope Boundaries

**Included**: define and validate six-dimension signal contracts; calculate justified stateless signals; fit and apply approved reference-based signal extractors using only approved training evidence; produce traceable, privacy-safe predictor feature records aligned with Feature 003 examples; report explicit signal availability and readiness; synthetic positive, negative, leakage, determinism, and compatibility verification.

**Excluded**: safety estimator training; correctness-target construction or ground-truth adjudication; patient-group splitting or changes to Feature 003; Safira reliability calibration; policy/threshold selection; TRUST/CAUTION/DEFER; runtime clinical assessment; diagnosis or treatment advice; changes to primary model training; mandatory use of every signal; automatic transfer of fitted states; arbitrary clinical or statistical thresholds; clinical validation claims; and changes to Feature 001–003 or existing `ModelAdapter`, `AdapterCapabilities`, `SafetyContext`, and `SafetyAssessment` contracts.
