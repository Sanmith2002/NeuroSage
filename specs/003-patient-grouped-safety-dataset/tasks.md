# Tasks: Patient-Grouped Safety Dataset Builder

**Input**: Approved documents in `/specs/003-patient-grouped-safety-dataset/`: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/dataset-python.md`, `quickstart.md`, and `implementation-context.md`.

**Prerequisites**: Python 3.11+, completed Feature 001 registry and Feature 002 collection, synthetic-only test data, Constitution v3.0.0.

**Tests**: Required by the specification and constitution. Write each focused test before its corresponding implementation where practical; confirm it fails for the missing behavior before implementing.

**Organization**: Tasks are ordered by shared setup/foundation and the five approved user stories. The implementation-batch section groups them into three cohesive review increments.

## Format: `[ID] [P?] [Story] Description`

- `[P]` means the task can run in parallel with other `[P]` tasks in the same dependency stage because it owns separate files.
- Story labels map to the five user stories in `spec.md`; setup, foundational, and polish tasks have no story label.
- Every task names its implementation or test file path.

## Phase 1: Setup

**Purpose**: Add Feature 003 package and synthetic test scaffolding without changing existing contracts.

- [ ] T001 [P] Create the `src/safira/dataset/` package skeleton and `src/safira/dataset/__init__.py`; do not edit `src/safira/registry/`, `src/safira/collection/`, `src/safira/context/`, or `src/safira/adapters/`.
- [ ] T002 [P] Add synthetic-only Feature 003 fixture builders in `tests/dataset_fixtures.py`, reusing `tests/conftest.py` and `tests/collection_fixtures.py` for exact registrations and immutable `PredictionRecord` inputs; do not use real patient records or clinical outcomes.

## Phase 2: Foundational

**Purpose**: Establish immutable dataset values and explicit, exact-scope trusted verification contracts used by every story.

- [ ] T003 Write value-contract tests for required target, outcome, linkage, protocol, exclusion, readiness, example, and manifest invariants in `tests/test_dataset_records.py`, including detached nested values, invalid binary coding, invalid partition roles, and privacy-safe errors.
- [ ] T004 Implement frozen dataset value types and typed privacy-safe exceptions in `src/safira/dataset/records.py` and `src/safira/dataset/exceptions.py`; enforce the `data-model.md` two-outcome target coding, exact source-qualified keys, four partition roles, allowed readiness states, recursive immutability, and detached serialization.
- [ ] T005 Write trusted-verifier contract tests in `tests/test_dataset_verification.py` proving Boolean flags, identifiers, self-asserted manifest completeness, and digests alone do not establish outcome, independence, linkage, or prior-history verification; check exact content/version/association/target and prior-history origin/source/scope/completeness/protected-membership binding and safe handling of verifier failures.
- [ ] T006 Define explicit verifier protocols and validate immutable, exact-scope verification results in `src/safira/dataset/verification.py`; keep outcome, model-development independence, patient linkage, prior-history coverage, and protected-test lifecycle checks distinct, with no global verifier state.
- [ ] T007 Export the foundational Feature 003 value types, verifier protocols, and typed errors from `src/safira/dataset/__init__.py`; export `DatasetBuilder` when implemented in T011 and preserve all existing top-level exports in `src/safira/__init__.py`.

## Phase 3: User Story 1 — Build Traceable Correctness Examples (Priority: P1)

**Goal**: Join eligible Feature 002 predictions to exact independently verified binary outcomes and derive traceable correctness targets.

**Independent Test**: Synthetic registered binary, multi-label, and multi-model predictions join only to matching target/outcome evidence. Correctness equals the existing registered predicted class comparison; mismatches and unknown evidence are excluded without changing primary scores or provenance.

### Tests for User Story 1

- [ ] T008 [US1] Write exact registration and target-binding tests in `tests/test_dataset_supervision.py`; cover unknown model/version/label, label ID collisions across models, target version/horizon mismatch, and mappings to registered positive/negative outcome meanings (FR-002–003, US1-AS1–2).
- [ ] T009 [US1] Write correctness and trusted-evidence tests in `tests/test_dataset_supervision.py` for both correct and incorrect registered `predicted_class` values, probability and continuous-score inputs, missing/non-binary/stale/conflicting outcomes, unverifiable outcomes, and unknown primary-model development lineage; prove no score cutoff or caller assertion creates a target (FR-004–007, US1-AS1/3/5).

### Implementation for User Story 1

- [ ] T010 [US1] Implement exact `ModelRegistry.get_metadata(model_id, model_version)` validation, target-to-label semantic compatibility, and equality-only correctness derivation in `src/safira/dataset/validation.py`; compare `PredictionRecord.primary.predicted_class` to the verified outcome mapped to the registered class and never reclassify `primary.value` (FR-002–003, FR-007).
- [ ] T011 [US1] Implement source-bound outcome/independence verification, exact patient-assessment-label-target joins, eligible-example assembly, and safe exclusion reasons in `src/safira/dataset/builder.py`; exclude failed or unknown checks and keep score semantics, source provenance, and evidence states intact (FR-001, FR-004–006, FR-008–010).
- [ ] T012 [US1] Add story acceptance tests in `tests/test_dataset_acceptance.py` for standalone single-label binary, multi-label, and independent multi-model contributors through live and trusted precomputed Feature 002 records; verify overlapping labels stay separate and no registry binding, classifier, or adapter prediction method is invoked (US1-AS1–5, SC-001, SC-005).

## Phase 4: User Story 2 — Keep Every Patient in One Partition (Priority: P1)

**Goal**: Resolve authorized patient aliases, detect duplicates/overlap, assign each patient group once, and preserve protected assignments across related dataset versions.

**Independent Test**: Synthetic aliases, visits, labels, contributors, cohorts, duplicates, supplied assignments, deterministic assignments, and prior manifests yield no cross-role patient group. Missing or incomplete history never produces a cross-version protection claim.

### Tests for User Story 2

- [ ] T013 [US2] Write patient-linkage tests in `tests/test_dataset_grouping.py` for namespace-qualified aliases, verified same-patient mappings, overlapping cohorts, unknown links, duplicate aliases, conflicting group identities, wrong-scope declarations, and rejection of name-only or Boolean-only assertions (FR-011, FR-013, US2-AS2/4).
- [ ] T014 [US2] Write duplicate and assignment tests in `tests/test_dataset_grouping.py` proving exact duplicate predictions do not increase example/patient counts, conflicting copies do not overwrite, repeated assessments remain distinct, and supplied assignments keep every related record in one role (FR-012–014, US2-AS1/3–4).

### Implementation for User Story 2

- [ ] T015 [US2] Implement verified linkage-declaration scope checks, opaque patient-group resolution, exact-duplicate detection, and conflicting-copy rejection in `src/safira/dataset/partitioning.py`; unknown aliases must remain unknown and cannot be considered disjoint (FR-011, FR-013).
- [ ] T016 [US2] Write deterministic allocation tests in `tests/test_dataset_grouping.py` for protocol-supplied role allocations and supplied assignments, stable results under input reordering, patient-level grouping across visits/labels/contributors, declared strata, and site/time constraints; instrument the allocator to verify it uses exactly the approved seed/configuration once and makes no alternative-seed attempts. Include a case where the approved seed is infeasible but an alternate seed would be favorable; assert the build reports infeasibility (FR-012–014, US2-AS1/4–5, SC-004).
- [ ] T017 [US2] Implement supplied and deterministic patient-group allocation in `src/safira/dataset/partitioning.py`; require the versioned protocol's roles, allocation intent, seed/algorithm version where applicable, strata, and hard constraints, with no default percentages/minima or constraint weakening (FR-012–014).
- [ ] T018 [US2] Write prior-history tests in `tests/test_dataset_grouping.py` for verified complete, missing, partial, contradictory, stale, wrong-origin, wrong-scope and unverifiable prior-assignment manifests; prove a self-asserted complete flag or digest cannot establish coverage, missing/unverifiable history never claims cross-version protection, and protocol-required verified history blocks publication as `NOT_READY` when unavailable (FR-014, FR-021, US2-AS4–5).
- [ ] T019 [US2] Implement trusted prior-history verification result validation and prior-manifest comparison in `src/safira/dataset/partitioning.py`; bind verification to actual manifest content/version and origin/source, requested/declaration scope, completeness evidence and relevant protected membership. Prevent silent movement of known protected groups; report missing/partial/unverifiable history as unknown without a cross-version protection claim, and return protocol-scoped `NOT_READY` when verified history is required (FR-014, FR-021–022).
- [ ] T020 [US2] Add integrated grouping acceptance tests in `tests/test_dataset_grouping.py` spanning multiple sources, patient aliases, repeated occurrences, overlapping labels, contributors, versions, exact duplicates, prior manifests, and all four partition roles (SC-002).

## Phase 5: User Story 3 — Protect Independent Supervision and Final Testing (Priority: P1)

**Goal**: Prevent primary-model overlap, temporal/preprocessing leakage, and development access to protected final-test observations or targets.

**Independent Test**: Synthetic source-development overlap, unknown independence, post-outcome evidence, held-out transform fitting, and protected-test inspection attempts are rejected, excluded, or reported not ready. Ordinary development outputs contain no protected rows or target distributions.

### Tests for User Story 3

- [ ] T021 [P] [US3] Write leakage tests in `tests/test_dataset_leakage.py` for primary-model training/tuning/calibration overlap, unknown lineage, outcome/correctness in predictor material, unavailable/post-outcome evidence timing, mismatched preprocessing identity, and transforms fitted on validation/calibration/final-test patients (FR-005, FR-015–016, US3-AS1–3).
- [ ] T022 [P] [US3] Write protected-test tests in `tests/test_dataset_protection.py` inspecting the complete ordinary `DatasetBuildResult` object, all public fields, repr/ordinary serialization and development-facing views; prove none exposes protected final-test rows, outcomes or correctness targets, while only protocol-approved integrity/structural summaries and a non-sensitive handoff receipt/status are available (FR-017, US3-AS4–5, SC-007).

### Implementation for User Story 3

- [ ] T023 [US3] Implement independence, predictor-field separation, timing, exact preprocessing identity, and declared transform-fit validation in `src/safira/dataset/validation.py`; exclude prohibited temporal or outcome-derived material and never fit or repair transforms (FR-005, FR-015–016).
- [ ] T024 [US3] Implement a separate explicit custodian-controlled protected-artifact handoff in `src/safira/dataset/builder.py`; pass row-bearing protected data only to the per-build handoff integration and return only its detached safe receipt/status. Ensure the ordinary `DatasetBuildResult`, every serialization form and all development-facing APIs never expose protected rows, outcomes or correctness targets. Require the handoff when the protocol requires protected-artifact delivery; do not add a storage/access-control service or claim later models are frozen (FR-017).
- [ ] T025 [US3] Add protected-supervision acceptance tests in `tests/test_dataset_protection.py` verifying final-test assignment isolation across prior builds, no final-test use for model/feature/threshold/eligibility/seed selection, full ordinary-result/serialization exclusion, successful authorized handoff without returning its rows, exact permitted summary behavior, and no final-test evaluation execution (FR-014, FR-017, SC-003, SC-007).

## Phase 6: User Story 4 — Reproduce and Audit a Dataset Version (Priority: P2)

**Goal**: Make eligible outputs, exclusions, and assignments reproducible and traceable without exposing patient data in ordinary reports.

**Independent Test**: Reordered equivalent inputs under the same protocol reproduce identical targets and assignments; changed source, target, outcome, linkage, or protocol creates a distinct immutable version or fails against protected history. Sensitive manifests remain detached and controlled.

### Tests for User Story 4

- [ ] T026 [US4] Write reproducibility/privacy tests in `tests/test_dataset_reproducibility.py` for canonical ordering, stable manifest content, source/version lineage, inclusion/exclusion coverage, safe aggregate reports, and no identifiers/raw values in routine errors (FR-021–023, US4-AS1/3).
- [ ] T027 [US4] Write immutability/version tests in `tests/test_dataset_reproducibility.py` proving original inputs, returned dictionaries, previous manifests, and prior dataset versions cannot be mutated through nested references or changed by corrected source data (FR-022, US4-AS2).

### Implementation for User Story 4

- [ ] T028 [US4] Implement canonical immutable dataset manifests and deterministic source/configuration/assignment lineage in `src/safira/dataset/records.py` and `src/safira/dataset/builder.py`; include verifier, target, linkage, protocol, transform, builder, exclusion, exact seed/configuration, and prior-history verification/coverage versions, and use digests only for change detection (FR-021–022).
- [ ] T029 [US4] Implement controlled audit references and privacy-safe aggregate serialization in `src/safira/dataset/builder.py`; retain per-record lineage/reasons only in restricted artifacts and ensure detached serialization cannot mutate accepted examples or manifests (FR-022–023).

## Phase 7: User Story 5 — Recognize Insufficient or Imbalanced Data (Priority: P2)

**Goal**: Report protocol-scoped readiness and inadequacy without fabricating or rebalancing data.

**Independent Test**: Synthetic limited, imbalanced, missing-label, missing-modality, and infeasible populations produce declared `NOT_READY` or `INSUFFICIENT_EVIDENCE` outcomes with scoped reasons, unchanged group assignments, and no fabricated examples.

### Tests for User Story 5

- [ ] T030 [US5] Write adequacy tests in `tests/test_dataset_adequacy.py` for patient-versus-row counts, positive/negative outcome and correctness-class support, missing labels/modalities, imbalanced or rare groups, infeasible constraints, and missing protocol criteria; assert no universal minimum or ratio is assumed and no rows are synthesized (FR-018–020, US5-AS1–3).

### Implementation for User Story 5

- [ ] T031 [US5] Implement versioned protocol adequacy evaluation and scoped `NOT_READY`/`INSUFFICIENT_EVIDENCE` results in `src/safira/dataset/partitioning.py` and `src/safira/dataset/builder.py`; distinguish patient counts from example counts, preserve partial label scope, and never rebalance, resample, drop classes, or relax constraints (FR-018–020).

## Phase 8: Final Integration and Verification

**Purpose**: Verify all stories together, preserve existing contracts, and document reproducible verification commands and limitations.

- [ ] T032 Add end-to-end synthetic acceptance tests in `tests/test_dataset_acceptance.py` covering all three classifier configurations, live/precomputed sources, exact correctness joins, all five evidence states, provenance failures, patient overlap, deterministic/supplied splits with exact-seed/no-alternative behavior, authoritative prior-history completeness and unknown-history handling, protected-test exclusion from the complete ordinary result/serialization plus separate authorized handoff, leakage, insufficiency, and immutability (FR-001–026, SC-001–008).
- [ ] T033 Add compatibility regression assertions in `tests/test_dataset_acceptance.py` confirming Feature 001 registry metadata, Feature 002 record/provenance/evidence values, `ModelAdapter`, `AdapterCapabilities`, `SafetyContext`, and `SafetyAssessment` contracts remain unchanged and no inference/training/calibration/signal/assessment path is invoked (FR-024–026, SC-007–008).
- [ ] T034 Run `pytest` on `tests/test_dataset_*.py`, then the relevant regression files `tests/test_registry_*.py`, `tests/test_collection_*.py`, `tests/test_safety_context.py`, `tests/test_assessment.py`, `tests/test_model_adapter.py`, and `tests/test_adapter_capabilities.py`, then run the full `pytest` suite; fix only Feature 003 defects and update `specs/003-patient-grouped-safety-dataset/quickstart.md` once with implemented public imports, runnable commands, observed results, a synthetic verification flow, and actual external-integration/storage limitations (FR-024–026, SC-007–008).

## Dependencies and Execution Order

### Phase dependencies

- Setup (Phase 1) has no code dependencies; T001 and T002 can proceed in parallel.
- Foundational (Phase 2) follows setup. T004 follows T003; T006 follows T005; T007 follows T004 and T006. No story work starts before T007.
- Each story follows the previous story to keep ownership of shared build/validation behavior explicit: US1 -> US2 -> US3 -> US4 -> US5. Final integration follows all stories.
- Within each story, focused tests precede their implementation. Acceptance tests verify the integrated behavior after the owning modules exist.

### Story dependency graph

```text
Setup T001-T002
  -> Foundation T003-T007
    -> US1 T008-T012
      -> US2 T013-T020
        -> US3 T021-T025
          -> US4 T026-T029
            -> US5 T030-T031
              -> Final verification T032-T034
```

US2 depends on US1's exact source-qualified examples; US3 depends on accepted group assignments; US4 records the results of prior stories; US5 evaluates protocol feasibility and adequacy after assignments are known. This ordered structure also limits repeated edits to the shared `builder.py`, `validation.py`, and `partitioning.py` modules.

### Parallel opportunities

- T001 and T002 can run in parallel.
- T001 and T002 are the only independent setup tasks; foundational tests and implementations follow the package and fixtures.
- In US3, T021 and T022 own separate test files and can be written in parallel before T023/T024; no implementation task begins until its corresponding test exists.
- Within US1, T008 and T009 can be prepared in the same test module only by one owner; do not edit `tests/test_dataset_supervision.py` concurrently. Implementation T010/T011 follows both tests.
- Within US2, T013 and T014 own the same test file and should be handled together by one owner; T016 and T018 also extend that file. Implementation in `partitioning.py` remains one owner for the batch.
- Within US3, T021 and T022 use separate files and can be written in parallel; implementations T023/T024 must follow the relevant tests.
- Within US4, T026 and T027 share one test module and one owner; no implementation starts until both tests are in place.
- Final T032 and T033 share `tests/test_dataset_acceptance.py`; assign one owner or combine as a single test-edit session. T034 follows all tests and updates the quickstart once with the actual verification results.

## Recommended Implementation Batches

Use three dependency-safe review batches. Finish and verify a batch before beginning the next; task IDs remain individually checkable.

1. **Batch A — Values, verification, and correctness joins (T001–T012)**: Establish package/fixtures, immutable values and verifier boundaries, then complete US1. This is the minimum useful increment for inspecting synthetic correctness examples; it does not yet establish patient-grouped split protection.
2. **Batch B — Patient linkage, deduplication, and protected assignments (T013–T020)**: Implement authorized linkage checks, duplicate handling, deterministic/supplied grouping and prior-manifest coverage. Do not claim cross-version protection when history is absent or incomplete.
3. **Batch C — Leakage, protected test, reproducibility, adequacy, and final verification (T021–T034)**: Complete the final three stories, manifests, privacy and acceptance coverage, then run focused, regression, and full suites and update quickstart.

## Implementation Strategy

- **MVP scope**: Batch A (US1) is the first reviewable increment. It creates verified synthetic correctness examples, but must not be described as partition-ready until Batch B and the applicable versioned protocol are implemented.
- **Incremental delivery**: Batch A -> Batch B -> Batch C. Each batch owns cohesive modules and has explicit tests before implementation. No batch introduces safety-estimator training or runtime assessment.
- **Verification order**: focused tests for the changed story; after each batch, run relevant focused regression tests. Run the complete pytest suite only in T034 after all Feature 003 stories and acceptance tests are integrated.

## Requirement Traceability

| Scope | Tasks | Coverage |
|---|---|---|
| Shared immutable values and verifier contracts | T003–T007 | data-model invariants; trusted exact-scope checks |
| US1 correctness examples | T008–T012 | FR-001–010; US1-AS1–5; SC-001/005 |
| US2 patient grouping/history | T013–T020 | FR-011–014, FR-021–022; US2-AS1–5; SC-002/004 |
| US3 supervision independence/leakage/final test | T021–T025 | FR-005, FR-015–017; US3-AS1–5; SC-003/007 |
| US4 reproducibility/privacy | T026–T029 | FR-021–024; US4-AS1–3; SC-004/007 |
| US5 limited data and adequacy | T030–T031 | FR-018–020; US5-AS1–3; SC-006 |
| Integrated acceptance and contract preservation | T032–T034 | FR-001–026; SC-001–008; constitution regression |
