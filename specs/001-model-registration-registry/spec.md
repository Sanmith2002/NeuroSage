# Feature Specification: Model Registration and Registry for Safira

**Feature Branch**: Not created (no branch hook configured)

**Created**: 2026-10-15

**Status**: Draft

**Input**: User description: "Feature 001: model registration and exact-version registry for supervised multi-label primary classifiers."

## Clarifications

### Session 2026-10-15

- Q: For Feature 001, must registered model-version records remain retrievable after a process restart, or only during the active registry lifecycle? → A: Identity and metadata survive restarts; the compatible adapter is reattached afterward.
- Q: Before a downstream feature uses a registered model version, should Safira resolve its exact classifier and compatible adapter as one validated association? → A: Yes; exact classifier-version and compatible adapter must resolve together before use, while metadata-only lookup remains available.
- Q: How should Feature 001 handle SC-005’s one-second lookup target when no research or product requirement justifies that number? → A: Remove the unsupported latency criterion; rely on SC-002 for exact lookup correctness and restart coverage.
- Q: If a registered classifier, its label schema, preprocessing, or adapter version changes, must it be registered under a new model version before downstream use? → A: Yes; every material change requires a new model version, and the earlier registration remains unchanged.
- Q: In Feature 001, must each supported label have a binary positive/negative outcome, or may a label have more than two classes? → A: Each label has binary ground truth, but the primary classifier must provide a continuous per-label score or probability and a defined score-to-class mapping; Safira's later reliability score and status are separate.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Register and Retrieve a Classifier (Priority: P1)

A researcher registers a supervised multi-label primary classifier with its stable identity,
label meanings, adapter, and declared evidence capabilities. The researcher can retrieve
that definition by exact identifier and version before a safety package exists.

**Why this priority**: Downstream safety training needs an unambiguous, compatible
classifier definition. Registration must work before training is possible.

**Independent Test**: Register one valid classifier with two distinct labels, retrieve
it by exact identifier and version, and confirm its label and capability information
matches the submitted definition without starting safety training.

**Acceptance Scenarios**:

1. **Given** a valid supervised multi-label classifier definition with a compatible
   adapter, two distinct binary-outcome labels, and continuous per-label prediction
   outputs, **when** it is registered, **then** a retrievable model-version record
   contains its model identifier, version-specific classifier artifact identity, label
   schema, adapter identity, output meanings, prediction-to-class mappings, and
   declared capabilities.
2. **Given** a registered classifier, **when** its exact identifier and version are
   requested, **then** the corresponding record and label/output semantics are returned.
3. **Given** a valid registration with no labelled safety data or safety package,
   **when** registration completes, **then** the classifier remains registered without
   initiating training, calibration, signal extraction, policy selection, or assessment.
4. **Given** a valid definition with input, modality, and preprocessing declarations,
   **when** it is retrieved, **then** those declarations match the registered version.
5. **Given** an active registration with its exact classifier and compatible adapter,
   **when** a downstream feature requests usable access to that identifier and version,
   **then** it receives the validated classifier-adapter association for that version.
6. **Given** a registered label with a continuous primary prediction score or
   probability, **when** its definition is retrieved, **then** the value's meaning,
   scale, and positive/negative class mapping are available without presenting it as
   Safira's separate reliability score.

---

### User Story 2 - Keep Multiple Models and Versions Distinct (Priority: P2)

A researcher registers several primary classifiers and a newer version of one classifier.
Each exact model-version record remains independently retrievable.

**Why this priority**: A later safety package can be valid only for its matching
classifier and version; replacement would undermine provenance and compatibility.

**Independent Test**: Register two model identifiers and two versions of one identifier,
then retrieve each and compare its schema and adapter metadata.

**Acceptance Scenarios**:

1. **Given** one registered classifier, **when** a different classifier identifier is
   registered, **then** both remain independently retrievable.
2. **Given** version A of a classifier, **when** version B is registered under the same
   identifier, **then** version A and its configuration remain unchanged and retrievable.
3. **Given** an existing identifier-version pair, **when** the same pair is registered
   again, **then** the attempt is rejected without replacing the existing record or a
   safety package linked to it.
4. **Given** one registered version, **when** another version is requested, **then**
   lookup does not silently return the existing version.
5. **Given** registered model-version metadata and a process restart, **when** the
   exact identifier and version are requested, **then** the same metadata is returned;
   downstream use remains unavailable until the exact classifier and compatible adapter
   are reattached and validated together.
6. **Given** a registered version, **when** its classifier, label schema, preprocessing,
   or adapter version changes materially, **then** the changed definition requires a new
   model version and the earlier record remains unchanged.

---

### User Story 3 - Reject Invalid Definitions and Lookups (Priority: P2)

A researcher receives a specific, actionable failure when a model definition is invalid,
an adapter is incompatible, or an exact lookup cannot be satisfied.

**Why this priority**: Invalid schemas and ambiguous lookups could corrupt later
label-level assessment or attach evidence to the wrong classifier.

**Independent Test**: Submit one case from each invalid category and confirm rejection
leaves existing registrations unchanged and identifies the reason.

**Acceptance Scenarios**:

1. **Given** a missing or malformed model identifier or version, **when** registration
   is attempted, **then** it fails with the offending field identified.
2. **Given** an empty, duplicate, or semantically incomplete label schema, **when**
   registration is attempted, **then** it fails without creating a record.
3. **Given** a task outside supervised multi-label classification, including a
   standalone single-label binary classifier, **when** registration is attempted,
   **then** it fails with the supported scope stated.
4. **Given** an adapter incompatible with the existing adapter and capability
   contracts, **when** registration is attempted, **then** the incompatibility is
   identified and no record is created.
5. **Given** a missing model identifier or wrong version, **when** exact lookup is
   attempted, **then** the missing identity is reported without returning a substitute.
6. **Given** a registration definition containing patient observations or restricted
   clinical data, **when** registration is attempted, **then** it is rejected without
   retaining or echoing that data in routine errors.
7. **Given** retained metadata but a missing or mismatched classifier-adapter pair,
   **when** usable access is requested, **then** Safira reports the linkage problem
   without substituting a different classifier or adapter.
8. **Given** an earlier identifier-version pair, **when** a materially changed
   classifier, schema, preprocessing, or adapter is reattached under that pair,
   **then** usable access is rejected without altering the earlier registration.
9. **Given** a classifier that exposes only hard 0/1 predictions, a label with more
   than two ground-truth classes, or an undefined score-to-class mapping, **when**
   registration is attempted, **then** it is rejected without creating a record.
10. **Given** competing registration attempts for the same identifier and version,
    **when** they occur together, **then** at most one succeeds and no accepted record
    is overwritten.

### Edge Cases

- Identifier or version fields containing only whitespace or control characters are
  invalid; leading or trailing whitespace is not silently normalized into another identity.
- Similar but unequal version strings remain distinct; lookup never falls back to a
  newest or closest version.
- A one-label schema is not a multi-label registration.
- Distinct display names do not make duplicate stable label identifiers valid.
- A label whose output mapping or outcome meaning is undefined makes the schema invalid.
- A score or probability may equal 0 or 1 for a particular prediction; registration
  remains valid if the classifier can produce continuous per-label outputs. A classifier
  limited to hard 0/1 outputs is invalid for Feature 001.
- A non-probability score requires its scale, direction, and mapping to the binary
  positive/negative outcome to be declared; it is not silently treated as a probability.
- An unsupported capability remains explicitly unsupported in registration metadata;
  registration does not invent a safety value for it.
- A failed registration leaves all prior records and later linked packages untouched.
- Competing attempts for one identifier-version pair cannot create two accepted
  definitions or overwrite the accepted record.
- A changed classifier or adapter cannot be reattached under an unchanged version
  merely because its declared labels or capabilities appear similar.
- After a restart, retained metadata does not imply that a classifier-adapter pair is
  attached or that a safety package is ready for use.
- Registration records contain model metadata, not patient observations or restricted data.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Safira MUST accept only supervised multi-label primary classifiers with at
  least two distinct supported label identifiers, each with binary ground-truth outcomes
  and a continuous per-label prediction score or probability. It MUST reject standalone
  single-label binary, regression, unsupervised, and reinforcement-learning tasks in
  Feature 001.
- **FR-002**: Every registration MUST specify a stable model identifier and explicit
  version. Both MUST be nonblank, free of control characters, and free of leading or
  trailing whitespace. The identifier-version pair MUST designate one immutable
  classifier definition.
- **FR-003**: The label schema MUST contain nonblank, unique, stable label identifiers
  and an explicit mapping from classifier outputs to each label. For every label it
  MUST define the positive and negative ground-truth outcomes, the meaning and scale
  of its continuous primary prediction score or probability, and the declared mapping
  from that value to the classifier's positive or negative prediction. A hard 0/1
  prediction alone MUST NOT satisfy the continuous-output requirement.
- **FR-004**: Registration MUST confirm compatibility with Safira's existing ModelAdapter
  and AdapterCapabilities contracts and reject capability declarations without valid
  true/false values or incompatible adapters without calling them on patient data.
  The adapter MUST declare a compatible way to expose each label's continuous primary
  prediction value through the existing contract. It MUST be associated with the exact
  classifier identifier and version; a non-probability score MUST NOT be represented
  as a probability capability.
- **FR-005**: Each registered record MUST expose adapter identity and version and its
  declared optional capabilities, including which are unsupported. Registration MUST NOT
  treat capability declarations as measured safety evidence. After a restart, the exact
  classifier and compatible adapter MUST be reattached and verified together before use.
- **FR-006**: Each record MUST retain the classifier task type, label schema, declared
  classifier artifact identity, input schema and modalities, and preprocessing identity
  for later compatibility checks.
  An explicit none value is permitted when no preprocessing applies. Material changes to
  the classifier, label schema, preprocessing, or adapter version MUST require a new
  model version rather than modifying this record.
- **FR-007**: Safira MUST allow multiple model identifiers and multiple versions under
  one identifier to coexist without changing earlier definitions. Their identity and
  metadata MUST remain retrievable after a process restart.
- **FR-008**: Re-registering an existing identifier-version pair MUST fail explicitly,
  even when the submitted metadata appears identical. It MUST NOT replace the existing
  configuration or an associated safety package. Competing registration attempts for
  that pair MUST result in at most one accepted definition.
- **FR-009**: Retrieval MUST require both identifier and exact version. It MUST NOT
  silently substitute another model or version. Metadata-only lookup MAY succeed when
  the usable classifier-adapter association is absent, but downstream usable access
  MUST fail explicitly until the exact pair is available and validated against the
  immutable registered definition.
- **FR-010**: Failed registration and lookup MUST distinguish invalid fields, unsupported
  task type, incompatible adapter, duplicate registration, unknown identifier, and
  unknown version with actionable reasons.
- **FR-011**: Registration and lookup MUST NOT prepare safety data, extract safety
  signals, train or calibrate a safety estimator, select a TRUST/CAUTION/DEFER policy,
  deploy a safety package, or assess a patient.
- **FR-012**: Registration MUST be possible without labelled safety data or a validated
  safety package and MUST NOT imply readiness for safety assessment.
- **FR-013**: Feature 001 MUST reuse ModelAdapter and AdapterCapabilities and preserve
  SafetyContext, SafetyAssessment, their current behavior, and associated tests.
  Registering another classifier MUST NOT require changing Safira's core implementation.
- **FR-014**: Registration records and routine errors MUST NOT store or disclose
  identifiable patient information or restricted clinical datasets.

### Key Entities

- **Registered Model Version**: One immutable classifier identifier and exact version,
  supervised multi-label task declaration, classifier artifact identity, label schema,
  adapter declaration, input definition, preprocessing identity, and association to
  its compatible adapter. A
  later safety package may refer to it; registration does not create that package.
- **Label Definition**: A stable label identifier, output mapping, and documented
  positive and negative ground-truth meanings, continuous primary score or probability
  semantics, and score-to-class mapping, kept distinct for future patient-label safety
  assessment.
- **Adapter Declaration**: Adapter identity, version, declared optional capabilities,
  and the exact classifier version with which the adapter is associated.
  Capabilities describe possible evidence, not observed values or safety readiness.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All valid review definitions with at least two distinct labels register
  and return identical model identifier, version, classifier artifact identity, binary
  outcome semantics, continuous-score meanings, class mappings, and capabilities on
  exact lookup.
- **SC-002**: A review catalog of at least three distinct classifiers and three versions
  of one classifier produces zero overwritten records and 100% correct exact metadata
  lookups, including after a process restart.
- **SC-003**: Every specified invalid-registration category and missing-lookup scenario
  yields the correct actionable reason and leaves existing records unchanged.
- **SC-004**: Across all registration acceptance scenarios, zero safety-training,
  calibration, signal-extraction, policy-selection, or patient-assessment operations occur.
- **SC-006**: Reviewers can identify every accepted label's outcome meaning and
  distinguish its primary prediction score or probability from Safira's future
  reliability score, and identify supported versus unsupported adapter capabilities
  without inspecting the classifier's internal implementation.

## Assumptions

- Multi-label registration declares at least two labels; each remains individually
  identifiable even when one prediction contains several labels.
- Each disease label has verified binary outcomes. A primary classifier's continuous
  per-label score or probability is different from Safira's later 0–1 reliability score
  and TRUST/CAUTION/DEFER status. Registration preserves the output contract and
  mapping; a later assessment preserves patient-level prediction scores separately
  from reliability scores. The registry does not store patient-level prediction values
  or generate assessments.
- Versions are explicit, opaque identifiers. Feature 001 does not infer version order
  or a latest version. A material classifier, label schema, preprocessing, or adapter
  change receives a new version rather than replacing an existing definition. The
  classifier artifact identity is version-specific and can be checked at reattachment;
  this specification does not prescribe how that identity is produced.
- Model-version identity and metadata survive process restarts. The compatible adapter
  and exact classifier must be reattached and verified together after restart; an
  unattached record is not usable for downstream work. Import/export and distributed
  synchronization remain outside Feature 001.
- Adapter compatibility can be checked from its contract and declarations without
  running predictions on clinical data. Actual evidence extraction is validated later.
- Registration captures input and preprocessing identity but does not load a reference
  cohort, collect outcomes, or determine safety eligibility.
- No current repository integration requires standalone single-label binary
  registration. If one is identified, it requires explicit scope approval.
- The repository has adapter and assessment contracts but no model registry or working
  automatic safety-training pipeline.

## Out of Scope

Safety-data preparation, clinical dataset loading, correctness target generation,
six-dimension signal extraction, estimator training, calibration, selective policy
generation, safety package training or deployment, runtime patient assessment, REST API
development, clinical deployment, and standalone single-label binary support are outside
Feature 001.
