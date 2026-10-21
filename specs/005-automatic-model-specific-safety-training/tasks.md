# Tasks: Automatic Model-Specific Safety Training

**Input**: Approved Feature 005 specification, planning artifacts and Constitution v3.0.0.

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/training-python.md`, `quickstart.md`, and `implementation-context.md`.

**Organization**: Three reviewable implementation batches. Tasks are grouped by the three Feature 005 user stories; each task records its prerequisite IDs, requirement trace and completion condition. All tests use synthetic records and an independently controlled fixture ledger.

## Batch A — Trusted Admission and Training Preparation

**Outcome**: Establish independently checked Feature 003/004/002 inputs, exact row/source alignment and per-scope eligibility. Batch A does not fit a candidate or publish a successful estimator artifact.

## Phase 1: Setup

- [X] T001 Create the `src/safira/training/` package skeleton and `tests/training_fixtures.py` synthetic Feature 001 registry, Feature 002 records, Feature 003 partitioned examples, Feature 004 signal sets, and separately controlled ledger fixture; trace FR-007, FR-027; prerequisites: none; done when fixtures cover standalone binary, multi-label, and independent contributors without patient data.
- [X] T002 [P] Add baseline package and fixture smoke tests in `tests/test_training_fixtures.py`; prerequisites: T001; trace FR-027, SC-008; done when the three configurations build valid synthetic inputs and fixtures contain only synthetic identifiers and observations.

## Phase 2: Foundational Records and Errors

- [X] T003 Define stable privacy-safe training error codes and exception classes in `src/safira/training/exceptions.py`; prerequisites: T001; trace FR-021, FR-026; done when input, verification, compatibility, and artifact failures expose safe codes without echoing raw rows, groups, categories, or values.
- [X] T004 [P] Write immutable record contract tests in `tests/test_training_records.py` for `TrainingScope`, `TrainingProtocol`, `TrainingOutcome`, exact source identity, required versioned policy, all status values, nested-input detachment, and detached serialization; prerequisites: T001; trace FR-005, FR-021, FR-025; done when tests fail against the empty package for each missing invariant.
- [X] T005 Implement deeply immutable configuration and outcome records in `src/safira/training/records.py`; require exact `(model_id, model_version, label_id)`, protocol identifier/version, frozen nested settings, and distinct readiness versus evidence failure states; depends on T003–T004; trace FR-005, FR-021, FR-025; done when T004 passes.
- [X] T006 Define `TrainingInputVerifier`, verifier result records, and admission error contract in `src/safira/training/verification.py`; require injected host-owned verification and disallow Boolean-only or digest-only trust results; depends on T003–T005; trace FR-001–FR-002, FR-021; done when the contract accepts only typed exact-scope checks for comparison against actual inputs.

## Phase 3: User Story 1 — Establish an Eligible Model-Specific Training Scope (Priority: P1)

**Goal**: Accept only complete, trusted, exact-scope Feature 003 correctness supervision aligned to Feature 004 predictors and independently admitted Feature 002 predictions.

**Independent test**: Given synthetic standalone binary, multi-label, and independent multi-model sources, trusted complete data returns one eligible result per exact model/version/label. Forged, incomplete, mismatched, duplicated, extra, or split-patient data fail before any training matrix, cohort claim, or artifact is published.

### Tests first

- [X] T007 [P] [US1] Write independent-ledger admission tests in `tests/test_training_verification.py` for a valid verifier result, absent provider/ledger entry, forged `TrainingInputCheck`, Boolean/digest-only assertion, stale evidence, and mismatched Feature 003/004 dataset/protocol/manifest/run identity; prerequisites: T001, T005–T006; trace FR-001–FR-002, FR-021, SC-001, SC-006; done when each adversarial case fails for the intended missing admission condition.
- [X] T008 [P] [US1] Write complete-inventory, row-alignment and registry-admission tests in `tests/test_training_alignment.py` for exact row-key derivation, changed target/predictor content, missing/extra/duplicate rows, wrong partition/source/Feature 002 admission/Feature 004 fitted-reference identity, unknown registered model ID, wrong model version, unknown or incompatible label, incorrect registered adapter identity, incorrect preprocessing identity, and incompatible source-qualified prediction semantics; prerequisites: T001, T005–T006; trace FR-002, FR-005, FR-009, SC-001–SC-002; done when each mismatch fails admission and no altered or incomplete inventory is accepted.
- [X] T009 [P] [US1] Write group and target-isolation tests in `tests/test_training_leakage.py` for repeated visits, labels and contributors; cross-partition patient groups; correctness/target/outcome/group/role/verification mutations; and primary-output metadata; prerequisites: T001, T005–T006; trace FR-003–FR-004, FR-015–FR-016, FR-029, SC-003–SC-004; done when groups affect only trusted eligibility and target-only changes do not alter predictors.
- [X] T010 [P] [US1] Write exact-scope eligibility tests in `tests/test_training_eligibility.py` for equal label IDs across classifiers/versions, per-scope group/class support, missing protocol criteria, and one inadequate scope beside an eligible scope; prerequisites: T001, T005–T006; trace FR-005–FR-008, FR-013, SC-002, SC-006; done when no label, contributor, version, or support counts are pooled.
- [X] T011 [P] [US1] Write ordinary-result privacy tests in `tests/test_training_privacy.py` inspecting outcome repr, `to_dict`, JSON serialization, error messages, and fixture files for patient identifiers, group keys, row keys, targets, raw observations, and protected values; prerequisites: T001, T005–T006; trace FR-004, FR-026–FR-027, SC-008; done when each forbidden marker is absent from every ordinary surface.

### Implementation

- [X] T012 [US1] Implement full input admission in `src/safira/training/verification.py`; execute the injected verifier, compare its typed result to actual full-content fingerprints and the exact Feature 003 manifest-bound build identity (`dataset_id`, `manifest_reference`, independently verified manifest digest, `protocol_id`/`protocol_version`, `builder_version`, complete inventory) plus Feature 004 dataset/run/method/reference identities, and independently verify every embedded Feature 002 prediction; depends on T006–T007; trace FR-001–FR-002, SC-001; done when missing, caller-forged, stale, or mismatched independent evidence fails closed and T007 passes.
- [X] T013 [US1] Implement exact role-wise Feature 003/004 row bijection in `src/safira/training/verification.py`; recompute existing `SignalRowKey` derivation, check full source/association/fingerprint lineage, and reject missing, extra, duplicate, changed, cross-role, or incompatible rows; depends on T008, T012; trace FR-002, FR-005, FR-009, SC-001; done when every admitted row has exactly one matching feature record in the same role and T008 passes.
- [X] T014 [US1] Implement patient-group partition checks and predictor/target separation in `src/safira/training/verification.py`; use opaque group refs only to verify train/validation/calibration disjointness and retain `correctness_target` only as a separate target field; depends on T009, T013; trace FR-003–FR-004, FR-015, SC-003–SC-004; done when repeated patient records cannot cross roles and no group, role, outcome, verification field, or target enters predictor construction.
- [X] T015 [US1] Add Feature 001 registry compatibility checks in `src/safira/training/verification.py`; validate registered classifier, exact label, adapter/preprocessing identity, and Feature 004 source semantics without changing existing contracts; depends on T008, T013–T014; trace FR-005–FR-009, FR-024; done when the T008 red tests demonstrate unknown model/version/label and incompatible adapter/preprocessing/source semantics fail admission for only their affected source.
- [X] T016 [US1] Implement per-source scope enumeration, protocol adequacy and evidence availability outcomes in `src/safira/training/service.py`; keep each exact source independent and return `NOT_READY`, `INSUFFICIENT_EVIDENCE`, `UNAVAILABLE_REQUIRED_EVIDENCE`, invalid, or incompatible outcomes without fitting candidates; depends on T005, T010, T012–T015; trace FR-006–FR-008, FR-013, FR-021; done when US1 tests pass and no estimator/artifact is produced in Batch A.
- [X] T017 [US1] Run the Batch A synthetic scope/admission test set and record the test command and expected outcomes in `specs/005-automatic-model-specific-safety-training/quickstart.md`; depends on T007–T016; trace FR-001–FR-002, SC-001; done when all Batch A tests pass and docs state that no candidate fitting/artifact publication exists yet.

**Batch A checkpoint**: trusted complete inputs and exact scopes are independently testable; candidate fitting and successful estimator artifacts remain unavailable.

---

## Batch B — Feature Encoding and Candidate Fitting

## Phase 4: User Story 2 — Automatically Train and Select a Correctness Estimator (Priority: P2), Part 1

**Goal**: Build protocol-approved per-scope predictor matrices using only Feature 004 signal records and fit predeclared baseline/logistic candidates on Feature 003 training rows.

**Independent test**: For synthetic eligible scopes, only approved Feature 004 values/states enter a stable ordered schema. Preprocessing and candidates fit on training rows only. With training inputs/protocol fixed, authorized validation changes cannot alter schema, imputation, scaling, baseline prevalence, or logistic coefficients; unauthorized mutations are rejected at full-service admission as tested in T028. Candidate selection itself remains disabled until Batch C.

### Tests first

- [ ] T018 [P] [US2] Add `scikit-learn==1.7.1` to the runtime dependency test contract in `tests/test_training_dependency.py`; assert Python >=3.11 and importable pinned API without introducing another estimator dependency; prerequisites: T017; trace FR-014, FR-028; done when environment/dependency mismatch is reported clearly and the supported version is asserted.
- [ ] T019 [P] [US2] Write ordered-schema tests in `tests/test_training_features.py` for approved finite numeric signals, exact method versions/semantics, nominal `seen`/`unseen`, allowlisted state columns, six optional dimensions, universally unsupported omission reasons, and exclusion of explanation/primary-output metadata; prerequisites: T017; trace FR-008–FR-012, SC-006; done when unapproved/non-finite or reordered inputs fail before fitting.
- [ ] T020 [P] [US2] Write missingness and preprocessing isolation tests in `tests/test_training_preprocessing.py` for all seven states, protocol rejection of invalid/not_ready, approved non-value handling, typed indicators, train-only median/scaling, fixed one-hot mapping, constant/all-missing rules, and validation mutation through an isolated train-only helper or freshly authorized fixture; prerequisites: T017; trace FR-011–FR-012, FR-017, SC-003–SC-004; done when validation mutations cannot change fitted preprocessing and no admission gate is bypassed.
- [ ] T021 [P] [US2] Write baseline/logistic candidate tests in `tests/test_training_candidates.py` for training-only prevalence, two-class requirement, fixed L2/lbfgs configuration, finite state, convergence warning, non-finite values, and no parameter/seed retry; prerequisites: T017; trace FR-013–FR-014, FR-020, SC-005–SC-006; done when each case asserts the specified candidate state without inspecting validation to change fit.

### Implementation

- [ ] T022 [US2] Declare the exact `scikit-learn==1.7.1` runtime pin in `pyproject.toml` and add dependency-version capture in `src/safira/training/candidates.py`; preserve Python >=3.11 and record scikit-learn, NumPy, SciPy, joblib, and threadpoolctl versions; depends on T018; trace FR-014, FR-028; done when dependency tests pass and no other runtime package is added.
- [ ] T023 [US2] Implement immutable ordered feature schema and state validation in `src/safira/training/features.py`; admit only protocol-listed finite numeric Feature 004 values, approved `seen`/`unseen`, and allowlisted state indicators, recording omitted universal unsupported dimensions; depends on T005, T016, T019; trace FR-008–FR-012, SC-006; done when schema tests pass and every column traces to exact source method/version/meaning.
- [ ] T024 [US2] Implement training-only preprocessing fit and frozen validation transform in `src/safira/training/features.py`; apply approved median fills only with separate state indicators, approved scaling/category maps, and declared constant/all-missing policy; depends on T020, T023; trace FR-011–FR-012, FR-017, SC-003–SC-004; done when preprocessing tests pass and validation/calibration/protected data cannot change fitted state.
- [ ] T025 [US2] Implement training-prevalence baseline fitting in `src/safira/training/candidates.py`; derive the constant solely from exact-scope training correctness targets and keep a single-class descriptive result separate from a successful candidate artifact; depends on T016, T021; trace FR-013–FR-014, SC-006; done when baseline tests pass with no row-level target in returned diagnostics.
- [ ] T026 [US2] Implement fixed L2 logistic candidate fitting in `src/safira/training/candidates.py`; use scikit-learn 1.7.1 `lbfgs`, L2, no class weights, intercept, and protocol-approved `C`, `tol`, `max_iter`; reject absent/unapproved parameters and single-class training; depends on T022, T024–T025; trace FR-014, SC-005; done when tests verify exact config, finite parameters, and no custom optimizer/search.
- [ ] T027 [US2] Implement explicit candidate failure and numerical validation in `src/safira/training/candidates.py`; convert convergence, fit exceptions, non-finite coefficients/probabilities and unsupported class shapes into safe candidate statuses without changed settings; depends on T026; trace FR-014, FR-021, SC-006; done when candidate failure tests pass and no artifact is published.
- [ ] T028 [US2] Verify training-only fit isolation in `tests/test_training_candidates.py` and `tests/test_training_preprocessing.py` using two distinct paths: (a) mutate a previously admitted validation or calibration record without fresh independent authorization and assert full-service input admission rejects it; (b) independently reauthorize changed synthetic full-service fixtures, or call isolated train-only preprocessing/candidate helpers directly, then hold approved training inputs and protocol fixed and assert fitted preprocessing, baseline state and logistic parameters are unchanged. Never bypass admission with unauthorized changed content; depends on T024–T027; trace FR-017–FR-020, SC-004–SC-005; done when both rejection and train-only independence are verified without a second Feature 005 CV or Feature 004 refit.

**Batch B checkpoint**: internal feature and candidate helpers work under fixed protocol settings; no successful end-to-end estimator artifact is published.

---

## Batch C — Automatic Selection, Artifacts, and Integration

## Phase 5: User Story 2 — Candidate Comparison and Lifecycle (Priority: P2), Part 2

**Goal**: Compare valid predeclared candidates exactly once on authorized Feature 003 validation and enforce the spent-validation/calibration/protected-test boundary.

**Independent test**: Synthetic cases verify Brier direction, tie-breaking, conditional undefined metrics, support prerequisites, candidate failure policy, no validation refit, and explicit non-success where comparison is infeasible.

### Tests first

- [ ] T029 [US2] Write Brier comparison tests in `tests/test_training_selection.py` for exact binary Brier formula, lower-is-better selection, exact numeric tie selecting prevalence baseline, fixed validation inventory, and no threshold or validation refit; prerequisites: T028; trace FR-014–FR-020, SC-005–SC-006; done when tests detect reversed metric direction, non-exact tie rules, or refitting.
- [ ] T030 [P] [US2] Write secondary metric tests in `tests/test_training_metrics.py` for conditional AUROC/AP, correctness-class support, undefined one-class metric reasons, optional undefined metrics, and protocol-required comparison infeasibility; prerequisites: T028; trace FR-013–FR-014, FR-021, SC-006; done when undefined secondary metrics remain explicit and required criteria produce non-success.
- [ ] T031 [US2] Write candidate-outcome and evidence-lifecycle tests in `tests/test_training_selection.py` for selected baseline versus selected logistic, one-class baseline-only non-success, predeclared candidate failure policy, validation marked spent, calibration not fitted/scored, and protected-test absence; prerequisites: T028; trace FR-018–FR-021, FR-023, FR-030–FR-031, SC-004, SC-006; done when no prohibited partition can influence selection or artifact state.

### Implementation

- [ ] T032 [US2] Implement validation Brier comparison and deterministic exact-tie policy in `src/safira/training/candidates.py`; use the same authorized validation rows for valid candidates and freeze the training-fitted winner without refit; depends on T025–T029; trace FR-014–FR-020, SC-005; done when Brier and tie tests pass.
- [ ] T033 [US2] Implement conditional AUROC/AP and explicit undefined/support outcomes in `src/safira/training/candidates.py`; follow protocol feasibility and report only safe aggregate support; depends on T030, T032; trace FR-013–FR-014, FR-021, SC-006; done when all secondary metric tests pass without numeric placeholders.
- [ ] T034 [US2] Implement candidate-fit failure selection and evidence-role lifecycle in `src/safira/training/service.py`; allow remaining-candidate selection only when the predeclared protocol permits it, mark validation spent, reserve calibration, and exclude protected final-test access; depends on T031–T033; trace FR-018–FR-021, FR-023, FR-030–FR-031, SC-004; done when outcome tests pass and no settings change after validation inspection.

## Phase 6: User Story 3 — Preserve Reproducibility and Model-Specific Artifacts (Priority: P3)

**Goal**: Publish only a validated, immutable, versioned, exact-scope intermediate artifact with safe serialization and traceable provenance.

**Independent test**: Repeated synthetic training under identical inputs/protocol yields reproducible declared state; artifact export is detached and private; altered classifier, version, label, schema, protocol, preprocessing, method or fitted-reference identity is rejected.

### Tests first

- [ ] T035 [US3] Write artifact immutability/privacy tests in `tests/test_training_artifact.py` for nested mutation, detached export, exact required fields, forbidden patient/group/row keys, targets, raw observations, restricted evidence, calibration/protected values, and separate training versus selection metrics; prerequisites: T034; trace FR-022–FR-027, FR-031, SC-007–SC-008; done when every serialization/result surface is inspected and mutations cannot change accepted state.
- [ ] T036 [US3] Write artifact compatibility and safe-loading tests in `tests/test_training_artifact.py` for exact model/version/label, registry, Feature 003 dataset/protocol/manifest-bound build identity, Feature 004 methods/run/reference, schema/preprocessing, artifact version, malformed/non-finite arrays, altered digest, and unauthorized origin; prerequisites: T034; trace FR-022, FR-024–FR-026, SC-007; done when mismatches fail closed and digest-only/caller-asserted origin is rejected.
- [ ] T037 [US3] Write numerical export/reproducibility tests in `tests/test_training_artifact.py` comparing exported frozen logistic coefficients/intercept and a test-only probability reconstruction—sigmoid of the frozen intercept plus coefficient dot product over the frozen transformed input, respecting stored class ordering—to the original scikit-learn output within declared numeric tolerance; test a selected prevalence baseline separately from its stored constant probability; repeat identical runs and test allowed nondeterminism metadata. This reconstruction is internal synthetic verification only, not a public inference, assessment, calibration, scoring, policy or deployment API; prerequisites: T034; trace FR-022–FR-023, FR-028, SC-005, SC-007; done when there is no estimator search or pickle/joblib load.
- [ ] T038 [P] [US3] Write three-configuration end-to-end acceptance tests in `tests/test_training_acceptance.py` for standalone binary, multi-label, and independent multi-model scopes, including same-label distinct contributors, one insufficient scope beside an eligible one, and baseline/logistic selection; prerequisites: T034; trace FR-005–FR-007, FR-010, FR-013–FR-016, FR-032, SC-001–SC-006; done when scopes remain independent and all outcomes are synthetic and exact-source traceable.

### Implementation

- [ ] T039 [US3] Implement immutable exact-scope artifact and detached privacy-safe export in `src/safira/training/records.py`; freeze selected estimator state, schema, preprocessing, configuration, dependency versions, safe training/selection metrics, Feature 001–004 provenance, lifecycle and limitations; always mark `uncalibrated` and `non_deployable`; depends on T005, T034–T035; trace FR-022–FR-027, FR-031, SC-007–SC-008; done when artifact immutability/privacy tests pass.
- [ ] T040 [US3] Implement allowlisted artifact validation and controlled loading in `src/safira/training/artifacts.py`; check structure, finite dimensions, canonical payload digest, exact compatibility and independently verified origin without pickle/joblib deserialization or durability claims; depends on T036, T039; trace FR-024–FR-026, SC-007; done when malformed, mismatched, unauthorized and digest-only payloads fail.
- [ ] T041 [US3] Implement the public per-scope `SafetyTrainingService.train` orchestration in `src/safira/training/service.py`; require complete admission before scope results, construct only train/validation matrices, fit on train, compare once on validation, return independent outcomes, and publish no artifact on non-success; depends on T015–T016, T023–T034, T038–T039; trace FR-001–FR-002, FR-015–FR-019, FR-021–FR-026, FR-030–FR-032, SC-001, SC-004, SC-006; done when end-to-end tests pass and calibration/protected data are not accessed.
- [ ] T042 [US3] Export the reviewed public training types, artifact validation, and service from `src/safira/training/__init__.py`; expose only the documented contract and keep internal admission/matrix helpers inaccessible as trusted public shortcuts; depends on T039–T041; trace FR-024, FR-033, SC-007, SC-009; done when import/API tests pass and no Feature 001–004 public interface changes.
- [ ] T043 [US3] Complete artifact compatibility matrix and repeatability acceptance in `tests/test_training_acceptance.py`; exercise every artifact mismatch, deterministic outputs under fixed dependencies/protocol, exact tie, safe failures, and validation-spent lifecycle; depends on T037–T042; trace FR-022–FR-028, SC-005, SC-007; done when SC-005 and SC-007 are covered by passing synthetic acceptance tests.

## Final Phase: Integration and Cross-Cutting Verification

- [ ] T044 Update `specs/005-automatic-model-specific-safety-training/quickstart.md` with implemented public API, dependency install/version check, synthetic examples, accurate test commands, actual expected statuses, and host-ledger/artifact-custody limitations; depends on T041–T043; trace FR-027, SC-008; done when every command and API name matches implementation and no test result is claimed without execution.
- [ ] T045 [P] Add a regression guard in `tests/test_training_regression.py` confirming Feature 005 training does not invoke primary prediction, Feature 004 extraction, Feature 003 target construction, calibration, policy, `SafetyAssessment`, or protected-test APIs; trace FR-009, FR-018–FR-020, FR-029–FR-033, SC-004, SC-009; prerequisites: T042; done when instrumented synthetic boundaries confirm no prohibited call.
- [ ] T046 Run focused Feature 005 tests, relevant Features 001–004/adapter/context/assessment regressions, and full pytest suite; record exact counts and any skips in `specs/005-automatic-model-specific-safety-training/quickstart.md`; depends on T038–T045; trace FR-033, SC-009; done when all required suites pass or documented defects are corrected and rerun.
- [ ] T047 Run `git diff --check` and a privacy/requirements trace audit across `src/safira/training/`, `tests/test_training_*.py`, and Feature 005 docs; map FR-001–FR-033 and SC-001–SC-009 to verified tasks/tests; depends on T044–T046; trace FR-001–FR-033, SC-001–SC-009; done when no whitespace/privacy/traceability defect remains and no Feature 001–004 contract or unrelated file was changed.

---

## Dependencies and Execution Order

### Batch dependencies

- **Batch A (T001–T017)**: package/tests setup, foundational records, independent trust gate, complete row/source alignment, group isolation, and per-scope eligibility. Batch A blocks all model fitting. It must not expose a successful artifact.
- **Batch B (T018–T028)**: depends on Batch A. Adds the pinned estimator dependency, frozen schema/encoding, train-only preprocessing, baseline and logistic candidate helpers. Helpers remain internal; no successful end-to-end artifact is published.
- **Batch C (T029–T047)**: depends on Batch B. Adds validation selection, metric semantics, artifact validation/export, public orchestration, end-to-end acceptance, quickstart, and regression verification.

### User story order

- **US1 (T007–T017)** depends on setup and foundational records (T001–T006); it is independently testable as trusted scope formation.
- **US2 (T018–T034)** depends on completed US1 and is split between Batch B fitting helpers and Batch C validation selection. It does not introduce a new CV split.
- **US3 (T035–T043)** depends on validated candidate selection and covers reproducible immutable exact-scope artifacts.
- Final integration (T044–T047) depends on all stories.

```text
T001–T006 → T007–T017 (US1 / Batch A)
                       ↓
            T018–T028 (US2 / Batch B)
                       ↓
            T029–T034 (US2 / Batch C)
                       ↓
            T035–T043 (US3 / Batch C)
                       ↓
            T044–T047 (final verification)
```

### Test-first checkpoints

1. T007–T011 are written before verifier/scope implementation (T012–T016); confirm the expected failures before implementation.
2. T018–T021 precede dependency/schema/preprocessing/candidate code (T022–T027); confirm red/green behavior.
3. T029–T031 precede selection code (T032–T034).
4. T035–T038 precede artifact and orchestration code (T039–T043).
5. Run focused tests at each batch checkpoint. Full pytest regression is reserved for T046 unless a concrete defect requires earlier broad coverage.

### Parallel opportunities

- After T001, T002 can proceed independently of T003–T006 fixture-independent record work.
- T007–T011 are parallelizable test files after shared synthetic fixtures exist.
- T018–T021 are separate dependency/schema/preprocessing/candidate test files, but implementation waits for Batch A.
- T029–T031 share `tests/test_training_selection.py` and therefore are sequential file edits, not parallel tasks. T035–T037 share `tests/test_training_artifact.py` and therefore are sequential file edits; T038 uses its own acceptance file and may proceed independently after candidate outcomes are defined. Remaining `[P]` markers apply only to tasks with disjoint file ownership and compatible dependencies.
- T045 regression guard can be developed alongside T044 documentation after the public service behavior is fixed; final T046/T047 remain sequential gates.
- No candidate implementation task is marked parallel if it depends on an incomplete schema, input verifier or candidate contract.

## Requirement and Success-Criteria Traceability

| Specification coverage | Tasks |
|---|---|
| FR-001–FR-002 trusted data and exact dataset/row admission | T006–T008, T012–T013, T017 |
| FR-003–FR-004 correctness target and predictor/group isolation | T009, T014, T019–T020, T045 |
| FR-005–FR-007 identity, independent scopes and classifier configurations | T010, T015–T016, T038 |
| FR-008–FR-012 signal availability, approved schema, states and non-fabrication | T019–T020, T023–T024, T038 |
| FR-013–FR-014 adequacy, candidates and metrics | T010, T021–T027, T029–T033 |
| FR-015–FR-020 patient grouping, cross-fit boundaries, lifecycle, no search/refit | T009, T014, T028–T034, T045 |
| FR-021 non-success outcomes | T003–T006, T015, T027, T030–T034 |
| FR-022–FR-025 immutable exact artifact, lineage and compatibility | T035–T043 |
| FR-026–FR-027 privacy and synthetic fixtures | T001–T002, T011, T035, T039, T044, T047 |
| FR-028 reproducibility | T018, T021, T028, T037, T043, T046 |
| FR-029–FR-031 target/scope exclusions and non-deployable status | T009, T031, T039, T045 |
| FR-032–FR-033 acceptance and regression protection | T038, T043, T045–T047 |
| SC-001 | T007–T008, T012–T013, T038 |
| SC-002 | T010, T015–T016, T038 |
| SC-003 | T009, T014, T019–T020, T045 |
| SC-004 | T009, T014, T028, T031, T045 |
| SC-005 | T021, T028–T029, T037, T043 |
| SC-006 | T010, T020–T021, T027, T030–T031, T038 |
| SC-007 | T035–T043 |
| SC-008 | T011, T035, T039, T047 |
| SC-009 | T045–T047 |

## Implementation Strategy

### MVP (Batch A / User Story 1)

Complete T001–T017. The MVP is trusted per-scope eligibility and safe failure only; it does **not** train or publish an estimator. Stop at the Batch A checkpoint for review.

### Incremental batches

1. Batch A proves independent admission, exact alignment, grouping and scope eligibility.
2. Batch B adds protocol-frozen encoding and candidate fitting helpers while the public end-to-end training operation remains unavailable.
3. Batch C adds one-shot validation selection, immutable artifacts and acceptance/regression verification.

## Blockers and Limitations

- Exact per-scope adequacy, feature allowlist/state policy, optional feature rules, preprocessing, logistic `C`/`tol`/`max_iter`, required-candidate handling, metric feasibility and disclosure settings must be approved in a versioned research protocol. Tasks must reject missing approval with `NOT_READY`, not invent values.
- A genuine independently controlled Feature 003/004/002 ledger and authorized artifact custodian are external integrations. Synthetic fixture ledgers verify software boundaries only; the core cannot authenticate malicious Python controlling the trusted host.
- Feature 004 cross-fitted training values and frozen full-training-reference validation values may differ. Synthetic determinism does not prove empirical generalization, calibration or clinical safety.
- Feature 005 does not provide independent later calibration, policy-selection evidence, protected final-test evaluation, or durable artifact storage.

**Task readiness**: All Feature 005 requirements and approved Decisions A–E have task/test coverage. No specification blocker prevents `$speckit-analyze`; research-protocol approvals and external ledgers remain runtime prerequisites, not unassigned implementation decisions.
