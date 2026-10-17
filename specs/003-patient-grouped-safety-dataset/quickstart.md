# Feature 003 Quickstart and Verification Guide

Feature 003 is planned to build immutable, patient-grouped correctness datasets from Feature 002 prediction records and separately verified binary outcomes. The package is not implemented yet. This guide defines the synthetic verification flow and commands expected after implementation; it does not report test results.

Run from the repository root in PowerShell with Python 3.11+ and the existing `.venv`.

## Planned focused and regression commands

After the Feature 003 tests are added, run focused dataset tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_dataset_records.py tests/test_dataset_supervision.py tests/test_dataset_grouping.py tests/test_dataset_leakage.py tests/test_dataset_protection.py tests/test_dataset_reproducibility.py tests/test_dataset_acceptance.py -q
```

Run the full existing and new regression suite:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The suite must verify that Feature 001 registry and Feature 002 collection contracts remain unchanged. The quickstart will be updated with observed test results after implementation.

## Synthetic end-to-end verification flow

The synthetic acceptance test should:

1. Reuse `tests/collection_fixtures.py` to create exact Feature 001 registrations and Feature 002 records for a standalone binary classifier, a multi-label classifier, and independently registered contributors with overlapping label IDs. Exercise both live and trusted precomputed record provenance.
2. Supply versioned synthetic `TargetDefinition` and exact `TargetBinding` values. Synthetic outcomes must include positive, negative, missing, conflicting and changed-content cases.
3. Inject a test-only trusted research verifier. It reads its own synthetic outcome and linkage ledgers, checks exact content and association/target scope, independently checks model-development lineage, checks versioned patient mapping scope, and rejects replayed or reassigned declarations. It must derive results from its separate fixture data rather than a Boolean included in an input record.
4. Build a versioned protocol with supplied assignments or an explicit deterministic grouped allocation, declared adequacy criteria and allowed protected-test summaries. For deterministic allocation, assert that the exact approved seed is used once: create a fixture where that seed is infeasible but another seed would look favorable, then verify the builder reports infeasibility without trying the alternative. Include multiple visits, occurrences, labels, contributors, source aliases, repeated observations, duplicate records, overlaps and an infeasible constraint.
5. Confirm exact `predicted_class` comparison produces correctness targets 1 and 0, preserves score kind/meaning, all five evidence states, exact model/version/label and live/precomputed provenance, while grouping every related record for one patient into one role.
6. Rebuild with reordered equivalent input and confirm assignments/targets are identical. Supply prior manifests and confirm protected patients cannot silently move to development. Have the trusted verifier check manifest origin, source/version, requested scope, completeness evidence and protected membership from its independent synthetic custodian ledger. A self-asserted “complete” manifest without a matching executed check must leave history unknown and provide no cross-version protection claim.
7. Probe privacy, deep immutability, unknown identity/independence/linkage, target mismatch, post-outcome evidence, held-out transform fitting and insufficient class/patient support. Confirm fixed safe exclusions or readiness states and no fabricated rows.
8. Assert the builder never calls classifier prediction, adapter inference, SafetyContext/SafetyAssessment construction, safety-signal calculation, estimator fitting, calibration or policy selection.

Expected acceptance result: eligible synthetic examples retain exact provenance and registered semantics; all related records for each patient share one partition; duplicates do not inflate counts; invalid and unknown evidence does not create supervision; infeasible/insufficient cases report the protocol-scoped state; the full ordinary result object and all ordinary serialization contain no protected rows, outcomes or correctness targets.

## Planned public API shape

The names and signatures below describe the planned contract only; they are not executable until implementation:

```python
from safira.dataset import DatasetBuilder

builder = DatasetBuilder(registry, trusted_dataset_verifier)
result = builder.build(
    predictions=feature_002_records,
    outcomes=verified_outcome_candidates,
    target_definitions=target_definitions,
    target_bindings=target_bindings,
    linkage_declaration=authorized_linkage,
    protocol=versioned_protocol,
    prior_manifests=prior_controlled_manifests,
    timing_declarations=prediction_time_evidence,
    protected_artifact_handoff=authorized_custodian_handoff,
)
```

`result` is planned to expose immutable development partitions, a non-sensitive protected-artifact handoff receipt/status, a controlled manifest reference, privacy-safe aggregate summary, readiness and exclusion reasons. It never contains protected-test rows, outcomes or correctness targets. The separately injected custodian handoff receives any authorized row-bearing protected artifact and owns its restricted persistence/release; Feature 003 adds no storage service. The trusted verifier is explicitly injected and performs source-specific checks; a caller Boolean, self-asserted completeness flag or digest is insufficient. See [dataset-python.md](contracts/dataset-python.md) for the planned contract and [data-model.md](data-model.md) for entities and privacy boundaries.

## Current dependencies and limitations

- No Feature 003 application code or tests exist yet.
- The project has no verified-ground-truth, model-development lineage, cross-source patient-equivalence or evaluation-protocol interface. An authorized research integration must supply these sources and checks before real records can be eligible.
- Feature 001/002 records keep patient references opaque but do not establish cross-source equivalence or prove independent safety supervision.
- Authorized custodian integrations must independently verify prior-history scope/completeness and receive the protected artifact through the explicit handoff. They remain responsible for restricted persistence, access control and release. Feature 003 adds no storage service or access-control mechanism; an ordinary result never carries the protected rows.
- Passing future synthetic tests will verify software behavior only; it will not validate clinical outcomes, demonstrate adequate real-world sample size, or establish clinical safety.
- Feature 003 does not train safety estimators, calculate safety dimensions, calibrate reliability, choose policies, generate reliability scores or TRUST/CAUTION/DEFER, or diagnose disease.
