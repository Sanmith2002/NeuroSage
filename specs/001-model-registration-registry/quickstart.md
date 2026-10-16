# Verification Quickstart: Feature 001 Registry

Feature 001 stores immutable supervised multi-label registration metadata in a
local SQLite catalog and keeps validated classifier-adapter bindings in memory.
Verification uses synthetic models and temporary files. Registration requires
neither labelled safety data nor a safety package.

## Run verification

From the repository root, use Python 3.11+ with Safira and pytest available.
The workspace's existing `.venv` contains both. On PowerShell:

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pytest -q tests/test_registry_acceptance.py
.\.venv\Scripts\python.exe -m pytest -q
```

Expected for this revision: **4 acceptance tests pass** and **231 tests pass in
the full suite**, including all 28 original Safira contract tests. Any collection
error, assertion failure, unexpected exception, or subprocess failure fails
verification. Counts may change with later approved work; no numerical lookup
latency target is asserted.

The acceptance file exercises executable toy classifiers with two, three, and four
labels, including probabilities and non-probability continuous scores. It verifies
exact metadata round trips, active attachment, mutation resistance, and no safety
setup or assessment calls. Primary output methods are exercised independently on
invented numeric vectors after the registry operations. A five-record catalog
contains three model IDs and three versions of one ID; a fresh interpreter verifies
all metadata, refuses usable access before attachment, and reattaches exact pairs.

Tests place catalogs and synthetic manifests in pytest temporary directories.
Keep manual catalogs and model artifacts outside tracked source or under ignored
`artifacts/`. Never commit patient datasets or identifiable records.

## Public operations

Import types from `safira.registry`. The owning integration supplies a
`RegisteredModelVersion` (constructed directly or with `from_dict`), its actual
classifier, an existing `ModelAdapter`, and a trusted `IdentityProvider`.

| Operation | Expected behavior |
|---|---|
| `ModelRegistry(storage_path)` | Open/create the local catalog; reject corrupt or unsupported storage. Supports `with` and `close()`. |
| `register(definition, classifier, adapter, identity_provider)` | Validate, commit once, and bind the submitted pair to this registry handle; return immutable metadata. |
| `get_metadata(model_id, model_version)` | Return exact immutable metadata even while unattached; never choose a latest version. |
| `attach(model_id, model_version, classifier, adapter, identity_provider, definition=candidate_definition)` | Obtain fresh identity evidence and compare every candidate declaration before publishing a binding. |
| `resolve_usable(model_id, model_version)` | Return metadata, classifier, and adapter together; raise `UnattachedModelError` until attachment succeeds. |

The required `definition=` argument supplies candidate label/output, input,
modality, preprocessing, and adapter declarations. Safira does not call
patient-facing adapter methods to infer them. `to_dict()` returns detached values;
nested collections retained in definitions are immutable.

`IdentityProvider.identify_loaded_pair(classifier, adapter)` returns
`IdentityEvidence(classifier_sha256, adapter_sha256, loaded_pair_verified)`.
Digests must be 64 lowercase SHA-256 hexadecimal characters. Attestation must be
an actual Boolean and true for acceptance; both digests must match the declared
or stored identities. See the [Python contract](contracts/registry-python.md) and
the working test-only loader in
[test_registry_acceptance.py](../../tests/test_registry_acceptance.py). Its JSON
artifact format is an example owner integration, not a serialization standard.

## Requirement and acceptance coverage

Test paths below are relative to the repository root under `tests/`.

| Functional requirements | Verification files and evidence |
|---|---|
| FR-001–FR-003 | `test_registry_us1.py`, `test_registry_us3.py`, `test_registry_acceptance.py`: multi-label scope, exact keys, binary outcome meanings, continuous outputs and class mappings, schema rejection. |
| FR-004–FR-006 | `test_registry_identity.py`, `test_registry_us1.py`, `test_registry_us2.py`, `test_registry_us3.py`, `test_registry_acceptance.py`: existing adapter methods, Boolean capabilities, checked identities, deep immutability, input/modality/preprocessing round trips, material-change rejection. |
| FR-007–FR-009 | `test_registry_us2.py`, `test_registry_concurrency.py`, `test_registry_errors.py`, `test_registry_acceptance.py`: exact versions, subprocess persistence, explicit reattachment, no substitution, duplicate/concurrent insertion protection. |
| FR-010 | `test_registry_us3.py`, `test_registry_errors.py`, `test_registry_storage.py`: actionable typed validation, compatibility, missing identity and storage failures; prior state preserved. |
| FR-011–FR-012 | `test_registry_us1.py`, `test_registry_acceptance.py`: registration without safety data/packages; spies verify no patient-facing adapter calls or safety work during registry operations. |
| FR-013 | `test_model_adapter.py`, `test_adapter_capabilities.py`, `test_safety_context.py`, `test_assessment.py`, and registry acceptance: original contracts preserved; new models use owner integrations. |
| FR-014 | `test_registry_errors.py`, `test_registry_us3.py`, `test_registry_storage.py`: restricted payload rejection without echo/logging/persistence, sanitized integration errors, invalid stored-row rejection. |

| User-story acceptance scenarios | Verification |
|---|---|
| US1: 1–6 | `test_registry_us1.py`, `test_registry_acceptance.py` |
| US2: 1–6 | `test_registry_us2.py`, `test_registry_concurrency.py`, `test_registry_acceptance.py` |
| US3: 1–10 | `test_registry_us3.py`, `test_registry_errors.py`, `test_registry_us2.py`, `test_registry_concurrency.py` |

| Success criteria | Verification |
|---|---|
| SC-001, SC-006 | Acceptance tests preserve label meanings, scale, mapping, artifact identity, and supported/unsupported capabilities without inventing reliability scores or selective statuses. |
| SC-002 | Five-record catalogs retain three model IDs and three versions of one ID across genuine subprocess boundaries; concurrent duplicate tests accept one insert without overwrite. |
| SC-003 | Parameterized invalid declaration, adapter, lookup, and stored-row tests require typed failures and unchanged accepted state. |
| SC-004 | US1 and final acceptance spies require zero safety setup or assessment work during registry operations. |

SC-005 was removed during clarification. The full command above runs all listed
evidence, including the writer/reader subprocess tests and synchronized duplicate
race tests.

## Known limitations and scope

- Identity provenance depends on the classifier owner or trusted loader linking
  live objects to fingerprinted material. A digest alone cannot prove an arbitrary
  Python object's origin. Safira checks evidence and digests; it does not authenticate
  arbitrary integration code.
- Owners must keep loaded classifier, adapter, and preprocessing behavior fixed.
  Material changes require a new model version. Bindings belong to a registry
  handle and disappear on close or process exit; retained metadata alone establishes
  neither usable access nor a ready safety package.
- Registration checks declarations and method availability without predictions.
  It cannot prove an arbitrary model's future output ranges, correctness, calibration,
  or clinical validity. Toy output checks validate only the synthetic integrations.
- Storage is a local SQLite file with explicit schema versioning. Concurrent insert
  tests use two independent connections to an initialized catalog. Distributed
  synchronization, network-filesystem guarantees, import/export, and migrations
  are outside Feature 001. Unknown schema versions fail closed.
- Only supervised multi-label classifiers with at least two binary-outcome labels
  and continuous per-label outputs are supported. Standalone single-label binary
  classifiers and other learning tasks remain unsupported.

These tests verify registry software behavior. Feature 001 performs no safety-model
training, calibration, policy selection, or runtime patient assessment and supplies
no TRUST/CAUTION/DEFER operating point. **Safira remains a research prototype, not a
clinically validated medical device.**
