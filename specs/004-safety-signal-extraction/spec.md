# Feature Specification: Safety Signal Extraction and Feature Engineering

**Feature Branch**: Not created (no branch hook configured)  
**Created**: 2026-10-18  
**Status**: Draft — research clarification required before planning  
**Input**: Specify model-agnostic extraction of traceable safety signals from validated primary predictions, evidence, and patient-grouped safety datasets.

## Context and Scope

Safira is a post-hoc reliability research framework, not a disease-prediction model. Constitution v3.0.0 defines exactly six safety dimensions: data sufficiency, distribution conformity/out-of-distribution (OOD), prediction uncertainty, modality agreement, domain familiarity, and explanation reliability. The dimensions are evidence families; they do not imply six mandatory numeric values or an already approved calculation for every family.

The repository has no operational signal algorithms or signal-specific tests. `src/safira/signals/base.py` is empty. Existing `ModelAdapter` and `AdapterCapabilities` expose optional primary probabilities, feature representations, repeated outputs, modality outputs, domain metadata, explanations, input metadata, and available modalities. Those capabilities establish possible evidence collection, not the scientific validity or applicability of a signal.

Feature 001 supplies immutable registrations and exact model/version/label score semantics. Feature 002 supplies validated, source-qualified `PredictionRecord` values, evidence provenance and explicit evidence states. Feature 003 supplies patient-grouped correctness examples and train, validation, and calibration datasets through its ordinary development result. Protected-test rows are transferred only through a separate custodian-controlled handoff. Feature 003 has no configured real verification or storage integrations; its manifest handoff can bind a receipt to an exact manifest but does not by itself prove durable storage. Feature 004 MUST honor these limits and MUST NOT weaken any of these contracts.

Feature 004 specifies WHAT signal extraction and feature preparation must guarantee. It does not approve particular algorithms, thresholds, or a universal signal vector. It does not train a safety estimator or create a safety assessment.

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
- **FR-009**: A signal result MUST contain either a validated value with declared semantics or an explicit non-value state and safe reason. It MUST distinguish at least unsupported, missing, unavailable, invalid, insufficient evidence, and not ready conditions; it MUST NOT replace them with fabricated measurements such as zero.
- **FR-010**: Extraction MUST be capability-aware. It MUST NOT call unsupported adapter operations, and MUST NOT assume that every classifier or assessment can supply all six signal dimensions.
- **FR-011**: Data sufficiency MUST describe support for a declared signal or research scope, not primary-model correctness, clinical eligibility, or general safety. A count or adequacy statistic MUST NOT be used as a patient-level predictor unless a separately approved definition establishes that interpretation and prevents leakage.
- **FR-012**: Distribution-conformity/OOD results MUST identify the evidence space and reference scope being compared. A result MUST NOT imply clinical abnormality, diagnosis, or safety solely because an input is common or rare under a reference.
- **FR-013**: Prediction-uncertainty results MUST preserve the source output semantics. Probability-based measures require compatible probability evidence; measures based on repeated outputs require valid repeated-output provenance. A non-probability score MUST NOT be treated as probability or uncertainty without an approved, justified method.
- **FR-014**: Modality-agreement results MUST require multiple valid modality-specific outputs with compatible label, target, scale and timing semantics. Missing modalities MUST be represented as missing/unavailable evidence, not disagreement or agreement.
- **FR-015**: Domain-familiarity results MUST use only permitted, source-qualified domain/cohort evidence and identify their reference population and temporal scope. Patient identity and patient-group linkage MUST NOT be predictors.
- **FR-016**: Explanation-reliability results MUST preserve explanation method, target, output space, calibration relationship, and available stability/fidelity evidence. Explanation availability alone MUST NOT be treated as explanation reliability. Explanation stability MAY be one method but MUST NOT replace the broader constitutional dimension.
- **FR-017**: Stateless calculations MUST use only the current approved prediction/evidence record and declared configuration; they MUST NOT fit or update hidden state.
- **FR-018**: Any fitted extractor or reference distribution MUST be fit only from permitted predictor evidence in the approved Feature 003 training partition. It MUST record the source dataset/protocol/version, exact model/version/label, preprocessing and evidence schema, fit configuration, method version, and provenance needed to assess compatibility and reproduce the state.
- **FR-019**: Fitted state MUST NOT use verified outcomes, primary correctness targets, patient-group identifiers, partition assignments as predictor values, validation/calibration observations for fitting, or protected-test observations/outcomes. Partition roles may gate access but MUST NOT become predictor features.
- **FR-020**: Fitted state MUST be rejected or explicitly not ready when its model/version/label, preprocessing identity, evidence definition, reference cohort/scope, method version, or required provenance is missing or incompatible. State MUST NOT be reused automatically across incompatible identities or scopes.
- **FR-021**: Applying a fitted state outside its training partition MUST respect the approved Feature 003 protocol. Protected-test rows, outcomes, correctness targets and fitted artifacts MUST remain outside ordinary development-facing results and serialization. Any permitted protected-test transformation path MUST preserve custodian control and MUST NOT refit, select, tune, or reveal protected information.
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
| Data sufficiency | Whether the permitted evidence/reference supports a declared extraction or research use at the stated model/version/label/population scope. | Requires a declared support unit, eligible evidence and scope. It may be reference- or cohort-level rather than per prediction; the unit and any permitted predictor interpretation remain open for clarification. | Feature 003 adequacy counts or correctness-class support are not automatically patient features. No universal minimum, class-balance rule, or sufficiency cutoff is set here. |
| Distribution conformity / OOD | How current permitted input evidence compares with a named, compatible reference distribution in a declared feature space. | Generally requires a validated current representation and an approved reference; only applicable when both use the same compatible representation and preprocessing semantics. | Atypicality is not diagnosis, error probability, or proof of unsafe/unsafe prediction. Reference method and scope need research approval. |
| Prediction uncertainty | A declared measure of ambiguity or variability in the primary prediction process. | May use probabilities, compatible output distributions, or provenance-qualified repeated outputs if an approved method supports them. Applicability depends on output semantics and evidence actually available. | Primary confidence, a non-probability score, or one output alone does not establish correctness or safety. Probability-only binary outputs may not support every candidate method. |
| Modality agreement | Consistency or disagreement among valid predictions/evidence from multiple modalities for the same exact contributor, label and assessment. | Requires at least two available, semantically comparable modality-specific outputs and matching target/timing scope. | Missing or incomparable modality output is unavailable, not evidence of agreement or disagreement. |
| Domain familiarity / cohort shift | Whether permitted domain evidence is represented by a declared reference cohort or domain scope. | Requires valid domain/cohort metadata and a compatible reference with documented site, time and population scope. May be inapplicable when metadata are unavailable or too identifying. | Must remain distinct from feature-space OOD unless an approved research definition relates them. Cohort membership alone does not establish eligibility or clinical meaning. |
| Explanation reliability | Evidence that an explanation has a declared, supportable reliability property for its target output. | Requires a validated explanation, method, target and output-space semantics; a candidate method may additionally need perturbations, repeated explanations, or other approved evidence. | Explanation presence or magnitude is not reliability. Stability is only one possible method; no method or universal score is approved in this specification. |

### Applicability by Classifier Configuration

| Configuration | Applicability rule |
|---|---|
| Standalone supervised single-label binary classifier | A signal is eligible only when the exact label's registered primary semantics and required evidence support its approved method. One binary probability may support some uncertainty definitions, but MUST NOT be assumed to support every distributional or uncertainty calculation. |
| Supervised multi-label classifier | Evaluate each label independently using that label's exact registered score semantics and evidence. A signal for one label MUST NOT be substituted for another label merely because the outputs share a model. Shared representations are usable only when a method explicitly defines and validates that scope. |
| Multi-model component | Evaluate each contributor independently using its exact model/version/label and evidence. Different contributors may have different applicable dimensions and fitted states. Component-level composition does not establish modality agreement; agreement across modalities requires comparable outputs from modalities of the same declared prediction target, while agreement/fusion across separate classifiers is outside this feature. |

No classifier form is required to provide all six signals. Missing probability vectors, modality outputs, representations, repeats, explanations, or domain metadata make only the dependent operation unavailable, subject to its approved definition.

### Stateless and Reference-Fitted Operations

Stateless extraction calculates a declared value from the current validated prediction/evidence record and fixed, versioned method configuration. It does not learn, update, or retain a reference from other patients. Reference-fitted extraction learns parameters or a comparison reference from an approved training population and later applies that frozen state. Fitted state is subject to FR-018–FR-021.

The likely distinction is a research question, not an approved method map: OOD and cohort familiarity generally require a named reference; a current-record uncertainty or modality comparison may be stateless when the needed outputs are directly available; data sufficiency and explanation reliability may be cohort-level or reference-dependent. Every specific signal/method pair MUST be classified and justified during clarification and planning. These examples do not approve an algorithm or establish that a signal is feasible.

### Open Research Decisions for `$speckit-clarify`

These decisions are intentionally unresolved; they are not implementation instructions or approved algorithms.

1. **Signal definitions and algorithm selection**: Select defensible operational definitions and candidate algorithms for each of the six dimensions, especially the unit of data sufficiency; reference-space and validation requirements for OOD/domain familiarity; uncertainty semantics for scalar probabilities and non-probability scores; comparability requirements for modality agreement; and whether explanation reliability is evaluated through stability, fidelity, another validated property, or remains unavailable.
2. **Reference fitting and in-sample bias**: Confirm which signals are stateless versus reference-fitted, whether a fitted reference is valid for scoring its own training observations, and whether training features require patient-grouped cross-fitting or another protocol-approved safeguard. All fitting remains restricted to permitted training data; the unresolved choice concerns producing unbiased training rows without changing that boundary.
3. **Availability states and small-cohort behavior**: Confirm the public signal-state vocabulary and how missing, unsupported, extraction failure, insufficient support, non-comparable evidence, and absent fitted state map into it. Establish per-method feasibility/adequacy evidence without universal counts or thresholds.
4. **Feature 003 and protected-test lifecycle**: Confirm which Feature 003 dataset/version and authorized manifest provenance are required, how signal rows align without using patient-group identity as a feature, and whether Feature 004 needs any custodian-controlled transformation path for protected-test predictions. The existing ordinary Feature 003 result does not contain protected rows; Feature 004 MUST NOT assume that restricted artifact is available through ordinary APIs.

## Key Entities

- **SignalDefinition**: A versioned research definition within one of the six dimensions, including purpose, prerequisites, applicability, value semantics, method, limitations, and required evidence provenance.
- **SignalResult**: A value or explicit non-value state for one exact model/version/label and assessment occurrence, with evidence lineage, method/configuration identity, interpretation, and safe reason.
- **SignalFeatureRecord**: A set of independently traceable signal results aligned with one eligible Feature 003 example. Alignment references are separate from the predictor values and do not include group identity as a feature.
- **FittedSignalState**: Immutable, versioned parameters or reference data learned only from approved training predictor evidence, with exact compatibility scope and reproducibility provenance.
- **SignalRunManifest**: A privacy-safe record of input dataset/protocol versions, signal definitions and method versions, deterministic configuration, fitted-state references, exclusions, and output lineage, without restricted rows or identifying content.
- **AvailabilityState**: The declared condition of a signal result (for example, available, unsupported, missing, unavailable, invalid, insufficient evidence, or not ready), separate from its numeric/structured value and separate from safety assessment.

## Success Criteria

### Measurable Outcomes

- **SC-001**: All six constitutional dimensions have an explicit definition record identifying purpose, evidence prerequisites, applicable configurations, limitations, and whether the currently proposed operation is approved, unresolved, or unsupported.
- **SC-002**: In synthetic acceptance cases, every emitted signal value is traceable to one exact registered `(model_id, model_version, label_id)` and its source/evidence lineage; overlapping-label contributors remain distinct.
- **SC-003**: In tests covering standalone binary, multi-label and multi-model inputs, each signal either produces a contract-valid result when its approved prerequisites hold or an explicit non-value state when they do not; no test requires all six signals to be available.
- **SC-004**: Altering only ground truth, correctness targets, patient-group identifiers, split assignments, validation/calibration values, or protected-test values cannot cause those values to appear in predictor features or fitted training state.
- **SC-005**: A fitted reference created from synthetic training data is unchanged when validation, calibration or protected-test records are changed, and it is rejected for an incompatible model version, label, preprocessing identity, evidence schema or scope.
- **SC-006**: Repeating deterministic extraction with the same approved inputs, state and configuration produces identical signal values and lineage; nondeterministic methods identify their reproducibility limitations.
- **SC-007**: Tests for unsupported, missing, unavailable, invalid and insufficient evidence confirm that no fabricated measurement is emitted and that valid independent signal results are not discarded solely because another optional signal is unavailable.
- **SC-008**: Privacy and compatibility tests confirm that routine outputs contain no patient-identifying data, restricted manifest contents or protected-test rows, and that Features 001–003 and existing adapter/context/assessment behavior remain unchanged.
- **SC-009**: No Feature 004 output or documentation presents a signal value as a Safira reliability score, TRUST/CAUTION/DEFER decision, diagnosis, or clinical safety claim.

## Assumptions

- Feature 001 exact registrations, Feature 002 validated records and Feature 003 grouped datasets remain authoritative and are consumed without contract changes.
- Feature 003's ordinary development dataset can supply train, validation and calibration examples. Protected-test examples are available only through an authorized separate custodian pathway if a later approved protocol requires them; this specification does not create such access.
- Feature 004 may define a small set of justified methods after research clarification. It does not need to produce a numeric value for every dimension or every record.
- Research owners provide lawful, privacy-preserving inputs and authorized reference data. Passing synthetic tests establishes software behavior only, not the validity of a method or clinical safety.
- Fitted states are scoped to exact model/version/label, preprocessing, evidence schema, reference population and method version unless a separately justified compatibility decision is approved.
- No numerical threshold, minimum cohort size, universal algorithm, signal ranking, or clinical meaning is assumed.

## Scope Boundaries

**Included**: define and validate six-dimension signal contracts; calculate justified stateless signals; fit and apply approved reference-based signal extractors using only approved training evidence; produce traceable, privacy-safe predictor feature records aligned with Feature 003 examples; report explicit signal availability and readiness; synthetic positive, negative, leakage, determinism, and compatibility verification.

**Excluded**: safety estimator training; correctness-target construction or ground-truth adjudication; patient-group splitting or changes to Feature 003; Safira reliability calibration; policy/threshold selection; TRUST/CAUTION/DEFER; runtime clinical assessment; diagnosis or treatment advice; changes to primary model training; mandatory use of every signal; automatic transfer of fitted states; arbitrary clinical or statistical thresholds; clinical validation claims; and changes to Feature 001–003 or existing `ModelAdapter`, `AdapterCapabilities`, `SafetyContext`, and `SafetyAssessment` contracts.
