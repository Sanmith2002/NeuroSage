# Data Model: Feature 002 Prediction and Evidence Collection

**Scope:** In-memory standardized collection results. The existing Feature 001 `RegisteredModelVersion` and SQLite schema are unchanged. Names below are proposed Feature 002 Python value types, not fields attributed to an external JSON source. See [collection-python.md](contracts/collection-python.md) for operations.

## Relationships and keys

```text
CollectionResult (one requested assessment occurrence)
  ├── CollectionAssociation (opaque patient, assessment, occurrence references)
  ├── optional ComponentIdentity (component ID + version; grouping only)
  ├── 1..n PredictionRecord (exact model ID + model version + label ID)
  │    ├── 1 PrimaryOutput (continuous value + semantics + registered mapped class)
  │    ├── 1 SourceProvenance (live binding or checked precomputed source)
  │    └── EvidenceItem by applicable evidence category (five-state availability)
  └── declared ComponentContribution map, if component supplied
```

The uniqueness key within an occurrence is `(patient_ref, assessment_ref, occurrence_ref, model_id, model_version, label_id)`. For a component, retain `(component_id, component_version)` as an additional grouping namespace. A different source contract's external output selector is not part of the registered key; it is preserved in provenance and must map unambiguously to it. Two classifiers can contribute the same `label_id`. Repeated collections have different `occurrence_ref` values and do not become repeated model outputs automatically.

## Entity definitions

| Entity | Fields / meaning | Required validation |
|---|---|---|
| `CollectionAssociation` | Opaque nonblank `patient_ref`, `assessment_ref`, `occurrence_ref`; no actual patient observation. | Compare all declarations that refer to the same record; reject missing/conflicts. Source owner/trusted integration may supply missing values separately from JSON. Do not log raw references. |
| `ComponentIdentity` | Opaque `component_id`, `component_version`; distinct from each classifier version. | Both present when a component is declared; never derive an underlying model identity from these fields. |
| `ComponentContribution` | External selector under `(source_contract_id, version)` to exact `model_id`, `model_version`, `label_id` and registered classifier `output_selector`; optional owner-declared contributor set. | Selectors may differ. Compare to exact `get_metadata` label/semantics; reject absent, duplicate, conflicting or ambiguous translations. Declared expected set determines completeness. |
| `PrimaryOutput` | `value`, `value_kind` (`probability` or `continuous_score`), scale/domain, meaning, positive direction, registered `class_mapping`, derived binary `predicted_class`; optional supplied class and primary calibration declaration. | Strict int/float, never bool/string; finite; probability in [0,1], score in registered domain. Apply registration's comparator/boundary exactly and reject supplied-class disagreement. No new cutoff. |
| `PredictionRecord` | Association + exact source key + optional component + primary output + source mode + input-verification state + evidence and provenance. | Full required validation before publication. No unlinked probability-only record, score as probability or implicit model fusion. |
| `SourceProvenance` | `mode` = `live` or `precomputed`; registry metadata key; external contract/version/selector where applicable; assurance kind; trusted integration/check method; independently controlled evidence reference; provenance-event ID; content-, contributor- and association-binding results; freshness/revocation and replay/reuse results; limits. | Live mode requires validated `resolve_usable` pair. Precomputed mode requires one executed source-specific check that covers the exact accepted content, registered contributor and association occurrence. Stale, revoked, replayed, reassigned or mismatched events fail. Neither mode is a clinical-safety claim. |
| `EvidenceItem` | Category, source-qualified key and association; `state`, optional validated value, safe reason code, interpretation metadata. | Available items require contract-valid value/meaning. Missing/unavailable/unsupported/invalid items have no fabricated numeric value. A valid primary survives any optional failure. |
| `PrecomputedOutput` | Raw versioned JSON plus separate source-owned declarations and integration check material at boundary; normalized candidates only after parsing. | No universal external field names. Contract ID + version selects parser. Duplicate JSON members, nonfinite constants, ambiguous/unsupported structure or extensions fail per contract. The source contract defines the deterministic content covered by provenance; raw payload is not logged or persisted. |
| `TrustedSourceIntegration` | Immutable application-owned pair of one `SourceContract` and one `TrustedProvenanceVerifier`; its key is derived from the contract's exact `(contract_id, version)`. | `PrecomputedCollector` accepts a finite iterable, rejects duplicate/conflicting derived keys, and stores a detached read-only mapping. Payloads and per-call declarations may select only; they cannot install, replace or mutate handlers. No process-global mutable catalog. |
| `PrecomputedAdapterView` | Ephemeral `ModelAdapter` view bound to one admitted exact contributor label and association; saved primary/evidence only. | All methods require matching opaque request reference; never attaches to original registry identity or calls an original classifier. |

## Evidence categories and interpretation

Use the existing adapter capability names for `feature_representation`, `repeated_outputs`, `modality_outputs`, `domain_metadata`, `explanation`, `input_metadata`, and `available_modalities`. `prediction_probability` is a primary-value capability, not an optional safety signal. Each category's source contract or live integration declares applicable shape/type and interpretation. Keep target label/output, units, space, calibrated versus uncalibrated meaning, feature or modality identifiers, repeat provenance, scope and truncation when relevant. A category may contain more than one item when the declared contract warrants it; no fixed embedding size, repeat count or modality list is imposed. Data completeness and cohort/training-scope information may be represented as declared input/domain metadata, never inferred as OOD, eligibility or safety.

| State | Meaning | Value rule |
|---|---|---|
| `available` | Supplied or extracted, interpreted and validated for this source/association. | Contract-valid value present; zero is allowed only as an actual valid measurement. |
| `unsupported` | Source has no declared capability for the category. | No extraction call and no value. |
| `missing` | Evidence was expected/supported but omitted. | No invented value; safe reason. |
| `unavailable` | Collection could not obtain evidence now, including a caught extraction failure. | No value; sanitized reason category, never original exception text. |
| `invalid` | Supplied value/meaning contradicts or fails its evidence contract. | No validated value; the offending raw value is not echoed. |

For supplied optional evidence, missing interpretation that the source contract requires produces `invalid`, while a valid primary record remains. An explanation of an uncalibrated output remains identified with that output even if the delivered primary probability was calibrated. Unknown explanation semantics prevent validation as a comparable explanation. A truncated attribution list is marked truncated. Repeated outputs are distinct source observations with provenance, not copies of the primary value.

## Input verification and state transitions

Live input is checked against the registered structural `InputDefinition` before adapter calls. A declared type/shape that cannot be checked by the generic validator requires a source-specific validator or an explicit failure; no clinical plausibility inference is made. In precomputed mode, absence of raw input means `input_verification=unavailable`, not a passed check. Separate supplied declarations may fill association or interpretation gaps, but must match the source contract and not conflict with the output.

```text
received
  ├── invalid required field / unknown exact registration / failed provenance → rejected
  └── complete required validation → primary_valid
       ├── optional evidence valid → accepted with available evidence
       └── optional evidence absent, failed or invalid → accepted, explicitly incomplete
```

An envelope with conflicting duplicate source keys or required fields does not publish a partly accepted result. Previously returned results and Feature 001 metadata are unchanged after later failures. Record construction detaches mutable input so later changes cannot silently rewrite accepted meanings. No stored transition to a safety assessment exists in this feature.

## Provenance-event binding

For a precomputed candidate, the trusted integration checks an independently controlled source record against one indivisible tuple:

```text
(exact covered output content,
 exact model_id + model_version + label_id + selectors,
 opaque patient_ref + assessment_ref + occurrence_ref,
 source provenance_event_id)
```

The source contract defines how exact content is compared: deterministic contract-level normalization, an independently calculated content digest, or exact authoritative field/byte comparison are valid examples. Safira does not prescribe a universal cryptographic format. The independent record cannot be supplied solely by the same untrusted output or caller assertion. It must also state whether the event is current, revoked, previously reused or already assigned elsewhere under that integration's policy. Any content change, contributor substitution, association reassignment, stale/revoked event or disallowed replay rejects admission. Duplicate event IDs within one collection fail. Cross-request replay status is obtained from the independently controlled source authority; Feature 002 adds no persistent replay database.

## Deep immutability

Accepted `CollectionResult`, association, component/contribution, prediction, primary output, evidence, interpretation and provenance values are deeply immutable or own fully detached defensive copies. Nested sequences use immutable values where possible; mappings and source-specific evidence are recursively frozen or copied under their evidence contract. Construction never retains mutable references owned by the caller, JSON parser, adapter or trusted verifier. Public conversion methods return detached copies, and the Precomputed Adapter returns fresh defensive copies of mutable evidence. A `SafetyContext` projection is also detached. Mutating any original or returned nested object cannot change an accepted record or later adapter result.

If a supplied value cannot be safely detached and validated, a required value rejects the envelope and optional evidence becomes `invalid`. The framework does not accept a shared mutable object as validated evidence.

## Privacy and compatibility invariants

- Feature 001 metadata provides fixed classifier/label semantics; Feature 002 never mutates its registration, adapter fingerprints or bindings.
- Opaque references still require privacy handling. No patient input, prediction, raw JSON, explanation value or identifier is written to registry metadata, routine logs, committed fixtures or diagnostic exception text.
- `SafetyContext` can be projected from a validated record for existing consumers, but its Boolean availability helper and empty defaults cannot encode these five states. The standardized record remains authoritative.
- `SafetyAssessment` is not created. Primary `value` and any calibration declaration are distinct from Safira reliability scores and policies.
