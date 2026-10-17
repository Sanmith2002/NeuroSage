# Feature 002 Quickstart and Verification Guide

Feature 002 collects and standardizes primary predictions and optional evidence
from registered Safira classifiers or explicitly integrated precomputed sources.
It supports standalone supervised binary classifiers, supervised multi-label
classifiers, and independently registered contributors to a component output.
This guide uses synthetic fixtures only. Run commands from the repository root
(`C:\Users\User\Desktop\NeuroSage-Workspace\safira-auto-training`) in
PowerShell with Python 3.11+ and the project's `.venv`.

## Verified test commands

Run the focused Feature 002 suite:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_collection_records.py tests/test_collection_errors.py tests/test_collection_live.py tests/test_collection_live_errors.py tests/test_collection_source_contracts.py tests/test_collection_provenance.py tests/test_collection_precomputed.py tests/test_collection_adapter.py tests/test_collection_component.py tests/test_collection_evidence.py tests/test_collection_context.py tests/test_collection_acceptance.py -q
```

**Verified result:** 136 passed, 0 failed, 0 skipped.

Run the complete repository suite, including ModelAdapter, AdapterCapabilities,
SafetyContext, SafetyAssessment, and Feature 001 registry regression tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

**Verified result:** 401 passed, 0 failed, 0 skipped.

These counts were observed on 2026-10-17. Re-run the commands after changing
the source or tests; counts may change as the repository evolves.

## Public collection interfaces

The package exports the public value types and operations from
`src/safira/collection/__init__.py`:

```python
from safira.collection import (
    CollectionAssociation,
    ComponentContribution,
    ComponentIdentity,
    LiveRequest,
    PrecomputedCollector,
    SourceDeclarations,
    TrustedSourceIntegration,
    collect_live,
    precomputed_adapter,
    to_safety_context,
)
```

`collect_live(registry, association, requests, patient_data, *, component=None,
expected_contributors=None)` resolves exact registered live bindings. A caller
uses one `LiveRequest(model_id, model_version, label_id)` per requested label;
add explicit modality and evidence-meaning declarations when applicable. Live
collection validates input structure and calls the primary adapter method for
each requested source-qualified label. Optional evidence capability methods
are invoked only when the registered adapter declares support.

```python
association = CollectionAssociation("opaque-patient-ref", "assessment-1", "occurrence-1")
result = collect_live(
    registry,
    association,
    [LiveRequest("registered-model", "v1", "label-a")],
    {"registered-input-field": [0.25]},  # match the registered input schema
)
record = result.records[0]
context = to_safety_context(record)  # optional compatibility projection
```

`PrecomputedCollector(registry, integrations)` receives versioned source
contracts and their trusted verifier implementations through
`TrustedSourceIntegration(contract, verifier)`. The integration parser maps
its own external output selectors to explicit `ComponentContribution` records.
The caller supplies a `SourceDeclarations` value and the applicable
`CollectionAssociation` to `ingest`. Before admission, the injected verifier
must execute and report content-, contributor-, and association-bound
provenance checks, including its source-specific freshness and reuse checks.
The collector does not infer original model identity from an external model
name, component version, digest assertion, or payload-installed callback.

```python
integration = TrustedSourceIntegration(source_contract, trusted_verifier)
collector = PrecomputedCollector(registry, [integration])
declarations = SourceDeclarations(tuple(contributions))
result = collector.ingest(
    association, (source_contract.contract_id, source_contract.version),
    raw_source_json, declarations,
)
record = result.records[0]
adapter_view = precomputed_adapter(record)  # saved values only
```

For a component collection, pass its `ComponentIdentity` and the exact expected
`(model_id, model_version, label_id)` contributor set. Each contributor remains
an independent prediction record even when labels overlap. No prediction
fusion or aggregation is performed.

After successful precomputed ingestion, `precomputed_adapter(record)` provides
a request-scoped view using existing `ModelAdapter` methods. It only returns
admitted record values for the exact association and label. Optional evidence
that is missing, unsupported, unavailable, or invalid is not fabricated.
`to_safety_context(record, patient_data=None)` provides a detached compatibility
projection for existing consumers; the collection record remains authoritative
for provenance and the five evidence states.

## Deterministic synthetic validation flow

The automated fixtures in `tests/collection_fixtures.py` create synthetic
classifiers, adapters, source contracts, and an independent in-memory provenance
ledger. The acceptance tests in `tests/test_collection_acceptance.py` exercise
standalone binary, multi-label, and multi-model component configurations through
both live and precomputed collection, then compare the primary values, mapped
classes, and exact source keys. They also check that live and precomputed
provenance assurances stay distinct, absent raw precomputed input is reported as
`input_verification="unavailable"`, scope metadata stays source-reported, and
mutating serialized output cannot mutate an accepted record.

Additional focused tests cover exact Feature 001 registrations and versions,
subprocess restart behavior, adapter reattachment, two unrelated source
contract layouts, changed content, wrong contributors and associations,
stale/revoked/reused/reassigned provenance, duplicate event IDs, optional
evidence states, explanation/calibration distinctions, privacy-safe failures,
and existing contract compatibility. All test values are synthetic; they are
not clinical data or evidence of clinical performance.

## External integration limitations

Passing the synthetic tests does not establish direct compatibility with the PD
Co-Pathology component or another external source. Before onboarding a real
source, its actual versioned output schema, exact Feature 001 registrations and
class mappings, owner-supplied contributor mapping, and independently controlled
source provenance evidence must be available and reviewed. The PD handoff does
not establish all of those artifacts, so no PD-specific parser, provenance
assurance, threshold, or compatibility claim is made here.

Feature 002 only collects primary predictions and optional evidence. It does not
compute safety signals, train or calibrate safety models, select safety policy,
create reliability scores, emit TRUST/CAUTION/DEFER, or make diagnoses. Safira
remains a research prototype, not a clinically validated medical device.
