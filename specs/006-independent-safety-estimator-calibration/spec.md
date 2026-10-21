# Feature Specification: Independent Safety Estimator Calibration

**Feature Branch**: `feature-06/Independent-calibration`
**Created**: 2026-10-21
**Status**: Completed — adversarially verified; closed within approved research-software scope.
**Closed**: 2026-10-21
**Input**: Independently calibrate a frozen Feature 005 correctness estimator using only its authorized Feature 003 calibration targets and exactly aligned Feature 004 calibration signals.

## Purpose and Scope

Safira Feature 006 fits one fixed calibration mapping for each exact `(model_id, model_version, label_id)` scope from an already selected, frozen Feature 005 correctness estimator. Its binary target is the Feature 003 correctness target for that primary classifier prediction. It is not a disease outcome, primary-model probability, safety decision, or clinical action.

A successful result is an immutable `CALIBRATOR_FITTED_UNEVALUATED` research artifact. It records that a mapping was fitted; it does not establish independent calibration performance. The artifact is non-deployable and not clinically validated. Feature 006 does not add an inference or per-patient calibrated-score API.

Features 001–005 remain authoritative for registration, prediction admission, verified correctness targets and partitions, safety-signal extraction, and the selected base estimator. Feature 006 consumes those contracts without changing them. The approved decisions A–G are recorded in [decision-record.md](decision-record.md). The methodology review and architecture feasibility review remain preserved as pre-specification research references; their historical pending-approval statements describe their original review stage, not current approval status.

## Clarifications

All seven research-owner decisions A–G were explicitly approved before this specification was finalized. No research-critical decision is left for `$speckit-clarify`. Exact protocol settings that were intentionally delegated to a versioned, approved calibration protocol remain prerequisites to readiness; this specification does not invent their numerical values.

## User Scenarios & Testing

### User Story 1 — Admit Verified Calibration Inputs (Priority: P1)

As a research owner, I want Feature 006 to admit only the exact, independently verified calibration evidence and frozen estimator for one registered classifier-version-label scope, so that calibration cannot silently use mismatched or untrusted records.

**Why this priority**: Calibration is invalid if the correctness target, signal row, classifier identity, partition, or frozen estimator does not refer to the same authorized prediction scope.

**Independent Test**: With synthetic standalone binary, multi-label, and multi-model records, provide independently controlled verification evidence for a complete Feature 003 calibration inventory, matching Feature 004 calibration features, exact Feature 001 registration, and a Feature 005 artifact. Verify admission and reject each missing, altered, extra, duplicate, stale, wrong-scope, wrong-role, or unverified item before fitting.

**Acceptance Scenarios**:

1. **Given** a complete verified calibration dataset and matching signal set, **when** the exact selected Feature 005 artifact is admitted, **then** Feature 006 verifies exact model/version/label, manifest-bound dataset identity, artifact origin, signal methods and fitted-reference identities before any fitting work.
2. **Given** a caller-constructed record, self-asserted status, digest, Boolean, or stale receipt without independent host-controlled evidence, **when** admission is attempted, **then** it fails closed and no calibrator artifact is produced.
3. **Given** an altered, missing, extra, duplicated, reordered-to-a-different-source, or cross-partition calibration prediction/signal row, **when** the complete inventory is checked, **then** the input is rejected before score reconstruction or fitting.
4. **Given** two independently registered contributors with the same label, or two versions of one model, **when** evidence is admitted, **then** each exact scope remains separate and no evidence or support is pooled.

### User Story 2 — Fit the Approved Calibration Mapping (Priority: P1)

As a research owner, I want a fixed, protocol-approved mapping fitted from the frozen estimator's private scores and verified calibration correctness targets, so that the estimator's output has an explicitly defined calibration transformation without retraining its base estimator.

**Why this priority**: The mapping must be statistically identifiable, exact-scope, and fitted only on the partition reserved for calibration.

**Independent Test**: Use deterministic synthetic data for both supported Feature 005 estimator families. Independently calculate expected fitted forms and verify occurrence weighting, patient-group support checks, numerical feasibility, failure-state distinctions, and no access to train, validation, or protected-test evidence.

**Acceptance Scenarios**:

1. **Given** an admitted `l2_logistic` artifact, **when** its private frozen linear score is reconstructed using its exact ordered schema and frozen preprocessing, **then** only the recalibration intercept and slope are fitted according to `q = sigmoid(a + b*z)` and the approved protocol.
2. **Given** an admitted `prevalence_baseline` artifact with `0 < p0 < 1`, **when** calibration succeeds, **then** only the offset in `q = sigmoid(logit(p0) + a)` is fitted and the output remains constant across occurrences with no individualized discrimination claim.
3. **Given** repeated prediction occurrences for a patient, **when** the approved objective is fitted, **then** each occurrence has equal objective weight, while adequacy counts unique verified patient groups and does not treat visits as independent people.
4. **Given** an absent target class, unmet approved support, unidentified or nonvarying logistic scores, rank deficiency, separation, nonconvergence, nonfinite output, or a non-positive fitted logistic slope, **when** the method is evaluated, **then** it produces the specified distinct non-success state and never silently clips, regularizes, reverses, retries with changed parameters, or substitutes another method.

### User Story 3 — Freeze and Safely Report an Unevaluated Calibrator (Priority: P2)

As a research reviewer, I want a deeply immutable artifact bound to its estimator, evidence, protocol, and exact scope, with privacy-safe fit status, so that the calibration work can be inspected and reproduced without exposing patient-level data or implying validation.

**Why this priority**: Calibration parameters are useful only when their provenance and lifecycle limitations remain explicit and reviewable.

**Independent Test**: Inspect synthetic success and failure artifacts, mutate original nested inputs and returned serialization, and search the complete ordinary object and serialization surface for restricted information or a per-patient application operation.

**Acceptance Scenarios**:

1. **Given** a successful fit, **when** its artifact is created and serialized, **then** it is immutable, JSON-compatible, exactly bound to its model/version/label, base estimator, frozen preprocessing, Feature 003/004 evidence and calibration protocol, and marked `CALIBRATOR_FITTED_UNEVALUATED`, non-deployable, and not independently evaluated.
2. **Given** an incompatible artifact or any mutation to its schema, preprocessing, source evidence, method/reference identity, or exact scope, **when** compatibility is checked, **then** it is rejected without migration or transfer.
3. **Given** calibration-fit diagnostics, **when** ordinary results are reported, **then** only approved convergence and privacy-safe adequacy/lifecycle metadata appear; default fit-set Brier, log loss, ECE, reliability diagrams, patient rows, outcomes, targets, identifiers, raw signals, or protected values do not appear.
4. **Given** a successful calibration artifact, **when** its lifecycle is reviewed, **then** Feature 005 validation remains spent for estimator selection, Feature 003 calibration is spent for fitting, protected final-test remains inaccessible, and independent evaluation or policy selection requires separately authorized evidence.

### Edge Cases

- The host origin verifier, Feature 002 admission lineage, Feature 003 dataset/manifest check, Feature 004 alignment, or required protocol approval is absent, stale, incomplete, or inconsistent.
- Feature 005 artifact is newly produced in memory but has not been independently registered or vouched for by the authorized host-controlled origin verifier.
- A class is absent; unique patient-group support is below protocol criteria; repeated visits inflate row count; or the exact scope is otherwise inadequate.
- A prevalence baseline has `p0` equal to 0 or 1, so the approved offset mapping is not finite.
- Logistic scores are constant, insufficiently varied under approved criteria, rank-deficient, separated, non-finite, or yield a non-positive slope; the protocol's numerical ambiguity rule is missing.
- A required Feature 004 predictor state is missing, unavailable, invalid, not ready, or incompatible with the frozen Feature 005 schema. Feature 006 does not impute, refit, or revise that schema.
- Feature 003/004 records include extra, missing, duplicated, substituted, changed, wrong-association, wrong-label, or wrong-partition content.
- A caller attempts to use Feature 005 validation for calibration, access protected-test material, reconstruct labels from primary scores, or get calibrated per-patient outputs.
- Serialization, exception details, fit diagnostics, or artifact provenance accidentally disclose patient/group/occurrence identifiers, correctness values, raw evidence, restricted verification content, or protected-test material.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST calibrate only an already selected and frozen Feature 005 correctness estimator, independently for each exact `(model_id, model_version, label_id)` scope.
- **FR-002**: The system MUST verify the exact Feature 001 registration and classifier, adapter, preprocessing, version, and label compatibility for every calibrated scope.
- **FR-003**: Before producing any scope result that implies trusted admission, the system MUST execute an authorized host-controlled verification of the complete Feature 003 build and its calibration partition, Feature 004 calibration feature set, and every embedded Feature 002 prediction admission lineage. It MUST compare actual submitted content with the verification result; caller assertions, dataclass construction, status flags, or digests alone MUST NOT establish origin or admission.
- **FR-004**: The system MUST bind admitted Feature 003/004 evidence to the exact dataset, manifest reference and independently verified manifest digest, protocol ID/version, builder version, full authorized row inventory, Feature 004 run/method identities, fitted-reference identities, and exact calibration partition. It MUST use existing upstream identity fields and MUST NOT assume a separate `dataset_version` or builder-ID field.
- **FR-005**: For every calibration `CorrectnessExample`, the system MUST require exactly one matching Feature 004 calibration record derived from the same admitted prediction and exact source/association. Missing, extra, duplicated, changed, stale, cross-role, or conflicting records MUST fail before fitting.
- **FR-006**: The system MUST independently verify the selected Feature 005 artifact's compatibility and origin for both newly created in-memory artifacts and safely loaded artifacts. A matching object, artifact digest, or self-asserted receipt MUST NOT substitute for an authorized host-controlled origin check. The core MUST document that it cannot authenticate arbitrary malicious Python controlling the trusted host.
- **FR-007**: The system MUST reconstruct the frozen Feature 005 logistic linear predictor privately from the artifact's exact ordered schema, stored training-fitted preprocessing, coefficients and intercept, without invoking the primary classifier, exposing a general inference API, or refitting any base-estimator state.
- **FR-008**: For `l2_logistic`, the system MUST fit only `q = sigmoid(a + b*z)` by fixed, unpenalized Bernoulli logistic maximum likelihood using scikit-learn 1.7.1's supported `lbfgs` solver. The versioned calibration protocol MUST predeclare solver configuration, tolerance, iteration limit, convergence/separation criteria, deterministic expectations, and any allowed numerical safeguards before calibration outcomes are examined.
- **FR-009**: For `prevalence_baseline`, the system MUST require finite `0 < p0 < 1` and fit only the offset in `q = sigmoid(logit(p0) + a)`. The result MUST retain constant-output semantics and MUST state that it adds no individualized discrimination.
- **FR-010**: The system MUST NOT perform isotonic regression, calibrator search, algorithm fallback, successful identity-only calibration, or any method choice based on the same calibration fitting evidence.
- **FR-011**: The calibration objective MUST give each prediction occurrence equal weight. The system MUST separately assess independent evidence using unique verified patient groups and protocol-declared class/support criteria; repeated visits MUST NOT count as independent patients. Patient/group/occurrence identifiers MUST remain restricted metadata and MUST NOT be predictors or ordinary artifact contents.
- **FR-012**: The system MUST require both correctness target classes and protocol-approved support. Logistic calibration MUST additionally require adequately identifiable score variation. No universal sample minimum, group minimum, class ratio, score-variation cutoff, or other arbitrary threshold may be introduced.
- **FR-013**: A fitted non-positive logistic calibration slope MUST produce an explicit non-success outcome. The system MUST NOT reverse score ordering, clip or force the slope positive, substitute intercept-only fitting, or change methods. Any numerically ambiguous slope treatment MUST be fixed by the approved protocol without an invented tolerance. This requirement does not apply to the constant baseline mapping, which has no estimated slope.
- **FR-014**: The system MUST distinguish at least `NOT_READY` (required approval, authority, protocol, or verifier not established), `INSUFFICIENT_EVIDENCE` (approved support or identifiability unmet), `UNAVAILABLE_REQUIRED_EVIDENCE` (required compatible Feature 004 signal cannot be supplied under the frozen schema), malformed-input rejection, compatibility rejection, and numerical failure. No non-success state may contain a successful calibrator artifact.
- **FR-015**: The system MUST treat missing scientific approval as `NOT_READY`, not malformed input. It MUST treat malformed or altered evidence as invalid input, exact identity mismatch as incompatible input, and solver/finite-estimate failure as numerical failure, using privacy-safe stable reason codes.
- **FR-016**: The system MUST reuse the exact frozen Feature 005 feature schema, preprocessing, missingness rules, estimator family and state. It MUST NOT refit preprocessing, alter the schema, recalibrate Feature 004 signals, or use train/validation records as calibration observations.
- **FR-017**: Only Feature 003's authorized `calibration` correctness targets and exactly matched Feature 004 `calibration` signal records MAY affect calibration fitting. Feature 005 train and validation MUST NOT be reused; validation is already spent for estimator selection. Protected final-test data MUST be inaccessible to Feature 006.
- **FR-018**: The system MUST produce a deeply immutable, versioned, exact-scope calibrator artifact bound to the Feature 005 artifact and its schema/preprocessing identities, Feature 003 dataset/manifest/protocol/build provenance, Feature 004 run/method/fitted-reference identities, and approved calibration protocol/configuration.
- **FR-019**: The successful artifact MUST state `CALIBRATOR_FITTED_UNEVALUATED`, `not_independently_evaluated`, `non_deployable`, and `not_clinically_validated`, and preserve the baseline constant-output limitation when applicable.
- **FR-020**: Artifact serialization MUST be allowlisted, detached, and safely JSON-compatible; it MUST NOT depend on unsafe pickle/joblib deserialization. It MUST exclude patient, assessment, occurrence, group, row and restricted identifiers; correctness targets/outcomes; raw training/calibration observations; protected evidence; and restricted verifier content.
- **FR-021**: Ordinary Feature 006 outputs MUST be limited to protocol-approved fitting/convergence and privacy-safe lifecycle/adequacy information. Default outputs MUST NOT include calibration-fit Brier, log loss, ECE, reliability diagrams, per-row predictions, or claims of demonstrated calibration performance.
- **FR-022**: Feature 006 MUST mark Feature 003 calibration as spent once used for fitting. It MUST state that Feature 005 validation is spent for estimator selection and that future independent calibrator evaluation and policy selection require separately authorized evidence. It MUST NOT reallocate partitions or borrow protected-test observations.
- **FR-023**: The system MUST preserve standalone binary, multi-label, and independently composed multi-model support by operating independently per exact contributor scope, including overlapping labels. No data, support, fitted mapping, or artifact may be pooled across models, versions, or labels.
- **FR-024**: Repeated runs with unchanged verified inputs and protocol MUST be reproducible within the protocol-declared deterministic execution expectations; any platform-dependent limitation MUST be recorded without claiming bitwise reproducibility beyond demonstrated behavior.
- **FR-025**: Errors, diagnostics, ordinary outcomes, and serialization MUST be privacy-safe and MUST NOT include raw patient values, identifiers, targets, raw optimizer messages, or protected/restricted evidence.
- **FR-026**: Automated verification MUST use synthetic fixtures to cover both estimator families, all three supported classifier configurations, exact scope separation, trusted admission, row alignment, fitting formulas, weighting/support, numerical and non-success cases, artifact immutability/privacy, partition lifecycle, reproducibility, and compatibility regressions for Features 001–005.

## Success Criteria

- **SC-001**: Synthetic valid cases for each supported classifier configuration admit only after independently controlled verification of exact registry, Feature 002 prediction lineage, Feature 003 manifest-bound calibration inventory, Feature 004 aligned calibration features, and Feature 005 artifact origin; missing or mismatched evidence yields no successful artifact.
- **SC-002**: For both Feature 005 estimator families, synthetic tests demonstrate the approved mapping formula and match independently calculated reference parameters within the protocol/test-declared numerical tolerance; baseline outputs remain constant and logistic outputs use only the frozen linear score.
- **SC-003**: Synthetic tests confirm equal per-occurrence objective weights and unique-patient support accounting, including repeated visits, without using patient/group identifiers as predictors or exposing them in ordinary outputs.
- **SC-004**: Each missing, altered, extra, duplicate, stale, wrong-scope, wrong-association, wrong-role, unverified, or cross-partition input case is rejected before fitting; separately controlled legitimate evidence is admitted.
- **SC-005**: Synthetic edge cases for a missing class, inadequate approved support, baseline `p0` outside `(0,1)`, insufficient logistic score variation, rank deficiency, separation, nonconvergence, non-finite result, and non-positive slope produce their specified distinct non-success outcomes without silent fallback or changed parameters.
- **SC-006**: With unchanged admitted calibration inputs, frozen Feature 005 artifact, and protocol, repeated synthetic runs produce equivalent fitted state and provenance. Feature 003 train and validation rows/targets are not reused as calibration observations; holding the frozen artifact and calibration inputs fixed, changes to those partitions do not change the fitted mapping. Attempts to access protected-test values are rejected or impossible through ordinary Feature 006 inputs.
- **SC-007**: A successful synthetic artifact is deeply immutable, exact-scope and compatibility-bound; mutation of original nested inputs or detached serialized output cannot alter it, and incompatible schema, preprocessing, model/version/label, artifact, dataset/manifest, signal, reference, or protocol identity is rejected.
- **SC-008**: Full inspection of ordinary results, errors, diagnostics, object representations, and serialization reveals no patient/group/occurrence identifiers, target values, raw observations, protected content, or restricted verifier payload; outputs contain no default fit-set calibration-performance claims or patient-level application API.
- **SC-009**: Focused tests and the complete pytest regression suite verify Feature 006 behavior while existing Feature 001–005 public contracts and tests remain unchanged; passing software checks are reported separately from scientific or clinical validation.

## Key Entities

- **Calibration Protocol**: Versioned, pre-outcome-approved rules for exact scopes, evidence admission, calibration method, occurrence estimand, adequacy criteria, solver configuration, numerical feasibility, deterministic execution and disclosure.
- **Verified Calibration Input Bundle**: Feature 003 calibration examples plus the exact Feature 004 calibration records and Feature 005 selected artifact, bound to Feature 001 registration and independently checked Feature 002 admission lineage and host-controlled verification evidence.
- **Frozen Base Score**: The private Feature 005 linear predictor reconstructed from its frozen ordered schema, training-only preprocessing, coefficients and intercept; for the baseline family, the stored constant probability.
- **Calibration Mapping**: The fixed family-specific parameterization fitted to verified binary correctness targets; either logistic intercept/slope or baseline logit offset.
- **Calibration Fit Outcome**: One exact-scope success or privacy-safe non-success status, with only protocol-approved support and convergence metadata.
- **Calibrator Artifact**: Immutable, safely serializable, exact-scope mapping and provenance that is explicitly unevaluated, non-deployable and not clinically validated.
- **Origin Verification Evidence**: Host-controlled independent check that binds the submitted Feature 005 artifact content, exact scope and artifact version to an authorized origin; a digest alone is not origin evidence.

## Assumptions and Dependencies

- Features 001–005 are complete and their contracts remain unchanged. Feature 005's selected `prevalence_baseline` and `l2_logistic` artifacts carry their frozen feature schema, preprocessing, estimator state and existing upstream provenance.
- Feature 003 exposes ordinary development partitions including calibration rows, while protected final-test data remain outside ordinary results. The Feature 003 verified identity is the existing manifest-bound tuple of dataset ID, manifest reference/digest, protocol ID/version, builder version and complete inventory; no separate dataset-version field is assumed.
- Feature 004 supplies an exact calibration `SignalFeatureSet` row and frozen method/reference provenance for each admitted Feature 003 calibration prediction. Feature 006 does not recompute signals or refit references.
- An authorized trusted host can execute independent verifiers for Feature 001 registration, Feature 002 admission, Feature 003/004 content and alignment, and Feature 005 artifact origin. The repository has no production evidence ledger, artifact custodian or durable storage integration. The core cannot authenticate arbitrary malicious code controlling the trusted Python host.
- scikit-learn `1.7.1` is the approved runtime dependency and implementation pin. Environment installation and compatibility verification occur during implementation. This approval does not establish scientific or clinical validity.
- A versioned calibration protocol must provide exact scope support criteria and numerical settings before use. This specification intentionally defines no universal minimum sample counts, score-variation threshold, tolerance, iteration limit, optimizer fallback, or separation cutoff.
- Calibration estimates correctness probability for the declared target population. It does not establish future transportability, independent performance, clinical safety, decision policy, or deployability.

## Included and Excluded Scope

**Included**: trusted exact-scope admission; complete calibration row alignment; private reconstruction of the frozen Feature 005 score; fixed family-specific calibration fitting; protocol-specific support and numerical failure handling; immutable privacy-safe artifact and fit-only status reporting.

**Excluded**: primary classifier execution; Feature 003 target reconstruction; Feature 004 signal/reference recomputation; Feature 005 estimator or preprocessing refitting, retuning, or validation reuse; calibrator comparison; isotonic regression; successful identity-only mapping; public per-patient calibrated-score/inference API; `SafetyAssessment`; reliability policy or TRUST/CAUTION/DEFER; clinical thresholds; protected final-test access; independent evaluation; policy selection; durable-storage claims without a separately verified custodian; clinical validation or effectiveness claims.
