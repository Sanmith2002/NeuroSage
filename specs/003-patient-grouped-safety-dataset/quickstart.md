# Feature 003 Quickstart and Verification Guide

Feature 003 is an in-memory research dataset builder. It consumes accepted Feature 002 `PredictionRecord` values, exact Feature 001 registrations, versioned target and protocol values, and explicit trusted verification integrations. It derives correctness only from the registered `predicted_class` and a separately verified binary outcome.

Run the commands from the repository root in PowerShell with Python 3.11+ and the existing `.venv`.

## Public imports

```python
from safira.dataset import (
    DatasetBuilder,
    EvaluationProtocol,
    TargetDefinition,
    TargetBinding,
    OutcomeCandidate,
    IndependenceEvidence,
    PatientLinkageDeclaration,
)
```

The build call is `DatasetBuilder(registry, trusted_verifier).build(predictions, outcomes, target_definitions, target_bindings, linkage_declaration, protocol, ...)`. Optional arguments are `prior_manifests`, `timing_declarations`, `independence_evidence`, `transformation_declarations`, and `protected_artifact_handoff`. Verifier and custodian implementations are injected for each builder/build; Feature 003 provides no global verifier, outcome service, or artifact store.

## Verified commands and results

Run the focused Feature 003 tests:

```powershell
$datasetTests = Get-ChildItem tests -Filter 'test_dataset_*.py' | ForEach-Object { $_.FullName }
.\.venv\Scripts\python.exe -m pytest @datasetTests -q
```

Run the Feature 001/002 compatibility regressions:

```powershell
$registryTests = Get-ChildItem tests -Filter 'test_registry_*.py' | ForEach-Object { $_.FullName }
$collectionTests = Get-ChildItem tests -Filter 'test_collection_*.py' | ForEach-Object { $_.FullName }
.\.venv\Scripts\python.exe -m pytest @registryTests @collectionTests tests/test_safety_context.py tests/test_assessment.py tests/test_model_adapter.py tests/test_adapter_capabilities.py -q
```

Run the full suite:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Latest recorded results: Feature 003 focused tests **52 passed**; Feature 001/002 compatibility regressions **401 passed**; full pytest suite **453 passed**. `git diff --check` also passed.

## Synthetic verification coverage

The test-only fixtures use synthetic registrations, predictions, outcomes, opaque patient aliases, and independent in-memory ledgers. They cover single-label and multi-label records, distinct contributors with overlapping label IDs, live and trusted precomputed records, exact target and association joins, all five Feature 002 evidence states, unknown and conflicting evidence, verified linkage and prior history, patient-level roles, duplicate rejection, one-pass seeded allocation, leakage checks, protected-test handoff, immutable manifests, and protocol-scoped adequacy.

No classifier or adapter prediction method runs during dataset construction. A trusted verifier must return typed results bound to exact outcome content/source and target, model development lineage, linkage declaration, prior-history scope, and any supplied timing or transformation declaration. A caller Boolean or self-declared history completeness flag is not accepted as verification.

## Integration limits

- There is no authorized real outcome, model-development lineage, patient-linkage, timing, transform-lineage, or prior-history source configured in this repository. Synthetic passing tests establish software behavior only; they do not establish clinical validity, adequate real-world sample size, or safety.
- The builder returns only a manifest reference and safe aggregates. The caller or custodian must persist the controlled manifest and restricted artifacts under its approved storage and access rules; Feature 003 adds no store or access-control service.
- Deterministic assignment uses the configured seed exactly once. This implementation does not interpret arbitrary site, time, or strata constraints; it returns `INSUFFICIENT_EVIDENCE` when such hard constraints are declared. Supply verified assignments or add a separately approved constraint integration before using those constraints.
- Protected rows are omitted from ordinary results and serialization. When required, a per-build custodian handoff receives them and returns only a safe accepted status.
- Safira remains a research prototype. Dataset construction performs no estimator fitting, calibration, policy selection, safety-signal calculation, reliability scoring, or clinical assessment.
