# Feature Specification: Prediction/Evidence Collection and Precomputed Adapter for Safira

**Feature Branch**: `feature-02/evidence-collection` (existing checkout; no branch created)

**Created**: 2026-10-17

**Status**: Draft — clarification required before planning

**Input**: User request for Feature 002: collect, validate and standardize primary
predictions and supporting evidence from live adapters or versioned precomputed outputs,
covering standalone binary, multi-label and independent multi-model components.

## Context and Scope

Safira Constitution v3.0.0 and the completed, amended Feature 001 govern this feature.
Feature 002 prepares evidence for later analysis; it does not perform that analysis.
It applies to arbitrary eligible registered supervised single-label binary classifiers,
multi-label classifiers and multi-model components, regardless of disease, algorithm,
architecture or label names. A component's declared contributors determine its size;
this feature imposes no fixed contributor count or disease-specific topology. Each
classifier retains Feature 001's own task/cardinality rules. External outputs may use
different explicitly declared source contracts; no reference component's JSON structure
is the universal ingestion format. The PD handoff is one non-normative integration
reference, documented separately at the end of this specification.
One patient-label pair remains the assessment unit, qualified by its contributing exact
model/version whenever several classifiers predict the same label.

Inspected the existing `ModelAdapter`, `AdapterCapabilities`, `SafetyContext`,
`SafetyAssessment`, registry definitions and registry operations. Preserve these
contracts and the registry's immutable metadata and separate process-local bindings.
Existing context availability Booleans alone cannot express all required evidence
states; standardization must preserve the additional distinctions without redefining
those Booleans or treating empty defaults as proof of unsupported capability.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Collect a Registered Classifier's Predictions (Priority: P1)

A researcher requests primary predictions and available supporting evidence for one
assessment from a registered standalone binary or multi-label classifier. Each result
retains the model's exact identity, label meaning and primary-output semantics.

**Why this priority**: Downstream research needs correct, attributable predictions
before any reliability analysis can be meaningful.

**Independent Test**: Use synthetic registered one-label and multi-label classifiers
with probabilities and non-probability scores. Collect their outputs and verify source
identity, numeric semantics, assessment association and optional-evidence states.

**Acceptance Scenarios**:

1. **Given** a registered one-label binary classifier with a validated live binding,
   **when** a prediction is requested for its label, **then** one record contains the
   exact model/version/label, patient/assessment association, continuous primary value,
   declared output meaning and collection provenance, without a reliability score.
2. **Given** a registered multi-label classifier, **when** several labels are collected,
   **then** each requested label has a separate record and its own output mapping; the
   values are not normalized to sum to one across independent binary labels.
3. **Given** a declared non-probability score, **when** a finite value in its declared
   domain is collected, **then** its scale and direction are preserved and it is not
   populated into a probability field or silently transformed into a probability.
4. **Given** an unknown model/version, unknown label, incompatible adapter, missing live
   binding or mismatched input declaration, **when** live collection is requested,
   **then** it fails explicitly before prediction where the mismatch is detectable,
   without substituting another version or changing registration metadata.
5. **Given** an invalid primary value, **when** validation runs, **then** the affected
   prediction is not accepted; the reason identifies the failing category without
   disclosing patient input or silently coercing the value.

---

### User Story 2 - Ingest Precomputed Predictions Without Loading the Classifier (Priority: P1)

An integration owner supplies a versioned prediction/evidence JSON output and associated
source declarations. Safira validates and standardizes it without calling or loading the
original classifier. A precomputed adapter exposes only the already supplied values.

**Why this priority**: External model components may be accessible only through their
exported output contracts; lack of a live classifier must not force fabricated identity
verification or evidence.

**Independent Test**: Ingest synthetic outputs under different explicitly supported
source contracts and their versions, using retained exact registration metadata but no
live binding. Compare the
accepted values and declared provenance with equivalent live collection, while confirming
that the external provenance is not relabeled as verified live identity. Final admission
expectations depend on clarification C2 below.

**Acceptance Scenarios**:

1. **Given** a supported versioned output, compatible exact registration metadata and
   the provenance required by the approved admission policy, **when** it is ingested,
   **then** its source-qualified primary values and evidence are standardized without
   calling the original classifier or creating a live registry binding.
2. **Given** two sources containing equivalent primary values and evidence, **when**
   one is collected live and the other is ingested, **then** semantic values, label
   definitions and assessment associations agree while source mode and provenance
   assurance remain distinguishable.
3. **Given** malformed JSON, duplicate JSON member names, an unsupported schema version,
   non-finite or wrong-type numbers, ambiguous labels or contradictory identity fields,
   **when** ingestion is attempted, **then** no affected record is presented as valid
   and the failure is actionable and privacy-safe.
4. **Given** a precomputed adapter, **when** an available value is requested for the
   associated assessment and exact registered label, **then** it returns that supplied
   value; requesting another assessment, label or unavailable capability fails explicitly
   and never triggers inference, training or evidence fabrication.
5. **Given** missing or conflicting contributor identity evidence, **when** ingestion
   runs, **then** the uncertainty/conflict is explicit; a digest assertion or shared
   component version is never reported as verified live-model identity. Admission
   follows C1/C2 and cannot bypass Feature 001 validation.
6. **Given** equivalent predictions/evidence encoded in different explicitly declared
   source contracts with different field names or structures, **when** each is ingested
   using its own supported contract and version, **then** the standardized meanings and
   exact provenance are preserved without requiring either source to adopt the other's
   format. Unknown contract/version combinations fail explicitly.

---

### User Story 3 - Keep Component Contributors Independently Traceable (Priority: P2)

A researcher consumes one component output containing predictions from several
independently registered classifiers. Each contribution remains separately attributable,
even when multiple models predict the same label or have the same architecture.

**Why this priority**: A component's several output labels do not make its constituent
classifiers multi-label or make their predictions and safety evidence interchangeable.

**Independent Test**: Standardize synthetic all-single-label and mixed single/multi-label
components with different declared contributor counts, including overlapping label IDs
and two different versions of one model. Verify every intended contribution, its exact
source and component association without relying on disease labels or model families.

**Acceptance Scenarios**:

1. **Given** a component's declared set of independently registered single-label binary
   models, **when** their outputs are collected, **then** each requested contribution has
   one distinct source-qualified record sharing the component/assessment association
   while retaining its own definition. The outcome holds for different contributor counts;
   no particular count, algorithm or label naming convention is required.
2. **Given** a mixture of single-label and multi-label contributors with overlapping
   labels, **when** records are standardized, **then** none is merged, overwritten or
   attributed solely by label name; each exact model/version/label remains distinguishable.
3. **Given** only a component-level version and model family names, **when** contributor
   mapping is attempted, **then** exact individual classifier identities are not inferred.
   Missing provenance is reported according to C1/C2 rather than silently supplied.
4. **Given** missing contributors, conflicting duplicate contributions or mixed subject/
   assessment associations, **when** a component output is validated, **then** its
   incomplete/invalid state is explicit; it cannot be reported as a complete valid set.
   No source is silently omitted or replaced to achieve apparent completeness.

---

### User Story 4 - Inspect Evidence Availability Without Inferring Safety (Priority: P2)

A researcher inspects what evidence actually accompanies a prediction, what is absent
and why, and whether its meaning matches the primary output. Missing evidence does not
become a zero score, and primary confidence does not become a safety decision.

**Why this priority**: Honest evidence accounting prevents unsupported downstream
reliability claims and preserves research limitations.

**Independent Test**: Collect synthetic examples for every evidence category and state,
including an optional extraction exception and an explanation of an uncalibrated score
paired with a calibrated probability. Confirm meanings, absence reasons and safe errors.

**Acceptance Scenarios**:

1. **Given** an unsupported optional capability, **when** collection runs, **then** its
   method is not invoked and its evidence state is unsupported, with no invented value.
2. **Given** supported evidence that is absent, cannot currently be obtained, is invalid
   or raises an exception, **when** collection runs, **then** these cases are distinguished
   with safe reasons; an otherwise valid primary record may remain explicitly incomplete.
3. **Given** calibrated probabilities and explanations of a different declared output
   space, such as an uncalibrated probability or log-odds score, **when** evidence is
   standardized, **then** both meanings and their relationship are preserved without
   claiming the explanation targets the calibrated probability or establishes explanation
   stability. This applies regardless of explanation method, including SHAP where supplied.
4. **Given** completeness or cohort-scope metadata, **when** it is collected, **then**
   its supplied scope is retained without converting it into an OOD result, a diagnosis
   or a safety signal. Missing eligibility remains unknown, not implicitly eligible.
5. **Given** sensitive input or a failing external component, **when** validation or
   extraction fails, **then** routine logs/errors contain neither identifying patient
   content nor raw input/evidence payloads, and existing registrations remain unchanged.

### Edge Cases

- Two different models or versions produce the same label for the same patient and
  assessment; all sources remain distinct. A conflicting repeated source key does not
  silently overwrite an earlier record.
- Probability 0 or 1 is valid if the primary model supports continuous probabilities;
  Boolean values, numeric strings, NaN, infinity and values outside [0, 1] are not.
  Non-probability scores may be negative or unbounded as declared but must be finite.
- An output contains only a hard class, a third ground-truth class, an unknown label,
  or a different preprocessing/output mapping from its exact registration.
- A field is omitted, explicitly null, empty or structurally malformed; these cases are
  interpreted under the supported source contract, not guessed to mean measured zero.
- A source declares a capability unsupported but supplies purported evidence for it;
  the contradiction cannot silently upgrade the capability or the evidence's validity.
- A component-level input schema is a union of several models' inputs; a contributor's
  schema is not replaced by that union. Shared metadata is not assumed to describe every
  contributor unless its declared applicability says so.
- Top-feature explanations may contain feature names or observation values that require
  privacy protection. A truncated attribution list is not a complete attribution vector, whatever its length.
- A calibrated value and its explanation refer to different spaces; absent explanation
  space or target makes the evidence incomplete/invalid rather than silently comparable.
- Original raw input or domain metadata is absent in precomputed mode; neither may be
  reconstructed or inferred from probabilities or component labels.
- The external output has no patient/assessment identifier; an explicit trusted caller
  association is needed. Contradictory supplied associations must not be ignored.
- Reingesting the same output cannot be mistaken for stochastic repeated predictions;
  genuinely repeated outputs require their own provenance and compatible semantics.
- A source schema, exact contributor mappings or class mappings are unavailable;
  report that source's integration limitation without inventing fields or model versions.
- Different source contracts reuse the same version string or use unrelated field names
  and nesting. Contract identity and version together determine interpretation; neither
  a shared version nor a reference component's format authorizes guessing another format.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Safira MUST support live and precomputed collection for standalone
  supervised single-label binary classifiers, supervised multi-label classifiers with
  binary outcomes per label, and components containing independent eligible classifiers.
  A component's label count MUST NOT determine its contributors' task types. Eligibility
  MUST NOT depend on disease, algorithm, architecture, label names or a fixed number of
  contributing models beyond Feature 001's individual classifier task/cardinality rules.
- **FR-002**: Each standardized prediction MUST retain exact model ID, model version
  and label ID, plus an opaque patient association and assessment/collection occurrence
  association. Component-originated records MUST additionally retain component identity
  and its declared version. These identities MUST remain separate namespaces; no latest
  version fallback or identity inference from architecture/display names is allowed.
- **FR-003**: Accepted records MUST be compatible with an existing immutable Feature 001
  registration: binary label definitions, output selector and semantics, preprocessing,
  input declaration and adapter compatibility MUST agree wherever applicable. Unknown
  or conflicting identities/definitions MUST be reported explicitly. Ingestion MUST NOT
  create incomplete registrations, mutate definitions or relax registry validation.
- **FR-004**: Live collection MUST use the exact classifier-adapter association validated
  by Feature 001. Missing bindings, including after restart, MUST require verified exact
  reattachment before live prediction. Feature 002 MUST NOT replace or weaken the trusted
  IdentityProvider boundary or claim it proves arbitrary Python object origin.
- **FR-005**: Precomputed collection MUST work without the original classifier and MUST
  distinguish source assertions, independently checked provenance and live-binding
  verification. It MUST preserve what was checked, by whom/which trusted integration,
  what evidence supports that check and what remains unverified, without retaining
  patient data in routine provenance diagnostics. A supplied digest does not itself
  prove that an output was generated by the claimed classifier. Admission is subject to C2.
- **FR-006**: Component collection MUST associate each source output with its individual
  exact registered model/version/label and retain component-to-contributor provenance.
  Shared bundle/schema versions MUST NOT substitute for individual model versions or
  artifact identity. Required mapping authority and consistency checks are subject to C1.
- **FR-007**: Primary probabilities MUST be finite numeric values within [0, 1]; primary
  non-probability scores MUST be finite values within their declared domain, preserving
  meaning, direction and scale. Boolean/string coercion, silent clipping, conversion of
  scores to probabilities and normalization across independent labels are prohibited.
  Hard predictions alone MUST NOT replace required continuous primary values.
- **FR-008**: Existing Feature 001 label definitions and prediction-to-class mappings
  MUST be preserved. A supplied primary class, if present, MUST agree with its registered
  mapping. Feature 002 MUST NOT invent thresholds, derive them from patient values or
  substitute target-definition cutoffs for classifier decision rules. Behavior for
  probability-only sources lacking the required registered mapping is subject to C3.
- **FR-009**: Live inputs and supplied output/evidence structure MUST be validated against
  applicable declared schemas and requested source/label/assessment associations.
  Shape, type, output selection and declared modality mismatches MUST be explicit.
  Precomputed output with no raw input MUST state that input consistency could not be
  independently checked; it MUST NOT fabricate an input-validation result. This feature
  does not infer clinical plausibility from type validation.
- **FR-010**: Optional evidence MUST be collected only through supported existing adapter
  capabilities or explicitly supplied, compatible precomputed evidence. Supported
  categories include feature representations, repeated outputs, modality outputs and
  available modalities, explanations, input-quality metadata and domain metadata.
  Capability declarations describe potential support, not successful collection or
  measured safety signals. An external adapter MUST NOT inherit unsupported capabilities
  merely because the original model could have provided them.
- **FR-011**: Every applicable evidence category MUST distinguish available and validated,
  unsupported, missing, unavailable and invalid states with reasons. Unsupported means
  the source does not provide that capability; missing means expected/supported evidence
  was not supplied; unavailable means it cannot be obtained for this collection, including
  a failed extraction; invalid means a supplied value fails its evidence contract.
  None may be represented by fabricated zero, empty data presented as measured evidence,
  or a successful collection flag. Empty values are valid only when the declared evidence
  contract permits them. Review the partial-record policy at clarification.
- **FR-012**: Validated evidence MUST retain its contributing source and association,
  representation/meaning and applicable dimensions, feature/modality identifiers or
  repetition provenance needed to interpret it. Numeric evidence MUST reject non-finite
  values where numbers are expected. Unknown formats or mismatched lengths/sources MUST
  not be labeled validated. Repeated outputs MUST NOT be manufactured by duplicating a
  single value; modality agreement or uncertainty MUST NOT be computed here.
- **FR-013**: Explanations MUST retain the explained label/output, method and output
  space where supplied, including whether the explained output is calibrated. Unknown
  explanation semantics MUST be explicit. A truncated attribution list MUST retain that
  limitation. An explanation of an uncalibrated score MUST NOT be relabeled as explaining
  the calibrated probability, and explanations MUST NOT imply stability or safety.
- **FR-014**: Precomputed ingestion MUST accommodate different explicitly declared JSON
  source contracts, selecting each by its contract identity and version. It MUST validate
  that contract's required fields/types and source mappings and report unsupported
  contract/version combinations or ambiguous member names explicitly. It MUST NOT guess external field
  meanings or silently accept changed semantics. Source extensions MUST follow that
  contract's declared rules; arbitrary fields MUST NOT automatically enter contexts/logs.
  Ingestion MUST NOT require a source to use another component's field names, nesting
  or evidence layout. Concrete source mappings require that source's actual declared contract;
  integration summaries alone do not establish schema compatibility.
- **FR-015**: A precomputed adapter MUST expose supplied predictions/evidence through the
  existing ModelAdapter semantics for the associated assessment and exact labels, without
  inference or original-classifier access. Its capabilities MUST reflect what it can
  genuinely return. Unavailable capabilities and mismatched requests MUST fail explicitly.
  This adapter MUST NOT masquerade as the original live adapter or be attached under its
  immutable identity; external ingestion and live registry usable access remain distinct.
- **FR-016**: Records/evidence MUST NOT be reassigned across patients, assessments,
  collection occurrences or contributor versions. Where an external output lacks these
  associations, the caller MUST supply them explicitly; conflicts MUST fail validation.
  Real-world patient identifiers MUST NOT be required in order to collect evidence.
- **FR-017**: Within an assessment/collection occurrence, each model/version/label
  contribution MUST be unique. Conflicting duplicates MUST fail explicitly without
  overwrite. Separate occurrences MUST remain distinguishable; no merging of overlapping
  labels, fusion of model values or implicit deduplication into repeated evidence is allowed.
- **FR-018**: Patient inputs and potentially sensitive evidence MUST be handled only as
  needed for the requested collection. This feature MUST NOT persist patient predictions,
  raw inputs or evidence into registry metadata, routine logs, committed examples or new
  datasets. Errors MUST NOT echo patient identifiers, observations, feature values or
  arbitrary component exception text. Verification MUST use synthetic data exclusively.
- **FR-019**: Malformed primary predictions, invalid required associations and ambiguous
  envelope structure MUST prevent acceptance of the affected collection envelope; no
  partially validated result may be presented as complete. Optional evidence failures
  MUST be isolated and reported explicitly while retaining an otherwise valid primary
  record as incomplete, without synthesizing evidence. Exceptions MUST identify safe
  error categories and preserve earlier accepted records/registrations. This default
  partial-evidence policy is to be confirmed at clarification.
- **FR-020**: Feature 002 MUST reuse ModelAdapter, AdapterCapabilities and SafetyContext
  where their meanings fit, preserving existing behavior and SafetyAssessment unchanged.
  Contexts prepared for downstream use MUST retain source identity, value kind and
  evidence states; non-probability scores MUST NOT enter `prediction_probability`.
  Default context collections and its availability Booleans MUST NOT erase distinctions
  required by FR-011. No existing contracts may be rewritten merely for convenience.
- **FR-021**: Collection MUST NOT construct safety datasets, calculate the six safety
  dimensions, train safety models, calibrate reliability, select policies, generate
  reliability scores or TRUST/CAUTION/DEFER, diagnose or make clinical decisions. Existing
  primary calibration metadata may be retained without recalibration. Existing primary
  training pipelines, including AD/PD pipelines, and Feature 001 architecture MUST remain
  unchanged.
- **FR-022**: Verification MUST include automated pytest acceptance and regression tests,
  deterministic synthetic fixtures for all three configurations and both source modes,
  and clear exception cases. Equivalent input declarations and supplied outputs MUST
  produce reproducible standardization results; live inference need not be deterministic
  if the primary model is not. Existing adapter/context/registry tests MUST remain valid.
- **FR-023**: Declared target definitions, including research proxies, primary calibration
  declarations and
  supplied cohort/training-scope information MUST retain their original meaning and
  provenance. Missing scope MUST remain unknown. Training-scope membership MUST NOT be
  inferred as clinical eligibility or safety, and completeness MUST NOT be interpreted
  as validated sufficiency or OOD evidence. All outputs remain research artifacts.

### Key Entities

- **Prediction Record**: One primary continuous value for an exact model-version-label
  and patient/assessment occurrence, with declared semantics, optional class if verified
  against its mapping, source mode, provenance and evidence collection status.
- **Collection Association**: Opaque patient reference, assessment reference and occurrence
  identity linking values/evidence without embedding identifying patient information.
- **Component Contribution**: Component identity/version plus an explicit association
  to each exact independent classifier/version/label. It groups sources, not values or
  classifier task types, and identifies whether the expected set is complete. Its declared
  contributor set is not restricted to a particular size, disease or model architecture.
- **Evidence Item**: An optional source-associated value, evidence category, interpretation
  metadata, availability/validation state and safe absence/failure reason.
- **Source Provenance**: Source contract identity/version, source mode, contributor and adapter
  declarations, applicable artifact/output references and verification evidence/status.
  It distinguishes checking a declaration from verifying how a prediction was produced.
- **Precomputed Output**: An external versioned JSON record and separately supplied
  association/mapping declarations where required, validated without original-model access.
  Its layout follows its own explicitly declared source contract, not a fixed component
  example. Safira's internal concepts do not assert undocumented external field names.
- **Precomputed Adapter**: A view of accepted saved values through the existing adapter
  semantics; it is distinct from the original classifier's registry binding.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every valid synthetic acceptance case across the three configurations and
  two source modes preserves 100% of requested model/version/label identities, association
  references and primary-value meanings; no contribution is overwritten or substituted.
- **SC-002**: For paired live/precomputed cases with identical supplied values, all
  standardized semantic values and evidence states agree; reviewers can distinguish the
  source modes and assurance levels for every record without inspecting classifier code.
  Applicable precomputed admission cases will be finalized after C2.
- **SC-003**: Every listed malformed-value, schema, identity, association and duplicate
  category produces its specified rejection or explicit incomplete evidence outcome;
  zero invalid primary values or ambiguous contributor identities appear as valid records.
- **SC-004**: Synthetic cases cover every evidence category and all five states. Every
  unsupported capability has zero extraction calls, and no absent/invalid evidence is
  represented as a measured zero or an inferred safety signal.
- **SC-005**: Across synthetic components with different declared contributor counts and
  eligible classifier configurations, 100% of expected source-qualified predictions,
  target meanings and supplied cohort/training-scope provenance are preserved. Equivalent
  cases under different explicitly declared source contracts retain equivalent standardized
  meanings. Where calibration or explanations are supplied, their declared output spaces
  remain distinguishable; absent semantics/scope stay explicit. Zero class thresholds,
  eligibility claims or source-field meanings are invented. Success does not depend on
  any disease, label naming convention, model family or fixed contributor count.
- **SC-006**: Across all collection/ingestion cases, zero safety-training, reliability
  calibration, safety-signal computation, policy selection or safety-assessment operations
  occur; precomputed cases additionally perform zero original-classifier inference calls.
- **SC-007**: Synthetic privacy probes find zero patient identifiers, raw observations or
  sensitive evidence values in routine diagnostics or registry metadata. Existing Safira
  behavior passes regression verification without changing the established contracts.

## Assumptions

- Feature 001 registrations already exist and satisfy its immutable identity and mapping
  requirements. Their metadata can be read without a live binding; that alone never
  grants live usable access or verifies an external prediction's generation provenance.
- Collection is caller-initiated and returns research evidence for downstream use. No
  new persistence service, transport, authentication system, retention platform or patient
  dataset is specified. Callers supply opaque association references; organizational
  access control and reidentification mappings remain outside this feature.
- Both source modes preserve the same output/evidence meanings; they need not have equal
  provenance assurance or equal available evidence. No model must support all optional
  capabilities or all six future safety dimensions.
- Available evidence is validated against an explicit declared evidence contract; no
  universal embedding dimension, explanation algorithm, repeat count or modality list is
  imposed. Concrete evidence representations belong to clarification and later contracts.
- Collection requires no new patient's verified ground truth, no labelled safety dataset
  and no trained safety package. A successful collection is not safety readiness.
- Each external source supplies an explicitly declared contract and version for its own
  output structure. Supporting a source does not require other sources to use its layout
  or evidence categories. Source-specific mapping details remain subject to C1/C2.
- Source-reported clinical results, bundle files and hash assertions are not independently
  verified merely by reading an integration handoff. Only synthetic examples are used
  for this feature; a reference integration does not define general eligibility.

## Clarification Priorities Before Planning

These are intentionally deferred to the requested subsequent `$speckit-clarify` stage;
no answers have been assumed and no clarification questions were asked in this draft.

1. **C1 — Component/contributor mapping authority.**
   [NEEDS CLARIFICATION: Who supplies and validates the mapping from a component identity,
   version and output selector to each exact registered classifier/version/label when the
   external output has no per-model identity evidence?] The mapping may be supplied
   separately; it must not be inferred from the shared bundle version. This determines
   the acceptable provenance contract for FR-002/003/006 and US3.3.
2. **C2 — Precomputed provenance admission.**
   [NEEDS CLARIFICATION: May structurally valid registry-matched predictions with only
   claimed external provenance enter downstream evidence collection, or must independently
   checked producer/output provenance be supplied first?] Both paths must work without
   loading the original classifier and distinguish assertions from verified generation.
   This sets acceptance rules for FR-005/015, US2 and SC-002; no live-binding claim is allowed.
3. **C3 — Missing prediction-to-class mapping.**
   [NEEDS CLARIFICATION: Should probability-only outputs lacking a Feature 001-compliant
   registered class mapping be rejected entirely or returned only as clearly unlinked
   diagnostic input outside accepted downstream prediction records?] Accepted compatible
   records still require the existing registration. Supporting accepted mapping-free
   records would need a separate approved Feature 001 contract amendment. The PD handoff
   does not resolve this requirement, and no threshold may be invented.
4. **Missing/invalid optional evidence:** confirm the FR-011/019 default of retaining a
   valid primary prediction with explicit incomplete evidence, while rejecting invalid
   primary values/associations. Confirm whether any consumer-required evidence changes
   acceptance; no automatic safety policy is implied.
5. **Association and evidence detail:** confirm caller responsibility for opaque subject/
   assessment/occurrence references when absent externally, and the minimal supported
   evidence structures. Review each actual source contract before binding its field
   mappings; the unavailable PD schema is one example of this source-specific dependency.

## Acceptance Traceability

| Requirements | Acceptance scenarios / outcomes |
|---|---|
| FR-001–004, FR-007–009 | US1.1–5, US3.1–2; SC-001/003/005; arbitrary eligible classifiers and contributor counts; C3 controls mapping-free diagnostics. |
| FR-005, FR-014–015 | US2.1–6; SC-002/003/005/006; distinct declared source contracts; C1/C2 gate provenance admission. |
| FR-002/006/016–017 | US2.4–5, US3.1–4; SC-001/003/005. |
| FR-010–013, FR-023 | US4.1–4; SC-004/005. |
| FR-018–020 | US1.3–5, US2.3–4, US4.2/5; SC-003/007. |
| FR-021–022 | All stories; SC-001–007; synthetic automated acceptance and existing-contract regression evidence required. |

## Out of Scope

Safety dataset construction, six-signal computation, automatic model-specific safety
training, Safira reliability calibration or policy selection, reliability scores,
TRUST/CAUTION/DEFER generation, clinical decision-making, diagnosis, primary pipeline
training/calibration changes, clinical threshold selection, classifier fusion, changing
registry architecture or identity validation, and building a new patient database or
transport service. Safira remains a research prototype, not a clinically validated
medical device. This draft authorizes no implementation or technical planning.


## Integration Reference and Optional Example (Non-normative)

The following PD Co-Pathology reference illustrates the general requirements; it does
not define Feature 002's architecture, eligible algorithms, label names, evidence methods,
source contract layout or contributor count. Its unavailable schema affects only claims
of direct compatibility with that source, not the definition of generic ingestion.

The supplied `C:/Users/User/Downloads/PD Copathology Handoff.md`, dated 2026-10-16,
describes three independent binary models: PD-type Random Forest, AD-like elastic-net
logistic regression, and vascular-risk Random Forest. They produce one versioned
component output. Model family names and that output's shared version do not identify
the exact contributing classifier artifacts or their compatible adapters.

The handoff names `docs/output_schema_v1.json` and `docs/output_schema.md`, but neither
was found in the available NeuroSage workspace or Downloads. This specification has
not verified their actual field nesting, required fields, types or null rules. It does
not invent them or claim direct PD schema compatibility. The external schema and
synthetic conforming examples are prerequisites for a concrete PD ingestion contract.
The handoff is integration evidence, not authorization to change primary pipelines.

Handoff-documented output names are `schema_version` (reported as 1.0), `model_version`
(`pd-copathology-v1.0`), and per-signal `probability`, `model`, `calibration`,
`target_definition`, `cohort_in_training_scope`, `shap_space`, `shap_explains`, and
`top_features`, plus `data_quality` completeness and a disclaimer. The labels are
`pd_type_v1`, `ad_like_v1`, and `vascular_v1`. No subject/assessment linkage field,
per-classifier artifact digest or prediction-to-class threshold is established by
this summary. Additional Safira association/provenance requirements below are internal
requirements or separately supplied integration declarations, not alleged PD fields.

A synthetic PD-like example may illustrate three independent binary contributors,
research-proxy target meanings, supplied cohort scope, calibrated probabilities and
SHAP in uncalibrated output spaces. It supplements the generic acceptance cases in
SC-005; it is not required for general success and does not establish actual PD schema
compatibility. No clinical data, real-model threshold or undocumented field is invented.
