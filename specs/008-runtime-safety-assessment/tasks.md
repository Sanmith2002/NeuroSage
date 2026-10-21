# Tasks: Research-Only Synthetic Runtime Safety Assessment

**Input**: Design documents from `specs/008-runtime-safety-assessment/`  
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/runtime-python.md`  
**Testing**: Synthetic tests are required by `FR-020` and MUST be written before the implementation they validate.  
**Organization**: Three sequential batches mapped to the user stories: trusted admission, frozen application, and result/lifecycle integration.

## Format

Every task uses `- [ ] T### [P?] [US#?] Description with exact file path`. `[P]` marks independent work; user-story labels occur only in story phases.

## Phase 1: Setup — Synthetic Test Support

**Purpose**: Provide reusable synthetic fixtures and keep all test inputs isolated from real data.

- [X] T001 Create synthetic prediction, original-training provenance, frozen artifacts, and test-only verifier builders in `tests/runtime_fixtures.py`.

---

## Phase 2: Foundational — Internal Result Contract

**Purpose**: Define the private, immutable, privacy-safe simulation result before admission and scoring work.

- [X] T002 [P] Write immutability, lifecycle-constant, exact-scope, and allowlisted-serialization tests in `tests/test_runtime_records.py`.
- [X] T003 Implement internal request/result records and a non-exporting runtime package initializer in `src/safira/runtime/_records.py` and `src/safira/runtime/__init__.py`.

**Checkpoint**: Internal records cannot represent a deployable, independently evaluated, or clinically valid outcome.

---

## Phase 3: User Story 1 — Admit One Synthetic Prediction (Priority: P1)

**Goal**: Admit the exact synthetic prediction and complete frozen package atomically before any score calculation.

**Independent Test**: Exact synthetic fixtures pass; altered prediction admission, association, registry identity, source scope, original inventory, artifact origin, policy protocol, or artifact bindings fail before signal/scoring calls and return no partial results.

### Tests for User Story 1 — Write First

- [X] T004 [P] [US1] Test exact prediction admission, source association, registry identity, and original Feature 003 inventory in `tests/test_runtime_admission.py`.
- [X] T005 [P] [US1] Test forged/missing artifact origin, policy protocol mismatch, cross-scope substitution, atomic shared failure, safe error codes without upstream text, and unexpected exception distinction in `tests/test_runtime_admission.py`.

### Implementation for User Story 1

- [X] T006 [US1] Implement exact prediction, registry, provenance, protocol, and estimator/calibrator/policy origin checks in `src/safira/runtime/_verification.py` using existing typed host checks.
- [X] T007 [US1] Add documented stable runtime failure types that discard upstream exception text and preserve unexpected programming errors in `src/safira/runtime/_exceptions.py`.

---

## Phase 4: User Story 2 — Apply the Frozen Research Package (Priority: P1)

**Goal**: Derive one query's approved signals, apply exact frozen Feature 005/006 transformations, and compare to the unchanged Feature 007 cutoff.

**Independent Test**: Synthetic parity tests pass for supported estimator families and methods; query evidence never enters reference fitting; exact cutoff equality follows the stored rule; unsupported schemas and altered reference or artifact digests do not produce a status.

### Tests for User Story 2 — Write First

- [X] T008 [P] [US2] Test single-record Feature 004 signal derivation, evidence and explanation availability states, original-training-only reference reconstruction, and no caller-row substitution in `tests/test_runtime_signals.py`.
- [X] T009 [P] [US2] Test frozen estimator and calibrator parity, numerical failures, and artifact mismatch in `tests/test_runtime_scoring.py`.
- [X] T010 [P] [US2] Test cutoff comparison equality, TRUST/CAUTION mapping, and DEFER for invalid/unavailable evidence in `tests/test_runtime_policy.py`.

### Implementation for User Story 2

- [X] T011 [US2] Implement private one-record Feature 004 signal construction and reference-state application in `src/safira/runtime/_signals.py`.
- [X] T012 [US2] Implement the private frozen Feature 005 schema/preprocessing/estimator and Feature 006 mapping adapter in `src/safira/runtime/_scoring.py`.
- [X] T013 [US2] Implement exact Feature 007 cutoff and comparison application without fitting or mutation in `src/safira/runtime/_policy.py`.

---

## Phase 5: User Story 3 — Preserve Synthetic Result and Lifecycle (Priority: P2)

**Goal**: Orchestrate the admitted one-record simulation and emit only a private, immutable, synthetic-only result.

**Independent Test**: Synthetic end-to-end success and failure cases preserve exact scope and lifecycle, expose no score or protected content, retain multi-scope independence, and cannot be imported as a public patient assessment API.

### Tests for User Story 3 — Write First

- [X] T014 [P] [US3] Test result `repr`, `str`, serialization, exception and diagnostic privacy in `tests/test_runtime_privacy.py`.
- [X] T015 [P] [US3] Test synthetic-only boundary, non-exported API, lifecycle constants, and no `SafetyAssessment` projection in `tests/test_runtime_boundaries.py`.
- [X] T016 [US3] Test synthetic end-to-end success, safe DEFER, atomic rejection, and non-pooled artifact handling across separate exact-scope calls in `tests/test_runtime_acceptance.py`.

### Implementation for User Story 3

- [X] T017 [US3] Implement the internal synthetic-only orchestration, shared-admission-before-scoring order, scoped outcomes, and cleanup of ephemeral values in `src/safira/runtime/_service.py`.
- [X] T018 [US3] Complete immutable result validation, safe reason allowlist, and non-reversible association binding in `src/safira/runtime/_records.py`.

---

## Phase 6: Polish and Cross-Feature Verification

**Purpose**: Verify the complete design boundary and document only validation actually run after implementation.

- [X] T019 Run focused Feature 008 tests and existing Feature 001–007 regression suites with the repository `uv` environment; record unique node totals in `specs/008-runtime-safety-assessment/quickstart.md`.
- [X] T020 Run `uv run python -m pytest -q` and `git diff --check`; record exact results in `specs/008-runtime-safety-assessment/quickstart.md`.
- [X] T021 Reconcile the final `specs/008-runtime-safety-assessment/quickstart.md` commands and recorded outcomes with `specs/008-runtime-safety-assessment/implementation-context.md` after verification is complete.

## Dependencies and Execution Order

### Batch Dependencies

- **Batch A — Trusted Runtime Admission**: T001–T007. T001 and T002 precede the records implementation; T004–T005 precede T006–T007. No scoring is available before the full admission helper passes its tests.
- **Batch B — Frozen Research Assessment**: T008–T013. Requires Batch A. All query/reference/scoring/policy tests precede their corresponding modules.
- **Batch C — Result Integration and Verification**: T014–T021. Requires Batch B. Privacy/boundary/end-to-end tests precede orchestration; broader regression follows integration.

### User Story Dependencies

- **US1 (P1)**: Depends on T001–T003; provides verified exact inputs for US2.
- **US2 (P1)**: Depends on US1; produces only an ephemeral mapped status for US3.
- **US3 (P2)**: Depends on US1 and US2; adds no live or public assessment surface.

### Parallel Opportunities

- T002 can be prepared alongside T001 after defining fixture fields.
- T004 and T005 can be authored in parallel once T001 fixture helpers exist.
- T008, T009, and T010 are independent test files and can be authored in parallel after Batch A fixtures are stable.
- T014 and T015 can be authored in parallel; T016 integrates their assertions.
- No implementation task may start before the corresponding test task is written and shown to fail for the intended behavior.

## Implementation Strategy

Deliver Batch A first and stop if shared admission cannot be established. Batch B proves one frozen synthetic assessment path without outputting a score. Batch C validates the internal-only lifecycle and privacy boundary. Only after all three batches pass should existing Feature 001–007 regressions and the full suite run. No production integration, independent evaluation, Feature 009, or clinical deployment work is included.
