# Planned Python Contract: Feature 002 Collection

This is an in-process library contract for implementation planning, not existing application code. Exact names may be refined in tasks without changing the specified behavior. It does not add methods to `ModelAdapter`, `AdapterCapabilities`, `SafetyContext`, `SafetyAssessment` or Feature 001 `ModelRegistry`. See [data-model.md](../data-model.md).

## Public operations

| Operation | Inputs | Result | Required behavior |
|---|---|---|---|
| `collect_live(registry, association, requests, patient_data, *, component=None)` | Exact registered `(model_id, model_version, label_id)` requests, opaque association, live input, optional component grouping | `CollectionResult` | Resolve each exact `UsableRegistration`; check input and label declarations; call only registered `value_source` once per label; validate primary and optional evidence; retain independent contributions. Missing binding fails. |
| `PrecomputedCollector(registry, integrations)` | Feature 001 registry and a finite application-owned iterable of trusted contract/verifier pairs | Configured collector | Derive exact keys from contract declarations, reject duplicate/conflicting keys, and retain a detached read-only mapping. Do not use global mutable registration or permit payload-installed handlers. |
| `collector.ingest(association, contract_key, raw_json, declarations, *, component=None)` | Exact configured source contract ID/version, versioned JSON, owner/integration mapping and any separately supplied association/meaning declarations | `CollectionResult` | Select the injected trusted pair; parse under that contract; look up immutable exact metadata; check mapping and independent source-specific output provenance for every contribution; require no original classifier or live binding. Record `input_verification=unavailable` when raw input is absent. Reject required-field failures before returning accepted records. |
| `precomputed_adapter(record)` | One admitted precomputed `PredictionRecord` | `ModelAdapter`-compatible view | Expose only saved value and validated, available optional evidence for that exact record/association. Never attach it to Feature 001 as the original adapter. |
| `to_safety_context(record, *, patient_data=None)` | One validated record and optional live input already held by the caller | `SafetyContext` projection | Preserve existing context semantics; leave five-state evidence and source provenance authoritative in `record` (or an explicitly paired companion), never infer support from context defaults. No assessment is created. |

`association` is a typed opaque value carrying patient, assessment and occurrence references; no identifying patient value is needed. Calls return in-memory data only. A collection request containing multiple contributors uses the same exact per-contributor rules, including an explicit expected contributor set where completeness is claimed.

## Source integration boundary

The host constructs `PrecomputedCollector(registry, integrations)` before accepting outputs. `integrations` is an application-owned finite iterable of immutable `TrustedSourceIntegration` values. The constructor derives each exact `contract_key = (contract_id, version)` from its contract declaration, rejects duplicate/conflicting keys, and stores a detached read-only mapping. Two collectors may have different mappings without affecting each other. An incoming JSON value or per-call declaration may select a configured key, but it cannot install, replace or mutate a parser or provenance verifier. There is no process-global mutable catalog. A minimal structural contract is:

```python
class SourceContract(Protocol):
    contract_id: str
    version: str

    def parse(self, raw_json: str | bytes) -> NormalizedEnvelope: ...
    def validate_declarations(
        self, envelope: NormalizedEnvelope, declarations: SourceDeclarations
    ) -> NormalizedEnvelope: ...

class TrustedProvenanceVerifier(Protocol):
    integration_id: str

    def check_output_link(
        self, raw_json: str | bytes, candidate: OutputCandidate,
        contributor: RegisteredModelVersion, label: LabelDefinition,
        association: CollectionAssociation
    ) -> ProvenanceCheck: ...

@dataclass(frozen=True)
class TrustedSourceIntegration:
    contract: SourceContract
    verifier: TrustedProvenanceVerifier

class PrecomputedCollector:
    def __init__(
        self,
        registry: ModelRegistry,
        integrations: Iterable[TrustedSourceIntegration],
    ) -> None: ...

    def ingest(
        self, association: CollectionAssociation,
        contract_key: tuple[str, str], raw_json: str | bytes,
        declarations: SourceDeclarations, *, component: ComponentIdentity | None = None,
    ) -> CollectionResult: ...
```

`NormalizedEnvelope`/`OutputCandidate` are internal parsed values, not universal JSON field names. The handler defines required fields, extension rules, external selector extraction, allowed association/meaning side declarations, evidence structure and resource limits for its own format. Generic JSON parsing rejects duplicate member names and nonfinite constants before source-specific parsing. Different contracts can use unrelated nesting/field names and identical version strings without collision.

The verifier must **perform** a source-specific comparison with evidence controlled independently of the submitted output and caller assertions. Examples include a trusted export manifest, producer-side result ledger or loader-owned record. The independent evidence MUST bind all of the following as one provenance event:

1. the exact candidate output content, including its primary value and covered evidence, using the source contract's deterministic content representation or exact byte/field comparison;
2. the exact registered `(model_id, model_version, label_id)` and applicable external/registered selectors; and
3. the applicable opaque `(patient_ref, assessment_ref, occurrence_ref)` association, or a source-controlled opaque token that the trusted integration resolves exactly to that association.

No universal digest, signature or canonical JSON scheme is required. Each source contract documents how its verifier compares the exact covered content. A digest is acceptable only when the verifier computes or obtains it from independently controlled evidence and compares it with the submitted candidate; a digest merely repeated inside the submitted JSON is still an assertion.

`ProvenanceCheck` includes integration ID, check method, independent evidence reference, source provenance-event ID, content-binding method/result, covered selector and exact contributor, association-binding result, freshness/revocation result, replay/reuse result and known limits. The ingestion boundary executes the check for the current candidate and association. It confirms every scope field, rejects missing or conflicting fields, and rejects evidence created for different content, contributor, patient, assessment or occurrence. The independently controlled authority must identify stale, revoked or already reassigned/reused provenance events according to its source-specific policy; the collector rejects those results. Within one collection, duplicate provenance-event IDs also fail. This prevents an old or valid output from being relabeled as a new assessment occurrence without adding a universal Safira replay service. If an integration cannot establish current association, freshness and reuse status, it cannot return a successful admissible check.

A bare Boolean, caller-selected event ID, metadata match, batch-wide attestation or stale check is insufficient. A trustworthy host must configure trustworthy implementations; Safira cannot prove arbitrary external origin merely because a Python callback returns a structured value. This boundary is separate from Feature 001's `IdentityProvider`, which checks a loaded live pair.

## Exact contributor mapping

`SourceDeclarations` contains a mapping from each external output selector (as defined by that source contract) to `(model_id, model_version, label_id, registered_output_selector)` and the expected contributor set. For each candidate, the collector uses `get_metadata(model_id, model_version)` and checks that label's exact ID and registered selector, value kind/source, scale/direction, binary outcome meanings, class mapping and applicable schema/preprocessing/adapter declarations. A source selector such as a JSON path **need not equal** Feature 001's `LabelDefinition.output_selector`; the explicit translation is what is validated. Missing, duplicate, ambiguous or conflicting entries fail. Same label IDs from two models produce two records. No component version, model family, label display name or implicit latest version resolves a contributor.

Live collection uses `resolve_usable`; precomputed ingestion uses `get_metadata` and the separate provenance check. A precomputed collection may succeed after process restart while `resolve_usable` would raise `UnattachedModelError`. A material classifier/schema/adapter change still requires a new Feature 001 model version.

## Primary and optional output rules

- A probability label uses `ModelAdapter.predict_probability(patient_data, label)` in live mode, and only an admitted supplied probability in precomputed mode. A continuous-score label uses `predict`. Do not invoke both as duplicate primary inference. Require exact int/float (not bool), finite values and the registered range; no clipping, conversion or cross-label normalization.
- Apply `LabelDefinition.class_mapping` and its comparator/boundary to derive a binary primary class. Check any externally supplied class. If a compliant registered mapping does not exist, reject the prediction, including probability-only output. No arbitrary class cutoff or Safira status is created.
- For each applicable optional evidence category, return `available`, `unsupported`, `missing`, `unavailable` or `invalid` with a safe reason for incomplete states. Unsupported live capability methods are never invoked. Exceptions during optional extraction become `unavailable` without exposing their original text. Missing required interpretation makes supplied optional evidence invalid; it does not erase a valid primary.
- Explanation metadata keeps the explained label/output, method, output space and calibrated status where known. It cannot silently attach an uncalibrated explanation to a calibrated delivered probability. Cohort scope and completeness remain source-reported research metadata, not OOD or safety results.

## Precomputed Adapter method behavior

The view is bound to one exact registered contributor label and one association occurrence. The existing `patient_data: Any` argument is a typed opaque request reference, **not** raw clinical input. Every method rejects an unmatched reference; methods with `label` also reject a different label. `predict_probability` returns the saved probability when value kind is probability. `predict` returns the saved score for a score label, or the registered-mapping-derived primary class for a probability label. Optional methods return only saved, validated evidence; `capabilities` reflects this view's genuinely returnable values, not the original adapter's declaration. Unsupported, missing, unavailable or invalid items fail with an explicit category, never a fabricated empty/zero success. Returned mutable evidence is a defensive copy and cannot modify the accepted record. No method invokes the original classifier, retrains, calibrates or computes safety signals.

## Record immutability and copying

`CollectionResult`, `PredictionRecord`, `PrimaryOutput`, `SourceProvenance`, `EvidenceItem`, association and component/contributor values are deeply immutable accepted values. Construction recursively detaches all caller, parser, verifier and adapter-returned containers before validation/publication. Prefer frozen value types plus tuples and immutable mappings for representable nested data; where an evidence contract admits a mutable third-party representation, store an owned defensive copy and return a fresh defensive copy on every outward access. Do not retain caller lists/dictionaries, mutable array views, raw parsed-object references or verifier-owned records.

Public serialization such as `to_dict()` returns a fully detached representation. Mutating original JSON-derived declarations, live adapter results, provenance-check objects, returned dictionaries/lists or a `SafetyContext` projection cannot alter the accepted prediction, evidence, provenance, association or later Precomputed Adapter results. Failed copying or an unsupported non-detachable evidence representation makes that optional evidence `invalid`; it never creates a shared mutable accepted value.

## SafetyContext projection

After strict Feature 002 validation, an optional projection can populate `patient_id` with the opaque patient reference, `label` with the registered label, `prediction` with the mapped primary class, and `prediction_probability` only for a true probability label. For a non-probability score, retain its value/kind in the authoritative record and, if projected, in namespaced `model_metadata`; do not place it into `prediction_probability`. Keep source-qualified key, assessment/occurrence and evidence states in namespaced metadata or a paired typed companion. `SafetyContext.evidence_availability()` reports simple current values only and must not be used to reconstruct five-state evidence. `SafetyAssessment` is never instantiated by Feature 002.

## Error contract

Feature 002 introduces typed, privacy-safe categories. Names here are proposed; exact class names can be finalized in tasks. No routine message includes patient references, raw values, JSON snippets, evidence content or arbitrary external exception text.

| Category | Trigger | Postcondition |
|---|---|---|
| `InvalidCollectionRequest` | Missing/contradictory association, duplicate contributor key, unsupported/uncheckable live input declaration | No new result published. |
| `UnknownSourceContract` | Contract ID/version unsupported, malformed JSON or ambiguous duplicate members | No parsed record admitted; distinguish malformed from unsupported in detail code. |
| `ContributorMismatch` | Unknown exact registration/label, mapping absent/duplicated/conflicting, selector/semantics mismatch, incomplete declared contributor set | No falsely complete component result. Registry typed errors remain distinguishable as causes. |
| `ProvenanceCheckFailed` | No configured trusted check; changed content; wrong contributor/association; stale, revoked, replayed or reassigned event; failed/wrong-scope/conflicting check; assertion-only evidence | No affected precomputed prediction admitted. |
| `InvalidPrimaryOutput` | Hard-only output, Boolean/string/nonfinite/out-of-range value, supplied class mismatch or missing registered mapping | No affected prediction accepted. |
| `EvidenceUnavailable` | Precomputed adapter optional method requested for an item not validated/available | No fabricated evidence returned; safe state/reason exposed. |

Earlier accepted records and immutable registrations remain intact after later failures. Structural and primary failures reject the affected envelope; isolated optional evidence failures return an explicitly incomplete valid primary record.

## Contract verification examples

1. A one-label registered classifier and a multi-label classifier yield records with exact `(model_id, version, label_id)` and independent primary values. Two different models' same label IDs remain separate.
2. A live model after restart fails as unattached; the same exact model's precomputed record may be admitted with `get_metadata` plus an executed, output-scoped trusted provenance check and no original inference.
3. Two synthetic source contracts with unrelated field layouts map external selectors to registered selectors and produce equivalent standardized meanings. Changing a model version, selector semantics or association causes rejection.
4. A saved probability with registered mapping and an explanation of an uncalibrated score keeps both output spaces. A probability without a compliant registered mapping is rejected; missing explanation meaning makes only that optional evidence invalid.
5. A precomputed adapter invoked with another label or occurrence fails; requesting unavailable optional evidence fails explicitly. No reliability score or status appears.
6. A trusted manifest entry for output content A cannot admit changed content B, another registered contributor or another patient/assessment/occurrence. A stale, revoked, previously reused or reassigned provenance event fails even when its original output was once valid.
7. After admission, mutate every original nested mapping/list and every mutable value returned by serialization or the Precomputed Adapter. The accepted record and later reads remain exactly unchanged.
