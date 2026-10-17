# Feature 003 Implementation Context

Reusable repository and sequencing notes for task generation and implementation. This is a compact companion to [plan.md](plan.md), [data-model.md](data-model.md), and the [Python contract](contracts/dataset-python.md).

## Existing contracts to consume

- `src/safira/registry/`: `ModelRegistry.get_metadata(model_id, model_version)` returns the exact immutable `RegisteredModelVersion`; `resolve_usable` is unnecessary. `LabelDefinition` declares binary positive/negative class names, value kind/scale, and the existing primary class mapping. Never modify or infer around it.
- `src/safira/collection/`: `PredictionRecord` is immutable and source-qualified by `(model_id, model_version, label_id)`, with opaque `CollectionAssociation(patient_ref, assessment_ref, occurrence_ref)`, `PrimaryOutput.predicted_class`, score semantics, `SourceProvenance`, component identity and five-state `EvidenceItem` values. Consume these records directly; no re-inference or changes to collection types.
- `src/safira/context/`, `src/safira/adapters/`, `src/safira/models/`: `SafetyContext`, `ModelAdapter`, `AdapterCapabilities`, and `SafetyAssessment` remain unchanged and are not used to store correctness/ground-truth outputs.
- Feature 001/002 do not define target versions, verified outcomes, primary-model data-development lineage, cross-source patient groups, dataset partitions, or protected assignment history. Add these as supplemental Feature 003 values and explicitly injected verifier results.
- Root `pyproject.toml` requires Python >=3.11 and declares no runtime dependencies. Tests use pytest. Keep implementation on the standard library and existing packages.

## Proposed modules and jobs

| Module | Job |
|---|---|
| `src/safira/dataset/records.py` | Deeply immutable target/outcome/linkage/protocol, correctness example, partition, manifest and summary values. |
| `src/safira/dataset/verification.py` | Explicit verifier protocols and exact-scope result validation for outcomes, independence and linkage. |
| `src/safira/dataset/validation.py` | Exact registry/target joins, eligibility, duplicate/conflict, timing and transform-leakage checks; safe exclusion reasons. |
| `src/safira/dataset/partitioning.py` | Supplied or deterministic patient-group assignment, prior-manifest conflict checks and scoped adequacy. |
| `src/safira/dataset/builder.py` | Ordered orchestration into development partitions, separately handled protected artifact, manifest and redacted report. |
| `src/safira/dataset/exceptions.py` | Typed, privacy-safe exceptions and readiness categories. |

## Dependency order

1. Value types, error categories, safe serializer, and synthetic Feature 003 fixtures.
2. Verifier protocols and exact Feature 001 registration/target compatibility.
3. Verified outcome/independence joins and correctness target derivation.
4. Authorized patient-linkage validation, duplicate/conflict and overlap checks.
5. Versioned protocol and patient-grouped assignments; frozen prior/final-test membership and adequacy.
6. Prediction-time evidence and transform leakage checks; protected output separation and deterministic manifest.
7. End-to-end story tests, privacy/immutability probes, contract regression, quickstart and full pytest.

Tests should reuse `tests/conftest.py` and `tests/collection_fixtures.py` for registry, adapters and accepted prediction records. Add a synthetic-only `tests/dataset_fixtures.py`; keep Feature 003 tests under `tests/test_dataset_*.py`.

## Non-negotiable invariants

- Correctness is `record.primary.predicted_class == verified_outcome_mapped_to_registered_class`; never derive another boundary from the score.
- Every output remains exact `(model_id, model_version, label_id)` and association qualified. Two contributors with the same label remain distinct.
- No caller flag, source identifier, or digest alone proves outcome truth, development independence, or patient equivalence. Injected trusted integrations execute exact-scope checks against their controlled sources; Safira does not claim universal verification.
- Unresolved patient overlap is unknown, not disjoint. Every related record for an authorized patient group occupies exactly one of train, validation, calibration, or protected final test.
- No default split ratios/minima, seed search, fabricated/balanced samples, silent reassignment, or weakening constraints to achieve readiness.
- Ground truth, correctness, group identity, verification, and role never become prediction-time features. Future transforms are declared and checked, never fit here.
- Protected rows, full linkage and assignment manifests are controlled artifacts; ordinary diagnostics expose no patient identifiers, raw evidence or protected outcome distributions.
- No classifier/adapter prediction, safety signals, estimator training, calibration, policy selection, reliability score or assessment occurs in Feature 003.
