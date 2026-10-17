# Implementation Plan: Feature 002 — Prediction/Evidence Collection and Precomputed Adapter

**Branch**: `feature-02/evidence-collection` (existing checkout; Spec Kit setup identified the `002-prediction-evidence-collection` feature directory) | **Date**: 2026-10-17 | **Spec**: [spec.md](spec.md)

**Input**: Clarified Feature 002 specification and Safira Constitution v3.0.0. This plan ends at design; it authorizes no implementation.

## Summary

Add a small in-process collection layer that produces source-qualified, transient primary prediction and optional-evidence records from exact Feature 001 live bindings or admitted versioned external outputs. It validates one classifier's one label at a time, retaining contributor identity even when a component groups independent models. External source contracts supply parsers and real provenance checks without defining a universal JSON layout. No safety signals, packages, policies, reliability scores or assessments are created.

## Technical Context

**Language/Version**: Python 3.11+.

**Primary Dependencies**: Existing `safira.adapters`, `safira.registry`, `safira.context`; Python standard library (`json`, `math`, `dataclasses`, typing). No new runtime package required. `pytest` for verification.

**Storage**: Feature 001 SQLite remains the metadata catalog. Feature 002 records and admitted precomputed values are in-memory, scoped to a collection; no new persistent patient store.

**Testing**: Synthetic pytest unit, contract, end-to-end and existing regression tests. Two differently shaped synthetic versioned JSON contracts; no restricted data.

**Target Platform**: Existing in-process Python library on supported Python 3.11+ environments.

**Project Type**: Python library; no REST, CLI or training pipeline interface.

**Performance Goals**: No numerical latency or throughput target was approved. Correctness and zero unnecessary inference calls are measurable.

**Constraints**: Exact immutable registration compatibility; verified live pair for live mode; independently checked source-specific provenance bound to exact output content, contributor and association occurrence for precomputed admission; deeply immutable/defensively copied accepted records; opaque associations; privacy-safe errors; no new assessment or safety computation.

**Scale/Scope**: One or more independent contributors per component, each with one registered binary label or multiple binary-outcome labels. No fixed label/contributor count, disease or algorithm assumption. Contract-specific resource limits, if needed, are operational limits rather than clinical thresholds.

## Constitution Check

*Gate evaluated before research and again after design.*

| Principle | Design check | Result |
|---|---|---|
| I–II, V | Preserve exact classifier/version/label for both eligible classifier forms and composed contributors; collect primary values without safety claims or package transfer. | Pass |
| III | Reuse `ModelAdapter`, `AdapterCapabilities`, `SafetyContext` where fitting; leave `SafetyAssessment` and existing methods unchanged. | Pass |
| IV, VII | Explicit optional evidence states; no computation or fabrication of any of the six safety dimensions. | Pass |
| VI, VIII–IX | No safety-data splits, correctness targets, Safira calibration, operating points or TRUST/CAUTION/DEFER outputs. Primary calibration declarations stay labeled as primary metadata. | Pass |
| X | Opaque association, in-memory patient values, sanitized errors and synthetic examples only. | Pass |
| XI–XIII | Pytest acceptance/regression strategy, reproducible synthetic fixtures, specification-driven sequencing and research-prototype claims. | Pass |

**Gate conclusion:** No constitutional violation or exception is required. Recheck after Phase 1 design: contracts and data model retain these boundaries; gate remains **Pass**. Collection does not establish safety readiness.

## Phase 0 — Research decisions

See [research.md](research.md) for decisions, rationale and alternatives. All generic design unknowns raised by the clarified specification have a contract-level treatment. Concrete external schemas and trusted evidence checks remain per-integration onboarding dependencies; the PD schema is not inferred.

## Phase 1 — Design

### Collection flow

1. **Validate request:** Opaque patient, assessment and occurrence references, exact model/version/label, optional component identity and source-contract identity. Validate declared contributor set and reject a duplicate source-qualified key within an occurrence.
2. **Resolve compatibility:** Live uses `ModelRegistry.resolve_usable`; precomputed uses `get_metadata`. Check the requested label and immutable output semantics. External selector translation is explicit and checked; it need not equal the registered classifier selector.
3. **Acquire primary value:** Live calls only the registered `LabelDefinition.value_source` after structural input checks. Precomputed parses under its configured source contract and requires an executed trusted check that binds the exact covered content, exact registered contributor and applicable patient/assessment/occurrence association before admission.
4. **Validate primary:** Strict numeric type/finiteness/domain, exact registered class mapping and any supplied class, calibration/target semantics, association and input-verification status. Invalid required fields reject the affected envelope before publication.
5. **Collect optional evidence:** Gate live calls by adapter capabilities. Validate supplied evidence and its interpretation against source rules. Represent all five states and sanitized reasons; retain valid primary predictions when optional evidence fails.
6. **Return records:** Recursively detach and freeze accepted source-qualified records, evidence and provenance. Defensive-copy any contract-approved mutable representation and every mutable outward return. Project a detached `SafetyContext` only where useful, without treating it as the sole evidence-state record or creating an assessment.

### Separate external boundary

A small set of supported `(source_contract_id, version)` handlers identifies the correct JSON parser/validator and permitted external declarations. Each yields normalized output candidates and their declared mappings; it does not assert model origin. A configured trusted integration executes a source-specific check against independently controlled evidence that binds one provenance event to the exact covered output content, registered model/version/label and applicable opaque patient/assessment/occurrence association. The check reports source-controlled freshness/revocation and replay/reuse status. Safira verifies the complete scope and rejects mismatched content, contributor substitution, reassignment, stale/revoked evidence and disallowed replay. Each contract defines its own deterministic comparison; no universal hash/signature scheme, Safira replay service or PD layout is embedded in core collection.

### Failure and commit boundary

Required identity, provenance, association, source-contract or primary-value failures reject the affected collection envelope without exposing partial accepted results. Duplicate/conflicting contributor keys and duplicate provenance-event IDs within a collection never overwrite earlier records. Optional evidence errors yield an explicit incomplete state on an otherwise valid prediction. Feature 001 storage and identity errors retain their meanings. Collection errors identify safe field categories only; raw input, raw JSON, unknown extensions and original exception text never appear in routine diagnostics.

### Existing context and adapter compatibility

The standardized record is authoritative. A `SafetyContext` view may carry opaque patient/label, mapped primary class, and probability only for true probability outputs, plus namespaced source/assessment/evidence-state metadata; it must not interpret empty defaults or availability Booleans as evidence states. Keep non-probability continuous scores and their kinds explicit outside `prediction_probability`. `SafetyAssessment` remains untouched. An ephemeral `PrecomputedAdapter` implements existing methods for **one** admitted assessment occurrence and exact contributor label, checking an opaque typed request reference on every call. It returns saved values only, advertises only genuinely available capabilities, and is never attached as the registered original adapter.

## Project Structure

### Documentation (this feature)

```text
specs/002-prediction-evidence-collection/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/collection-python.md
├── quickstart.md
└── checklists/requirements.md
```

### Proposed source and tests (not created by this planning step)

```text
src/safira/collection/
├── __init__.py             # narrow public operations/types
├── records.py              # prediction, association, evidence, provenance values
├── validation.py           # shared primary/evidence/mapping checks
├── live.py                 # existing registry + ModelAdapter collection
├── precomputed.py          # source-contract ingestion and scoped adapter view
└── exceptions.py           # privacy-safe collection failures
tests/
├── test_collection_live.py
├── test_collection_precomputed.py
├── test_collection_component.py
├── test_collection_evidence.py
└── test_collection_acceptance.py
```

**Structure decision:** One focused package beside the existing registry and adapter packages. Modules can be combined during implementation if the public contract and tests stay clear. Existing adapter, context, assessment and registry tests remain regression checks.

## Verification strategy

Use deterministic synthetic one-label and multi-label adapters; build components with varying contributor counts and overlapping labels. Verify exact keys and selector translation; one primary method call per live label; strict probability/score/class behavior; subprocess restart and precomputed ingestion without binding; successful checks and rejection of changed content, wrong contributors/associations, stale/revoked events, replay/reuse and reassignment; two source layouts; duplicate JSON members; the optional-evidence state matrix and explanation/calibration separation; deep immutability against original-input and returned-value mutation; Precomputed Adapter scope/capabilities; zero original-model inference or safety operations; safe errors; and full pytest regression. See [quickstart.md](quickstart.md).

## Important tradeoffs and dependencies

- **Narrow precomputed view:** One record per adapter view because current capability flags are adapter-wide and some methods take no label. Multi-label/component results are collections of such views and records.
- **Trust boundary:** Safira requires a configured integration's documented, executed check to bind exact content, contributor and association using independently controlled evidence, including current and reuse status. It cannot prove arbitrary external generation from a digest or Boolean. Source onboarding defines the deterministic comparison and authority; no universal cryptographic or replay infrastructure is added.
- **Input validation:** Feature 001's schema is structural. Generic type/shape checks cover supported declarations; uncheckable source-specific structures need an explicitly declared validator or fail, never an assumed pass. No clinical plausibility claim follows.
- **PD integration:** The handoff is informative; its actual versioned JSON schema and artifact-level contributor evidence are unavailable here. Generic implementation may use synthetic contracts, but direct PD compatibility remains unverified until those inputs are supplied.

## Complexity Tracking

No constitutional violations or exceptional infrastructure are proposed. Source-contract and provenance boundaries are needed for clarified FR-005/014 and remain small in-process interfaces, not services or universal serialization systems.
