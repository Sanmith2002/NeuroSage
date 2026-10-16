# Data Model: Feature 001 Model Registration and Registry

**Scope**: Declarative classifier registration and process-local usable association. This is a design artifact; none of these types or tables exists in application code yet.

## Relationships

```text
RegisteredModelVersion (model_id, model_version)
  ├── 2 or more LabelDefinition records (unique label_id within model version)
  ├── 1 AdapterDeclaration
  ├── 1 ClassifierArtifactIdentity
  └── 1 InputDefinition

ProcessLocalBinding (same exact model_id, model_version)
  ├── 1 live classifier object
  ├── 1 live ModelAdapter instance
  └── checked identity evidence matching RegisteredModelVersion
```

Only `RegisteredModelVersion` and its nested declarative values persist. `ProcessLocalBinding` is neither serialized nor inferred from a stored record. A future safety package may point to the immutable key and compatibility fingerprint; Feature 001 does not create such a package.

## RegisteredModelVersion

| Field | Rule |
|---|---|
| `model_id`, `model_version` | Nonblank exact strings, no leading/trailing whitespace or control characters; composite immutable key. Opaque versions have no ordering or latest alias. |
| `task_type` | Fixed supervised multi-label classification declaration; other tasks and one-label classifiers rejected. |
| `classifier_artifact` | Checkable immutable artifact identity, including digest algorithm and digest/fingerprint of version-specific classifier material. No executable bytes in the record. |
| `labels` | Ordered or explicitly indexed set of at least two unique `LabelDefinition` values. Order/output selection is part of immutable compatibility metadata. |
| `adapter` | `AdapterDeclaration` for the associated implementation and this exact classifier version. |
| `input` | Declarative input shape/type and named modality metadata, without observations. |
| `preprocessing_identity` | Checkable version/fingerprint of required preprocessing, or explicit `none`. |
| `metadata_schema_version` | Storage serialization version for fail-closed decoding/migration. |

The persistent representation uses canonical JSON for structured metadata in a SQLite row or normalized tables where appropriate, with a composite primary key and schema-version marker. Serialization must round-trip exact values and validate on decode. Storage internals do not expand the public contract.

## LabelDefinition

| Field | Rule |
|---|---|
| `label_id` | Stable, nonblank, unique within the model version; display names do not substitute for ID uniqueness. |
| `negative_outcome`, `positive_outcome` | Distinct, explicit meanings of verified binary ground-truth classes. There are exactly two ground-truth outcomes per label. |
| `output_selector` | Unambiguous mapping from classifier output position/key to this label. Selectors cannot collide or ambiguously refer to another label. |
| `value_kind` | `probability` or `continuous_score`; describes the primary classifier's output, never Safira reliability. |
| `value_source` | Existing `ModelAdapter.predict_probability` for probabilities or `ModelAdapter.predict` for a declared non-probability continuous score. |
| `value_scale` | Defined numeric domain/scale and meaning; probability is 0–1, with direction and positive-class semantics stated. A non-probability score may have an unbounded declared domain, but each observed value must be finite. |
| `class_mapping` | Deterministic rule mapping a value to positive or negative primary prediction, including threshold/boundary behavior and positive direction. This rule describes the **primary classifier**, not a Safira TRUST/CAUTION/DEFER policy. |

Validation rejects missing output mapping, duplicate label IDs/selectors, a third ground-truth class, ambiguous scale/direction/boundary, a hard 0/1-only declaration, or a non-probability score mislabeled as a probability. Individual predictions may legitimately equal 0 or 1; capability to provide continuous values is the requirement. Static validation cannot prove observed runtime output distributions.

## AdapterDeclaration

| Field | Rule |
|---|---|
| `adapter_id`, `adapter_version` | Nonblank stable implementation identity and exact version. A material version change requires a new registered model version. |
| `implementation_fingerprint` | Checkable identity for the adapter implementation, distinct from a human-readable class name/version assertion. |
| `associated_model_id`, `associated_model_version` | Must exactly match the parent record's key. |
| `capabilities` | Snapshot of every existing `AdapterCapabilities` flag with actual Boolean values. Unsupported flags remain `false` and do not imply a numeric signal value. |

At registration and attachment, check `ModelAdapter` conformance, the capability snapshot, and concrete implementation of methods claimed by relevant capabilities. A `probability` value source requires `prediction_probability=True` and a concrete method override. A non-probability `predict` score does not set that capability unless true probabilities are independently supported. No optional safety dimension is inferred from an unclaimed capability.

## InputDefinition and identity evidence

`InputDefinition` contains only structural input schema (field names/types/shapes as required to identify compatibility) and declared modality names. It cannot include sample values, observations, outcomes, patient identifiers, clinical records, or arbitrary data blobs. `preprocessing_identity` identifies transformations that affect classifier behavior, with an explicit `none` when none applies. The classifier artifact and adapter implementation identity providers operate on immutable artifact/code material or deterministic non-patient state; their callables and source material are not persisted. Exact identity verification is required before usable attachment.

## ProcessLocalBinding

| Field | Rule |
|---|---|
| `model_id`, `model_version` | Exact foreign key to one persisted record. |
| `classifier` | Live object supplied by the owning integration; never stored in SQLite. |
| `adapter` | Live `ModelAdapter` instance for that classifier; never stored in SQLite. |
| `checked_identity` | Fingerprints and metadata comparison result for this attachment. Not a claim of clinical validation. |

The binding is created only after all checks pass and is lost on process exit. `resolve_usable` yields the metadata, classifier, and adapter atomically as one result. A failed attach does not publish a partial binding or replace an earlier validated one.

## State transitions

```text
unregistered
  └─ valid register + committed INSERT → registered and optionally attached
registered, unattached
  ├─ exact get_metadata → registered, unattached
  ├─ validated attach → registered, attached
  └─ invalid attach → registered, unattached
registered, attached
  ├─ exact resolve_usable → registered, attached
  ├─ failed replacement attach → registered, attached (old binding preserved)
  └─ process restart → registered, unattached
```

Duplicate registration always fails; no update/delete/relabel transition is part of Feature 001. A materially changed classifier, label schema, preprocessing, or adapter version enters through a *new* `model_version` and leaves prior metadata unchanged. Persistent catalog errors halt lookup/registration without inventing an empty registry.

## Invariants and privacy

- `(model_id, model_version)` identifies one immutable definition and is never reused for changed material.
- All lookups and bindings use both exact key components. Metadata existence does not imply a usable classifier or ready safety package.
- One registration may describe multiple disease labels, but no patient record or patient-label assessment is stored here.
- Primary prediction values and Safira reliability scores are separate; neither per-patient value is retained in registry metadata.
- Routine error text identifies safe field names and error categories, not raw input payloads or restricted data.
