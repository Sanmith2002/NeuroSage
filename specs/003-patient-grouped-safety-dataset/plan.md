# Implementation Plan: Patient-Grouped Safety Dataset Builder

**Branch**: `feature-03/Safety-Dataset-Builder` | **Date**: 2026-10-17 | **Spec**: [spec.md](spec.md)

**Input**: Clarified Feature 003 specification and Safira Constitution v3.0.0.

## Summary

Add a small `safira.dataset` library package that consumes immutable Feature 002 `PredictionRecord` values, exact Feature 001 registrations, independently checked target/outcome and independence evidence, authorized patient-linkage declarations, and a versioned research protocol. It produces immutable source-qualified correctness examples, patient-grouped partition assignments, a controlled manifest, and safe readiness/exclusion summaries. It does not collect predictions, fit transformations, train or calibrate safety estimators, compute safety signals, or assess predictions.

## Technical Context

**Language/Version**: Python 3.11+.

**Primary Dependencies**: Python standard library only; existing Safira registry and collection packages. `pytest` for automated tests; no new runtime dependency.

**Storage**: In-memory immutable values returned to the caller. The caller or authorized research custodian persists manifests, assignment history, and protected data using its approved restricted store. Feature 003 adds no database, storage service, or default export format.

**Testing**: Existing pytest suite; focused synthetic Feature 003 unit, negative, and end-to-end acceptance tests. Re-run relevant registry/collection regression suites and full `pytest` suite during implementation.

**Target Platform**: Existing Python library on Python 3.11+ platforms supported by the repository.

**Project Type**: Python library under `src/safira`.

**Performance Goals**: No numeric throughput or latency target is justified. Construction must terminate with an explicit result or typed failure for finite supplied collections; correctness, determinism, and safe failure are the measurable goals.

**Constraints**: Do not change Feature 001/002 or `ModelAdapter`, `AdapterCapabilities`, `SafetyContext`, or `SafetyAssessment` contracts. Do not retain raw patient data in logs/manifests by default. Do not infer unknown identity, target mapping, independence, or cohort disjointness. Preserve protected-test isolation and fail closed when protocol requirements cannot be checked.

**Scale/Scope**: Research dataset construction for finite, caller-supplied prediction/outcome collections. No universal row limit, patient minimum, allocation ratio, balance target, or supported clinical population is defined.

## Constitution Check

**Gate before research — PASS**

- Uses binary correctness supervision derived from the exact registered `predicted_class` and verified target outcome; it does not create disease predictions or new thresholds (Principles I, VIII).
- Keeps each patient and source-qualified contributor/label record traceable and in one partition (Principles II, VI).
- Consumes existing registry and collection contracts without changing adapters, contexts, assessments, or primary pipelines (Principle III).
- Preserves evidence availability and does not compute any safety dimensions (Principles IV, VII).
- Prepares data only; no safety-estimator training, calibration, policy selection, score, or status generation is in scope (Principles V, IX, XII).
- Requires documented independent supervision and keeps the final test protected under a versioned protocol (Principle VI).
- Uses privacy-safe diagnostics, synthetic tests, deterministic manifests, and research-prototype claims (Principles X, XI, XIII).

**Gate after design — PASS with external integration prerequisites**

The design assigns execution of outcome, independence, and patient-linkage checks to explicitly injected trusted research integrations. A check result is accepted only for the exact subject and scope that was checked; caller flags, matching identifiers, and content digests alone are not proof. Trust still rests on the integration's configured authority and access to independently controlled evidence; Safira does not promise universal verification. Dataset-specific protocol, outcome and linkage evidence must be supplied before a real cohort can be admitted. Those are data/integration prerequisites, not a reason to change existing contracts or add security infrastructure.

## Architecture and Design

1. **Pure dataset builder boundary**: A `DatasetBuilder` receives a registry, explicit trusted verifier/linkage integrations, and one versioned `EvaluationProtocol`. It accepts Feature 002 records and supplemental target, outcome, evidence-timing, independence, and linkage declarations. No integration is global or discovered implicitly.
2. **Validate before join**: Check Feature 002 record type and provenance, exact Feature 001 model/version/label metadata, and target-to-label compatibility. The registry is used for exact metadata lookup only; no classifier is attached, invoked, or re-collected.
3. **Verified binary supervision**: The trusted outcome integration executes a source-specific check bound to outcome content, patient/assessment, label, target definition/version and applicable timing. A separate executed independence check evaluates documented primary-model development lineage against the approved protocol. Missing, stale, conflicting, non-binary, out-of-scope, or unverifiable material yields a controlled exclusion or `NOT_READY`; it never produces a target.
4. **Correctness target**: Reuse `PredictionRecord.primary.predicted_class` and the registered label's positive/negative outcome meanings. Map the verified target outcome through an explicit target-to-label semantic declaration and emit integer `1` for equality or `0` for inequality. Never re-derive a class from a primary score or introduce a threshold.
5. **Patient group resolution**: Consume an authorized, versioned opaque linkage/overlap declaration. The injected linkage verifier checks its source, scope, integrity, and conflicts. Keep source namespaces; do not match patient identity in Safira. Unknown or conflicting cross-source equivalence cannot be treated as disjoint for a combined scope.
6. **Protocol-controlled partitioning**: The versioned protocol either supplies complete patient-group assignments or declares a deterministic group allocator, seed, role allocation intent and constraints. The initial allocator is intentionally simple and stable (canonical opaque group key plus a stable hash); it honors protocol-provided allocation settings and then validates hard site/time/group constraints. It does not search seeds or weaken constraints. Complex or infeasible constraints require custodian-supplied assignments or return `INSUFFICIENT_EVIDENCE`/`NOT_READY`.
7. **Protected test and history**: The builder emits development partitions and a distinct protected-test artifact, plus a sensitive immutable assignment/lineage manifest for custodian-controlled persistence. A caller supplies prior approved manifests for version checks. Existing group assignments and final-test membership are immutable across related builds unless an explicitly authorized protocol lifecycle action permits a new version; a new seed or source name cannot silently move a protected group into development. Ordinary reports expose only allowed protocol summaries, never protected row values or correctness distributions before release.
8. **Leakage and readiness checks**: Keep verified outcomes, correctness targets, group identity, verification metadata, partition membership, and audit details out of prediction-time feature material. Supplemental timing evidence declares when primary/evidence values were available; unknown or post-outcome material is excluded when prohibited by protocol. Validate declared transform history for held-out fitting; Feature 003 fits no transform. Missing prerequisites return `NOT_READY`; protocol inadequacy/infeasibility returns scoped `INSUFFICIENT_EVIDENCE` with safe reasons.
9. **Immutable, reproducible outputs**: Frozen dataclasses, tuples and recursively detached immutable mappings follow Feature 002 patterns. `to_dict()` produces detached copies. A canonical manifest records source/version references, exact registrations/targets, verifier and linkage versions, eligibility/protocol versions, partition config and assignment lineage, exclusions, transform declarations, and builder version. Stable canonical serialization and SHA-256 may detect content/version changes; a digest is not an identity or verification guarantee.

Dataset row data and the full patient-group/partition manifest are controlled sensitive artifacts. The library returns them to its caller; storage permissions, secret handling, custodian authorization and release operations remain the caller's responsibility. Feature 003 does not add a database, access-control service, cryptographic protocol or export subsystem.

## Implementation Dependencies and Test Strategy

Implementation should follow this dependency order:

1. Immutable dataset value records, typed errors, safe summaries and synthetic fixture constructors.
2. Explicit trusted verifier contracts and exact registration/target compatibility validation.
3. Outcome and independence verification, exact join, correctness target derivation, exclusion audit.
4. Patient-linkage verification and group/duplicate/cohort conflict checks.
5. Versioned protocol validation, deterministic or supplied patient assignments, protected assignment history and adequacy checks.
6. Leakage/timing/transform validation, protected test output handling, canonical manifests and build orchestration.
7. Synthetic story acceptance, privacy/immutability/leakage probes, quickstart verification, Feature 001/002 and full-suite regression.

Tests use only synthetic identities, outcomes and predictions. Reuse existing registry and collection fixtures where appropriate, with Feature 003-specific fixtures for trusted outcome, independence, linkage, timing and protocol integrations. Core tests assert exact join semantics, all three classifier configurations, both collection modes, overlapping contributor labels, four-way disjoint patient groups, duplicate handling, immutable prior manifests, final-test restrictions, readiness reasons, deterministic order-independent builds, and privacy-safe outputs. Acceptance tests must also prove that no classifier, adapter prediction method, safety estimator, calibration, signal, or assessment path is invoked.

Acceptance verification maps directly to the specification: US1 => FR-001–010/SC-001/005; US2 => FR-011–014/SC-002; US3 => FR-005/015–020/SC-003/006/007; US4 => FR-021–024/SC-004/007; US5 => FR-018–020/SC-006; scope/regression => FR-025–026/SC-008.

## Project Structure

### Documentation (this feature)

```text
specs/003-patient-grouped-safety-dataset/
├── plan.md
├── research.md
├── data-model.md
├── implementation-context.md
├── quickstart.md
├── contracts/
│   └── dataset-python.md
└── tasks.md                 # Created only by a later $speckit-tasks step
```

### Source Code (repository root)

```text
src/safira/
├── registry/                # Existing; exact immutable metadata lookup
├── collection/              # Existing; immutable PredictionRecord source values
└── dataset/                 # Proposed; no edits to registry/collection contracts
    ├── __init__.py
    ├── records.py            # Frozen target, verification, example, protocol, manifest values
    ├── verification.py       # Explicit trusted integration protocols and result validation
    ├── validation.py         # Exact joins, eligibility, leakage and safe exclusion checks
    ├── partitioning.py       # Patient-group assignment and protected-history checks
    ├── builder.py             # Ordered build orchestration and readiness result
    └── exceptions.py          # Typed privacy-safe errors

tests/
├── collection_fixtures.py    # Existing synthetic registry/collection helpers
├── dataset_fixtures.py       # Proposed synthetic trusted checks, outcomes and protocols
├── test_dataset_records.py
├── test_dataset_supervision.py
├── test_dataset_grouping.py
├── test_dataset_leakage.py
├── test_dataset_protection.py
├── test_dataset_reproducibility.py
└── test_dataset_acceptance.py
```

**Structure Decision**: Feature 003 belongs in a focused `src/safira/dataset` package alongside the existing registry and collection packages. It consumes their public values and metadata, with no changes to those packages. Tests remain in the repository's existing top-level `tests` package.

## Complexity Tracking

No constitution violations or new infrastructure are proposed. A separately supplied trusted integration boundary is necessary because Feature 001/002 do not define ground truth, cross-source patient equivalence, or primary-model development lineage. Dataset storage and access control remain external to keep the feature lightweight.

## Implementation Context Summary

For a reusable, task-generation-ready reference, see [implementation-context.md](implementation-context.md). It records existing public contracts, proposed module responsibilities, implementation dependency order, key invariants, test locations, and external integration prerequisites.
