# Feature Specification: Model Registration and Registry for Safira

**Feature Branch**: Not created (no branch hook configured)

**Created**: 2026-10-15

**Status**: Draft

**Input**: User description: "Feature 001: model registration and exact-version registry for supervised multi-label primary classifiers."

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
   adapter and two distinct labels, **when** it is registered, **then** a retrievable
   model-version record contains its identity, label schema, adapter identity, and
   declared capabilities.
2. **Given** a registered classifier, **when** its exact identifier and version are
   requested, **then** the corresponding record and label/output semantics are returned.
3. **Given** a valid registration with no labelled safety data or safety package,
   **when** registration completes, **then** the classifier remains registered without
   initiating training, calibration, signal extraction, policy selection, or assessment.
4. **Given** a valid definition with input, modality, and preprocessing declarations,
   **when** it is retrieved, **then** those declarations match the registered version.

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

### Edge Cases

- Identifier or version fields containing only whitespace or control characters are
  invalid; leading or trailing whitespace is not silently normalized into another identity.
- Similar but unequal version strings remain distinct; lookup never falls back to a
  newest or closest version.
- A one-label schema is not a multi-label registration.
- Distinct display names do not make duplicate stable label identifiers valid.
- A label whose output mapping or outcome meaning is undefined makes the schema invalid.
- An unsupported capability remains explicitly unsupported in registration metadata;
  registration does not invent a safety value for it.
- A failed registration leaves all prior records and later linked packages untouched.
- Registration records contain model metadata, not patient observations or restricted data.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Safira MUST accept only supervised multi-label primary classifiers with at
  least two distinct supported label identifiers. It MUST reject standalone single-label
  binary, regression, unsupervised, and reinforcement-learning tasks in Feature 001.
- **FR-002**: Every registration MUST specify a stable model identifier and explicit
  version. Both MUST be nonblank, free of control characters, and free of leading or
  trailing whitespace. The identifier-version pair MUST designate one immutable definition.
- **FR-003**: The label schema MUST contain nonblank, unique, stable label identifiers
  and an explicit mapping from classifier outputs to each label. It MUST define each label's
  outcome meaning, including positive and negative meanings for binary labels.
- **FR-004**: Registration MUST confirm compatibility with Safira's existing ModelAdapter
  and AdapterCapabilities contracts and reject capability declarations without valid
  true/false values or incompatible adapters without calling them on patient data.
- **FR-005**: Each registered record MUST expose adapter identity and version and its
  declared optional capabilities, including which are unsupported. Registration MUST NOT
  treat capability declarations as measured safety evidence.
- **FR-006**: Each record MUST retain the classifier task type, label schema, declared
  input schema and modalities, and preprocessing identity for later compatibility checks.
  An explicit none value is permitted when no preprocessing applies.
- **FR-007**: Safira MUST allow multiple model identifiers and multiple versions under
  one identifier to coexist without changing earlier definitions.
- **FR-008**: Re-registering an existing identifier-version pair MUST fail explicitly,
  even when the submitted metadata appears identical. It MUST NOT replace the existing
  configuration or an associated safety package.
- **FR-009**: Retrieval MUST require both identifier and exact version. It MUST NOT
  silently substitute another model or version.
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
  supervised multi-label task declaration, label schema, adapter declaration, input
  definition, and preprocessing identity. A later safety package may refer to it;
  registration does not create that package.
- **Label Definition**: A stable label identifier, output mapping, and documented
  outcome meaning, kept distinct for future patient-label safety assessment.
- **Adapter Declaration**: Adapter identity, version, and declared optional capabilities.
  Capabilities describe possible evidence, not observed values or safety readiness.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All valid review definitions with at least two distinct labels register
  and return identical identity, version, label semantics, and capabilities on exact lookup.
- **SC-002**: A review catalog of at least three distinct classifiers and three versions
  of one classifier produces zero overwritten records and 100% correct exact lookups.
- **SC-003**: Every specified invalid-registration category and missing-lookup scenario
  yields the correct actionable reason and leaves existing records unchanged.
- **SC-004**: Across all registration acceptance scenarios, zero safety-training,
  calibration, signal-extraction, policy-selection, or patient-assessment operations occur.
- **SC-005**: With 100 registered model-version records, at least 95% of exact lookups
  complete within one second in an agreed reference environment.
- **SC-006**: Reviewers can identify every accepted label's outcome meaning and
  distinguish supported from unsupported adapter capabilities without inspecting the
  classifier's internal implementation.

## Assumptions

- Multi-label registration declares at least two labels; each remains individually
  identifiable even when one prediction contains several labels.
- Versions are explicit, opaque identifiers. Feature 001 does not infer version order
  or a latest version.
- Records remain available throughout the active registry lifecycle. Persistence across
  process restarts, import/export, and distributed synchronization are excluded from
  Feature 001 unless later specified.
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
