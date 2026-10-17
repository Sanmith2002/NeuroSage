# Tasks: Feature 002 — Prediction/Evidence Collection and Precomputed Adapter

**Input**: Design documents in `specs/002-prediction-evidence-collection/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/collection-python.md`, `quickstart.md`, Safira Constitution v3.0.0, and completed Feature 001 registry contracts.

**Tests**: Use test-first development where practical. Write the listed pytest tests before their corresponding implementation and confirm that they fail for the intended missing behavior. All fixtures and payloads must be synthetic.

**Organization**: Tasks are grouped by user story. Feature 001 registry behavior and existing `ModelAdapter`, `AdapterCapabilities`, `SafetyContext`, and `SafetyAssessment` contracts must remain compatible throughout.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it targets different files and has no dependency on another incomplete task in the same phase.
- **[Story]**: Maps the task to a user story from `spec.md`.
- Every task names the concrete file or files it affects.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the minimal package and synthetic test support without changing existing Safira contracts.

- [ ] T001 Create the Feature 002 package skeleton and module docstrings in `src/safira/collection/__init__.py`, `src/safira/collection/records.py`, `src/safira/collection/validation.py`, `src/safira/collection/live.py`, `src/safira/collection/precomputed.py`, and `src/safira/collection/exceptions.py`; do not export incomplete operations yet.
- [ ] T002 [P] Create reusable synthetic one-label and multi-label classifiers/adapters, two differently shaped external source payload builders, and an independently controlled provenance-manifest test double in `tests/collection_fixtures.py`; extend `tests/conftest.py` only to expose shared pytest fixtures and use no patient data or ML dependency.

**Checkpoint**: The collection package imports without affecting existing public contracts, and synthetic fixtures are available for test-first work.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Define immutable records, common validation, and typed privacy-safe failures used by every story.

**⚠️ CRITICAL**: No user-story implementation begins until this phase passes its focused tests.

### Tests first

- [ ] T003 [P] Write failing record tests in `tests/test_collection_records.py` covering exact source-qualified uniqueness, all five evidence states, detached serialization, mutation of original nested inputs, mutation of returned nested values, unsupported non-detachable optional evidence becoming `invalid`, and rejection of non-detachable required values (FR-002, FR-011–012, FR-016–019; SC-001/003/004).
- [ ] T004 [P] Write failing error-contract and privacy tests in `tests/test_collection_errors.py` proving typed failures identify only safe categories/field paths and never echo opaque patient references, raw observations, JSON fragments, evidence values, or arbitrary adapter/verifier exception text (FR-018–019; SC-003/007).

### Implementation

- [ ] T005 Implement the typed collection exception hierarchy and safe reason/error codes in `src/safira/collection/exceptions.py`, including invalid request, source contract, contributor mapping, provenance, primary output, and evidence-access failures without changing registry exceptions (FR-018–020).
- [ ] T006 Implement deeply immutable or defensively copied `CollectionAssociation`, `ComponentIdentity`, `ComponentContribution`, `PrimaryOutput`, `EvidenceItem`, `SourceProvenance`, `PredictionRecord`, and `CollectionResult` values in `src/safira/collection/records.py`; enforce “opaque nonblank `patient_ref`, `assessment_ref`, `occurrence_ref`,” the five exact evidence states, recursive detachment on input, immutable nested values where supported, and detached public serialization (FR-002, FR-011–013, FR-016–019, FR-023).
- [ ] T007 Implement shared validation in `src/safira/collection/validation.py`: exact association/key checks; strict primary values that are “strict int/float, never bool/string; finite; probability in [0,1], score in registered domain”; exact registered comparison/boundary class mapping; structural input type/shape/modality checks; and privacy-safe deep-detachment failure handling (FR-003, FR-007–009, FR-016–019).
- [ ] T008 Define only stable foundational public value/error exports in `src/safira/collection/__init__.py` and add import-surface assertions to `tests/test_collection_records.py`; do not modify `src/safira/adapters/`, `src/safira/context/`, `src/safira/models/`, or `src/safira/registry/` (FR-020–021).
- [ ] T009 Run `tests/test_collection_records.py`, `tests/test_collection_errors.py`, `tests/test_model_adapter.py`, `tests/test_adapter_capabilities.py`, `tests/test_safety_context.py`, `tests/test_assessment.py`, and `tests/test_registry_acceptance.py`; resolve only Feature 002 failures in `src/safira/collection/records.py`, `src/safira/collection/validation.py`, `src/safira/collection/exceptions.py`, and `src/safira/collection/__init__.py` before continuing.

**Checkpoint**: Shared records cannot be changed through accepted or returned references, validation is strict and privacy-safe, and existing Safira contracts still pass.

---

## Phase 3: User Story 1 — Collect a Registered Classifier's Predictions (Priority: P1) 🎯 MVP

**Goal**: Collect exact, attributable primary outputs from a validated live Feature 001 classifier-adapter binding for standalone binary and multi-label classifiers.

**Independent Test**: Register synthetic one-label and multi-label classifiers with probability and continuous-score labels, collect one assessment, and verify exact model/version/label association, registered value semantics and class mapping, one primary call per label, explicit initial evidence states, and privacy-safe rejection of invalid requests.

### Tests first

- [ ] T010 [P] [US1] Write failing live happy-path tests in `tests/test_collection_live.py` for standalone binary and multi-label registrations, probability versus continuous-score semantics, per-label records without cross-label normalization, exact associations, registered class mapping, exactly one call to the declared `value_source` per label, capability-gated optional-method invocation, zero calls for unsupported capabilities, and explicit initial evidence states for supported results and extraction failures (US1.1–3; FR-001–004, FR-007–012; SC-001/003/005/006).
- [ ] T011 [P] [US1] Write failing live negative tests in `tests/test_collection_live_errors.py` for unknown model/version/label, unattached or incompatible binding, input schema/modality mismatch before inference, Boolean/string/NaN/infinite/out-of-range primary values, adapter exceptions, and privacy-safe atomic failure with unchanged registry metadata; rely on the existing Feature 001 invalid-registration regression for its mandatory class-mapping invariant rather than constructing malformed registry metadata (US1.4–5; FR-003–004, FR-007–009, FR-018–019; SC-003/007).

### Implementation

- [ ] T012 [US1] Implement `collect_live` in `src/safira/collection/live.py` using exact `ModelRegistry.resolve_usable`, registered label/input declarations, and only the registered `predict_probability` or `predict` source; derive the primary class solely from the stored mapping and never create reliability or safety outputs (FR-001–004, FR-007–009, FR-021).
- [ ] T013 [US1] Implement live source provenance plus capability-gated optional evidence invocation and initial evidence-state construction in `src/safira/collection/live.py`; classify supported successful values and extraction failures using shared validation, ensure unsupported methods have zero calls, and ensure output records own detached copies of adapter-returned values. Advanced category-specific interpretation normalization remains T030/T031 (FR-010–012, FR-018–020).
- [ ] T014 [US1] Export `collect_live` from `src/safira/collection/__init__.py`, run `tests/test_collection_live.py` and `tests/test_collection_live_errors.py`, and fix only `src/safira/collection/live.py`, `src/safira/collection/validation.py`, `src/safira/collection/records.py`, and the collection export until User Story 1 passes independently.

**Checkpoint**: Live collection works independently for both eligible classifier forms and preserves all existing Safira behavior.

---

## Phase 4: User Story 2 — Ingest Precomputed Predictions Without Loading the Classifier (Priority: P1)

**Goal**: Admit versioned external predictions without a live classifier only when their source contract, exact registration, association, and independently checked provenance all agree; expose admitted values through a scoped Precomputed Adapter.

**Independent Test**: Ingest equivalent outputs from two unrelated synthetic source layouts after a subprocess restart with no live binding, verify standardized equivalence and distinct provenance, and reject every malformed, mismatched, stale, replayed, reassigned, or assertion-only case without original-model inference.

### Tests first

- [ ] T015 [P] [US2] Write failing source-contract tests in `tests/test_collection_source_contracts.py` for two unrelated `(contract_id, version)` layouts; constructor-injected trusted integrations; duplicate/conflicting derived contract keys; isolation between collectors with different configurations; rejection of payload/per-call attempts to install or replace handlers; duplicate JSON members; nonfinite constants; unknown versions; contract-specific required fields/extensions; separately supplied compatible association/meaning declarations; conflicting declarations; and no inferred field meanings (US2.3/7–8; FR-009, FR-012–014, FR-019; SC-003/005).
- [ ] T016 [P] [US2] Write failing provenance tests in `tests/test_collection_provenance.py` using an independently controlled synthetic manifest that binds exact covered primary/evidence content, exact registered model/version/label/selectors, opaque patient/assessment/occurrence, and provenance-event ID; reject changed content, wrong contributor, reassignment, duplicate event IDs, stale/revoked/reused events, caller Booleans/event IDs, submitted-only digests, batch-wide checks, and missing/conflicting scope fields (US2.1/5; FR-005–006, FR-016–019; SC-002/003/007).
- [ ] T017 [P] [US2] Write failing precomputed-ingestion tests in `tests/test_collection_precomputed.py` for metadata-only lookup after a genuine subprocess restart, no original classifier calls or registry attachment, exact output semantics/class mapping, `input_verification=unavailable` when no raw input exists, atomic rejection without partial records, rejection of an output claiming an unregistered contributor that therefore has no Feature 001-compliant mapping with no fallback diagnostic record, and equivalent standardized meanings across live/precomputed modes with different assurance levels (US2.1–3/6–8; FR-003, FR-005, FR-007–009, FR-014, FR-019; SC-001–003/005/006).
- [ ] T018 [P] [US2] Write failing scoped Precomputed Adapter tests in `tests/test_collection_adapter.py` for one admitted contributor/association, correct saved probability/score/class behavior, actual available capabilities only, rejection of another label or occurrence, explicit unavailable evidence errors, zero inference, and defensive copies that cannot mutate the accepted record (US2.4; FR-015–016, FR-020–021; SC-002/004/006).

### Implementation

- [ ] T019 [US2] Implement immutable `TrustedSourceIntegration` pairs and `PrecomputedCollector(registry, integrations)` in `src/safira/collection/precomputed.py`; derive exact keys from the finite injected iterable, reject duplicate/conflicting keys, retain a detached read-only mapping, satisfy T015's collector-isolation cases, and accept no payload/per-call or global runtime installation. Implement configured source-contract selection, strict duplicate/nonfinite JSON parsing, normalized candidates, and source-specific declaration validation without hardcoded PD fields (FR-009, FR-012–014, FR-018–019).
- [ ] T020 [US2] Implement the executed trusted provenance-check boundary in `src/safira/collection/precomputed.py`, validating independently controlled evidence for exact content, contributor, selectors and association plus freshness/revocation and replay/reuse status; require source-specific deterministic comparison while adding no universal cryptography or persistent replay service (FR-005–006, FR-016–019).
- [ ] T021 [US2] Implement `PrecomputedCollector.ingest` in `src/safira/collection/precomputed.py` using only its constructor-injected integration mapping, exact `ModelRegistry.get_metadata`, contributor/label semantics and class mapping, explicit `input_verification=unavailable` when raw input is absent, atomic envelope admission, detached immutable records, and no requirement for a live binding or original classifier (FR-001–009, FR-014, FR-016–019, FR-021).
- [ ] T022 [US2] Implement the one-record, one-association `ModelAdapter`-compatible Precomputed Adapter view in `src/safira/collection/precomputed.py`; validate the opaque request reference on every method, advertise only genuinely returnable capabilities, return fresh defensive copies, and never attach the view under the original registry identity (FR-010–016, FR-020–021).
- [ ] T023 [US2] Export `PrecomputedCollector`, trusted-integration value/protocol types, and adapter operations from `src/safira/collection/__init__.py`, run `tests/test_collection_source_contracts.py`, `tests/test_collection_provenance.py`, `tests/test_collection_precomputed.py`, and `tests/test_collection_adapter.py`, and resolve only Feature 002 failures in `src/safira/collection/precomputed.py`, `src/safira/collection/validation.py`, `src/safira/collection/records.py`, and the collection export.

**Checkpoint**: Precomputed mode works without classifier access, distinguishes its assurance from live mode, and fails closed on provenance, schema, identity, association, replay, or mutation errors.

---

## Phase 5: User Story 3 — Keep Component Contributors Independently Traceable (Priority: P2)

**Goal**: Preserve each independently registered contributor and its provenance when a component groups outputs, including overlapping labels and mixed single-label/multi-label models.

**Independent Test**: Collect synthetic all-single-label and mixed components with varying contributor counts, overlapping labels, two versions of one model, and external selectors different from registered selectors; confirm exact independent records and explicit incomplete/invalid component outcomes.

### Tests first

- [ ] T024 [P] [US3] Write failing component tests in `tests/test_collection_component.py` for all-single-label and mixed contributors, arbitrary contributor counts, overlapping label IDs, two exact versions, explicit external-to-registered selector translation, expected-set completeness, duplicate/conflicting source-qualified keys, mixed associations, and no merging, substitution, latest-version fallback, or classifier fusion (US3.1–4; FR-001–003, FR-006, FR-016–017; SC-001/003/005).

### Implementation

- [ ] T025 [US3] Implement owner/trusted-integration contributor-map validation in `src/safira/collection/validation.py`, comparing external selector translation with exact Feature 001 model/version/label, registered selector, value kind/source, scale/direction, outcomes, class mapping, and applicable input/preprocessing/adapter declarations; reject missing, duplicate, ambiguous and conflicting entries (FR-003, FR-006, FR-014, FR-016–017).
- [ ] T026 [US3] Integrate component identity, expected contributor-set completeness, unique source-qualified records, and atomic mixed-association/duplicate handling into `src/safira/collection/live.py` and `src/safira/collection/precomputed.py` without persisting a component entity or aggregating predictions (FR-001–003, FR-006, FR-016–017, FR-021).
- [ ] T027 [US3] Run `tests/test_collection_component.py` together with `tests/test_collection_live.py` and `tests/test_collection_precomputed.py`; fix only component behavior in `src/safira/collection/validation.py`, `src/safira/collection/live.py`, `src/safira/collection/precomputed.py`, and `src/safira/collection/records.py` until User Story 3 passes independently and earlier stories remain green.

**Checkpoint**: Components group contributors without changing any contributor's task type, identity, version, label semantics, or provenance.

---

## Phase 6: User Story 4 — Inspect Evidence Availability Without Inferring Safety (Priority: P2)

**Goal**: Preserve available evidence and explicit unsupported/missing/unavailable/invalid states, including interpretation and calibration/explanation distinctions, without computing safety signals.

**Independent Test**: Exercise every optional evidence category and all five states from live and precomputed sources, including extraction exceptions and uncalibrated explanations paired with calibrated primary probabilities; verify a valid primary remains explicitly incomplete and context projection changes no existing behavior.

### Tests first

- [ ] T028 [P] [US4] Write failing evidence tests in `tests/test_collection_evidence.py` covering all existing adapter evidence categories and `available`, `unsupported`, `missing`, `unavailable`, `invalid`; zero calls for unsupported methods; sanitized extraction failures; finite/shape/source validation; repeated-output provenance; modality identifiers; completeness/cohort scope; explanation target/output-space/calibration/truncation; and valid primaries retained as incomplete (US4.1–5; FR-010–013, FR-018–019, FR-023; SC-003–005/007).
- [ ] T029 [P] [US4] Write failing SafetyContext compatibility tests in `tests/test_collection_context.py` proving probability-only population of `prediction_probability`, continuous scores retained outside that field, exact source/assessment/evidence-state metadata retained in a detached projection, five-state authority remains in the standardized record, projected mutation cannot affect the record, and no `SafetyAssessment` or reliability/status value is created (FR-007, FR-020–021; SC-002/004/006).

### Implementation

- [ ] T030 [US4] Implement shared evidence validation and interpretation normalization in `src/safira/collection/validation.py`, enforcing the five states, contract-valid empty values only, finite numeric evidence, source/association/shape/meaning checks, and invalid optional evidence without fabricated values or primary rejection (FR-010–013, FR-019, FR-023).
- [ ] T031 [US4] Complete advanced category-specific evidence interpretation and precomputed/live parity in `src/safira/collection/live.py` and `src/safira/collection/precomputed.py`, reusing T013's live capability invocation and initial-state path rather than duplicating it; normalize explanation/calibration, cohort scope, modality, repeat and other source meanings, isolate optional exceptions, and return owned immutable/defensive copies (FR-010–013, FR-018–021, FR-023).
- [ ] T032 [US4] Implement detached `to_safety_context` projection in `src/safira/collection/records.py`, export it through `src/safira/collection/__init__.py`, and run `tests/test_collection_evidence.py`, `tests/test_collection_context.py`, `tests/test_safety_context.py`, and `tests/test_assessment.py` until User Story 4 passes without changing existing context or assessment contracts.

**Checkpoint**: Evidence availability is explicit and reviewable, while collection still performs no safety analysis or clinical decision.

---

## Phase 7: Final Acceptance, Regression, and Documentation

**Purpose**: Verify all requirements and success criteria together, preserve existing behavior, and publish accurate validation instructions.

- [ ] T033 Write end-to-end synthetic acceptance tests in `tests/test_collection_acceptance.py` covering all three classifier configurations and both source modes, live/precomputed equivalence with distinct assurance, subprocess restart behavior, constructor-injected integration isolation with no payload-installed handler, explicit unavailable input verification when precomputed raw input is absent, content-bound provenance negatives, replay/reassignment protection, deep immutability of original and returned nested values, privacy probes, and zero safety-training/signal/calibration/policy/assessment operations (FR-001–023; SC-001–007).
- [ ] T034 Run the focused suite in `tests/test_collection_records.py`, `tests/test_collection_errors.py`, `tests/test_collection_live.py`, `tests/test_collection_live_errors.py`, `tests/test_collection_source_contracts.py`, `tests/test_collection_provenance.py`, `tests/test_collection_precomputed.py`, `tests/test_collection_adapter.py`, `tests/test_collection_component.py`, `tests/test_collection_evidence.py`, `tests/test_collection_context.py`, and `tests/test_collection_acceptance.py`; resolve discovered defects only in the named tests and `src/safira/collection/` while preserving the approved architecture.
- [ ] T035 Run the complete pytest suite under `.venv`, including existing `tests/test_model_adapter.py`, `tests/test_adapter_capabilities.py`, `tests/test_safety_context.py`, `tests/test_assessment.py`, and `tests/test_registry_*.py`; fix Feature 002 regressions only in `src/safira/collection/records.py`, `src/safira/collection/validation.py`, `src/safira/collection/live.py`, `src/safira/collection/precomputed.py`, `src/safira/collection/exceptions.py`, `src/safira/collection/__init__.py`, or the exact failing `tests/test_collection_*.py` file and leave established contracts unchanged.
- [ ] T036 Update `specs/002-prediction-evidence-collection/quickstart.md` with the exact working focused/full test commands, observed results, public collection import paths, deterministic synthetic validation flow, and known PD-specific onboarding limitations; do not claim direct PD compatibility or clinical safety.

**Checkpoint**: Feature 002 is fully verified against the specification, Constitution v3.0.0, and existing Safira regression suite.

---

## Dependencies & Execution Order

### Phase dependencies

- **Phase 1 — Setup**: Starts immediately.
- **Phase 2 — Foundational**: Depends on Phase 1 and blocks every user story.
- **Phase 3 — US1 Live Collection**: Depends on Phase 2; this is the smallest runnable MVP.
- **Phase 4 — US2 Precomputed Ingestion**: Depends on Phase 2 and can proceed alongside US1 after the shared foundation is stable.
- **Phase 5 — US3 Component Traceability**: Depends on US1 and US2 because it composes both collection paths and their exact contributor semantics.
- **Phase 6 — US4 Evidence Inspection**: Depends on US1 and US2 because it completes optional evidence behavior for both paths; it does not depend on US3.
- **Phase 7 — Final Acceptance**: Depends on all selected user stories; full Feature 002 completion requires US1–US4.

### User-story dependency graph

```text
Setup → Foundation ─┬→ US1 Live ───────────┬→ US3 Components ─┐
                    └→ US2 Precomputed ────┘                  ├→ Final Acceptance
                                      └────────→ US4 Evidence ┘
```

### Within each phase

- Write the story's pytest tasks first and confirm the intended failures before implementation.
- Implement shared values and validation before orchestration.
- Resolve exact Feature 001 metadata/bindings before calling or admitting any source output.
- Validate required fields and provenance before publishing a result; optional evidence failures remain isolated.
- Run the story checkpoint before starting a dependent story.

### Task-level critical path

- Foundation: T001/T002 → T003/T004 → T005 → T006 → T007 → T008 → T009.
- US1: T010/T011 → T012 → T013 → T014.
- US2: T015/T016/T017/T018 → T019 → T020 → T021 → T022 → T023.
- US3: T024 → T025 → T026 → T027.
- US4: T028/T029 → T030 → T031 → T032.
- Final verification: T033 → T034 → T035 → T036.

## Parallel Opportunities

- T001 and T002 can proceed in parallel.
- T003 and T004 can proceed in parallel after setup.
- T010 and T011 can proceed in parallel before US1 implementation.
- T015, T016, T017, and T018 can proceed in parallel because they target separate test modules.
- US1 and US2 can proceed in parallel after Phase 2 if separate workers avoid concurrent edits to shared foundation files.
- T028 and T029 can proceed in parallel before US4 implementation.
- US3 and US4 can proceed in parallel after US1 and US2, with coordination around `validation.py`, `live.py`, `precomputed.py`, and `records.py`.

## Parallel Examples

### User Story 1

```text
Task T010: Live probability/score happy-path tests in tests/test_collection_live.py
Task T011: Live invalid-input and fail-closed tests in tests/test_collection_live_errors.py
```

### User Story 2

```text
Task T015: Source-contract parsing tests in tests/test_collection_source_contracts.py
Task T016: Content/contributor/association-bound provenance tests in tests/test_collection_provenance.py
Task T017: Precomputed ingestion and restart tests in tests/test_collection_precomputed.py
Task T018: Scoped Precomputed Adapter tests in tests/test_collection_adapter.py
```

### User Story 4

```text
Task T028: Five-state evidence tests in tests/test_collection_evidence.py
Task T029: SafetyContext projection compatibility tests in tests/test_collection_context.py
```

## Requirement Traceability

| Requirement area | Primary tasks |
|---|---|
| Classifier forms, exact identity and live binding (FR-001–004) | T010–T014, T024–T027, T033 |
| Checked precomputed provenance and source contracts (FR-005–006, FR-014) | T015–T023, T033 |
| Primary numeric/class semantics and input validation (FR-007–009) | T007, T010–T012, T015/T017, T021, T033 |
| Optional evidence and explanations (FR-010–013, FR-023) | T013, T018/T022, T028–T033 |
| Precomputed Adapter and association isolation (FR-015–017) | T006, T016–T018, T020–T027, T033 |
| Privacy, safe failures and atomic outcomes (FR-018–019) | T003–T007, T011, T015–T021, T024–T031, T033 |
| Existing contract preservation and excluded safety work (FR-020–021) | T008–T014, T018/T022–T023, T029/T032–T035 |
| Automated reproducible verification (FR-022; SC-001–007) | All test tasks, T009, T014, T023, T027, T032–T036 |
| Content-bound provenance, replay/reassignment and immutability refinement | T003, T006, T016, T018, T020–T022, T033 |

## Implementation Strategy

### Suggested MVP

1. Complete Setup and Foundation (T001–T009).
2. Complete User Story 1 live collection (T010–T014).
3. Stop and validate the live-only MVP independently.

The full P1 capability requires adding User Story 2 (T015–T023), because external precomputed outputs are a primary Feature 002 objective.

### Incremental delivery

1. **Foundation**: Immutable records, strict validation, safe errors, and synthetic fixtures.
2. **US1**: Live exact-version prediction collection.
3. **US2**: Versioned precomputed ingestion with executed provenance checks and scoped adapter.
4. **US3**: Independent component contributors and overlapping-label traceability.
5. **US4**: Complete optional evidence states and context projection.
6. **Final**: End-to-end acceptance, full regression, and verified quickstart.

## Notes

- `[P]` denotes file-level parallel work only; tasks sharing collection implementation files remain sequential.
- Do not add a patient database, REST API, universal cryptographic format, persistent replay service, safety dataset, signal computation, training, calibration, policy, reliability score, or TRUST/CAUTION/DEFER output.
- Do not edit established adapter, context, assessment, or registry contracts unless an independently reviewed blocker demonstrates a required compatibility change.
- Mark each checkbox complete only after its implementation and stated verification pass.
