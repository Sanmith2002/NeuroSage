# Feature Specification: Research-Only Synthetic Runtime Safety Assessment

**Feature Branch**: `feature-08/Runtime-Safety-Assessment`  
**Created**: 2026-10-22  
**Status**: Completed — independently adversarially verified; closed within approved synthetic-only research-software scope.
**Input**: Approved synthetic-only internal simulation of a compatible Feature 007 selected-but-unevaluated policy.

## User Scenarios & Testing

### User Story 1 - Admit one synthetic prediction and frozen package (Priority: P1)

A Safira researcher runs an internal test fixture containing one synthetic prediction and its compatible frozen estimator, calibrator, selected policy, original reference provenance, and trusted test verification. The simulation admits the complete bundle for one exact classifier, version, label, and assessment association before deriving any result.

**Why this priority**: Applying frozen methods to an incorrectly admitted prediction or mismatched package would produce a misleading result even in a research simulation.

**Independent Test**: Synthetic fixtures exercise exact and altered prediction, scope, origin, protocol, reference, estimator, calibrator, and policy bindings. Exact inputs pass; missing, forged, or incompatible shared evidence produces only a safe non-success.

**Acceptance Scenarios**:

1. **Given** an exact synthetic prediction and complete authorized fixture evidence, **When** admission runs, **Then** prediction association and `(model_id, model_version, label_id)` are independently verified before scoring.
2. **Given** any missing, forged, stale, or cross-scope input, **When** admission runs, **Then** no assessment status is accepted and no partial scope result is returned.

### User Story 2 - Apply the frozen research package (Priority: P1)

A researcher applies the original Feature 004 signal definitions and reference state, frozen Feature 005 estimator, Feature 006 calibration mapping, and Feature 007 cutoff to the admitted synthetic prediction. The run performs no fitting, recalibration, cutoff selection, or protected-test access.

**Why this priority**: This is the core question of whether the already frozen components can be composed consistently in a deliberately limited synthetic simulation.

**Independent Test**: Known synthetic records produce the expected intermediate parity and policy-boundary status; altered schemas, reference digests, mappings, or cutoff semantics are rejected. Tests verify runtime observations never enter reference fitting.

**Acceptance Scenarios**:

1. **Given** a valid synthetic prediction and exact frozen package, **When** the simulation completes, **Then** it applies the supported calibrated correctness score against the policy's single frozen cutoff and comparison rule, mapping a score that satisfies the stored comparison to `TRUST` and a valid score that does not satisfy it to `CAUTION`.
2. **Given** required evidence, compatibility, authorization, or readiness is absent or invalid, **When** the simulation runs, **Then** it returns `DEFER` with a safe reason and no numeric score.
3. **Given** any runtime query, **When** Feature 004 reference signals are derived, **Then** only previously verified original training evidence can contribute to the frozen reference; the query is never fitted or used to alter the reference.

### User Story 3 - Inspect a bounded simulation result (Priority: P2)

A researcher receives an immutable internal result that preserves exact scope and association binding while clearly identifying the execution as synthetic-only, non-deployable, and based on a policy that remains unevaluated. The result exposes no raw patient content or per-patient score.

**Why this priority**: Status semantics must remain reviewable without making a test result look like an authorized clinical assessment.

**Independent Test**: Inspect success and failure result fields, serialized content, representations, logs, and exceptions. Verify exact-scope ordering, lifecycle markers, absence of patient-level payload, and no public `SafetyAssessment` or general runtime API.

**Acceptance Scenarios**:

1. **Given** a successful synthetic simulation, **When** its internal result is inspected, **Then** it is marked `SYNTHETIC_TEST_ONLY`, exact-scope bound, `SELECTED_UNEVALUATED`, non-deployable, not independently evaluated, and not clinically validated.
2. **Given** a failed or deferred simulation, **When** its result or error is inspected, **Then** it contains only allowlisted scope metadata and safe reason codes, with no patient, group, assessment, raw target, evidence payload, or individual score.
3. **Given** a request to use real patient data or to publish/serialize an assessment through the public `SafetyAssessment` contract, **When** it reaches this feature, **Then** the operation is unavailable.

### Edge Cases

- Incomplete or forged Feature 002 admission, incomplete inventory, mismatched association, unknown registry identity, altered artifact origin, or a stale policy authorization fails shared admission atomically.
- A frozen artifact, protocol, method version, preprocessing identity, or fitted reference digest is mismatched; shared verification rejects atomically before scoring. A validly admitted query lacks a required runtime measurement; return `DEFER` without substituting a signal or refitting.
- A valid, explicitly optional signal is missing or unsupported; existing frozen estimator behavior governs it. A required signal that cannot be represented by the frozen schema defers safely.
- A query has non-finite or malformed values, unexpected feature dimensions, duplicate evidence categories, or unavailable explanations; reject or defer according to the existing signal state contract and never fabricate explanation content.
- The calibrated value equals the cutoff; use the policy's stored inclusive/exclusive comparison exactly.
- Two exact scopes are simulated in separate calls; keep prediction associations and all artifacts independent, with no pooling or substitution.
- A verifier, scorer, or serializer raises an unexpected programming exception; do not silently reinterpret it as an ordinary `DEFER`.
- An attempted protected final-test read, correctness-target construction, fitting, recalibration, or threshold selection is outside the workflow and must not occur.

## Requirements

### Functional Requirements

- **FR-001**: The feature MUST be limited to internal synthetic research/testing execution and MUST NOT accept real patient data or expose a general patient-data runtime assessment API.
- **FR-002**: The feature MUST use an independently verified Feature 002 prediction with its exact assessment association and exact `(model_id, model_version, label_id)` identity.
- **FR-003**: The feature MUST require exact Feature 001 registry compatibility for the registered classifier, adapter, version, preprocessing identity, and label.
- **FR-004**: A trusted host/test verifier MUST verify prediction admission, estimator and calibrator origin, policy origin and authorization, exact artifact scope, and complete original Feature 003/004 reference provenance before scoring. Caller assertions, Boolean flags, digests alone, and locally constructed receipts MUST NOT establish trust.
- **FR-005**: The feature MUST reconstruct or obtain the exact approved Feature 004 reference using only independently verified original training evidence and MUST match the frozen reference identity required by the artifacts.
- **FR-006**: Runtime signal rows MUST be privately derived from the admitted prediction; caller-supplied signal rows MUST NOT be accepted.
- **FR-007**: Runtime observations MUST NOT enter reference fitting. The workflow MUST NOT train the primary classifier, construct correctness targets, fit an estimator, recalibrate, or select or modify a cutoff.
- **FR-008**: The feature MUST apply only Feature 004 method versions, evidence schemas, preprocessing identities, modality semantics, and missingness behavior approved for the exact frozen Feature 005 schema.
- **FR-009**: The feature MUST reconstruct and apply only the exact frozen Feature 005 estimator schema, preprocessing, family, and score semantics, without fitting or changing any state.
- **FR-010**: The feature MUST verify that the Feature 006 calibrator binds to the exact Feature 005 artifact and apply only its approved frozen mapping with finite numerical results.
- **FR-011**: The feature MUST apply only an independently authorized Feature 007 `SELECTED_UNEVALUATED` policy whose origin, exact scope, estimator/calibrator digests, cutoff, and comparison semantics match the submitted frozen package.
- **FR-012**: For a valid synthetic query, the feature MUST map a calibrated score satisfying the policy comparison at its cutoff to `TRUST`, and a valid score that does not satisfy it to `CAUTION`, including equality according to the stored comparison, without adding thresholds or changing the policy.
- **FR-013**: A forged, unverified, unauthorized, or cross-scope shared input MUST fail atomically with a safe error and no result. For a fully admitted bundle, a missing, unavailable, unsupported-required, invalid, incompatible, or not-ready runtime measurement MUST produce `DEFER` with an allowlisted reason and no score. An explicitly optional missing value MAY proceed only through its already frozen Feature 005 missingness behavior. No case may fabricate evidence or become a reassuring status.
- **FR-014**: The feature MUST emit only a new immutable internal result marked `SYNTHETIC_TEST_ONLY`, `SELECTED_UNEVALUATED`, non-deployable, not independently evaluated, and not clinically validated. It MUST NOT modify or project through the existing public `SafetyAssessment` contract.
- **FR-015**: Results, representations, diagnostics, serialization, and safe exceptions MUST exclude raw patient/group/assessment identifiers, targets, individual scores, restricted evidence, and protected content. An internal association binding MUST use a non-reversible fingerprint where retained.
- **FR-016**: The workflow MUST preserve exact-scope isolation for model, version, label, association, estimator, calibrator, policy, and runtime evidence; it MUST NOT pool or substitute any of them.
- **FR-017**: Explanation availability and metadata MUST reflect only independently admitted Feature 002 evidence and existing `AdapterCapabilities`; the feature MUST NOT create or infer explanation content.
- **FR-018**: The feature MUST NOT access the protected final-test partition, claim independent policy evaluation or future-risk guarantees, make clinical-validity claims, or authorize clinical deployment.
- **FR-019**: The feature MUST reuse existing `ModelAdapter`, `AdapterCapabilities`, registry, prediction, signal, and frozen artifact contracts where they fit. Any proposed existing-contract change requires separate approval and compatibility tests.
- **FR-020**: Tests MUST use synthetic fixtures only and MUST precede the implementation they validate in each implementation batch.

### Key Entities

- **Synthetic Runtime Input**: One synthetic, independently admitted prediction record, its exact association and source scope, and verified frozen package references.
- **Verified Runtime Bundle**: The exact registry identity, Feature 002 admission, original Feature 003/004 reference provenance, Feature 005 estimator, Feature 006 calibrator, Feature 007 policy, and executed trusted checks.
- **Internal Research Assessment Result**: Immutable exact-scope status, non-reversible association binding, safe reason code, artifact digests, and synthetic-only/unevaluated lifecycle markers; excludes the calibrated score and raw evidence.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Synthetic admission tests accept every exact fixture and reject every altered prediction, scope, origin, provenance, and authorization case before scoring.
- **SC-002**: Synthetic parity and boundary tests reproduce the approved frozen signal, estimator, calibrator, and cutoff behavior for every supported package family and cutoff equality rule.
- **SC-003**: A complete synthetic adversarial matrix yields only the expected `TRUST`, `CAUTION`, `DEFER`, or safe rejection outcomes; no case exposes a numeric score or private input.
- **SC-004**: Tests verify zero fitting on runtime observations, zero protected final-test access, zero training/recalibration/cutoff-selection operations, and unchanged Features 001–007 public contracts.
- **SC-005**: Serialization and exception inspection of every synthetic success/failure result finds no patient/group/assessment identifiers, raw targets, individual scores, restricted evidence, or protected data.

## Assumptions

- The approved boundary is synthetic fixture execution in an internal research/testing path, with no public runtime API and no use of `SafetyAssessment`.
- Feature 007 remains `SELECTED_UNEVALUATED`. Synthetic status application demonstrates only software behavior and conveys no independent policy performance evidence.
- The trusted provider is injected by the test/research host. Test doubles can demonstrate contract behavior but cannot authenticate a hostile Python host or substitute for production trust infrastructure.
- Original verified Feature 003 training evidence and Feature 004 protocol/manifests needed for exact reference reconstruction must be supplied by an authorized test fixture. If unavailable, execution defers or rejects safely.
- Independent policy evaluation, protected final testing, clinical validation, production patient-data access, persistence/custody, and deployment are future separately authorized work.
