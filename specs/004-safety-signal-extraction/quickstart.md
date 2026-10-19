# Quickstart: Feature 004 Signal Extraction

Feature 004 now provides synthetic-verifiable signal extraction and a verified development-feature-set path. Use synthetic records only in tests and demonstrations. The package does not train a safety estimator or make a clinical or reliability decision.

## Prerequisites

- Python 3.11+ and the repository environment.
- A Feature 001 exact model/version/label registration.
- Feature 002 live or trusted precomputed `PredictionRecord` values.
- A ready Feature 003 `DatasetBuildResult` containing only its ordinary train, validation and calibration rows.
- An explicitly injected independent integration implementing `verify_prediction` and, for dataset building, `verify_dataset`. The dataset check must bind the canonical whole input, dataset/protocol/manifest/builder scope, authorized partitions, complete row inventory, and each row's exact Feature 002 admission. Synthetic test ledgers demonstrate this contract; no real verifier is configured.
- A custodian integration only if `apply_protected` is used. No real custodian is configured.

## Public interfaces

The public package is `safira.signals`. The implemented methods are:

- `SignalExtractor.extract_record(record)`: source-qualified evidence coverage, Bernoulli entropy, modality JSD, repeated-output variance when configured, explanation applicability metadata, and a `not_ready` placeholder for reference methods that lack a verified dataset.
- `SignalExtractor.build_feature_set(dataset, reference)`: performs exact Feature 003 admission, checks every embedded prediction through the injected Feature 002 verifier, validates registrations, cross-fits training reference signals by patient group, fits final references from training only, then applies those frozen references to validation/calibration rows.
- `SignalExtractor.apply_protected(request)`: sends a reference-only, exact-scope request to the injected custodian and accepts only a receipt bound to that request. It never returns protected transformed values or proves durability by itself.

For reference methods, the `SignalMethodConfig.parameters` must declare their versioned study choices. `knn_distance` requires `k`, `metric="euclidean"`, `fold_count`, `seed`, `evidence_schema`, and `preprocessing_identity`. `domain_familiarity` additionally requires the category field, mapping version and privacy approval reference. Reference methods in one protocol use the same seed and fold count. The registered preprocessing identity and evidence interpretation must match exactly.

Typical setup:

```python
from safira.signals import SignalExtractor, SignalProtocol, SignalSourceKey

protocol = SignalProtocol(
    protocol_id="study-protocol", protocol_version="v1",
    source_keys=(SignalSourceKey("model-a", "v1", "label-a"),),
    method_configs=approved_method_configs,
    evidence_prerequisites={"data_sufficiency": ("feature_representation",)},
)
extractor = SignalExtractor(
    registry, protocol, prediction_verifier,
    dataset_verifier=dataset_verifier,
    protected_apply=custodian_handoff,
)
signals = extractor.extract_record(prediction_record)
feature_set = extractor.build_feature_set(dataset_build_result, dataset_reference)
```

`dataset_verifier` may be omitted only when the explicitly injected prediction verifier itself implements `verify_dataset`. No global verifier or payload-selected implementation is used. A missing or inconsistent verifier fails closed. Dataset protocol ID/version must match the signal protocol.

## Expected output meaning

- Evidence coverage is a prerequisite-to-Feature-002-state mapping, not a numeric sufficiency score.
- Entropy is computed only from a registered probability and uses the declared log base. It describes the primary prediction distribution, not correctness or Safira reliability.
- Modality JSD is emitted only for comparable modality-specific Bernoulli probabilities from the same contributor, label and assessment semantics.
- kNN emits a raw k-th-neighbour Euclidean distance; it is not a probability and has no universal threshold.
- Domain familiarity emits only `seen` or `unseen`; raw category names and the reference vocabulary are not returned.
- Explanation applicability preserves method, target, output space, calibration relation and truncation metadata. V1 produces no numeric explanation-reliability score.
- Every generated `SignalResult` preserves the registered primary output value and its value kind, scale, direction, class mapping, predicted class and calibration declaration. This primary prediction is not a Safira reliability score.
- Missing, unsupported, unavailable, invalid, insufficient and not-ready states have no fabricated numeric value.
- A `SignalFeatureRecord` contains an opaque `SignalRowKey`, exact source key and predictor `SignalResult` values. Outcomes, correctness targets, patient/group/assessment IDs and partition roles are excluded. Train/validation/calibration membership remains in the enclosing `SignalFeatureSet` collections.

## Verification commands

Focused Feature 004 tests:

```powershell
python -m pytest tests -k signals -q
```

Feature 001–003 and existing adapter/context/assessment regression tests:

```powershell
python -m pytest tests/test_registry_acceptance.py tests/test_collection_acceptance.py tests/test_dataset_acceptance.py tests/test_dataset_protection.py tests/test_dataset_leakage.py tests/test_adapter_capabilities.py tests/test_model_adapter.py tests/test_safety_context.py tests/test_assessment.py -q
```

Full repository suite:

```powershell
python -m pytest -q
```

The Feature 004 focused suite contains **85 passing tests** (all tests selected by `-k signals`). Feature 001–003 and adapter/context/assessment regression selection contains **49 passing tests**. The full repository suite contains **556 passing tests**. These are implementation verification results from this Batch C run, not evidence of scientific or clinical validity.

## Synthetic end-to-end example

`tests/test_signals_acceptance.py` builds a synthetic probability of `0.8`, valid vector and domain metadata, comparable modality probabilities, explanation metadata, and both live and trusted precomputed records. It builds a verified Feature 003 development set and asserts all six dimensions are represented. For the entropy method with base 2, `H(0.8) ≈ 0.722` bits. The exact kNN distance is calculated from the synthetic vectors and approved `k=1` Euclidean configuration; the domain output is only `seen`/`unseen`. Serialized feature rows contain no correctness target or patient/group identifier. Protected data is not an argument or return value of the ordinary API.

## Known limitations

- Trusted Feature 002/003 verification is an application-owned injection point. Synthetic ledgers test fail-closed behavior but do not establish deployment authority, clinical validity, or evidence authenticity outside their test environment.
- Protected final-test processing is only a custodian-controlled apply-only interface. The custodian owns authorization and restricted processing/storage. A matching accepted receipt does not prove durable storage unless that integration verifies and attests durability; no such integration is configured.
- Optional evidence availability depends on adapters and source contracts. Representation vectors, domain categories, repeated outputs, modality scores and explanations are not guaranteed.
- Reference methods require study-approved parameters and exact registered preprocessing/evidence compatibility. Small or incompatible references return explicit non-value states. No alternate seed search, universal sample minimum, clinical threshold or automatic transfer across models/labels is supported.
- `cohort_support` contains per-source unique training patient-group counts only. Feature 003 does not currently provide authorization for correctness-class support summaries in its ordinary result, so the feature set does not expose them or claim protocol adequacy from counts alone.
- The research method set has not been empirically validated for clinical use. Generic numerical explanation reliability, population-level distribution tests, safety-estimator training, reliability calibration and TRUST/CAUTION/DEFER policy remain outside Feature 004.
