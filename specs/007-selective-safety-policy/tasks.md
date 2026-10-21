---
description: "Test-first task list for Safira Feature 007 Selective Safety Policy"
---

# Tasks: Selective Safety Policy

**Input**: Design documents from `specs/007-selective-safety-policy/`
**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/policy-python.md`, `quickstart.md`, `implementation-context.md`
**Scope**: Feature 007 only. Do not modify Features 001–006 public contracts, access protected final-test evidence, or implement Feature 008.

Every test task must run before its associated implementation and demonstrate expected failure first. Use synthetic fixtures only. Each task lists owned files; parallel tasks must not edit the same file.

## Phase 1: Setup

**Purpose**: Create only the package/test foundation needed by the approved design.

- [x] T001 Create `src/safira/policy/__init__.py` and ensure the existing `tests/` layout is ready for `tests/policy_fixtures.py`; keep package exports empty until T006 confirms the approved cohort-only public boundary.
- [x] T002 Create synthetic exact-scope Feature 001–006 records, independently controlled verifier/ledger doubles, original training evidence, and a separate policy-selection `DatasetBuildResult` in `tests/policy_fixtures.py`; include no real patients or protected rows.

## Phase 2: Foundational Contracts

**Purpose**: Define immutable protocol/scope/outcome records and safe errors before selection.

- [x] T003 [P] Write failing tests for deep immutability, exact scope uniqueness, required protocol settings, pre-outcome index rules, and allowlisted serialization in `tests/test_policy_records.py`.
- [x] T004 Implement `PolicyScope`, `PolicySelectionProtocol`, evidence references, outcome, and safe summary record validation in `src/safira/policy/records.py` to satisfy T003; recursively freeze inputs and return detached serialization.
- [x] T005 [P] Write failing tests that error strings, `repr`, and exception chaining never expose patient, row, raw evidence, verifier, or upstream exception content in `tests/test_policy_privacy.py`.
- [x] T006 Implement stable privacy-safe typed errors and export only approved cohort-level records/service names from `src/safira/policy/exceptions.py` and `src/safira/policy/__init__.py`; do not export scoring or per-patient helpers.
- [x] T007 Write failing verifier-result contract tests for executed, exact-bound checks and rejection of Boolean/digest/status assertions in `tests/test_policy_verification_contract.py`.
- [x] T008 Implement typed verification-check records and explicit injected verifier protocols in `src/safira/policy/verification.py`; satisfy T007 without accepting caller-constructed checks as a verification substitute.

## Phase 3: User Story 1 — Admit Evidence and Reconstruct Frozen Scores (Priority: P1)

**Goal**: Admit complete trusted evidence and privately score a new independent policy cohort using the exact frozen upstream model chain.

**Independent Test**: Synthetic exact bundles pass; any missing, stale, changed, overlapping, or incompatible element fails before correctness outcomes are evaluated.

### Tests for User Story 1 — write first

- [x] T009 [P] [US1] Write failing tests for Feature 002 admission lineage, complete new Feature 003 validation inventory, exact target/association binding, missing/extra/duplicate/changed rows, and stale manifests in `tests/test_policy_dataset_admission.py`.
- [x] T010 [P] [US1] Write failing tests for exact Feature 001 registry compatibility, Feature 005 artifact digest/origin, Feature 006 calibrator origin/base linkage, and separation of original versus policy provenance in `tests/test_policy_artifact_admission.py`.
- [x] T011 [P] [US1] Write failing tests for policy-patient disjointness from original training/validation/calibration and protected membership; incomplete history, unknown links, forged checks, and stale linkage must reject or return `NOT_READY` in `tests/test_policy_disjointness.py`.

### Implementation for User Story 1

- [x] T012 [US1] Implement complete trusted-host admission for predictions, policy dataset/manifest, outcomes, registry bindings, artifact origins, full inventory, and patient-history/linkage evidence in `src/safira/policy/verification.py`; satisfy T009–T011 and never infer disjointness from incomplete history.
- [x] T013 [US1] Write failing tests proving original Feature 004 references can be re-derived only from verified original Feature 003 training predictors, reproduce exact frozen state digests, and reject unavailable or altered evidence in `tests/test_policy_reference_reconstruction.py`.
- [x] T014 [US1] Implement private original Feature 004 reference-state reconstruction and exact Feature 005/006 digest matching in `src/safira/policy/references.py`; policy evidence must never enter fitting.
- [x] T015 [US1] Write failing tests proving Feature 004 signal rows are derived internally from admitted Feature 002 predictions using the original `SignalProtocol` and reconstructed references, with one-to-one exact row alignment; reject caller-supplied/forged rows and incompatible signal methods in `tests/test_policy_signals.py`.
- [x] T016 [US1] Implement private signal-row derivation and alignment in `src/safira/policy/signals.py`, reusing Feature 004 record-level stateless extraction semantics and only verified reconstructed original reference state; satisfy T015 without refitting on policy evidence.
- [x] T017 [US1] Write failing numeric-equivalence tests for exact Feature 005 schema/preprocessing/estimator plus Feature 006 mapping, logistic and constant-baseline semantics, malformed artifacts, nonfinite values, and no per-patient return in `tests/test_policy_scoring.py`.
- [x] T018 [US1] Implement private frozen Feature 005 transformation/estimator and exact Feature 006 mapping application in `src/safira/policy/scoring.py`; satisfy T017 and return only an ephemeral internal score batch.
- [x] T019 [US1] Write failing atomic service tests proving no reference reconstruction or score computation occurs until every shared evidence, origin, inventory, and disjointness check passes in `tests/test_policy_service_admission.py`.
- [x] T020 [US1] Implement atomic shared admission and private score-path orchestration in `src/safira/policy/service.py`; satisfy T019, preserve separate original/policy provenance, and return safe non-success when trusted evidence or exact reference reproduction is absent.

**Checkpoint**: Evidence is verified before score reconstruction; no patient score or runtime API is public.

## Phase 4: User Story 2 — Select an Empirical Patient-Level Cutoff (Priority: P1)

**Goal**: Select one deterministic TRUST cutoff per exact scope that maximizes eligible-patient coverage under the approved empirical risk ceiling.

**Independent Test**: Synthetic one-index-assessment-per-patient fixtures yield independently reproducible risk, coverage, cutoff, tie, empty-set, and constant-score results.

### Tests for User Story 2 — write first

- [x] T021 [P] [US2] Write failing tests for one deterministic index assessment per patient/scope, outcome-blind eligibility, cross-scope isolation, repeated visits, duplicate patients, and unsupported index rules in `tests/test_policy_index_assessment.py`.

### Implementation for User Story 2

- [x] T022 [US2] Implement protocol-bound patient eligibility and deterministic one-index-assessment-per-patient selection in `src/safira/policy/selection.py`; use only the new policy validation partition.
- [x] T023 [P] [US2] Write failing tests for exact empirical risk/coverage formulas, candidate cutoff generation, equality semantics, maximum feasible coverage, support rules, and deterministic ties in `tests/test_policy_selection.py`.
- [x] T024 [US2] Implement permitted cutoff enumeration, empirical risk/coverage, maximum-coverage choice, equality/ties, and constant-score/empty-set rules in `src/safira/policy/selection.py`; satisfy T023 without guarantee claims or default thresholds.
- [x] T025 [P] [US2] Write failing tests for empty TRUST selection (undefined risk), constant-score all-or-none behavior, ceiling failure, inadequate support, and safe non-success outcomes in `tests/test_policy_selection_edges.py`.
- [x] T026 [US2] Implement scope-local `NOT_READY`, `INSUFFICIENT_EVIDENCE`, and no-feasible-cutoff handling in `src/safira/policy/selection.py`; satisfy T025 and never create a successful empty-set policy.

**Checkpoint**: Each exact scope has at most one selected-but-unevaluated outcome; no cross-scope pooling or empty-set zero-risk claim is possible.

## Phase 5: User Story 3 — Freeze a Traceable Selected Policy (Priority: P2)

**Goal**: Produce an immutable per-scope artifact with separate original and policy evidence provenance, aggregate selection results, and non-deployable lifecycle markers.

**Independent Test**: Synthetic artifact round-trips preserve exact scope and bindings while excluding all row-level and protected values.

### Tests for User Story 3 — write first

- [x] T027 [P] [US3] Write failing tests for artifact field allowlists, nested immutability, canonical digest, separate original/policy provenance, exact compatibility, and mutation-safe round-trip in `tests/test_policy_artifacts.py`.
- [x] T028 [P] [US3] Write failing tests inspecting the entire outcome/artifact, `repr`, exceptions, and serialization for absence of patient/group/occurrence IDs, outcomes, row scores, raw evidence, restricted manifests, protected data, and verifier payloads in `tests/test_policy_artifact_privacy.py`.
- [x] T029 [P] [US3] Write failing lifecycle tests for selection evidence spent, independent evaluation incomplete, protected-test access false, deployment false, and clinical validity false in `tests/test_policy_lifecycle.py`.

### Implementation for User Story 3

- [x] T030 [US3] Implement deeply immutable `SelectivePolicyArtifact`, canonical allowlisted export, digest validation, and exact compatibility checks in `src/safira/policy/artifacts.py`; satisfy T027–T028 without row-level data.
- [x] T031 [US3] Implement per-scope artifact freezing and safe non-success outcomes in `src/safira/policy/service.py`; satisfy T029, include only permitted aggregates, and never attach an artifact to non-success.

**Checkpoint**: Success is `SELECTED_UNEVALUATED` and non-deployable; policy data is spent and final evaluation remains separate.

## Phase 6: User Story 4 — Enforce Evaluation and Runtime Boundaries (Priority: P2)

**Goal**: Keep policy selection, independent final evaluation, and future runtime assessment separate.

**Independent Test**: Synthetic service and package inspection prove no protected input access or patient-level scoring/status API.

### Tests for User Story 4 — write first

- [x] T032 [P] [US4] Write failing tests that protected rows/outcomes cannot be supplied, loaded, serialized, or accessed and that no public `predict`, `apply`, calibrated-score, `SafetyContext`, or `SafetyAssessment` operation exists in `tests/test_policy_boundaries.py`.

### Implementation for User Story 4

- [x] T033 [US4] Enforce cohort-only public exports, fixed lifecycle fields, spent-selection status, protected-test exclusion, and safe readiness/status mapping in `src/safira/policy/__init__.py` and `src/safira/policy/service.py`; satisfy T032 without modifying Features 001–006.
- [x] T034 [US4] Write end-to-end synthetic acceptance tests for exact-scope admission, artifact origin, reference-digest reproduction, internally generated signal-row alignment, independent policy evidence, patient-level risk/coverage, immutable artifacts, empty/constant score cases, privacy, and safe failures in `tests/test_policy_acceptance.py`.

**Checkpoint**: Feature 007 freezes only a selected policy and neither evaluates on final test nor assesses patients at runtime.

## Phase 7: Final Verification and Documentation

**Purpose**: Verify the complete approved scope and document actual operation and limitations.

- [x] T035 Update `specs/007-selective-safety-policy/quickstart.md` with actual cohort-level public operations, verified commands, expected results, trusted-host limitations, and the no-inference boundary; report only tests actually run.
- [x] T036 Run focused Feature 007 and unchanged Feature 001–006 compatibility tests, then the full pytest suite and `git diff --check`; fix only Feature 007 defects and check tasks complete only after successful verification in `specs/007-selective-safety-policy/tasks.md`.

## Requirement Traceability

| Requirements / criteria | Tasks |
|---|---|
| FR-001–FR-008, FR-026; SC-001–SC-002 | T009–T012, T019–T020 |
| FR-009–FR-011, FR-030; SC-001, SC-005, SC-008 | T013–T020, T032–T033 |
| FR-012–FR-019; SC-003–SC-004 | T021–T026, T034 |
| FR-020–FR-025; SC-006–SC-007 | T027–T031, T033–T035 |
| FR-027–FR-029; SC-008–SC-009 | T032–T036 |
| US1 acceptance | T009–T020, T034 |
| US2 acceptance | T021–T026, T034 |
| US3 acceptance | T027–T031, T034 |
| US4 acceptance | T032–T036 |

## Dependencies & Execution Order

- Phase 1 creates package and synthetic fixtures.
- Phase 2 defines shared immutable records, exceptions, and verifier contracts; it blocks all user stories.
- Phase 3 (US1) builds exact evidence admission, original reference reconstruction, private scoring, and atomic orchestration.
- Phase 4 (US2) depends on US1's admitted ephemeral score batch.
- Phase 5 (US3) depends on US2's selected outcome.
- Phase 6 (US4) verifies public/protected-data boundaries.
- Phase 7 runs integration and regression verification.

### Safe Parallel Work

- After T002, T003 and T005 may be authored in parallel (different test files). T007 follows the foundational record tasks.
- After T008, T009–T011 may be authored in parallel (different test files); T012 implements only after all red checks exist.
- T027–T029 may be authored in parallel (different test files); T030/T031 start after their tests.
- Do not parallelize implementation edits to `verification.py`, `selection.py`, `service.py`, or `__init__.py`. User stories run sequentially because each consumes the prior story's output.

## Suggested Implementation Batches

1. **Batch A — Foundation and trusted scoring bridge (T001–T020)**: immutable records, verifier contract, full admission, original reference reconstruction, private signal-row generation, frozen scoring, atomic gate. Stop if exact state reproduction or trust checks fail.
2. **Batch B — Empirical cutoff and artifact freeze (T021–T031)**: index-assessment rule, risk/coverage selection, empty/constant behavior, immutable artifact and lifecycle.
3. **Batch C — Boundaries and final verification (T032–T036)**: protected/public API boundaries, synthetic end-to-end acceptance, quickstart, all Feature 001–006 regressions and full pytest.

## Implementation Strategy

Complete Setup and Foundational first, then Batch A as the trust/compatibility gate. Batch B adds the policy-selection value. Batch C is required to claim Feature 007 software-scope completion. Real evidence-dependent operations remain `NOT_READY` until the approved protocol, original verified inputs, trust/linkage providers and new patient-disjoint policy-selection build are available.

## Notes

- All tasks are unchecked; this document is not evidence of implementation.
- `[P]` is used only for test tasks in distinct files with no incomplete dependency.
- No task authorizes real patient data, protected final-test access, upstream contract changes, numerical clinical thresholds, or Feature 008.
- Run focused tests at batch checkpoints and the full suite at final integration; repeat only to resolve a concrete failure.
