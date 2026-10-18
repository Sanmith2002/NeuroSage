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
    PredictionAdmissionVerification,
    DatasetManifestReceipt,
    DatasetManifestHandoff,
    prediction_fingerprint,
)
```

The build call is `DatasetBuilder(registry, trusted_verifier).build(predictions, outcomes, target_definitions, target_bindings, linkage_declaration, protocol, ...)`. Optional arguments include `prior_manifests`, `timing_declarations`, `independence_evidence`, `transformation_declarations`, `protected_artifact_handoff`, `manifest_handoff`, `source_namespaces`, and `group_attributes`. Verifier and custodian implementations are injected for each builder/build; Feature 003 provides no global verifier, outcome service, or artifact store.

The trusted verifier must implement `verify_prediction_admission(prediction)`. It checks the complete Feature 002 record against independently controlled source admission evidence and returns a `PredictionAdmissionVerification` bound to the canonical record fingerprint, model/version/label, association, provenance mode, authority, method, and evidence reference. A hash or `SourceProvenance` fields alone do not establish admission. Tests use an in-memory synthetic ledger to model this boundary; real integrations must provide their own independent evidence.

For live records, provide an exact source namespace in the verified linkage declaration when that patient reference maps to one namespace, or pass `source_namespaces={prediction_fingerprint: namespace}` to disambiguate it. Do not use `unknown`. `group_attributes` supplies only the opaque site, timezone-qualified timestamp, or stratum values required by declared partition constraints.

When the research custodian needs the reproducibility artifact, pass an explicit `manifest_handoff` implementing `accept(manifest, protocol, manifest_reference)`. It receives the complete immutable, restricted `DatasetManifest`; the ordinary result contains only the handoff receipt and digest reference. Without this handoff, Feature 003 does not retain or expose the manifest for later recovery.

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

Latest recorded results after F1–F6 remediation: Feature 003 focused tests **60 passed**; Feature 001/002 compatibility regressions **401 passed**; full pytest suite **461 passed**. `git diff --check` also passed.

## Synthetic verification coverage

The test-only fixtures use synthetic registrations, predictions, outcomes, opaque patient aliases, and independent in-memory ledgers. They cover single-label and multi-label records, distinct contributors with overlapping label IDs, live and trusted precomputed records, exact target and association joins, all five Feature 002 evidence states, caller-forged provenance rejection, verified linkage and prior history, patient-level roles, duplicate rejection, one-pass seeded allocation, supplied and deterministic site/time/strata checks, leakage checks, protected-test and manifest custodian handoffs, deep immutability, and exact contributor-scoped adequacy.

No classifier or adapter prediction method runs during dataset construction. A trusted verifier must return typed results bound to the exact Feature 002 record, outcome content/source and target, model development lineage, linkage declaration, prior-history scope, and any supplied timing or transformation declaration. A caller Boolean, self-declared provenance field, or self-declared history completeness flag is not accepted as verification.

## Integration limits

- There is no authorized real outcome, model-development lineage, patient-linkage, timing, transform-lineage, or prior-history source configured in this repository. Synthetic passing tests establish software behavior only; they do not establish clinical validity, adequate real-world sample size, or safety.
- The builder returns only a manifest reference and safe aggregates. To obtain and persist the complete controlled manifest, the authorized custodian supplies `manifest_handoff`; Feature 003 adds no store or access-control service. The handoff receipt must be non-sensitive.
- Supported constraints are site isolation (`same_partition`), timezone-qualified time windows, and declared strata membership. Unknown constraints return `NOT_READY`; missing group attributes return `NOT_READY`; unsatisfied supported constraints return `INSUFFICIENT_EVIDENCE`. Deterministic allocation uses exactly the approved seed with no alternatives.
- Per-label adequacy criteria apply independently to each exact model/version/label contributor. `adequacy_by_source` can declare additional exact-key counts, including correct/incorrect support; no contributor's counts are combined solely by label name.
- Protected rows are omitted from ordinary results and serialization. When required, a per-build custodian handoff receives them and returns only a safe accepted status.
- Safira remains a research prototype. Dataset construction performs no estimator fitting, calibration, policy selection, safety-signal calculation, reliability scoring, or clinical assessment.
