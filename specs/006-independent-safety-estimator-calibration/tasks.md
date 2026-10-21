---
description: "Test-first implementation tasks for Feature 006 independent estimator calibration"
---

# Tasks: Independent Safety Estimator Calibration

**Input**: Approved Feature 006 spec, Decisions A–G, plan, research, data model, Python contract, quickstart and implementation context.

**Prerequisites**: Constitution v3.0.0, Features 001–005 contracts, and approved versioned `CalibrationProtocol` settings for any fit. Missing run-time approval must yield `NOT_READY`; tasks do not invent minima or numerical parameters.

**Organization**: Three reviewable implementation batches: Batch A establishes trusted admission/readiness (Setup, Foundation, US1); Batch B implements private frozen scores and fixed fitting (US2); Batch C freezes artifacts and completes the public service/verification (US3 and final polish).

**Test policy**: Synthetic-only, test-first. For each test task, demonstrate red for the intended defect before its implementation task, then green afterward. Test ledgers are independently populated and are not accepted merely because a fixture constructs a verification dataclass.

## Phase 1: Setup — Batch A

**Purpose**: Add only Feature 006 package/test scaffolding and synthetic input support. No application behavior is introduced here.

- [x] T001 [P] Create the empty Feature 006 package boundary in `src/safira/calibration/__init__.py` and verify imports do not expose an inference or assessment API; completion means the package imports without changing `src/safira/__init__.py` or Features 001–005.
- [x] T002 [P] Create synthetic Feature 001–005 registry, prediction, dataset, signal-set and frozen-estimator builders in `tests/calibration_fixtures.py`; use only opaque synthetic references and verify the fixtures exercise standalone binary, multi-label and independently composed multi-model scopes.
- [x] T003 Create independently controlled prediction, dataset, signal and Feature 005 artifact-origin ledgers in `tests/calibration_ledgers.py`; populate ledger evidence before submissions and verify a merely constructed check object is not ledger evidence (depends on T002).

## Phase 2: Foundational — Batch A

**Purpose**: Define immutable shared calibration records and safe error codes before story-specific admission or fitting.

- [x] T004 Write failing contract tests for immutable protocol/scope/status/outcome and safe error records in `tests/test_calibration_records.py`; cover nested defensive copying, exact three-part source identity and invalid status/lifecycle rejection before implementation (depends on T001).
- [x] T005 Implement deeply immutable `CalibrationProtocol`, `CalibrationOutcome`, status/reason types and privacy-safe shared exceptions in `src/safira/calibration/records.py` and `src/safira/calibration/exceptions.py`; satisfy T004 with no implicit approved settings or patient fields (depends on T004).

---

## Phase 3: User Story 1 — Admit Verified Calibration Evidence (Priority: P1) — Batch A

**Goal**: Establish an exact, independently verified eligible calibration scope before any frozen-score reconstruction or fitting.

**Independent Test**: Synthetic records with separate ledgers admit only when registration, prediction lineage, dataset/manifest, calibration targets, aligned signals, artifact origin and protocol scope all match. Forged, incomplete, stale, duplicate or changed evidence fails before numerical helpers are called.

### Tests for User Story 1 (write first; red before implementation)

- [x] T006 [P] [US1] Add failing tests that require explicit verifier injection and executed verification, rejecting caller booleans/check objects/digests and ensuring absent or stale providers fail closed in `tests/test_calibration_admission.py`; assert no score/fitting helper is called (depends on T003, T005; FR-003, FR-006; SC-001, SC-004).
- [x] T007 [P] [US1] Add failing exact Feature 001 registration, model/version/label, classifier artifact, adapter identity, preprocessing identity and overlapping-label contributor-isolation cases in `tests/test_calibration_registry_compatibility.py`; verify unknown or mismatched registry scopes are rejected (depends on T003, T005; FR-001, FR-002, FR-023; SC-001, SC-004).

### Implementation for User Story 1

- [x] T008 [US1] Implement the explicit `CalibrationInputVerifier` protocol, immutable verification-check types and exact Feature 001 registry compatibility checks in `src/safira/calibration/verification.py`; make T006–T007 pass without global verifier state or caller-selected providers (depends on T006, T007; FR-002, FR-003, FR-006; SC-001, SC-004).
- [x] T009 [US1] Add failing tests for Feature 002 prediction admission lineage and Feature 003 exact dataset/manifest/protocol/builder/inventory binding, including forged, missing, changed, extra, stale, duplicate, wrong-association and wrong-role rows in `tests/test_calibration_dataset_admission.py` (depends on T008; FR-003–FR-005; SC-001, SC-004).
- [x] T010 [US1] Implement complete Feature 002 lineage checks and Feature 003 ordinary development/calibration inventory validation in `src/safira/calibration/verification.py`; bind existing dataset ID, manifest reference/digest, protocol ID/version, builder version and complete inventory without inventing a `dataset_version` or builder-ID field (depends on T009; FR-003–FR-005; SC-001, SC-004).
- [x] T011 [US1] Add failing Feature 004 calibration row alignment tests for one-to-one prediction fingerprint, exact source/association/label/version, method parameters, run identity, fitted-reference identity, missing/extra/duplicate/altered/cross-role rows in `tests/test_calibration_signal_alignment.py` (depends on T010; FR-004–FR-005; SC-001, SC-004).
- [x] T012 [US1] Implement exact Feature 004 calibration alignment and run/reference compatibility checks in `src/safira/calibration/verification.py`; do not recompute signals or refit references (depends on T011; FR-004–FR-005, FR-016; SC-001, SC-004).
- [x] T013 [US1] Add failing Feature 005 origin tests for newly created in-memory and safely loaded artifacts, requiring an independently populated host ledger bound to digest, exact source key and artifact version in `tests/test_calibration_artifact_admission.py` (depends on T003, T012; FR-006; SC-001, SC-004).
- [x] T014 [US1] Implement exact Feature 005 artifact compatibility and executed origin authorization in `src/safira/calibration/verification.py`, reusing safe artifact contracts where possible; reject object/digest/status assertions without ledger evidence and document trusted-host limits (depends on T013; FR-006; SC-001, SC-004).
- [x] T015 [US1] Add failing private per-scope readiness tests for unique verified patient-group support, patient disjointness across Feature 003 roles, exact per-model/version/label adequacy, and distinct `NOT_READY` versus `INSUFFICIENT_EVIDENCE` behavior in `tests/test_calibration_readiness.py`. Use already implemented independently ledger-backed verifier primitives for synthetic evidence; do not construct verification checks/tokens or publish a trusted bundle from the unit helper. Include an admitted, exactly aligned signal record whose required predictor is unavailable under its approved frozen Feature 005 state policy; expect `UNAVAILABLE_REQUIRED_EVIDENCE`, no artifact or score/fitting helper call for that scope. Distinguish this from missing/extra/forged rows, malformed/incompatible evidence, absent approval, inadequate support, and permitted non-value states already handled by frozen preprocessing. Cross-scope behavior after full shared admission is verified in T017–T018 and the public service tests (depends on T014; FR-011–FR-015, FR-023; SC-003–SC-005).
- [x] T016 [US1] Implement private exact-scope group-support and readiness checks in `src/safira/calibration/verification.py`; count repeated visits once for unique-group adequacy, keep identifiers outside predictors/results, and avoid pooling labels or versions. Batch A may inspect only independently admitted evidence states and approved frozen-policy metadata to classify `UNAVAILABLE_REQUIRED_EVIDENCE`; it must not construct/learn a schema, fit preprocessing, or reconstruct numerical scores. Preserve permitted non-value handling, distinguish unavailable required predictors from admission failures and `NOT_READY`/`INSUFFICIENT_EVIDENCE`, and do not publish a trusted bundle or public outcome before T018 (depends on T015; FR-011–FR-015, FR-023; SC-003–SC-005).
- [x] T017 [US1] Add failing complete-bundle tests covering shared atomic rejection, complete admitted inventory before any scope result, and independent scope-local insufficiency or `UNAVAILABLE_REQUIRED_EVIDENCE` after shared admission, including an unavailable exact scope beside an independently eligible scope in `tests/test_calibration_admission.py` (depends on T014, T016; FR-003–FR-006, FR-014–FR-015, FR-023; SC-001, SC-003–SC-005).
- [x] T018 [US1] Implement the internal `verify_bundle` orchestration and restricted verified-input token in `src/safira/calibration/verification.py`; a shared trust/inventory failure must abort before numerical work, and per-scope insufficiency or unavailable required evidence must not affect another scope after shared admission succeeds (depends on T017; FR-003–FR-006, FR-014–FR-015, FR-023; SC-001, SC-003–SC-005).
- [x] T019 [US1] Add failing positive readiness cases for standalone binary, multi-label and independent multi-model inputs, including same label across different contributors and versions, in `tests/test_calibration_acceptance.py`; verify all exact scopes remain separate (depends on T018; FR-001–FR-006, FR-023; SC-001, SC-004).
- [x] T020 [US1] Complete the admission-only acceptance path in `src/safira/calibration/verification.py` so T019 yields an internal verified bundle/readiness result but no frozen scores, calibration fit, successful calibrator artifact or public scoring operation (depends on T019; FR-001–FR-006, FR-023; SC-001, SC-004).

**Batch A checkpoint**: Run `python -m pytest -q tests/test_calibration_records.py tests/test_calibration_admission.py tests/test_calibration_registry_compatibility.py tests/test_calibration_dataset_admission.py tests/test_calibration_signal_alignment.py tests/test_calibration_artifact_admission.py tests/test_calibration_readiness.py tests/test_calibration_acceptance.py`. Only verified admissions/readiness may be published; there is no calibration fit or successful artifact yet.

---

## Phase 4: User Story 2 — Fit the Approved Calibration Mapping (Priority: P1) — Batch B

**Goal**: Reconstruct private frozen Feature 005 scores and fit exactly the approved family-specific mapping using only admitted calibration observations.

**Independent Test**: Synthetic Feature 005 states reproduce the frozen linear score; logistic and baseline calculations match independent reference calculations. Group support, class support, separation, convergence, slope and numerical failures return the specified non-success states without fallback.

### Tests for User Story 2 (write first; red before implementation)

- [ ] T021 [US2] Add failing parser tests for the supported Feature 005 `artifact_version` and exact ordered schema/preprocessing field shapes (without assuming a separate `schema_version` field), active indices, dimensions, class order `(0, 1)`, finite coefficients/intercept and malformed artifact payloads in `tests/test_calibration_scores.py` (depends on T018; FR-007, FR-016; SC-002, SC-007).
- [ ] T022 [US2] Implement a private allowlisted Feature 005 schema/preprocessing reconstruction adapter in `src/safira/calibration/scores.py`, reconstructing exact typed frozen objects exclusively from the validated artifact representation. Validate the supported existing `artifact_version` and corresponding schema/preprocessing field shapes (Feature 005 defines no separate `schema_version` field), dimensions, column/active-index order, category/state mappings, finite parameters, and compatibility. Do not call `build_feature_schema` or `fit_preprocessing` on calibration observations; reuse only production `encode_rows(schema, rows)` and `transform_rows(state, schema, rows)` after reconstruction. Do not import `_reproduce_probability_for_test` (depends on T021; FR-007, FR-016; SC-002, SC-007).
- [ ] T023 [US2] Add failing tests for numeric parity of transformed rows and frozen logistic `z`, exact order, active columns, state encoding, strict-interior baseline `p0`, and proof that calibration reconstruction never invokes `build_feature_schema` or `fit_preprocessing`. Include an admitted aligned record with a required predictor unavailable beyond approved frozen handling; require a typed `UNAVAILABLE_REQUIRED_EVIDENCE` non-success with no fabricated value or score, while permitted non-value states follow the frozen policy (depends on T022; FR-007, FR-009, FR-014–FR-016; SC-002, SC-004–SC-005, SC-007).
- [ ] T024 [US2] Implement private calibration-row transformation and frozen logistic-score reconstruction in `src/safira/calibration/scores.py`; use only validated reconstructed frozen objects and existing production encoding/transformation signatures. Never call `build_feature_schema`, `fit_preprocessing`, or `_reproduce_probability_for_test`; verify finite dimensions and unchanged Feature 005 state. If transformation cannot form a required predictor under the frozen policy, return an internal typed scope-local `UNAVAILABLE_REQUIRED_EVIDENCE` result without fitting; do not treat permitted frozen non-value handling as unavailable. Expose no caller-facing `predict`/`apply` (depends on T023; FR-007, FR-014–FR-016; SC-002, SC-004–SC-005, SC-007).
- [ ] T025 [US2] Add failing tests for occurrence-weighted objective inputs, both correctness classes, unique patient-group support, repeated visits, and exclusion of group/occurrence IDs from predictors in `tests/test_calibration_fitting.py` (depends on T024; FR-011–FR-012; SC-003, SC-005).
- [ ] T026 [US2] Implement construction of ordered per-scope occurrence score/target vectors in `src/safira/calibration/fitting.py` using the verified input token and Batch A support result; do not recompute eligibility or let group/occurrence identifiers enter predictor vectors (depends on T025; FR-011–FR-012, FR-017; SC-003, SC-006).
- [ ] T027 [US2] Add failing tests that distinguish full-rank finite-MLE singleton-interior scores from complete separation, quasi-separation at equality, reversed ordering and constant-score rank deficiency in `tests/test_calibration_separation.py`; include class0 scores `{0,1,2}` with class1 singleton `{1}` as finite-MLE geometry (depends on T026; FR-012–FR-015; SC-005).
- [ ] T028 [US2] Implement the exact scalar-score separation check in `src/safira/calibration/fitting.py`: after both-class and full-rank checks, separation is `max(z0) <= min(z1)` or `max(z1) <= min(z0)`; finite-MLE feasibility requires both strict cross-endpoint inequalities, with no positive-width interval-intersection requirement or added tolerance (depends on T027; FR-012–FR-015; SC-005).
- [ ] T029 [US2] Add failing scikit-learn estimator tests for explicit `penalty=None`, `solver="lbfgs"`, binary classes, unit occurrence weights, protocol `tol`/`max_iter`, convergence warning/iteration exhaustion, nonfinite state, negative/zero slope and deterministic same-environment reruns in `tests/test_calibration_logistic.py` (depends on T028; FR-008, FR-013–FR-015, FR-024; SC-002, SC-005–SC-006).
- [ ] T030 [US2] Implement fixed unpenalized logistic recalibration in `src/safira/calibration/fitting.py` with scikit-learn 1.7.1 `penalty=None`, `solver="lbfgs"`, `fit_intercept=True`, `class_weight=None`, `warm_start=False`, protocol `tol`/`max_iter`, `(0,1)` classes and unit occurrence weights; return non-success for nonconvergence, rank/separation failures, nonfinite estimates and `b <= 0`, with no regularization, retry, clipping, order reversal or fallback (depends on T029; FR-008, FR-013–FR-015, FR-024; SC-002, SC-005–SC-006).
- [ ] T031 [US2] Add failing closed-form baseline tests for `a=logit(mean(y))-logit(p0)`, constant `q`, strict-interior `p0`, absent classes, repeat occurrences and numerical boundaries in `tests/test_calibration_baseline.py` (depends on T026; FR-009, FR-011–FR-015; SC-002, SC-003, SC-005).
- [ ] T032 [US2] Implement the stable baseline offset MLE in `src/safira/calibration/fitting.py` using `log`/`log1p`, requiring both classes and `0 < p0 < 1`; do not add pseudo-counts, clipping or an estimated slope (depends on T031; FR-009–FR-015; SC-002, SC-005).
- [ ] T033 [US2] Add failing leakage and immutability tests in `tests/test_calibration_fitting.py` proving train/validation records are not fitting observations, calibration-only inputs determine mapping parameters with a fixed frozen artifact, group IDs never enter the design matrix, and fitting does not mutate base artifact/schema/preprocessing (depends on T030, T032; FR-016–FR-017, FR-022, FR-025; SC-006, SC-008).
- [ ] T034 [US2] Implement the internal exact-scope fit dispatcher in `src/safira/calibration/fitting.py` to select only the method implied by the admitted Feature 005 artifact family and protocol; return parameter/state data only to internal callers and publish no end-to-end artifact or public per-patient score API (depends on T033; FR-001, FR-007–FR-017, FR-023; SC-002–SC-006).
- [ ] T035 [US2] Run the focused Batch B test set and record the synthetic singleton-interior, complete-separation, quasi-separation and degenerate-score results in `specs/006-independent-safety-estimator-calibration/quickstart.md`; completion requires all Batch B tests green and zero Feature 005 state mutation (depends on T034; FR-024, FR-026; SC-005–SC-006).

**Batch B checkpoint**: Run `python -m pytest -q tests/test_calibration_scores.py tests/test_calibration_fitting.py tests/test_calibration_separation.py tests/test_calibration_logistic.py tests/test_calibration_baseline.py` and repeat Batch A focused tests. Batch B produces internal mapping parameters only; no successful artifact or public service exists yet.

---

## Phase 5: User Story 3 — Freeze and Safely Report an Unevaluated Calibrator (Priority: P2) — Batch C

**Goal**: Orchestrate fully admitted exact-scope fitting, freeze only safe provenance and mapping fields, and report an unevaluated non-deployable artifact without protected or patient-level data.

**Independent Test**: End-to-end synthetic calls cover all three classifier configurations and both base-estimator families; exact-scope artifacts are immutable and compatible, insufficiency remains isolated, and ordinary results/errors/serialization expose no restricted content or evaluation claims.

### Tests for User Story 3 (write first; red before implementation)

- [ ] T036 [US3] Add failing `CalibratorArtifact` tests for exact scope/base-artifact binding, finite family-specific parameters, required lifecycle markers, deep immutability and no artifact on non-success in `tests/test_calibration_artifacts.py` (depends on T034; FR-018–FR-020; SC-007).
- [ ] T037 [US3] Implement the immutable family-specific `CalibratorArtifact` in `src/safira/calibration/records.py`; enforce `CALIBRATOR_FITTED_UNEVALUATED`, not independently evaluated, non-deployable and not clinically validated lifecycle metadata (depends on T036; FR-018–FR-020; SC-007).
- [ ] T038 [US3] Add failing serialization and compatibility tests that scan the entire artifact/result/error/repr/export surface for patient, assessment, occurrence, group, row, target, outcome, raw signal, protected or verifier payload, and reject altered/incompatible digests in `tests/test_calibration_artifacts.py` (depends on T037; FR-018–FR-021, FR-025; SC-007–SC-008).
- [ ] T039 [US3] Implement allowlisted detached JSON-compatible export and exact expected-compatibility validation in `src/safira/calibration/artifacts.py`; distinguish digest integrity from host-controlled origin and do not deserialize pickle/joblib or claim persistence (depends on T038; FR-018–FR-020; SC-007–SC-008).
- [ ] T040 [US3] Add failing public-service tests in `tests/test_calibration_service.py` for complete shared admission before output, one result per exact scope, independent scope-local insufficiency, and `UNAVAILABLE_REQUIRED_EVIDENCE` discovered only during frozen score transformation, with no fit/artifact for that scope and continued success of a separately eligible scope after shared admission. Also verify deterministic ordering, no train/validation fitting, no protected-data access and no patient-score API (depends on T039; FR-001–FR-006, FR-014–FR-017, FR-022–FR-026; SC-001, SC-003–SC-006, SC-009).
- [ ] T041 [US3] Add failing end-to-end cases in `tests/test_calibration_acceptance.py` for standalone binary, multi-label, and independent multi-model contributors with overlapping labels/versions and both Feature 005 families, including one inadequate scope beside a successful independent scope and one scope whose admitted aligned predictor becomes `UNAVAILABLE_REQUIRED_EVIDENCE` only when frozen transformation is applied (depends on T040; FR-001, FR-014–FR-016, FR-023–FR-026; SC-001–SC-007, SC-009).
- [ ] T042 [US3] Implement `CalibrationService.calibrate` in `src/safira/calibration/service.py` to run the whole verifier first, then exact per-scope readiness, score reconstruction, fixed fitting and artifact construction; short-circuit each preflight non-success before score reconstruction/fitting, and short-circuit transformation-time unavailable evidence before fitting. Shared failures return no partial outcomes, while an insufficient or unavailable-evidence scope does not contaminate an independently eligible scope (depends on T040, T041; FR-001–FR-026; SC-001–SC-009).
- [ ] T043 [US3] Add failing public-surface tests proving `safira.calibration` exports only the protocol, service, safe outcomes/artifact validation and typed errors, with no `predict`, per-patient `apply`, policy or `SafetyAssessment` API, in `tests/test_calibration_public_api.py` (depends on T042; FR-019–FR-021, FR-025; SC-008).
- [ ] T044 [US3] Implement the narrow stable public exports in `src/safira/calibration/__init__.py`; preserve private score/fitting helpers and verify T043 passes without modifying `src/safira/__init__.py` or existing contracts (depends on T043; FR-019–FR-021, FR-025; SC-008).
- [ ] T045 [US3] Add Feature 001–005 compatibility regression tests in `tests/test_calibration_regression.py` proving existing registry, collection, dataset, signal, estimator-artifact, context and assessment contracts remain unchanged and their existing public test suites still pass (depends on T044; FR-002–FR-006, FR-016, FR-023, FR-026; SC-009).
- [ ] T046 [US3] Update `specs/006-independent-safety-estimator-calibration/contracts/calibration-python.md` and `specs/006-independent-safety-estimator-calibration/quickstart.md` with only implemented public signatures, validation commands, actual trust-provider limitations, exact non-success meanings and fit lifecycle; leave actual execution counts for T047 (depends on T042, T044; FR-014, FR-018–FR-026; SC-007–SC-009).

## Phase 6: Final Polish and Verification — Batch C

**Purpose**: Complete reproducible verification and accurate implementation reporting without exceeding Feature 006 scope.

- [ ] T047 Run focused Feature 006 suites, relevant Features 001–005 regression suites and full `python -m pytest -q`, then run `git diff --check`; record actual counts/failures/limitations in `specs/006-independent-safety-estimator-calibration/quickstart.md` and mark only verified Feature 006 tasks complete.
- [ ] T048 Verify the final Feature 006 diff in `specs/006-independent-safety-estimator-calibration/tasks.md` and the repository status contains only approved Feature 006 package/tests/docs, all FR-001–FR-026 and SC-001–SC-009 have passing mapped tests, no task remains unchecked unintentionally, and Features 001–005 implementation/contracts are unchanged; report software verification separately from scientific/clinical validation.

---

## Dependencies and Execution Order

### Batch dependencies

- **Batch A — T001–T020**: Setup and foundational records precede US1. Trusted Feature 001–005 admission and exact calibration readiness complete without score reconstruction, fitting, or successful calibration artifacts.
- **Batch B — T021–T035**: Depends on Batch A. Implements private frozen score reconstruction and internal family-specific fit parameters only.
- **Batch C — T036–T048**: Depends on Batch B. Adds immutable artifacts, public service orchestration, compatibility/export, end-to-end acceptance, documentation and final regressions.

### User story dependencies

- **US1 (P1)** establishes the verified input/readiness boundary and is the prerequisite for numerical work.
- **US2 (P1)** depends on US1; it cannot consume an unverified bundle or publish a service result.
- **US3 (P2)** depends on US1 and US2; only it may construct and report successful calibrator artifacts.

### Required test-first checkpoints

- T004 before T005 establishes immutable shared records.
- T006–T007, T009, T011, T013, T015, T017 and T019 each demonstrate red before the corresponding US1 verifier/readiness implementation.
- T021, T023, T025, T027, T029, T031 and T033 each demonstrate red before the corresponding US2 score/fitting implementation.
- T036 before T037, T038 before T039, T040–T041 before T042, and T043 before T044 establish the Batch C red-test checkpoints for artifact, serialization, public service/acceptance, and public exports. T042 is an implementation task, not a test task.
- At each checkpoint, a failed test must fail for its intended requirement, not only because an unrelated import/setup is broken.

### Parallel execution boundaries

- T001 and T002 can run in parallel because they create separate package and fixture files; T003 depends on T002.
- T006 and T007 can be authored in parallel after the fixtures/records exist because they own different test modules. No verifier implementation begins until both red-test checkpoints pass.
- Within each remaining test/implementation pair, follow the listed order. Do not parallelize edits to `verification.py`, `fitting.py`, `records.py`, `service.py`, or the same test module.
- Batch A, B and C are sequential review gates; no cross-batch parallel implementation is allowed because each establishes the next batch's trust or numerical boundary.

## Requirement and Decision Traceability

| Requirement/decision | Primary task coverage |
|---|---|
| FR-001–FR-006; SC-001, SC-004; Decision G | T006–T014, T017–T020, T040–T042 |
| FR-007, FR-016; SC-002, SC-007 | T021–T024, T033–T034 |
| FR-008, FR-013–FR-015; SC-002, SC-004–SC-006; Decisions D–E | T015–T018, T023–T024, T027–T030, T040–T042 |
| FR-009–FR-012; SC-002–SC-005; Decisions A–C | T025–T032 |
| FR-017, FR-022; SC-006; Decision G | T026, T033, T040–T042 |
| FR-018–FR-021, FR-025; SC-007–SC-008; Decision F | T036–T039, T043–T046 |
| FR-023–FR-024, FR-026; SC-003, SC-009; Decisions A–G | T019, T029, T040–T048 |

## Implementation Strategy

### MVP — User Story 1 only

Complete Batch A. The deliverable is an internally verified, exact-scope calibration input/readiness boundary with synthetic proof of fail-closed admission. It does not fit scores or create successful calibration artifacts.

### Incremental implementation

1. Batch A: verify inputs/readiness; run its focused tests.
2. Batch B: add private frozen score reconstruction and family-specific numerical fitting; run Batch A and B focused tests.
3. Batch C: add service/artifact/export and full acceptance; run all focused tests, Features 001–005 regression tests and the full suite.

## Notes

- All task descriptions name exact affected paths, prerequisites, story labels where required, requirement/success traces, and objective completion conditions.
- `[P]` is used only for tasks that can edit different files without depending on incomplete work.
- No new numerical threshold, algorithm, runtime dependency, persistence service, primary-model invocation, policy or clinical claim is authorized.
