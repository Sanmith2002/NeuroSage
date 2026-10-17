# Research: Prediction/Evidence Collection and Precomputed Adapter

**Basis:** [clarified specification](spec.md), Safira Constitution v3.0.0, the implemented Feature 001 registry, existing adapter/context/assessment classes and their pytest coverage. This is design research; it does not verify any clinical model or external component output.

## R1. Keep one standardized, source-qualified result

**Decision:** Both live and precomputed paths produce the same transient prediction/evidence record shape. The key is opaque patient, assessment and occurrence references plus exact `(model_id, model_version, label_id)`; component identity/version is an additional grouping attribute. Preserve source mode and provenance separately. Accepted records recursively freeze supported nested values or own defensive copies; public views and serialization return detached copies. No collection data enters Feature 001 SQLite storage.

**Rationale:** Feature 001's immutable rows describe classifiers, not patient predictions. Distinct keys prevent two models predicting the same label from overwriting one another. A single validated record model permits equivalent meaning in both source modes without asserting equivalent provenance. Deep detachment prevents later mutation of caller, parser, adapter or verifier containers from changing an accepted result.

**Alternatives considered:** Extend `RegisteredModelVersion` or persist patient records in SQLite (violates the registry and privacy boundary); store one component-wide merged prediction (loses contributor identity).

## R2. Reuse exact registry operations according to source mode

**Decision:** Live collection calls `ModelRegistry.resolve_usable(model_id, model_version)` before any patient-facing adapter method. Precomputed ingestion calls `get_metadata` for each exact contributor and never requires or creates a live binding. Neither path changes `ModelAdapter`, `AdapterCapabilities`, `SafetyContext`, `SafetyAssessment`, or Feature 001 identity/storage behavior.

**Rationale:** `resolve_usable` returns the attached, validated classifier-adapter pair; `get_metadata` remains available after a restart. The original `IdentityProvider` attests a live pair, not an external prediction. An unattached model is fatal to live collection but expected for precomputed collection.

**Alternatives considered:** Treat a precomputed adapter as the registered original adapter (false identity); require the original model to ingest saved output (contradicts Feature 002).

## R3. Resolve owner-declared component mappings without equating selectors

**Decision:** A contributor map translates each external output selector under a declared source contract to an exact registered model/version/label and its registered `LabelDefinition.output_selector`. These are different namespaces and need not be identical strings or positions. Check both selector scopes, exact registration existence, label identity, value kind/source, scale/direction, binary outcomes, class mapping, applicable input/preprocessing and adapter declarations, and any claimed artifact identity. Reject missing, duplicate, ambiguous or conflicting mappings. Check the declared contributor set for completeness; retain overlapping labels as distinct records.

**Rationale:** External JSON layouts vary, while `output_selector` identifies a label within one classifier's registered output. The component's version and model family cannot replace exact contributor versions.

**Alternatives considered:** Match by label name, algorithm or shared component version (ambiguous); require every external source to copy the registered selector literally (contradicts source-contract independence).

## R4. Require an executed, source-specific external provenance check

**Decision:** Admission uses a configured trusted integration that executes a check against evidence controlled independently of the output and caller assertions. The evidence binds one source provenance event to (a) the exact covered primary/evidence content, (b) the exact registered model/version/label and selectors and (c) the applicable opaque patient/assessment/occurrence association. The source contract defines deterministic content comparison; this may be an independently calculated digest, deterministic representation or authoritative field/byte comparison. The result also reports current/revoked status and replay/reuse or prior-assignment status under the source's policy. Safira verifies every scope field and rejects content mismatch, contributor substitution, association reassignment, stale/revoked evidence and disallowed replay. A synthetic integration uses a fixture manifest prepared separately from submitted output. Production integrations use an appropriate source authority. A caller-provided `verified=True`, caller-controlled event ID, digest inside the same output, metadata match or batch-wide attestation is insufficient. The check is not called live-model verification or universal proof of generation.

**Rationale:** Safira cannot infer the origin of arbitrary JSON. Binding content, contributor and association together prevents a valid output from being claimed for another model or assessment. Independently controlled freshness/reuse state identifies stale or replayed claims without adding a universal Safira signing scheme or replay database. Recording the executed check and limits makes the assurance reviewable.

**Alternatives considered:** Accept claims with an assurance flag (unverified assertion); bind only a model or payload digest (permits reassignment); reuse `IdentityProvider` (attests a loaded live object); mandate universal cryptographic packaging or a Safira provenance service (unnecessary across sources).

## R5. Use an explicit source-contract boundary, not a universal external schema

**Decision:** Select a configured parser/validator by exact `(contract_id, contract_version)`. It parses JSON with duplicate-member and nonfinite-number rejection; applies that source's field, extension, type, cardinality and evidence rules; and yields a small normalized envelope. The source contract specifies how to locate outputs and which separately supplied owner/integration declarations may fill missing opaque associations or evidence meanings. Unknown versions, contradictory declarations and unrecognized semantics fail closed. Build two differently shaped synthetic contracts to test generality; do not claim PD schema compatibility from a handoff summary.

**Rationale:** A version is meaningful only within its named contract. A tiny explicitly registered contract interface permits format variation without a universal field-name guesser or dependency-heavy schema engine.

**Alternatives considered:** Hardcode the PD output shape (not generic and actual schema unavailable); heuristically infer fields from JSON names (unsafe); require one shared JSON layout for every component (contradicts the specification).

## R6. Preserve primary value and class semantics

**Decision:** For a live label, invoke only its registered `value_source`: `predict_probability` for probability or `predict` for continuous score. Check exact numeric type (exclude Boolean), finiteness and declared bounds, without clipping or cross-label normalization. Apply the already registered comparison and boundary to derive the primary class; check any supplied class against it. A probability-only source with no compliant Feature 001 mapping is rejected. Keep score and probability fields distinct and record meaning, positive direction and primary calibration declaration if supplied.

**Rationale:** Calling both prediction methods may repeat stochastic inference and produce inconsistent values. `SafetyContext.__post_init__` does not reject Boolean or NaN, so Feature 002 must validate before projection. Primary probabilities are not Safira reliability scores.

**Alternatives considered:** Infer a 0.5 class cutoff or calibration from a delivered probability (unapproved); coerce strings/Booleans; store an arbitrary score as `prediction_probability`.

## R7. Isolate optional evidence and scope precomputed adapters tightly

**Decision:** Each evidence category has an explicit `available`, `unsupported`, `missing`, `unavailable` or `invalid` state and a safe reason when incomplete. Unsupported live capability methods are never called. Optional extraction errors become `unavailable` with sanitized diagnostics; invalid supplied evidence stays `invalid`. A valid primary prediction survives those optional failures. Evidence interpretation includes applicable source, target, meaning, output space, units, shape, modality and repetition provenance. An ephemeral `PrecomputedAdapter` is scoped to one exact contributor label and one opaque assessment occurrence; all methods check a matching request reference. Its capability flags reflect only values it can actually return from that admitted record, not the original adapter's capabilities. The standardized record is authoritative; optional `SafetyContext` projection cannot use default empty collections or `evidence_availability()` to stand in for five-state evidence.

**Rationale:** `AdapterCapabilities` flags are adapter-wide, and three existing methods have no `label` argument. A narrow adapter view avoids claiming availability for another label or assessment and requires no contract rewrite.

**Alternatives considered:** One adapter for an entire heterogeneous component (would misstate capabilities); turn missing evidence into zero/empty success; alter existing context fields (unnecessary compatibility risk).

## R8. Validate association, input structure and privacy at boundaries

**Decision:** Require opaque nonblank patient, assessment and occurrence references; compare declarations in the source with separately supplied owner/integration values and reject conflicts. For live input, validate registered field/type/shape and modality declarations before inference for types the implementation can check; unsupported or uncheckable declarations fail explicitly or require a declared source-specific validator, never an assumed pass. In precomputed mode, record input verification as unavailable when raw input is absent. Keep raw input/evidence in memory only for the requested operation; do not echo values, identifiers or arbitrary exception messages in errors/logs. Use typed, field-category errors.

**Rationale:** Feature 001 input metadata is structural and model-agnostic, not a universal clinical validator. Associations must distinguish repeated collections and overlapping contributors. Privacy rules apply even to failed validation.

**Alternatives considered:** Infer association from source file names or component version; claim an absent input was schema-checked; log raw failed payloads for convenience.

## Remaining integration dependencies

- A concrete external source needs its actual versioned schema, permitted extensions and synthetic conforming examples before its contract can be implemented. The PD handoff's referenced schema is not available in this workspace; direct PD compatibility cannot be claimed.
- Each external integration must supply an explicit contributor mapping, registered class mappings and a trustworthy source-specific output-to-contributor check. A declared source digest alone does not meet this requirement. These are onboarding inputs, not unresolved generic architecture decisions.
- Feature 001's class mapping remains mandatory. No Feature 002 fallback threshold or standalone diagnostic record is planned.
