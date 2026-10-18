# Quickstart: Feature 004 Signal Extraction

This is a planned validation guide. Feature 004 has not been implemented; the commands below become runnable after implementation tasks add the listed tests. Use synthetic records only.

## Prerequisites

- Python 3.11+ and the current Safira repository environment.
- Feature 001 registry with exact synthetic model/version/label registration.
- Feature 002 synthetic `PredictionRecord` from `collect_live` or a test-only precomputed contract with an independent synthetic provenance ledger.
- Feature 003 synthetic `DatasetBuildResult` with train/validation/calibration rows assigned by patient group, plus exact dataset/protocol/manifest references.
- A test `SignalInputVerifier` backed by a synthetic ledger that is independent from the candidate record/result being checked. For Feature 003 inputs, its verification must bind every embedded Feature 002 prediction's canonical content and admission lineage to exact source identity, patient/assessment/occurrence association, dataset and authorized partition. An aggregate check is sufficient only if independently controlled evidence binds the complete row inventory and each row's admission lineage.
- No real patient data, real clinical classifier or real custodian access.

## Planned focused test commands

After implementation:

```powershell
python -m pytest tests/test_signals_stateless.py tests/test_signals_reference.py tests/test_signals_boundaries.py
```

Expected: synthetic formula, evidence-state, compatibility, grouped cross-fitting, leakage, privacy and protected-boundary tests pass. Feature 003 inputs with forged, modified, mismatched, stale, or unbound embedded predictions fail before signals, cohort-support summaries, feature sets or fitted states are published. No test claims empirical or clinical validation.

Feature 001–003 regression coverage:

```powershell
python -m pytest tests/test_registry_acceptance.py tests/test_collection_acceptance.py tests/test_dataset_acceptance.py tests/test_dataset_protection.py tests/test_dataset_leakage.py
```

Expected: existing contracts retain their behavior and no new imports or tests mutate Feature 001–003 APIs.

Full regression:

```powershell
python -m pytest
```

Expected: all repository tests pass; record actual counts and any optional skips in the implementation report.

## Planned public API flow

1. Register a synthetic classifier through the existing Feature 001 API and create an admitted Feature 002 record using existing collection interfaces.
2. Configure a versioned `SignalProtocol` with exact model/version/label scope, evidence prerequisites, method versions, protocol-approved entropy/JSD settings, kNN/domain reference scope and patient-group cross-fit seed/fold design.
3. Construct `SignalExtractor(registry, protocol, verifier=synthetic_verifier)`.
4. Call `extract_record(record)` for stateless evidence coverage, entropy, modality JSD and explanation applicability. Expected result is a tuple of independent `SignalResult` values. Missing capabilities produce explicit state values, never zero.
5. Pass a ready synthetic Feature 003 development result and matching `Feature003DatasetReference` to `build_feature_set(...)`. The injected trusted verifier must independently bind every embedded Feature 002 `PredictionRecord`'s exact canonical content, admission/provenance lineage, model/version/label identity, patient/assessment/occurrence association, dataset identity and authorized partition. Aggregate verification is accepted only when controlled evidence binds the complete inventory and every row's admission lineage. Expected: any unverified or mismatched row fails closed before contributing; training reference signals use patient-grouped cross-fitting; the final reference uses training predictor evidence only; validation/calibration use frozen state; outcomes and grouping data do not appear in `features`.
6. Do not pass protected-test rows to these ordinary methods. A test of `ProtectedSignalApplyHandoff` supplies only frozen-state and exact-scope references and receives a safe receipt; the protected artifact remains inside the synthetic custodian double.

## Formula checks

- Entropy: with base-2 logs, `p=0.5` yields 1 bit and `p=0` or `1` yields 0; preserve that this is distribution entropy, not correctness probability.
- Modality JSD: equal Bernoulli outputs yield 0; divergent outputs yield a finite nonnegative value within the declared base's bound.
- kNN: a small synthetic point set returns its declared k-th distance; the query's own patient-group reference must be absent during training cross-fit. A verified regrouping may change folds/scores, while merely renaming opaque group references cannot change the final full-training reference when evidence/configuration are unchanged.
- Domain familiarity: training cross-fit tests exclude the scored group from the fold vocabulary; output only approved `seen`/`unseen` state.

## Known limitations

- Current `src/safira/signals/base.py` is empty and there are no Feature 004 implementation tests.
- Feature 002 optional evidence varies by adapter/source. Representations, repeated outputs, modality probabilities, domain categories and explanations are not guaranteed.
- kNN metric/`k`, JSD aggregation/log base, domain category semantics, fold count/seed and adequacy criteria require approval in a versioned study protocol. No thresholds or universal sample minima are provided here.
- Generic numeric explanation reliability and population-level OOD/domain-shift tests are deferred or conditional.
- No real Feature 003 input-verification or protected-test custodian integration is configured. A test double proves boundary behavior only, not authority, persistence or scientific validity.
- Feature 004 prepares signals only. It does not train safety estimators, calibrate reliability, choose a policy or output TRUST/CAUTION/DEFER.
