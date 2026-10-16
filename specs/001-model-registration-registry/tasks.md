# Tasks: Model Registration and Registry for Safira

**Input**: Approved design documents in `/specs/001-model-registration-registry/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/registry-python.md`, `quickstart.md`

**Tests**: Automated pytest tasks are required by Constitution v2.0.0 and the user request. Write acceptance-focused tests before the corresponding implementation and use synthetic classifier artifacts/adapters only.

**Organization**: Tasks follow the three approved user stories after shared setup and foundation. Each implementation task cites its primary files; do not change the existing adapter, context, or assessment contracts without a separately justified finding.

## Phase 1: Setup

**Purpose**: Establish only the registry package and reusable synthetic test setup. Python 3.11+ and pytest already exist; SQLite is in the standard library, so no runtime dependency or service is added.

- [X] T001 Create the registry package entry point in `src/safira/registry/__init__.py` and shared temporary-catalog, synthetic classifier artifact, and test-only `ModelAdapter` fixtures in `tests/conftest.py`; keep fixtures free of patient data.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish tested local metadata storage, identity verification, and typed errors used by all stories.

- [X] T002 [P] Write SQLite storage contract tests in `tests/test_registry_storage.py` for schema-version initialization, canonical metadata round-trip, composite `(model_id, model_version)` uniqueness, close/reopen retrieval, and fail-closed handling of corrupt or unknown-schema catalogs.
- [X] T003 [P] Write identity contract tests in `tests/test_registry_identity.py` using a fake trusted loader/provider and synthetic classifier/adapter artifact bytes; assert deterministic SHA-256 fingerprints, evidence tied to the supplied live pair, true versus false `loaded_pair_verified` attestation, mismatch rejection, and fail-closed behavior when evidence is missing or unverifiable, without requiring a framework-specific serialization format.
- [X] T004 Implement typed registry exceptions in `src/safira/registry/exceptions.py` for invalid registration, unsupported task, incompatible adapter, duplicate registration, unknown model, unknown version, unattached model, binding mismatch, and storage failure.
- [X] T005 [P] Implement foundational SQLite metadata storage in `src/safira/registry/storage.py` using only `sqlite3`, a composite `(model_id, model_version)` primary key, immutable plain `INSERT`, explicit transaction/rollback, validated serialization, and no executable or patient data; enforce uniqueness and translate a basic composite-key conflict to `DuplicateRegistrationError`.
- [X] T006 [P] Implement `IdentityProvider.identify_loaded_pair(classifier, adapter)` and immutable `IdentityEvidence` in `src/safira/registry/identity.py`; require classifier artifact and adapter implementation SHA-256 fingerprints plus actual-Boolean `loaded_pair_verified`, validate evidence shape, fail closed on missing/false/unverifiable evidence, and impose no universal model serialization or `ModelAdapter` change.

**Checkpoint**: Storage primitives and checked identity inputs are ready; every story can build on them without modifying current Safira contracts.

---

## Phase 3: User Story 1 — Register and Retrieve a Classifier (Priority: P1, MVP)

**Goal**: Register a valid supervised multi-label primary classifier and retrieve its exact immutable metadata with its validated active classifier-adapter association.

**Independent Test**: Register a synthetic classifier with at least two labels and continuous per-label outputs, retrieve its metadata by exact ID/version, resolve the associated pair, and verify no safety or patient-facing work occurred.

### Tests for User Story 1 (write first)

- [ ] T007 [US1] Write definition tests in `tests/test_registry_us1.py` for deeply immutable model-version and label definitions, at least two distinct labels, binary positive/negative ground truth, explicit output selectors, continuous probability or non-probability score meaning/scale/direction, and a declared score-to-class mapping; prove mutations to original nested inputs and returned metadata cannot change an accepted record (FR-001–FR-003, FR-006; US1 acceptance 1, 4, 6; SC-001, SC-006).
- [ ] T008 [US1] Write registry tests in `tests/test_registry_us1.py` for valid registration with neither labelled safety data nor a safety package, exact metadata lookup, adapter/capability declarations, active usable resolution, exact input-schema/modality/preprocessing round-trip, no patient-facing method calls, and no training/calibration/signal/policy/assessment calls (FR-004–FR-006, FR-009, FR-011–FR-013; US1 acceptance 1–6; SC-001, SC-004, SC-006).

### Implementation for User Story 1

- [ ] T009 [US1] Implement deeply immutable `RegisteredModelVersion`, `LabelDefinition`, `AdapterDeclaration`, and `InputDefinition` values in `src/safira/registry/definitions.py`; enforce the data-model rules that model ID/version are “Nonblank exact strings, no leading/trailing whitespace or control characters,” task type is “Fixed supervised multi-label classification declaration,” and label IDs are “Stable, nonblank, unique within the model version”; use immutable nested collections or defensive copies on both input and output (FR-001–FR-006).
- [ ] T010 [US1] Implement `ModelRegistry.register` and exact `get_metadata` in `src/safira/registry/registry.py`; validate the configured trusted `IdentityProvider` evidence/attestation and current `ModelAdapter`/`AdapterCapabilities` declarations, persist metadata through `storage.py`, bind only the validated submitted classifier-adapter pair, and do not train, predict on patient data, extract signals, calibrate, select policy, or assess (FR-002–FR-006, FR-009, FR-011–FR-014; US1 acceptance 1–4; SC-001, SC-004).
- [ ] T011 [US1] Implement `attach` and `resolve_usable` behavior for an active registration in `src/safira/registry/registry.py` and export the public registry contract from `src/safira/registry/__init__.py`; return metadata, classifier, and adapter together only after exact compatibility checks (FR-004, FR-005, FR-009, FR-013; US1 acceptance 5; SC-006).

**Checkpoint**: US1 independently supports registration, metadata retrieval, and usable access to the registered pair before any safety package exists.

---

## Phase 4: User Story 2 — Keep Multiple Models and Versions Distinct (Priority: P2)

**Goal**: Preserve records across restarts, keep multiple model IDs and versions separate, require explicit reattachment, and reject duplicates without overwrite.

**Independent Test**: Register the SC-002 review catalog in a temporary SQLite file, reopen it, verify every exact metadata lookup, show that usable access requires valid reattachment, and race duplicate submissions so only one succeeds.

### Tests for User Story 2 (write first)

- [ ] T012 [P] [US2] Write persistence and reattachment tests in `tests/test_registry_us2.py` that launch a genuine subprocess against the same temporary catalog after registration; verify metadata survives the process boundary, no live binding is restored, usable access fails until attach, and reattaching the exact compatible classifier-adapter pair succeeds. Also cover at least three model IDs and three versions of one ID, wrong classifier/adapter/schema/preprocessing rejection, and no latest-version fallback (FR-005–FR-007, FR-009; US2 acceptance 1, 2, 4–6; SC-002).
- [ ] T013 [P] [US2] Write duplicate-race tests in `tests/test_registry_concurrency.py` using two independent registry connections with a synchronization barrier; assert one insert succeeds, the competing insert raises the duplicate error, and the accepted record is never overwritten (FR-008; US2 acceptance 3; SC-002).

### Implementation for User Story 2

- [ ] T014 [US2] Complete restart reattachment and immutable compatibility checks in `src/safira/registry/registry.py` and `src/safira/registry/identity.py`; call the configured provider again for the candidate pair and compare both fingerprints, adapter identity/version/capabilities, label/output mappings, input/modalities, and preprocessing before publishing a process-local binding, preserving any prior valid binding on failed attachment (FR-005–FR-007, FR-009; US2 acceptance 2, 4–6).
- [ ] T015 [US2] Complete and verify only the concurrent race handling in `src/safira/registry/storage.py`: use the foundational immutable insert/uniqueness behavior from T005, ensure two simultaneous same-key registrations have at most one commit, translate the losing key race to `DuplicateRegistrationError`, and leave the winning row unchanged; do not reimplement basic insertion or uniqueness (FR-008; US2 acceptance 3; SC-002).

**Checkpoint**: US2 survives restart for metadata, requires verified reattachment for usable access, maintains exact-version isolation, and prevents concurrent overwrite.

---

## Phase 5: User Story 3 — Reject Invalid Definitions and Lookups (Priority: P2)

**Goal**: Reject invalid scope, schemas, capabilities, identities, and lookups with typed, actionable, privacy-safe errors while preserving stored records.

**Independent Test**: Exercise each invalid category and missing lookup; check the exact error category, absence of unintended writes/binding changes, and no sensitive payload in database bytes or routine errors.

### Tests for User Story 3 (write first)

- [ ] T016 [P] [US3] Write parameterized definition and compatibility tests in `tests/test_registry_us3.py` for blank/whitespace/control-character IDs, duplicate or incomplete labels, one-label/standalone binary and unsupported task types, non-binary outcomes, hard-only 0/1 outputs, missing/ambiguous continuous-score mappings, invalid capability values, and incompatible or unimplemented adapter methods (FR-001–FR-006, FR-010; US3 acceptance 1–4, 9; SC-003).
- [ ] T017 [P] [US3] Write error, privacy, and state-preservation tests in `tests/test_registry_errors.py` for unknown ID versus unknown version, duplicate registration, incompatible/missing reattachment, corrupt or invalid stored metadata, failed registration/attachment leaving previous records and bindings unchanged, and patient/restricted payload rejection without echo or persistence (FR-008–FR-010, FR-014; US3 acceptance 5–10; SC-003).

### Implementation for User Story 3

- [ ] T018 [US3] Complete schema and output validation in `src/safira/registry/definitions.py`; enforce exactly two explicit ground-truth outcomes per label, declared continuous output semantics and class mapping, unique stable IDs/selectors, and actual Boolean capability values while keeping primary prediction scores distinct from Safira reliability scores (FR-001, FR-003–FR-004, FR-006; US3 acceptance 2, 3, 9).
- [ ] T019 [US3] Complete compatibility checks and actionable typed error translation in `src/safira/registry/registry.py` and `src/safira/registry/exceptions.py`; distinguish invalid field, unsupported task, incompatible adapter, duplicate, unknown model, unknown version, unattached, and binding mismatch without substituting another version or echoing submitted payloads (FR-004–FR-005, FR-009–FR-010, FR-014; US3 acceptance 1–5, 7–9; SC-003).
- [ ] T020 [US3] Complete fail-closed serialization and storage error handling in `src/safira/registry/storage.py`; reject corrupt/unknown-schema catalogs and semantically invalid stored rows as `RegistryStorageError`, and ensure registration declarations cannot persist patient observations or restricted clinical data (FR-010, FR-014; US3 acceptance 6, 10; SC-003).

**Checkpoint**: US3 reports the correct failure category and leaves valid records, bindings, and sensitive data untouched across invalid inputs.

---

## Phase 6: Polish and Cross-Cutting Verification

**Purpose**: Prove the completed story set against the measurable outcomes and preserve existing Safira behavior.

- [ ] T021 Write end-to-end synthetic acceptance tests in `tests/test_registry_acceptance.py` for SC-001, SC-002, SC-004, and SC-006, including registration without labelled safety data or a safety package; exact round-trip of label outcomes, continuous primary-output semantics/mapping, artifact identity, input schemas, modality declarations, preprocessing identities, and supported versus unsupported capabilities.
- [ ] T022 Update `specs/001-model-registration-registry/quickstart.md` with final test paths, exact commands, expected outcomes, and limitations; keep examples synthetic and preserve the research-prototype/no-clinical-validation claim.
- [ ] T023 Run the full pytest suite with `\.venv\Scripts\python.exe -m pytest -q`, including existing `tests/test_model_adapter.py`, `tests/test_adapter_capabilities.py`, `tests/test_safety_context.py`, and `tests/test_assessment.py`; fix registry regressions without changing those existing contracts or tests (FR-013; SC-004).

---

## Dependencies and Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001 establishes isolated registry and synthetic fixtures; no added package dependency.
- **Foundational (Phase 2)**: T002 and T003 are independent contract-test tasks after T001. T004 supplies shared errors. T005 and T006 then implement separate storage and identity modules in parallel. T005 owns base insert, uniqueness, and ordinary duplicate translation; T015 later adds only race-specific guarantees. All user stories depend on T001–T006.
- **US1 (Phase 3)**: T007 precedes T009; T008 exercises the public registry flow before T010/T011 implement it. T009 can begin after T007 and the foundation; T010 depends on T004–T006, T008, and T009; T011 depends on T010. US1 is the MVP.
- **US2 (Phase 4)**: T012 and T013 can be prepared in parallel after US1's public API exists. T014 depends on T012 and T010/T011. T015 depends on T013, T005, and T004; it adds only simultaneous-write race behavior on top of T005. Full US2 acceptance depends on both T014 and T015.
- **US3 (Phase 5)**: T016 and T017 can be written in parallel after the API from US1 and the persistence behavior from US2 exist. T018 depends on T016 and T009; T019 depends on T016/T017 and T018; T020 depends on T017 and T005. Complete US3 after T018–T020.
- **Polish (Phase 6)**: T021 depends on all stories. T022 records final behavior after T021. T023 is the final regression gate after all implementation and test tasks.

### User Story Dependencies

- **US1 (P1)**: Depends on shared foundation only; no dependency on later stories.
- **US2 (P2)**: Builds on US1's registration and exact lookup API to add durable restart/reattachment acceptance and concurrent duplicate guarantees.
- **US3 (P2)**: Builds on US1/US2 public behavior and hardens the tested invalid/error paths.

### Parallel Opportunities

- T002 and T003 can run together because they write separate test files.
- T005 and T006 can run together because they write separate registry modules after T004.
- T012 and T013 can run together because they write separate US2 test files.
- T014 and T015 can run together after both US2 test tasks; they modify separate registry and storage modules.
- T016 and T017 can run together because they write separate US3 test files.

### User Story Parallel Examples

```text
After T001:
  T002: tests/test_registry_storage.py
  T003: tests/test_registry_identity.py

After US1 is complete:
  T012: tests/test_registry_us2.py
  T013: tests/test_registry_concurrency.py

After US2 is complete:
  T016: tests/test_registry_us3.py
  T017: tests/test_registry_errors.py
```

## Implementation Strategy

1. Complete Setup and Foundation; use the standard library only.
2. Deliver the MVP with US1: immutable supervised multi-label definitions, continuous per-label output semantics, exact metadata lookup, and validated active association.
3. Add US2 restart persistence, exact-version reattachment, and duplicate-race guarantees; verify the SC-002 catalog using synthetic records.
4. Add US3 complete validation, error taxonomy, privacy, and fail-closed storage behavior.
5. Complete acceptance coverage, update quickstart, and run the full existing plus new pytest suite.

No task adds standalone single-label binary support, safety-model training, calibration, policy selection, runtime assessment, arbitrary operating thresholds, or REST endpoints.
