# Implementation Plan: Model Registration and Registry for Safira

**Branch**: `feature/automatic-model-specific-training` (current checkout; the feature directory is `001-model-registration-registry`) | **Date**: 2026-10-15 | **Spec**: [spec.md](spec.md)

**Input**: Clarified Feature 001 specification and [requirements checklist](checklists/requirements.md)

## Summary

Add a small Python library registry for supervised multi-label primary classifiers. It validates and durably stores immutable, exact-version metadata in a local SQLite catalog, while keeping executable classifier and compatible adapter objects in a separately validated process-local binding. After restart, callers can inspect metadata, then must reattach the exact classifier and adapter before any downstream feature receives usable access. Registration performs no safety training, clinical prediction, or patient assessment.

## Technical Context

**Language/Version**: Python 3.11 or later

**Primary Dependencies**: Python standard library (`sqlite3`, `dataclasses`, `hashlib`, `json`, `pathlib`, typing); existing Safira adapter contracts; pytest for verification

**Storage**: One configurable local SQLite file for declarative registration metadata; live objects only in process memory. Default runtime location must be outside tracked source or under gitignored `artifacts/`.

**Testing**: pytest with deterministic, synthetic classifier artifacts/adapters and temporary catalogs; existing test suite as regression gate

**Target Platform**: Python library on supported local filesystems; current workspace is Windows, with no server or cloud dependency

**Project Type**: Single Python package under `src/safira`

**Performance Goals**: Correct exact-version retrieval and no overwritten records for the SC-002 catalog. No latency threshold was approved.

**Constraints**: No patient data or restricted datasets in the registry; no pickled executable objects; no standalone single-label binary classifier support; no training or assessment; no change to existing adapter/assessment contracts
**Scale/Scope**: Feature 001 registry only: multiple classifier IDs and multiple exact versions; at least two binary-outcome labels with continuous primary prediction outputs per registration

## Constitution Check

*GATE: Checked before research and again after Phase 1 design. No exception is requested.*

| Constitution requirement | Design evidence and gate result |
|---|---|
| I, II, XIII: post-hoc research scope and multi-label patient-label boundary | Registry records primary classifier definitions only, requires at least two labels, and does not calculate safety scores, statuses, or clinical decisions. **Pass** |
| III: preserve contracts | Reuses `ModelAdapter` and `AdapterCapabilities`; leaves `SafetyContext` and `SafetyAssessment` unchanged. Registry-side declarations and binding are new, limited abstractions. **Pass** |
| IV, VII: six dimensions and explicit availability | Captures capability flags as declarations; unsupported remains false/unavailable. No safety dimension or signal value is calculated or added. **Pass** |
| V, VIII, IX: exact model-specific package boundary and evidence-derived policy | Immutable exact classifier/version and adapter identity support future package linkage. No package, threshold, calibration, TRUST/CAUTION/DEFER, or readiness claim is produced. **Pass** |
| VI: independent safety data | Registration consumes no labelled safety dataset and makes no split or clinical validation claim. Future training evidence remains separate. **Pass** |
| X: privacy and claims | Persist bounded structural metadata, not patient observations/predictions; use safe error messages and ignored local catalog files. Describe Safira as a research prototype. **Pass** |
| XI: verification | Plan deterministic pytest coverage for success, invalid input, storage, concurrency, identity mismatch, no patient calls, and regression. **Pass** |
| XII: specification workflow | Uses the approved spec, this plan and Phase 0/1 artifacts; tasks and implementation follow later review. **Pass** |

Post-design recheck: [research](research.md), [data model](data-model.md), [Python contract](contracts/registry-python.md), and [quickstart](quickstart.md) retain all of the above boundaries. No identified constitutional conflict.

## Architecture and implementation approach

1. **Validate a registration request**: Check identifier/version syntax, supervised multi-label scope, unique label IDs, binary outcome meanings, continuous per-label output semantics and mapping, declarative input/modality/preprocessing identities, adapter version and `AdapterCapabilities` Boolean flags. Check `ModelAdapter` conformance and required method overrides by introspection without invoking patient-facing methods. Reject restricted payload content at this boundary.
2. **Check identity evidence**: Require deterministic SHA-256 fingerprints for the version-specific classifier artifact and adapter implementation. A minimal owner-supplied `IdentityProvider` returns evidence for the live classifier-adapter pair at registration and again at attachment. It hashes exact immutable artifact bytes; for non-file-backed models, it hashes an owner-defined deterministic representation of non-patient model state. For a multi-file artifact, the provider uses a deterministic manifest with normalized relative paths and content digests. It must attest that the classifier object it received was loaded from the material it fingerprinted and that the adapter is the identified implementation. Safira compares both fingerprints and the registered declarations; it does not infer object origin from a digest alone. The classifier owner or trusted loader supplies this provider and owns its truthfulness. Missing provider, unsupported identity material, an unable-to-verify result, or either fingerprint mismatch fails registration/attachment closed. No universal serialization format, model-framework integration, or change to `ModelAdapter` is introduced; see [research](research.md).
3. **Commit immutable metadata**: Store deeply immutable, canonical, versioned metadata in a local SQLite transaction keyed by `(model_id, model_version)`. Plain insertion enforces uniqueness and baseline duplicate rejection; concurrent-race behavior is completed and verified in US2. Use immutable nested representations or defensive copies so mutation through input or returned references cannot change an accepted definition. Classifier objects, adapter objects, callable providers, patient data, and prediction values never enter the catalog.
4. **Provide two lookup boundaries**: Exact metadata lookup reads and validates the persistent row. Usable resolution requires a process-local association of the same exact model/version, classifier, and compatible adapter. Registration may attach the submitted pair only after successful commit and validation. A restart restores metadata, never the executable association.
5. **Reattach deliberately**: On `attach`, compare current checkable artifact and adapter fingerprints, declared adapter name/version/capability snapshot, label/output mapping, input schema, modality and preprocessing identities with the immutable record. Publish the binding only after every check succeeds. A failed attach leaves any earlier valid binding unchanged. Do not choose a substitute or "latest" version.
6. **Fail with typed, safe exceptions**: Distinguish invalid field/schema, unsupported task, incompatible adapter, duplicate pair, unknown model ID, unknown version, missing binding, binding mismatch, and storage failure. Never echo raw payloads. Treat corrupt or unknown-schema storage as an error, not an empty catalog.

The full entity rules are in [data-model.md](data-model.md); proposed call semantics and errors are in [contracts/registry-python.md](contracts/registry-python.md). All decisions and alternatives are in [research.md](research.md).

## Planned verification and requirement traceability

| Scope | Planned pytest evidence |
|---|---|
| FR-001–FR-003, SC-001, SC-006 | Valid two-label and larger multi-label records; unique stable IDs; binary ground truth plus continuous score/probability definitions and exact class mappings; hard-only and malformed mappings rejected. |
| FR-004–FR-006 | Existing adapter subclass checks, exact Boolean capability validation, probability override and non-probability `predict` declaration, checkable artifact/adapter identity, deep-immutability checks, input/modality/preprocessing round-trip; mismatches rejected. |
| FR-007–FR-009, SC-002 | Several models and versions; subprocess restart returns metadata and refuses usable access until exact reattachment; material changes require new version; same-key concurrent insert accepts at most one. |
| FR-010, SC-003 | Parameterized invalid fields, task, adapter, missing ID/version, duplicate, invalid reattachment and storage failure with typed actionable errors and unchanged prior rows. |
| FR-011–FR-012, SC-004 | A registration test supplies neither labelled safety data nor a safety package; spies assert zero prediction, safety training, signal extraction, calibration, policy, or assessment calls during registration/lookup. |
| FR-013–FR-014 | Existing pytest suite remains green; privacy tests ensure no patient fields, raw restricted payloads, or observation values enter storage or routine errors. |

The [quickstart](quickstart.md) gives the future runnable verification workflow. No clinical performance validation is implied by these software tests.

## Project Structure

### Documentation (this feature)

```text
specs/001-model-registration-registry/
├── spec.md
├── checklists/requirements.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/registry-python.md
└── quickstart.md
```

### Source Code (repository root; proposed implementation, not created here)

```text
src/safira/
├── adapters/                  # Existing ModelAdapter and AdapterCapabilities
├── context/                   # Existing SafetyContext
├── models/                    # Existing SafetyAssessment
└── registry/                  # Proposed, self-contained feature package
    ├── __init__.py            # Public registry exports
    ├── definitions.py         # Frozen validated metadata definitions
    ├── identity.py            # Artifact/adapter identity verification boundary
    ├── storage.py             # Local SQLite metadata catalog
    ├── registry.py            # Register, lookup, attach, resolve
    └── exceptions.py          # Typed public errors
tests/
├── test_model_adapter.py      # Existing regression tests
├── test_adapter_capabilities.py
├── test_safety_context.py
├── test_assessment.py
├── test_registry_definitions.py          # Proposed
├── test_registry_storage.py              # Proposed
└── test_registry_integration.py          # Proposed
```

**Structure Decision**: Use the current single-package `src` layout and flat pytest directory. New modules are limited to the registry boundary and do not alter existing adapter or assessment files. Actual file split may be reduced during implementation if it improves clarity without changing the public contract.

## Complexity Tracking

No constitution violations or justified exceptions.
