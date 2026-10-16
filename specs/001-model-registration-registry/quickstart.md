# Planned Verification Quickstart: Feature 001 Registry

This guide is for validating Feature 001 **after implementation**. The registry modules and proposed tests in [plan.md](plan.md) do not exist yet. Use synthetic classifiers and temporary catalogs only; no patient dataset or safety package is needed.

## Prerequisites and setup

From the repository root, use Python 3.11 or later with pytest available. The current workspace has a `.venv` containing pytest. On PowerShell:

```powershell
.\.venv\Scripts\python.exe --version
```

Do not place a runtime SQLite catalog or classifier artifact in tracked source; tests must use pytest temporary directories. After the proposed registry tests are created, run them and then the complete suite. These are implementation verification targets, not claims that the new tests already pass:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_registry_definitions.py tests/test_registry_storage.py tests/test_registry_integration.py
.\.venv\Scripts\python.exe -m pytest -q
```

## End-to-end review scenarios

The scenarios refer to the proposed [Python contract](contracts/registry-python.md) and [data model](data-model.md). Future pytest files should execute them deterministically with synthetic artifact bytes and test-only `ModelAdapter` subclasses.

1. **Valid registration**: Supply an exact model ID/version, checkable classifier and adapter identities, two binary-ground-truth labels, explicit output selectors, continuous per-label values, and class mappings. Register and retrieve metadata. Expect exact round-trip of schema, identity, capability, input, modality, and preprocessing fields. Expect usable resolution with the validated pair and no safety training or assessment call.
2. **Exact versions**: Register at least three distinct model IDs and three versions of one ID. Expect every exact lookup to return its own immutable definition. Query an absent ID and an absent version; expect the corresponding typed errors with no fallback.
3. **Restart and reattachment**: Close the first registry instance, open the same temporary catalog in a fresh process, and query metadata. Expect identical metadata but `UnattachedModelError` on usable resolution. Attach the exact classifier and compatible adapter with freshly checked identities; expect usable resolution. Try changed classifier material, adapter implementation/version, label mapping, and preprocessing under the old version; expect rejection and unchanged metadata.
4. **Invalid definitions**: Try empty/duplicate/one-label schemas, more than two ground-truth outcomes, hard 0/1-only declarations, missing score meaning/scale/class boundary, a probability without the required capability/method, non-Boolean capability flags, malformed keys, and non-supervised or non-multi-label tasks. Expect specific failures with no row inserted. Do not call adapters on patient data during these checks.
5. **Duplicate race and storage failure**: Use two independent connections/processes against one temporary catalog and attempt the same key concurrently. Expect one accepted row and an explicit duplicate failure, with no overwrite. Open corrupt or unknown-schema storage; expect `RegistryStorageError`, not an empty registry. Check a failed attach leaves any prior valid binding in place.
6. **Privacy and scope**: Try a registration payload with patient-level values or a restricted-data field and assert rejection without those values appearing in stored bytes or routine error text. Use spies to assert no prediction, extraction, training, calibration, policy selection, or assessment call occurs in registration and lookup.
7. **Regression**: Run all existing tests along with registry tests. Expect no change to `ModelAdapter`, `AdapterCapabilities`, `SafetyContext`, or `SafetyAssessment` behavior.

These software checks verify registry behavior only. They do not establish clinical safety, model correctness, calibration, or a TRUST/CAUTION/DEFER operating point. Safira remains a research prototype.
