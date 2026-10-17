# Verification Quickstart: Feature 001 Registry

Feature 001 stores immutable supervised single-label binary and multi-label metadata in a
local SQLite catalog and keeps validated classifier-adapter bindings in memory.
Verification uses synthetic models and temporary files. Registration requires
neither labelled safety data nor a safety package.

## Run verification

From the repository root, use Python 3.11+ with Safira and pytest available.
The workspace's existing `.venv` contains both. On PowerShell:

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pytest -q tests/test_registry_us1.py tests/test_registry_us2.py tests/test_registry_us3.py tests/test_registry_acceptance.py tests/test_registry_concurrency.py
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe .\scripts\manual_registry_demo.py
```

Verified on 2026-10-17: **167 focused tests passed** and **265 tests passed in
the full suite**, including all 28 original Safira contract tests. The focused
command includes **8 acceptance cases**. The manual demonstration exited successfully
with all PASS checks, distinct writer/reader processes and temporary storage cleanup. Any collection
error, assertion failure, unexpected exception, or subprocess failure fails
verification. Counts may change with later approved work; no numerical lookup
latency target is asserted.

The acceptance file exercises executable toy classifiers with one, two, three, and four
labels, including probabilities and non-probability continuous scores. It verifies
exact metadata round trips, active attachment, mutation resistance, and no safety
setup or assessment calls. Primary output methods are exercised independently on
invented numeric vectors after the registry operations. A five-record catalog
contains three model IDs and three versions of one ID; a fresh interpreter verifies
all metadata, refuses usable access before attachment, and reattaches exact pairs.
Additional acceptance cases resolve all-single-label and mixed component contributor
sets while retaining exact model/version/label sources, including overlapping labels.
The US2 writer/reader subprocess tests cover both legacy multi-label and mixed catalogs,
wrong classifier/adapter rejection and successful exact reattachment.

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
| FR-001–FR-003 | `test_registry_us1.py`, `test_registry_us3.py`, `test_registry_acceptance.py`: single-label binary and multi-label scope, task/count validation, exact keys, binary outcome meanings, continuous outputs and class mappings, schema rejection. |
| FR-004–FR-006 | `test_registry_identity.py`, `test_registry_us1.py`, `test_registry_us2.py`, `test_registry_us3.py`, `test_registry_acceptance.py`: existing adapter methods, Boolean capabilities, checked identities, deep immutability, input/modality/preprocessing round trips, material-change rejection. |
| FR-007–FR-009 | `test_registry_us2.py`, `test_registry_concurrency.py`, `test_registry_errors.py`, `test_registry_acceptance.py`: exact versions, subprocess persistence, explicit reattachment, no substitution, duplicate/concurrent insertion protection. |
| FR-010 | `test_registry_us3.py`, `test_registry_errors.py`, `test_registry_storage.py`: actionable typed validation, compatibility, missing identity and storage failures; prior state preserved. |
| FR-011–FR-012 | `test_registry_us1.py`, `test_registry_acceptance.py`: registration without safety data/packages; spies verify no patient-facing adapter calls or safety work during registry operations. |
| FR-013 | `test_model_adapter.py`, `test_adapter_capabilities.py`, `test_safety_context.py`, `test_assessment.py`, and registry acceptance: original contracts preserved; new models use owner integrations. |
| FR-015 | `test_registry_acceptance.py`: independent all-single-label and mixed sources, exact source-qualified labels and adapter declarations; missing/wrong-version/unattached sources fail explicitly without prediction or aggregation. |
| FR-014 | `test_registry_errors.py`, `test_registry_us3.py`, `test_registry_storage.py`: restricted payload rejection without echo/logging/persistence, sanitized integration errors, invalid stored-row rejection. |

| User-story acceptance scenarios | Verification |
|---|---|
| US1: 1–6 | `test_registry_us1.py`, `test_registry_acceptance.py` |
| US2: 1–7 | `test_registry_us2.py`, `test_registry_concurrency.py`, `test_registry_acceptance.py` |
| US3: 1–10 | `test_registry_us3.py`, `test_registry_errors.py`, `test_registry_us2.py`, `test_registry_concurrency.py` |

| Success criteria | Verification |
|---|---|
| SC-001, SC-006 | Acceptance tests preserve label meanings, scale, mapping, artifact identity, and supported/unsupported capabilities without inventing reliability scores or selective statuses. |
| SC-002 | Five-record catalogs retain three model IDs and three versions of one ID across genuine subprocess boundaries; concurrent duplicate tests accept one insert without overwrite. |
| SC-003 | Parameterized invalid declaration, adapter, lookup, and stored-row tests require typed failures and unchanged accepted state. |
| SC-004 | US1 and final acceptance spies require zero safety setup or assessment work during registry operations. |
| SC-007 | All-single-label and mixed source sets preserve exact model/version/label identity, including overlapping label IDs, without substitutions, patient calls or aggregation. |

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
- `supervised_single_label_binary_classification` requires exactly one label;
  `supervised_multi_label_classification` retains its at-least-two-label meaning.
  Both require binary outcomes, continuous primary outputs and defined class mappings.
  Empty schemas, task/count mismatches, hard-only outputs and other learning tasks
  remain unsupported. Existing multi-label records retain storage schema version 1;
  older Safira code does not automatically support the new task token.
- Component support resolves independently registered source associations only.
  Runtime output assembly, aggregation, clinical fusion and component persistence
  remain outside Feature 001.

These tests verify registry software behavior. Feature 001 performs no safety-model
training, calibration, policy selection, or runtime patient assessment and supplies
no TRUST/CAUTION/DEFER operating point. **Safira remains a research prototype, not a
clinically validated medical device.**

## Scope amendment verification completed (Constitution v3.0.0)

T024-T028 are complete. The earlier baseline had 231 tests; the 265-test result above
is the verified amended revision. Test-first execution initially produced 30 expected
single-label failures and 137 passes; after the focused validator change, all 167 focused
tests passed. The full suite then passed with 265 tests in 5.24 seconds. These durations
record this run, not a performance requirement. Verification covers:

1. Exactly-one-label binary registrations with the new explicit task token and existing
   multi-label registrations with the legacy token; continuous probability and score
   declarations remain distinct from future Safira reliability scores.
2. A consumer referencing several independent single-label models, and a mixed
   single-label/multi-label set, resolving each via `get_metadata(id, version)` and
   `resolve_usable(id, version)` with source-qualified labels and compatible adapters.
3. Restarted metadata-only access, unavailable usable access until verified exact
   reattachment, duplicate-race rejection, and unchanged privacy/identity failures.

Contributor checks execute no component inference, score aggregation or safety work.
Only the existing toy-model output tests independently exercise predictions after registry
operations. The manual demo checks five registrations (two multi-label models, a second
version of one, and two standalone binary models), all-single-label and mixed contributor
sets, overlapping source labels, duplicate/schema/version/adapter rejections, restart and
exact reattachment. Prediction, primary training, safety training, calibration and
reliability-assessment counters remain zero in both demo worker processes. The temporary
catalog and synthetic artifacts are removed on completion.

The supplied PD handoff confirms the amended topology, but actual PD onboarding is not
verified. Exact per-classifier/adapter identity evidence and authoritative
prediction-to-class mappings are still needed. Synthetic acceptance mappings must not
be presented as real PD decision rules; a component version or calibrated primary
probability does not establish a Safira safety package or readiness.
