# Quickstart Validation Guide: Feature 002

This guide describes the **planned** verification after Feature 002 is implemented. The `src/safira/collection/` package and `tests/test_collection_*.py` files do not exist at the planning stage; commands that name them are future acceptance commands, not a claim that the feature already runs. Use only synthetic inputs. See the [Python contract](contracts/collection-python.md) and [data model](data-model.md) for meanings.

## Prerequisites

- Python 3.11 or later and `pytest` in the repository's `.venv` environment. The
  system `python` currently lacks `pytest`; use the commands below as written.
- Run commands from the repository root: `C:\Users\User\Desktop\NeuroSage-Workspace\safira-auto-training`.
- Use a temporary Feature 001 SQLite catalog and synthetic registered classifier/adapter pairs. Never use real patient data or a production registry.

Existing Safira baseline can be checked now:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_model_adapter.py tests/test_adapter_capabilities.py tests/test_safety_context.py tests/test_assessment.py tests/test_registry_acceptance.py -q
```

**Observed during planning:** 36 existing adapter, context, assessment and Feature 001 registry tests passed. This checks the starting contracts, not Feature 002.

## Planned focused verification after implementation

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_collection_records.py tests/test_collection_errors.py tests/test_collection_live.py tests/test_collection_live_errors.py tests/test_collection_source_contracts.py tests/test_collection_provenance.py tests/test_collection_precomputed.py tests/test_collection_adapter.py tests/test_collection_component.py tests/test_collection_evidence.py tests/test_collection_context.py tests/test_collection_acceptance.py -q
```

**Expected after implementation:** All Feature 002 tests pass. The acceptance set must demonstrate:

1. Synthetic standalone binary and multi-label live collection uses exact registry bindings and the declared primary adapter method only once per requested label. A score stays a score; a probability stays a primary probability; the registered class mapping alone determines the class.
2. Multi-model components with different contributor counts, mixed classifier forms, overlapping labels and two exact versions retain every independent source key. External JSON selectors can differ from registered classifier selectors through an explicit checked mapping.
3. Two unrelated synthetic JSON contract layouts/versions produce equivalent standardized records through explicit `PrecomputedCollector` instances. Constructor-injected trusted integrations are detached and isolated per collector; mismatched/duplicate keys and payload or per-call handler-installation attempts fail. Duplicate JSON members, unsupported versions, malformed values, a claimed unregistered contributor without a compliant Feature 001 mapping, wrong model version and inconsistent associations fail explicitly. No fallback diagnostic record is created.
4. A **genuine subprocess restart** leaves Feature 001 metadata available but no live binding. Precomputed ingestion succeeds only after an executed trusted check binds the exact covered output content, exact registered contributor and opaque patient/assessment/occurrence association using independently controlled evidence. When no raw input is supplied, the accepted record states `input_verification=unavailable`; it never reports a passed input check. Live collection still requires reattachment.
5. All optional evidence categories and all five states are covered. Unsupported methods have zero calls; missing, invalid and failed extraction leave a valid primary explicitly incomplete. A calibrated primary probability and an explanation of an uncalibrated output keep different semantics.
6. A scoped Precomputed Adapter returns admitted values for its own assessment occurrence and label, rejects other references/capabilities, and calls the original classifier zero times. No safety-signal, training, reliability or assessment operation runs.
7. Privacy probes find no identifying references, raw observations, JSON payloads or sensitive evidence values in routine errors/logs or registry metadata.
8. Accepted prediction, evidence, association and provenance records are deeply immutable or defensively copied. Mutating original nested inputs, adapter-returned containers, verifier results, serialized return values, Precomputed Adapter results or a projected `SafetyContext` leaves accepted records and later reads unchanged.

### Required synthetic negative provenance cases

Use a trusted synthetic manifest maintained separately from the submitted JSON. Each entry binds a source provenance-event ID to deterministic covered content, exact registered contributor and opaque association occurrence, plus current/revoked and reuse/assignment status. Verify that admission rejects every case below without exposing submitted content in the error:

- change the primary value or any covered evidence after the manifest entry was prepared;
- present valid content for another model ID, model version, label ID or selector;
- present valid content under another patient, assessment or occurrence reference;
- reuse the same provenance event for a second occurrence or duplicate it within one collection;
- use a stale, revoked, previously reused or already reassigned manifest entry;
- provide only `verified=True`, a caller-controlled event ID, a digest copied from the submitted JSON or a batch-wide check that does not cover this candidate;
- return a structured check whose content, contributor, association, freshness or reuse scope is missing or conflicts with the candidate.

The positive companion case uses the same source contract and succeeds only when all bindings and current/reuse status match. Run the cases for two differently shaped source contracts to show that no universal cryptographic representation is assumed.

### Required synthetic immutability cases

After a successful live and precomputed collection, mutate original input dictionaries/lists, nested evidence and interpretation structures, and the verifier's original result object. Then mutate every nested collection returned by public serialization and Precomputed Adapter evidence methods. Verify the accepted records, provenance fields and subsequent adapter reads remain byte-for-byte or value-for-value equivalent to their post-admission snapshots. Unsupported non-detachable optional evidence must become `invalid`; a non-detachable required value must reject the envelope.

## Planned full regression verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

**Expected after implementation:** All existing and new tests pass, including unchanged `ModelAdapter`, `AdapterCapabilities`, `SafetyContext`, `SafetyAssessment` and registry tests. Record the actual pytest count and any skipped tests in the implementation report; no count is invented at planning time.

## External integration limits

The generic synthetic contracts do not establish direct compatibility with the PD Co-Pathology component. Its actual versioned JSON schema, exact per-classifier registrations/class mappings, owner-supplied selector mapping and trusted source-specific output provenance evidence must be supplied and reviewed before a PD-specific contract can be implemented or tested. No real prediction value, clinical claim or class threshold may be inferred from the handoff summary.
