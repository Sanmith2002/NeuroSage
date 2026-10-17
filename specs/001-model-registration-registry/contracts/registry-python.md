# Planned Python Contract: Feature 001 Registry

This describes the existing in-process Python library boundary and its proposed 2026-10-17 scope amendment. Single-label eligibility and amended acceptance remain pending implementation; existing operation signatures are preserved. There is no REST, CLI, training, or assessment endpoint in this feature. See [data-model.md](../data-model.md) for field meanings.

## Operations

| Operation | Inputs | Return | Required behavior |
|---|---|---|---|
| `ModelRegistry(storage_path)` | Path to local catalog | Registry instance | Open/create a versioned metadata catalog. Raise storage error for unreadable/corrupt/unknown-schema existing catalog; never treat it as empty. |
| `register(definition, classifier, adapter, identity_provider)` | `RegisteredModelVersion` declaration; live classifier; `ModelAdapter`; configured trusted `IdentityProvider` | Frozen `RegisteredModelVersion` | Validate scope, schema, existing adapter contract, and provider evidence; commit metadata once using exact key. Duplicate pair fails even if identical. No patient method or safety setup is called. After commit, a validated live binding may be established in this process. |
| `get_metadata(model_id, model_version)` | Exact ID and version | Frozen `RegisteredModelVersion` | Retrieve and validate persisted metadata independent of attachment. Distinguish unknown ID from missing version. No latest fallback. |
| `attach(model_id, model_version, classifier, adapter, identity_provider, *, definition)` | Exact key, live pair, trusted `IdentityProvider`, and candidate `RegisteredModelVersion` definition | `UsableRegistration` or success marker | Obtain fresh evidence for this live pair and compare artifact, adapter implementation/version/capabilities, label/output schema, input/modality/preprocessing identities with the immutable record. Publish binding only after all checks pass; no prediction call. |
| `resolve_usable(model_id, model_version)` | Exact ID and version | `UsableRegistration(metadata, classifier, adapter)` | Return the validated association as one value. Fail explicitly when metadata is absent, no pair is attached, or a binding cannot be trusted. Never substitute another pair. |

### IdentityProvider contract

The configured provider is a small integration boundary, not a new method on `ModelAdapter` and not a security service. It identifies a live classifier and adapter together and returns an immutable `IdentityEvidence` containing:

- `classifier_sha256`: deterministic SHA-256 fingerprint of the version-specific classifier artifact.
- `adapter_sha256`: deterministic SHA-256 fingerprint of the adapter implementation artifact.
- `loaded_pair_verified`: an actual Boolean attestation that the classifier object was loaded from the classifier material fingerprinted and that the supplied adapter is the implementation fingerprinted.

The provider implements `identify_loaded_pair(classifier, adapter) -> IdentityEvidence`. Safira calls it during registration and calls it again with the exact candidate pair during attachment. Safira checks evidence types, fingerprint encoding, `loaded_pair_verified is True`, and equality with the immutable identity stored in the registration.

For file-backed artifacts, the owner/provider computes the digest over exact immutable artifact bytes. For a multi-file artifact, it hashes a deterministic manifest with normalized relative paths and file-content digests. If the model is not file-backed, the owner/provider may derive the digest from an owner-defined deterministic representation of non-patient model state. The adapter fingerprint is derived from its immutable implementation artifact. Safira stores only the two fingerprints in the registration definition; it does not standardize model serialization or persist the provider or source material.

The classifier owner or trusted loader is responsible for making the provider observe or control the load operation well enough to associate the object with the fingerprinted material. Safira trusts the explicitly configured provider's attestation: a digest alone cannot prove the origin of an arbitrary live Python object. Missing provider, unsupported/unverifiable identity material, a false or absent attestation, or either mismatch fails registration or attachment closed. The provider must not inspect patient data or invoke prediction, and is never persisted.

`RegisteredModelVersion` and every nested declaration are deeply immutable values; callers cannot mutate accepted metadata through a returned object. The registry uses immutable nested representations or defensive copies on input and output. Mutating original labels, output mappings, capabilities, input schema, modality declarations, preprocessing metadata, or any other supplied collection after registration cannot alter the stored or returned definition. Mutating a returned collection is either rejected or affects only a detached copy. An input dictionary containing arbitrary extra values is not silently persisted. A registry may require the owner to supply the same structural declarations at attachment so it can compare exact schema/preprocessing semantics; identical strings without provider-verified identity evidence are insufficient.

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
| `UnsupportedTaskError` | Regression, unsupervised/reinforcement-learning task, unknown task declaration, empty label collection, or task/label-count mismatch | No new row. |
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

## Amended classifier eligibility and component use

- `supervised_single_label_binary_classification`: exactly one binary-outcome label.
- `supervised_multi_label_classification`: at least two binary-outcome labels; the
  existing token and existing records retain their meaning.
- Each label in either form requires continuous primary-output semantics and the same
  existing adapter methods, identity provider, class mapping, and privacy validation.
  Zero labels are rejected. A material task/schema change requires a new model version.
- A component consumer calls `get_metadata` and `resolve_usable` for each exact
  contributor; it retains `(model_id, model_version, label_id)` plus the resolved
  adapter compatibility metadata. Several one-label contributors do not become one
  multi-label registration. Overlapping label IDs remain separate source contributions.
- An unknown, wrong-version, unattached, or incompatible contributor fails by the
  existing typed error contract. It cannot be substituted or silently dropped to claim
  a complete output. Feature 001 exposes associations and declarations only; prediction,
  output assembly, aggregation, and safety decisions belong to separately specified
  consumers. No new registry operation, component persistence, or adapter method is added.
- Acceptance must exercise both all-single-label and mixed contributor sets, preserve
  exact source metadata, and verify no patient-facing methods execute during resolution.

### PD bundle onboarding prerequisite

The handoff's shared `pd-copathology-v1.0` output version is not proof of any individual
classifier/adapter identity. Each contributor still requires the same checked evidence
and complete candidate definition. The exported probabilities have no published decision
thresholds; registration cannot invent a class mapping to satisfy the existing contract.
Obtain the authoritative frozen mapping or seek a separately approved contract amendment.
The current scope amendment changes cardinality, not identity or mapping requirements.
