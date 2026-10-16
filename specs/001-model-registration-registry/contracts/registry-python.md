# Planned Python Contract: Feature 001 Registry

This is a design contract for a future in-process Python library interface, not implemented code. Type and symbol names may be refined at the tasks stage if the same observable behavior is preserved. There is no REST, CLI, training, or assessment endpoint in this feature. See [data-model.md](../data-model.md) for field meanings.

## Operations

| Operation | Inputs | Return | Required behavior |
|---|---|---|---|
| `ModelRegistry(storage_path)` | Path to local catalog | Registry instance | Open/create a versioned metadata catalog. Raise storage error for unreadable/corrupt/unknown-schema existing catalog; never treat it as empty. |
| `register(definition, classifier, adapter, identity_evidence)` | `RegisteredModelVersion` declaration; live classifier; `ModelAdapter`; checkable artifact and adapter identity evidence | Frozen `RegisteredModelVersion` | Validate scope, schema, existing adapter contract, identities and evidence; commit metadata once using exact key. Duplicate pair fails even if identical. No patient method or safety setup is called. After commit, a validated live binding may be established in this process. |
| `get_metadata(model_id, model_version)` | Exact ID and version | Frozen `RegisteredModelVersion` | Retrieve and validate persisted metadata independent of attachment. Distinguish unknown ID from missing version. No latest fallback. |
| `attach(model_id, model_version, classifier, adapter, identity_evidence)` | Exact key and live pair plus checkable identity evidence | `UsableRegistration` or success marker | Compare artifact, adapter implementation/version/capabilities, label/output schema, input/modality/preprocessing identities with the immutable record. Publish binding only after all checks pass; no prediction call. |
| `resolve_usable(model_id, model_version)` | Exact ID and version | `UsableRegistration(metadata, classifier, adapter)` | Return the validated association as one value. Fail explicitly when metadata is absent, no pair is attached, or a binding cannot be trusted. Never substitute another pair. |

`identity_evidence` is a registry-side verification input, not a new method on `ModelAdapter`. It must let the registry compute or independently check a deterministic fingerprint of the actual immutable classifier artifact and adapter implementation associated with the supplied live pair. It may use an owner-supplied deterministic identity provider where no universal artifact format exists, but assertion-only strings are insufficient for usable attachment. The provider must not inspect patient data or invoke prediction. The provider/callable itself is never persisted. A verifier unable to establish the live-object-to-artifact link must reject usable attachment; this integration obligation remains explicit.

`RegisteredModelVersion` and nested declarations are immutable values; callers cannot mutate the accepted catalog definition through a returned object. An input dictionary containing arbitrary extra values is not silently persisted. A registry may require the owner to supply the same structural declarations at attachment so it can compare exact schema/preprocessing semantics; identical strings without checkable artifact evidence are insufficient.

## Adapter output contract at registration

- `ModelAdapter.predict(patient_data, label)` remains mandatory. For a declared non-probability `continuous_score`, its per-label output is the primary score described by the label mapping.
- `ModelAdapter.predict_probability(patient_data, label)` remains optional. A declared probability source requires `AdapterCapabilities.prediction_probability is True` and a concrete implementation of that method. The returned value is a primary classifier probability, not a Safira reliability score.
- Registration checks declarations and method presence without calling either method on clinical data. A later consumer must check observed output type, finiteness, range, and mapping before safety use. Feature 001 does not place a non-probability score into `SafetyContext.prediction_probability` or alter `SafetyAssessment`.
- Optional capabilities stay explicit true/false declarations. A false or unavailable capability does not become a fabricated zero-valued safety signal.

## Error contract

All errors are typed, actionable, and safe for routine display. They may include a non-sensitive model key and offending *field name*, but must not echo patient observations or raw submitted payloads.

| Error category | Example trigger | Postcondition |
|---|---|---|
| `InvalidRegistrationError` with field detail | Blank/whitespace/control-character key; duplicate labels; missing outcome meanings, output selection, score semantics, boundary; invalid input/preprocessing declaration; non-Boolean capability flag | No new row or binding. |
| `UnsupportedTaskError` | Regression, unsupervised task, or standalone one-label binary classifier | No new row. |
| `IncompatibleAdapterError` | Not a compatible `ModelAdapter`, required method not implemented, false probability declaration, or uncheckable identity evidence | No new row/binding; existing records unchanged. |
| `DuplicateRegistrationError` | Existing `(model_id, model_version)`, including a concurrent losing insert | Prior row and binding untouched. |
| `UnknownModelError` | No record for `model_id` | No substitute returned. |
| `UnknownVersionError` | Model exists but exact `model_version` absent | No substitute returned. |
| `UnattachedModelError` | Metadata exists, but no validated live pair is present after restart or before attachment | Metadata remains available. |
| `BindingMismatchError` | Wrong classifier artifact, adapter implementation/version, capabilities, schema, preprocessing, or other compatibility declaration | No partial binding; existing valid binding unchanged. |
| `RegistryStorageError` | Corrupt database, unknown storage schema, invalid stored record, lock/I/O/permission failure | Fail closed; never report unknown model/version or replace catalog. |

Names above are proposed public exception names. Low-level SQLite exceptions must be translated into the correct category; only the actual composite-key conflict maps to `DuplicateRegistrationError`.

## Contract examples (behavioral)

1. Register model `m`, version `v1`, with two labels and a validated pair. Exact metadata lookup and usable resolution both succeed; registering `m/v1` again raises `DuplicateRegistrationError`.
2. Open the same catalog in a fresh process. `get_metadata("m", "v1")` succeeds, `resolve_usable("m", "v1")` raises `UnattachedModelError`, and `attach` with the exact checked pair enables usable resolution.
3. Reattach a changed classifier or adapter under `m/v1`. `BindingMismatchError` is raised; the immutable metadata is unchanged. Register the material change under `v2` instead.
4. Query `m/v3` when only `v1` and `v2` exist. `UnknownVersionError` is raised; `v2` is never chosen implicitly.
