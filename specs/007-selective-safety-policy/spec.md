# Feature Specification: Selective Safety Policy

**Feature Branch**: `feature-07/Selective-Safety-Policy-SDD`
**Created**: 2026-10-22
**Status**: Completed — adversarially verified; closed within approved research-software scope.
**Input**: User-approved Feature 007 scope and methodology decisions A–E, with Feature 006 closure at `12d1dc656e6f54f76e154d67372002bf20e439a6` as the starting point.

## User Scenarios & Testing

### User Story 1 — Admit independent policy evidence (Priority: P1)

A research owner supplies a frozen Feature 005 estimator, its Feature 006 calibrator, and a new independently authorized Feature 003 evidence build. Safira verifies exact scope, source admission, provenance, patient disjointness, and compatibility before using any correctness outcomes. It privately derives scores from the frozen artifacts; it does not call the primary classifier or expose a patient-level scoring API.

**Why this priority**: Policy selection is invalid if any evidence, model identity, fitted state, or patient-group relationship is unverified. This gate prevents spent or protected partitions from entering the policy workflow.

**Independent Test**: Submit synthetic bundles with exact and altered artifact/evidence bindings. Exact, independently verified bundles pass the admission gate; forged, incomplete, overlapping, spent, or incompatible bundles fail before outcome-derived selection work begins.

**Acceptance Scenarios**:

1. **Given** a frozen exact-scope Feature 005 artifact, a compatible Feature 006 calibrator, verified original Feature 003/004 training provenance, and a new patient-disjoint policy-selection build, **When** the research owner requests policy selection, **Then** every exact prediction and feature row is checked and internal scores are derived only after admission.
2. **Given** an altered manifest, prediction, row alignment, original fitted-reference digest, estimator artifact, calibrator, or model/version/label identity, **When** admission is attempted, **Then** the workflow fails closed without producing a policy or revealing sensitive values.
3. **Given** a policy dataset that overlaps any upstream development or protected final-test patient group, **When** admission is attempted, **Then** the workflow rejects it or returns `NOT_READY` when authoritative linkage evidence is unavailable.
4. **Given** Feature 005 validation, Feature 006 calibration, or protected final-test evidence offered as policy-selection evidence, **When** admission is attempted, **Then** the workflow rejects the evidence as spent or restricted.

### User Story 2 — Select an empirical TRUST operating point (Priority: P1)

A research owner defines a versioned protocol before correctness outcomes are examined. The protocol names each exact model/version/label scope, the patient-level index-assessment and eligibility rule, the empirical risk ceiling, and deterministic cutoff/tie rules. Safira selects the greatest observed patient coverage whose empirical selective error risk satisfies that ceiling.

**Why this priority**: It turns the frozen correctness estimator and calibration mapping into a traceable, evidence-derived research policy without inventing a cutoff or claiming a statistical guarantee.

**Independent Test**: Use synthetic, independently verified patient-level examples with predetermined score and correctness orderings; recompute empirical risk and coverage and confirm the chosen cutoff is the deterministic maximum-coverage feasible candidate.

**Acceptance Scenarios**:

1. **Given** a ready protocol, admitted nonempty evidence, and at least one feasible nonempty selected set, **When** candidate cutoffs are evaluated, **Then** the cutoff maximizes eligible-patient coverage subject to the approved empirical ceiling.
2. **Given** a candidate cutoff, **When** results are calculated, **Then** empirical risk is incorrect TRUST-selected eligible index-assessment patients divided by TRUST-selected patients, and coverage is TRUST-selected patients divided by all eligible patients.
3. **Given** equal scores or multiple cutoffs yielding the same selected set, **When** the selection rule is applied, **Then** the protocol's predeclared equality and deterministic tie rules select one reproducible cutoff.
4. **Given** zero patients selected by a candidate, **When** risk is calculated, **Then** risk is marked undefined and no zero-risk claim or successful empty-set policy is emitted.
5. **Given** a constant calibrated score, **When** the empirical ceiling is evaluated, **Then** only an all-or-none TRUST choice is considered; a nonempty choice is permitted only if it meets the ceiling and all support rules, otherwise the scope receives a safe non-success outcome.
6. **Given** multiple labels, contributors, or model versions, **When** candidates are evaluated, **Then** every result is scoped independently and no scores, outcomes, or support counts are pooled.

### User Story 3 — Freeze and inspect a selected policy artifact (Priority: P2)

A research owner receives an immutable, versioned record of a selected but unevaluated policy, its exact scope, protocol, threshold semantics, empirical selection results, and the distinct provenance of the estimator/calibrator and policy-selection cohort.

**Why this priority**: A reproducible policy record is needed for later independent evaluation, while its lifecycle must not be mistaken for a validated or deployable package.

**Independent Test**: Freeze and serialize synthetic successful and non-success outcomes; verify exact compatibility, deterministic digests, defensive immutability, separated provenance, and absence of patient-level or restricted values.

**Acceptance Scenarios**:

1. **Given** a successful nonempty cutoff selection, **When** a policy artifact is frozen, **Then** it records exact model/version/label, estimator and calibrator digests, original training/calibration provenance, policy evidence provenance, protocol/configuration, equality/tie semantics, empirical selection metrics, and an unevaluated/non-deployable lifecycle.
2. **Given** a caller modifies an original input or a returned serialized value, **When** the accepted artifact is inspected again, **Then** its content and digest remain unchanged.
3. **Given** a scope without valid protocol, independent evidence, artifact origin, compatible reference state, or feasible nonempty selection, **When** the workflow completes, **Then** it returns a typed safe non-success without an artifact.
4. **Given** ordinary artifact serialization or diagnostics, **When** inspected in full, **Then** patient/group/occurrence identifiers, outcomes, per-patient scores, protected rows, restricted manifests, raw evidence, and verification payloads are absent.

### User Story 4 — Preserve policy lifecycle and evaluation boundaries (Priority: P2)

A research owner can distinguish policy construction and empirical cutoff selection from policy freezing, later independent evaluation, and any future runtime application. Selection evidence is marked spent, and protected final-test evidence remains unavailable.

**Why this priority**: Passing software checks or satisfying a selection-cohort empirical criterion does not demonstrate independent performance, clinical validity, or readiness for runtime use.

**Independent Test**: Inspect policy lifecycle records, serializers, and workflow boundaries; verify selection cannot access protected rows, cannot promote a policy to evaluated/deployable, and cannot expose a per-patient application method.

**Acceptance Scenarios**:

1. **Given** a frozen policy selected on the approved cohort, **When** its lifecycle is inspected, **Then** it is labeled selected/unevaluated, the selection cohort is spent, and independent final evaluation remains a separate later workflow.
2. **Given** a request to evaluate or apply the policy to a patient, **When** it reaches Feature 007, **Then** no such Feature 007 operation is available; future evaluation and runtime work remain outside this feature.
3. **Given** a policy-selection workflow, **When** its inputs and outputs are inspected, **Then** protected final-test content is never read, serialized, logged, or used to tune a threshold.

### Edge Cases

- Trusted verification, provenance, patient-linkage, source-inventory, or prior-history evidence is missing, stale, partial, or inconsistent: reject or return `NOT_READY`; never infer disjointness.
- A Feature 005 or Feature 006 artifact is valid in isolation but its origin, scope, registry compatibility, dependency/schema state, or original Feature 003/004 provenance cannot be independently verified: no score reconstruction occurs.
- Original Feature 003 training evidence needed to deterministically reproduce a Feature 004 reference state is unavailable, or its reconstructed digest differs: return `NOT_READY`/incompatible; do not replace the reference or weaken matching.
- Policy signals use a changed Feature 004 method, preprocessing, reference state, row key, or source-qualified identity: reject them.
- A patient has no eligible index assessment, multiple candidate assessments with no approved deterministic rule, or unresolved cross-source linkage: exclude only if the approved protocol permits, otherwise return a safe non-success.
- A patient has repeated eligible records: use only the predeclared patient-level index-assessment rule; never count repeated visits as independent patients.
- A correctness outcome is conflicting, unavailable, unverified, or not bound to the exact registered prediction and target definition: the row is not eligible.
- No cutoff satisfies the empirical ceiling with a nonempty selected set: return an explicit non-success; do not call an empty set zero risk.
- Scores are constant: do not fabricate ranking or a threshold; consider only the protocol-authorized all-or-none set.
- Equal score values straddle a requested cutoff: use the protocol's fixed inclusive/exclusive equality rule consistently.
- Different thresholds yield the same selected set: apply the protocol's predeclared tie rule.
- Any final-test artifact or protected receipt appears in an ordinary request: reject it without inspecting protected content.
- An unexpected exception occurs: return a privacy-safe stable reason code without patient identifiers, raw values, or upstream exception text.

## Requirements

### Functional Requirements

- **FR-001**: The feature MUST operate independently for each exact `(model_id, model_version, label_id)` scope and MUST NOT pool scores, correctness targets, adequacy, or policy parameters across scopes.
- **FR-002**: The feature MUST derive each policy-selection correctness target only from independently verified Feature 003 ground truth bound to the exact patient, assessment, prediction, label, and target definition; correctness MUST compare the registered primary predicted class with the verified class mapping.
- **FR-003**: The feature MUST accept only a new, independently authorized Feature 003 build whose validation partition was reserved exclusively for policy selection by a versioned protocol before correctness outcomes were examined.
- **FR-004**: The feature MUST verify the complete policy evidence inventory and independently verified Feature 002 admission lineage for every prediction before using any policy-selection outcome, and MUST derive its Feature 004 rows from those admitted predictions rather than trust caller-constructed signal rows.
- **FR-005**: The feature MUST verify that policy-selection patient groups are disjoint from upstream estimator-development and calibration evidence and from protected final-test groups using authorized, scope-complete linkage/history evidence; unknown overlap MUST NOT count as disjoint.
- **FR-006**: The feature MUST reject reuse of Feature 005 validation evidence spent on estimator selection, Feature 006 calibration evidence spent on calibration fitting, and protected final-test evidence.
- **FR-007**: The feature MUST preserve original Feature 005/006 artifact provenance separately from the new policy-selection dataset, protocol, manifest, and inventory provenance.
- **FR-008**: Before private score reconstruction, the feature MUST verify Feature 005 and Feature 006 artifact content, independently checked origin, exact model/version/label identity, Feature 001 registration/adapter compatibility, and all original Feature 003/004/schema/preprocessing/fitted-reference bindings.
- **FR-009**: Any reconstructed Feature 004 reference state MUST use only the original independently verified Feature 003 training partition, reproduce the exact fitted-state digests required by the frozen artifacts, and be applied without refitting on policy-selection records. Failure to reproduce exact state MUST fail closed.
- **FR-010**: Policy-selection scores MUST be derived from the exact frozen Feature 005 schema, preprocessing, estimator, and Feature 006 mapping. The primary classifier MUST NOT be called, and upstream artifacts MUST NOT be modified.
- **FR-011**: The scoring bridge MUST remain private to Feature 007. The feature MUST NOT expose per-patient calibrated scores, a public estimator inference API, a public calibrated-score API, `SafetyContext`/`SafetyAssessment` application, or runtime clinical decisions.
- **FR-012**: A versioned, approved protocol MUST define the exact scopes, eligible population, one deterministic index assessment per patient and scope, empirical risk ceiling, score interpretation, candidate cutoff set, score equality behavior, tie-breaking, support rules, reproducibility settings, and non-success behavior before outcomes are examined.
- **FR-013**: For candidate cutoff `t`, TRUST selection MUST use the protocol-declared score comparison. The default V1 candidate semantics MUST be `score >= t` only when explicitly fixed by the approved protocol.
- **FR-014**: For each exact scope and candidate cutoff with a nonempty selected set, empirical selective risk MUST equal the number of incorrect TRUST-selected eligible patient index assessments divided by the number of TRUST-selected eligible patients.
- **FR-015**: For each exact scope and candidate cutoff, empirical patient coverage MUST equal the number of TRUST-selected eligible patients divided by all eligible policy-selection patients in that scope.
- **FR-016**: The selected operating point MUST maximize observed eligible-patient coverage among candidate cutoffs satisfying the preapproved empirical risk ceiling and support criteria, using deterministic protocol-declared tie rules.
- **FR-017**: Empirical policy-selection risk and coverage MUST be described only as selection-cohort results. They MUST NOT be presented as statistical guarantees, independent performance estimates, clinical thresholds, or clinical safety claims.
- **FR-018**: If no patients are TRUST-selected, risk MUST be represented as undefined and the feature MUST NOT create a successful zero-risk policy.
- **FR-019**: A constant calibrated score MUST NOT be represented as patient ranking. Only an all-or-none TRUST set may be considered; a nonempty set is permitted only if it meets the approved empirical ceiling and all support criteria, otherwise the exact scope MUST return an explicit non-success.
- **FR-020**: A successful policy MUST use one fitted TRUST cutoff; valid below-cutoff cases MUST map to CAUTION, while invalid, unavailable, incompatible, or not-ready inputs MUST map to DEFER. The feature MUST NOT fit a second cutoff.
- **FR-021**: Missing trusted evidence, protocol approval, patient disjointness proof, compatible original reference state, artifact origin, or a feasible supported policy MUST result in `NOT_READY`, `INSUFFICIENT_EVIDENCE`, or another typed safe non-success, never a fabricated value or policy.
- **FR-022**: Policy construction, cutoff selection, policy freezing, independent policy evaluation, and future runtime application MUST be represented as distinct lifecycle stages. Feature 007 MUST stop at selection and freezing of a selected-but-unevaluated artifact.
- **FR-023**: A successful policy artifact MUST be immutable and versioned and MUST bind exact scope, registry identity, Feature 005 estimator, Feature 006 calibrator, original Feature 003/004 provenance, policy evidence provenance, protocol, cutoff semantics, selection results, implementation/dependency versions, and lifecycle limitations.
- **FR-024**: A policy artifact MUST mark policy-selection evidence as spent, independent final evaluation as incomplete, protected-test access as false, and deployment/clinical validation as not established.
- **FR-025**: Ordinary APIs, errors, logs, and serialized artifacts MUST exclude patient identifiers, group keys, occurrence/assessment identifiers, individual correctness outcomes, per-patient scores, raw evidence, restricted manifests, protected-test contents, and verifier payloads.
- **FR-026**: Cross-scope or cross-version reuse of an estimator, calibrator, signal state, threshold, or policy MUST be rejected unless exact approved compatibility is independently established for the same scope.
- **FR-027**: The feature MUST preserve public Features 001–006 contracts and must not change the existing adapter, assessment, dataset, signal, training, or calibration behavior.
- **FR-028**: The feature MUST provide deterministic same-environment policy selection for unchanged admitted evidence and protocol and record enough non-sensitive provenance to reproduce the selection.
- **FR-029**: The feature MUST use synthetic fixtures to test positive, negative, leakage, replay, compatibility, lifecycle, privacy, and no-protected-data-access behavior; it MUST NOT use real patient data in tests or committed fixtures.
- **FR-030**: The feature MUST construct policy Feature 004 signal rows using the original approved method configuration and exact reconstructed original training references, verify one-to-one prediction/row alignment, and reject caller-supplied or forged rows as trusted evidence.

### Approved Methodology Decisions

1. **Objective**: Maximize empirical patient-level TRUST coverage subject to a protocol-preapproved empirical selective-error-risk ceiling. This is an empirical selection rule only, not a statistical or clinical guarantee.
2. **Patient unit**: One independently verified patient contributes one deterministic, protocol-defined eligible index assessment per exact scope. Eligibility and index selection are fixed before correctness outcomes are examined.
3. **Policy mapping**: One TRUST cutoff; valid below-cutoff cases are CAUTION; invalid, unavailable, incompatible, or not-ready cases are DEFER. No second fitted cutoff.
4. **Evidence lifecycle**: Use the validation partition of a new, independently authorized, patient-disjoint Feature 003 build reserved exclusively for Feature 007 policy selection. Feature 005 validation, Feature 006 calibration, and protected final-test evidence are unavailable. Policy-selection evidence becomes spent.
5. **Cutoff selection**: Evaluate only deterministic candidate cutoffs allowed by the frozen protocol; select maximum feasible coverage under the empirical ceiling. Equality and tie handling are fixed before outcome access. An empty TRUST set has undefined risk and is not successful.
6. **Constant scores**: A constant calibrated score has no ranking and allows only an all-or-none choice; a nonempty choice must meet the protocol ceiling and support criteria. Otherwise report safe non-success.
7. **Private scoring bridge**: Feature 007 may privately verify frozen Feature 005/006 artifacts, reproduce the exact Feature 004 training-reference state from the independently verified original training partition, verify matching frozen digests, then apply the unchanged Feature 005 preprocessing/estimator and Feature 006 mapping to authorized new policy evidence. It must not refit on policy records, expose individual scores, modify upstream artifacts/contracts, forge provenance, or provide public patient inference.
8. **Readiness**: Missing independent evidence, verified origin, required original training inputs, exact state reproduction, compatible schema, or approved protocol means `NOT_READY` or another appropriate non-success. No numerical ceiling, support minimum, or patient eligibility rule is supplied by this specification; an approved protocol must provide them.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Synthetic admission tests show that every policy prediction, outcome, source association, internally generated Feature 004 row, model/version/label scope, and original artifact/reference binding is checked before outcome-derived selection; caller-forged rows are not accepted and each single-field mutation is rejected or produces `NOT_READY`.
- **SC-002**: Synthetic linkage tests prove that all patients with verified prior development/calibration/protected membership are excluded from policy evidence, and unresolved linkage or incomplete authoritative history never yields a disjointness claim.
- **SC-003**: For each synthetic exact scope, independently recomputed empirical risk/coverage and deterministic cutoff selection match the service result exactly, including score equality, ties, empty selection, and constant-score cases.
- **SC-004**: Repeated same-environment runs with unchanged admitted evidence and protocol produce identical selected policy contents and digest; changing any approved protocol field or source evidence changes the appropriate identity or rejects the bundle.
- **SC-005**: Tests confirm that policy evidence cannot change the Feature 004 reference fit, Feature 005 preprocessing/estimator, or Feature 006 calibration mapping; original reference reconstruction uses only verified original training rows and its state digests match exactly.
- **SC-006**: Full ordinary API and serialization inspection finds no patient/group/occurrence identifiers, outcomes, per-patient scores, raw evidence, restricted manifest contents, protected data, or verifier payloads.
- **SC-007**: The successful output is labeled selected-but-unevaluated and non-deployable, marks policy-selection evidence spent, and makes no statistical guarantee, independent final-performance, clinical validity, or deployment-readiness claim.
- **SC-008**: The verified workflow performs no read of protected final-test rows or outcomes and offers no public per-patient inference or runtime assessment operation.
- **SC-009**: Existing Features 001–006 regression tests pass unchanged, and all new acceptance tests use synthetic records only.

## Key Entities

- **PolicySelectionProtocol**: Versioned, approved exact scopes, risk ceiling, eligibility and index-assessment rule, candidate cutoff semantics, support requirements, deterministic tie/equality policy, evidence provenance, and readiness rules.
- **PolicyEvidenceReference**: New Feature 003 dataset, protocol, manifest, validation partition, complete inventory, independent source admission, and cross-source patient-disjointness evidence.
- **VerifiedFrozenInputs**: Exact Feature 005 estimator, Feature 006 calibrator, Feature 001 registry compatibility, original Feature 003/004 references, and trusted origin checks.
- **PolicySelectionObservation**: Ephemeral exact-scope patient index-assessment score and verified binary correctness target; never an ordinary serialized record.
- **SelectivePolicyOutcome**: Exact-scope readiness/non-success or selected cutoff with empirical risk/coverage and reasons, without row-level content.
- **SelectivePolicyArtifact**: Immutable selected-but-unevaluated record separating original fitting/calibration provenance from policy-selection provenance and marking selection evidence spent.

## Assumptions

- The research custodian can provide independently controlled origin and linkage evidence; the core library does not authenticate arbitrary code controlling its trusted Python host.
- A future policy workflow may receive a new Feature 003 build whose validation partition has been reserved for policy selection; no such dataset, protocol values, production ledger, or real custodian integration is currently configured.
- The original Feature 003 training evidence and Feature 004 configuration needed to reproduce reference state are available to the trusted research workflow. If not, the outcome is `NOT_READY`.
- Empirical risk/coverage on the policy-selection cohort is subject to selection optimism and is not an unbiased or independent performance estimate.
- Feature 005 validation is spent for estimator selection; Feature 006 calibration is spent for calibrator fitting; policy-selection data will be spent for cutoff selection; protected final-test data remain isolated for a separately authorized later evaluation feature.
- Feature 007 does not perform final independent policy evaluation or runtime assessment. Feature 008 remains a provisional roadmap assignment subject to scope review.
- Safira remains a research prototype; no clinical or deployment readiness is established.

## Out of Scope

- Automatic safety-estimator training or recalibration.
- Reuse of Feature 005 validation or Feature 006 calibration observations for policy selection.
- Use, retrieval, tuning, or disclosure of protected final-test observations.
- Independent final evaluation of the frozen policy; it is a separate later feature.
- Patient-level score inference, clinical decision execution, runtime assessment, or changes to `SafetyContext`/`SafetyAssessment`.
- Numerical risk ceilings, minimum patient counts, clinical thresholds, cost matrices, or clinical-risk guarantees not supplied by an approved versioned protocol.
- Changes to Features 001–006 public contracts, artifact contents, model training pipelines, or trust infrastructure.
