---
description: "Implementation task list for Safira Feature 004"
---

# Tasks: Safety Signal Extraction and Feature Engineering

**Input**: Feature 004 design documents in `specs/004-safety-signal-extraction/`.

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/signals-python.md`, `quickstart.md`, and `implementation-context.md`.

**Architecture**: Python 3.11+, standard library only for V1; use pytest and synthetic data. Preserve Feature 001–003 and adapter/context/assessment contracts.

**Execution batches**: Batch A (T001–T014) builds the immutable foundation and stateless extraction; Batch B (T015–T024) owns reference fitting and cross-fitting; Batch C (T025–T038) owns Feature 003 alignment, protected-test handoff, end-to-end integration, documentation, and final regression.

## Phase 1: Setup

**Purpose**: Establish a synthetic test harness without introducing application behavior or dependencies.

- [ ] T001 Add reusable synthetic Feature 001 registrations, Feature 002 prediction/evidence records, and Feature 003 development-result builders in `tests/signals_fixtures.py`; include standalone binary, multi-label, overlapping-contributor, and patient-grouped examples with no real patient data.

## Phase 2: Foundational Contracts and Validation

**Purpose**: Implement shared immutable records, state vocabulary, errors, and trusted input-admission boundaries before any signal methods.

- [ ] T002 [P] Write contract tests for immutable `SignalMethodConfig`, `SignalProtocol`, source keys, signal results, fitted-state references, and all seven signal states in `tests/test_signals_records.py`; assert nested input mutation and returned-value mutation cannot alter accepted records (FR-005, FR-006, FR-009, FR-026).
- [ ] T003 Implement the immutable/detached Feature 004 records, six-dimension and seven-state vocabulary, canonical serialization, and safe value copying in `src/safira/signals/records.py` and `src/safira/signals/base.py` (FR-004–FR-009, FR-026).
- [ ] T004 [P] Write negative tests for unverified/caller-constructed `PredictionRecord`, forged provenance, missing verifier, wrong content, wrong model/version/label, stale evidence, and incompatible registration in `tests/test_signals_admission.py` (FR-001, FR-006–FR-008, FR-025).
- [ ] T005 Implement injected exact-scope `SignalInputVerifier` admission, Feature 001 registry metadata validation, Feature 002 source/evidence compatibility checks, and privacy-safe typed errors in `src/safira/signals/validation.py` and `src/safira/signals/exceptions.py`; never treat dataclass construction, a Boolean, or caller digest alone as proof (FR-001, FR-006–FR-010, FR-025).

**Checkpoint**: Shared contracts and trusted admission pass focused tests. No extraction task begins before this phase is complete.

## Phase 3: User Story 1 — Extract Applicable Safety Signals (Priority: P1)

**Goal**: Produce exact-source, evidence-aware stateless results for applicable signals across all approved classifier configurations.

**Independent Test**: Synthetic live/admitted records for standalone binary, multi-label, and independently composed contributors produce valid traceable results or the correct non-value state; overlapping labels remain separate and unsupported evidence never becomes a numeric value.

### Tests for User Story 1 (write first)

- [ ] T006 [P] [US1] Add exact identity and classifier-configuration admission tests in `tests/test_signals_us1_identity.py` for standalone binary, multi-label, and independently composed contributors, including overlapping labels and exact version mismatch (FR-001, FR-002, FR-003, SC-002–SC-003).
- [ ] T007 [P] [US1] Add evidence completeness/validity profile tests in `tests/test_signals_coverage.py` for available, unsupported, missing, unavailable, invalid, and insufficient evidence; verify coverage is structured and never a universal score. Test cohort adequacy as a pure/internal calculation per exact model/version/label using unique patient groups and only protocol-required correctness-class support, with no pooling of contributors; do not test or promise public publication from unverified Feature 003 inputs here (FR-009–FR-011, SC-003, SC-007).
- [ ] T008 [P] [US1] Add Bernoulli entropy and optional repeated-output tests in `tests/test_signals_entropy.py` and `tests/test_signals_repeats.py` for p=0, p=1, p=0.5, declared log bases, finite/range semantics, rejection of non-probability score coercion, and repeat identity/same-input/stochastic-setting prerequisites (FR-007, FR-013, FR-023, SC-003).
- [ ] T009 [P] [US1] Add modality JSD tests in `tests/test_signals_modality.py` for identical and maximally different Bernoulli distributions, probability boundaries, comparable output semantics, missing modality, and rejection of cross-contributor comparisons (FR-014, FR-023, SC-003).

### Implementation for User Story 1

- [ ] T010 [US1] Implement capability- and registration-aware exact source admission orchestration in `src/safira/signals/service.py`, using only the injected verifier and existing Feature 001 metadata (FR-001–FR-003, FR-006–FR-010).
- [ ] T011 [US1] Implement evidence prerequisite coverage profiles in `src/safira/signals/stateless.py` and an internal pure helper for exact-scope cohort support calculations in `src/safira/signals/service.py`, preserving Feature 002 states and counting only unique patient groups plus protocol-required correctness-class support without pooling source keys; keep the helper non-public until verified Feature 003 admission is enforced in T028 (FR-009–FR-011, SC-007).
- [ ] T012 [US1] Implement Bernoulli predictive entropy with explicit log-base, p∈[0,1] validation, and 0 log 0 handling in `src/safira/signals/stateless.py`; do not convert non-probability scores (FR-007, FR-013).
- [ ] T013 [US1] Implement pairwise Bernoulli Jensen–Shannon divergence for comparable modality-specific outputs in `src/safira/signals/stateless.py`; retain pair identity and declared aggregation semantics and reject mismatched target, timing, calibration, or contributor scope (FR-014, FR-023).
- [ ] T014 [US1] Implement optional repeated-output descriptive variance only when same-input, repeat identity, stochastic settings, and probability semantics are verified in `src/safira/signals/stateless.py`; preserve unavailable states when those prerequisites fail (FR-013, FR-023).

**Checkpoint**: Focused tests in `tests/test_signals_us1_identity.py`, `tests/test_signals_coverage.py`, `tests/test_signals_entropy.py`, and `tests/test_signals_modality.py` pass before Batch B begins.

## Phase 4: User Story 2 — Prepare Comparable Features from Approved References (Priority: P1)

**Goal**: Fit compatible reference states using Feature 003 training evidence, cross-fit training rows by patient group, and apply frozen state to permitted held-out development partitions.

**Independent Test**: Synthetic kNN/domain references are deterministic, exact-scope compatible, fitted only from allowed training evidence, and never contain the scored patient's group when producing its cross-fitted training values.

### Tests for User Story 2 (write first)

- [ ] T015 [P] [US2] Add fitted-state compatibility tests in `tests/test_signals_reference_compatibility.py` for exact model/version/label, preprocessing, evidence schema, reference cohort, method version, and protocol mismatch (FR-018, FR-020, SC-005).
- [ ] T016 [P] [US2] Add deterministic patient-group assignment tests in `tests/test_signals_crossfit.py` for the approved algorithm/seed, all visits/labels/contributors staying together, no alternate-seed attempts, and infeasible folds reporting `insufficient_evidence` (FR-019, FR-024, SC-003, SC-006, SC-010).
- [ ] T017 [US2] Add grouping-change adversarial tests in `tests/test_signals_crossfit.py`: changing verified patient grouping may change fold assignments and cross-fitted scores, but every scored group's full records remain excluded from its reference, identifiers never enter predictor features or ordinary serialization, no leakage occurs, and merely renaming opaque group references cannot change the final full-training fitted reference when evidence/configuration are unchanged (FR-019, FR-022, SC-004, SC-006, SC-010).
- [ ] T018 [P] [US2] Add kNN tests in `tests/test_signals_knn.py` for k-th distance, exact vector dimensions/preprocessing, non-finite/empty inputs, unsupported metric/transform, and insufficient reference support; assert outputs remain raw distances without thresholds (FR-012, FR-018–FR-020, SC-003, SC-005).
- [ ] T019 [P] [US2] Add domain-familiarity tests in `tests/test_signals_domain.py` for training-only vocabulary, patient-group self-exclusion, privacy-safe `seen`/`unseen` values, missing/invalid categories, and incompatible scope (FR-015, FR-018–FR-020, SC-003, SC-005).
- [ ] T020 [P] [US2] Add train-only fit and frozen-application tests in `tests/test_signals_reference_fit.py`: changing ground truth/correctness cannot alter predictor features; validation/calibration/protected mutations cannot affect fitted state; validation/calibration apply frozen state only; mismatched states fail safely; merely renaming opaque group references cannot change the final full-training fitted reference when evidence/configuration are unchanged. Keep these tests scoped to internal pure helpers; public Feature 003 inputs remain gated by T025/T028 (FR-018–FR-022, SC-004–SC-006, SC-010).

### Implementation for User Story 2

- [ ] T021 [US2] Implement immutable reference compatibility keys, finite-vector validation, method configuration validation, and exact-scope fitted-state checks in `src/safira/signals/validation.py` and `src/safira/signals/reference.py` (FR-018–FR-020).
- [ ] T022 [US2] Implement the protocol-declared deterministic patient-group fold assignment and whole-group exclusion in `src/safira/signals/reference.py`; use exactly one approved seed/configuration, support explicit complete assignments when declared, and never retry or split groups. A verified grouping change may change folds and cross-fitted scores; opaque group-reference renaming alone must not change the final full-training fitted reference (FR-019, FR-024, SC-004, SC-006, SC-010).
- [ ] T023 [US2] Implement compatible k-th-nearest-neighbour distance and patient-group cross-fitted training results in `src/safira/signals/reference.py`; fit only Feature 003 training predictor representations and return explicit insufficiency rather than self-reference (FR-012, FR-018–FR-020).
- [ ] T024 [US2] Implement internal training-only domain vocabulary fit, cross-fitted membership, final immutable reference-state construction, and frozen validation/calibration primitives in `src/safira/signals/reference.py`; do not expose a public fitted state or result from Feature 003 data until the exact trusted admission gate is implemented in T028 (FR-015, FR-018–FR-020, SC-005–SC-006).

**Checkpoint**: Focused reference, cross-fitting, kNN, and domain tests pass. If verified grouping changes, changed folds/scores are allowed; self-inclusion, leakage, or group identifiers in predictors are never allowed.

## Phase 5: User Story 3 — Keep Predictor Features Separate from Supervision and Evaluation (Priority: P1)

**Goal**: Align signal features with verified Feature 003 development rows while keeping supervision, grouping, partitions, and protected evaluation data outside predictor features and ordinary APIs.

**Independent Test**: Synthetic Feature 003 builds with independently verified exact dataset/protocol/manifest scope produce detached row-aligned development features; ordinary results, serializers, logs, and errors reveal no protected content or patient identifiers.

### Tests for User Story 3 (write first)

- [ ] T025 [P] [US3] Add Feature 003 verification and row-alignment tests in `tests/test_signals_dataset_integration.py`. Verify every embedded Feature 002 `PredictionRecord` by exact canonical content, source-qualified identity, patient/assessment/occurrence association, trusted Feature 002 admission lineage, dataset identity and authorized partition. Cover: forged records inside otherwise valid datasets; changed prediction/evidence/provenance content; wrong identity/association; missing or stale row admission evidence; aggregate verification lacking an independently controlled complete row inventory and per-row admission lineage; and a positive case where every row is independently bound. Prove no unverified row contributes to signals, cohort-support claims, training feature sets or fitted states; also test opaque row keys and exclusion of outcomes, correctness, group IDs, partition roles, targets and verification metadata from predictors (FR-001, FR-017–FR-022, SC-004, SC-008).
- [ ] T026 [P] [US3] Add protected-test boundary tests in `tests/test_signals_protected.py` that inspect complete ordinary result objects and every serialization/error/log surface; prove the custodian receives only frozen-state and exact-scope references and no protected rows, outcomes, correctness, or transformed values return (FR-021, FR-025, SC-008, SC-011).
- [ ] T027 [P] [US3] Add leakage/privacy adversarial tests in `tests/test_signals_privacy_leakage.py` for forbidden supervision fields, patient identifiers, raw evidence, restricted manifest content, and protected membership, including safe failure serialization (FR-019, FR-022, FR-025–FR-026, SC-004, SC-008).

### Implementation for User Story 3

- [ ] T028 [US3] Implement exact Feature 003 dataset/protocol/manifest verification through the injected verifier, requiring independently controlled evidence and matching development partition scope in `src/safira/signals/validation.py`. Bind the complete row inventory and every embedded Feature 002 record's exact canonical content, admission/provenance lineage, identity, association/occurrence, dataset and partition scope; permit aggregate verification only when independent evidence binds that complete inventory and each row's admission lineage. Fail closed before any signal, cohort-support claim, training feature set, fitted-state publication or protected handoff can consume an unverified row (FR-001, FR-017–FR-021, SC-004–SC-005, SC-010).
- [ ] T029 [US3] Implement opaque `SignalRowKey` alignment and predictor-only feature-set construction from verified train/validation/calibration rows in `src/safira/signals/service.py` and `src/safira/signals/records.py`; keep labels/targets, outcomes, correctness, patient/group IDs, and partition assignments outside feature values (FR-019, FR-022, FR-026).
- [ ] T030 [US3] Implement the injected custodian-controlled apply-only protected-state handoff in `src/safira/signals/service.py`; pass references/configuration only, forbid refit/tuning, return a safe detached receipt/status only, and make no persistence guarantee absent custodian verification (FR-021, FR-025, SC-011).

**Checkpoint**: Feature 003 alignment, protected-boundary, and adversarial privacy tests pass before documentation and final integration.

## Phase 6: User Story 4 — Review Signal Meaning and Limitations (Priority: P2)

**Goal**: Preserve interpretable signal semantics, evidence lineage, explanation applicability, and reproducibility limitations without implying reliability or clinical meaning.

**Independent Test**: Synthetic result inspection distinguishes primary score semantics from all derived signal semantics; explanation metadata remains non-numeric, method/config provenance is complete, and safe limitations are preserved.

### Tests for User Story 4 (write first)

- [ ] T031 [P] [US4] Add explanation and score-semantics tests in `tests/test_signals_explanations.py` for method, target, output-space, calibration relationship, provenance, applicability states, and the absence of a generic numerical explanation-reliability score (FR-007–FR-009, FR-016, FR-023, SC-001, SC-009).
- [ ] T032 [P] [US4] Add run-manifest, immutability, determinism, and safe-diagnostic tests in `tests/test_signals_manifest.py` for exact source/method/state references, one seed/fold configuration, exclusions, detached serialization, and no restricted data (FR-006, FR-024–FR-026, SC-006, SC-008).

### Implementation for User Story 4

- [ ] T033 [US4] Implement explanation provenance/applicability records with no generic numeric score and preserve primary prediction score/calibration semantics in `src/safira/signals/stateless.py` and `src/safira/signals/records.py` (FR-007–FR-009, FR-016, FR-023).
- [ ] T034 [US4] Implement immutable privacy-safe `SignalRunManifest`, method/reference lineage, safe exclusion reasons, and deterministic detached serialization in `src/safira/signals/records.py` and `src/safira/signals/service.py` (FR-006, FR-024–FR-026).

**Checkpoint**: All four user stories have focused tests and their promised independent test criteria pass.

## Phase 7: Polish and Final Verification

**Purpose**: Verify cross-story acceptance, regression compatibility, and accurate implementation guidance.

- [ ] T035 Add synthetic end-to-end acceptance tests in `tests/test_signals_acceptance.py` covering all six dimensions, standalone binary/multi-label/multi-model inputs, missing and invalid evidence, exact identity, row-complete Feature 002 admission within verified Feature 003 inputs, cross-fitted references and grouping invariants, predictor-only alignment, and protected-test isolation (SC-001–SC-011).
- [ ] T036 Update `specs/004-safety-signal-extraction/quickstart.md` with verified public API usage, focused pytest commands, full regression command, expected non-value states, and current verifier/custodian limitations after implementation is complete (FR-029, SC-001–SC-011).
- [ ] T037 Run the complete `pytest` suite, including Feature 001–003 and existing adapter/context/assessment regressions; resolve Feature 004 regressions and confirm no existing contracts changed in `tests/` and `src/safira/` (FR-027, SC-008).
- [ ] T038 Run focused Feature 004 tests and `git diff --check`; inspect ordinary result, error, log, and serialization surfaces and confirm no training, reliability calibration, policy, assessment, or clinical behavior entered `src/safira/signals/` (FR-025, FR-028–FR-029, SC-008–SC-009, SC-011).

## Dependencies and Execution Order

### Phase dependencies

- Phase 1 is independent setup.
- Phase 2 blocks every user story: T002–T003 and T004–T005 are test-first contract pairs; T001 supplies synthetic fixtures.
- Phase 3 follows Phase 2. For each signal, tests precede implementation; identity admission precedes calculations.
- Phase 4 reference algorithms may be developed as internal pure helpers, but they cannot publish cohort-support claims, training feature sets, or fitted states from Feature 003 data until T028's trusted exact-scope verifier gate is complete.
- Phase 5 verification tests in T025 precede T028; only after T028 passes may public row construction, cohort-support publication, reference fitting/state publication, or protected handoff consume Feature 003 inputs.
- Phase 6 consumes the completed result/config/state contracts and precedes final acceptance.
- Phase 7 follows all user stories.

### User story dependencies

- **US1 (P1)** depends on Phase 2 only.
- **US2 (P1)** depends on Phase 2 and admitted exact-scope records from US1; internal reference helpers are independently testable with synthetic fixtures, while all public Feature 003-backed outputs remain gated on T028.
- **US3 (P1)** depends on US1 records and US2 frozen states for feature-set construction and protected apply.
- **US4 (P2)** depends on the shared records and methods from US1–US3.

### Three implementation batches

1. **Batch A — Core records and stateless signals (T001–T014)**: complete setup/foundation and US1. Keep edits to `records.py`, `base.py`, `validation.py`, `exceptions.py`, `stateless.py`, and initial `service.py` focused. Run record/admission and US1 tests.
2. **Batch B — Training references (T015–T024)**: own `reference.py` plus reference-specific validation. Complete cross-fitting, kNN and domain tests before integrating further. Run all Batch A focused tests plus reference tests.
3. **Batch C — Dataset boundaries and integration (T025–T038)**: own Feature 003 alignment, custodian boundary, explanation/run manifest integration, end-to-end tests and quickstart. Run focused Feature 004 tests, Feature 001–003 regressions, full pytest, and diff check.

Within each batch, run the named focused tests at its checkpoint; do not defer red/green verification until Batch C. Full pytest is required at final integration.

### Parallel opportunities

- T002 and T004 are independent test files; T006–T009, T015–T020, T025–T027, and T031–T032 are parallelizable test authoring tasks after their listed fixtures/contracts exist.
- Implementation tasks that edit the same shared module are intentionally sequential. Batch boundaries assign ownership of shared modules to reduce overlapping edits and repeated Codex sessions.

## MVP and Implementation Strategy

The first reviewable increment is Batch A: immutable and trusted exact-source admission plus the stateless signal path, with explicit states for every unavailable method. Batch B adds reference-based signals only after training-only fitting and grouped self-exclusion are demonstrated. Batch C completes Feature 003 integration, protected-test boundaries, documentation and cross-feature regression. None of these increments trains a safety estimator or emits Safira reliability or assessment decisions.

## Traceability Notes

- All FR-001–FR-029 are cited in task descriptions and mapped to the relevant test/implementation pairs.
- SC-001–SC-011 are covered by focused method tests, end-to-end acceptance, privacy inspection and regression verification. SC-010 maps to T016, T017, T020 and T022; SC-011 maps to T026, T030, T035 and T038.
- Cross-fitting tests allow fold assignments/scores to change when verified grouping changes; the invariants are complete patient-group exclusion, no leakage, and no patient identifiers in predictors or ordinary outputs. Renaming opaque group references without changing evidence/configuration must not alter the final full-training fitted reference.
- Feature 003 admission is row-complete: every embedded Feature 002 prediction must have independently verifiable exact-content admission lineage bound to its identity, association/occurrence, dataset and authorized partition. Dataset-level assertions cannot substitute for row admission. T025 negative tests precede the T028 public verifier gate; internal pure helper tests do not authorize public outputs.
- Synthetic tests validate implementation contracts only; method-specific empirical validation remains separate.
