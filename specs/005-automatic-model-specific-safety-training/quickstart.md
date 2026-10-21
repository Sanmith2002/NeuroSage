# Feature 005 Quickstart and Validation Guide

**Status:** Planning guide. Feature 005 code/tests do not exist yet; commands below are implementation checkpoints, not claims of passing results. Use only synthetic data. See [Python contract](contracts/training-python.md) for the proposed API.

## Prerequisites

- Python 3.11+ in the repository root.
- Implemented Features 001–004 and their existing synthetic test fixtures.
- During implementation, add `scikit-learn==1.7.1` as an explicit `pyproject.toml` runtime dependency. Verify the installed NumPy/SciPy/joblib/threadpoolctl versions and record them in the run artifact. Do not infer bitwise reproducibility from a seed alone.
- An approved **versioned synthetic** `TrainingProtocol` with exact source-scoped feature allowlist, non-value/optional policy, independent-patient and correctness-class adequacy, comparison prerequisites, fixed logistic `C`/`tol`/`max_iter`, preprocessing and safe aggregate policy.
- A fixture host-owned verifier with an independently maintained ledger of accepted Feature 003 dataset, Feature 004 run/feature set and Feature 002 admissions. No production clinical ledger or artifact custodian is configured in the repository. A caller-created check, digest or Boolean is insufficient.

## Proposed synthetic workflow

1. Register synthetic standalone binary, multi-label and independent multi-model classifiers through Feature 001. Keep each model/version/label distinct, including two contributors that share a label name.
2. Produce admitted synthetic Feature 002 predictions and independently verified Feature 003 correctness examples. Build patient-grouped train/validation/calibration data. Keep final-test data in the Feature 003 protected custodian boundary; never pass it to Feature 005.
3. Produce the corresponding Feature 004 `SignalFeatureSet`. Its training reference signals must be patient-group cross-fitted and its validation signals must use a compatible frozen reference fitted only on Feature 003 train. Do not recalculate signals in Feature 005.
4. Configure `SafetyTrainingService(registry, protocol, input_verifier=trusted_fixture_verifier)` and call `train(dataset_result, signal_feature_set)`. The verifier must actually consult its independent ledger. The service checks complete content and admission lineage before any matrix or artifact is published.
5. Inspect per-scope `TrainingOutcome`: one exact model/version/label may select logistic, another may select baseline, while a sparse label reports `INSUFFICIENT_EVIDENCE`. A single-class scope may show descriptive prevalence but no successful artifact. All successful artifacts are explicitly uncalibrated and non-deployable.
6. Inspect only the privacy-filtered artifact export. It must include selected family, ordered schema, preprocessing state, exact Feature 001–004 references, dependency versions, validation-selection label and lifecycle limitations. It must not include group/row keys, targets, raw rows, calibration or final-test values. Exportability does not prove durable custody.

Illustrative call shape **after implementation** (fixture constructors and protocol values come from future synthetic tests, not from this guide):

```python
trainer = SafetyTrainingService(
    registry=synthetic_registry,
    protocol=approved_synthetic_training_protocol,
    input_verifier=independent_fixture_verifier,
)
outcomes = trainer.train(verified_dataset_result, verified_signal_feature_set)
for outcome in outcomes:
    print(outcome.scope, outcome.status, outcome.reason_code)
```

The actual test fixture must first record accepted source evidence in a ledger controlled separately from the caller's submitted objects. The public `TrainingProtocol` and `TrainingOutcome` fields will be finalized during implementation without changing Features 001–004 contracts.

## Expected positive and negative results

| Synthetic case | Expected result |
|---|---|
| Valid exact single-label scope with both correctness classes, approved support, eligible predictors and validation | Valid baseline/logistic comparison; lower validation Brier wins, exact tie baseline; successful intermediate artifact labeled uncalibrated/non-deployable. |
| Multi-label classifier with one adequate and one sparse label | Independent per-label outcomes; sparse scope cannot borrow support or alter the adequate scope. |
| Two contributors/versions with the same label | Separate schemas, fits and artifacts; no pooling or transfer. |
| No independent ledger entry or forged typed check/digest | `NOT_READY`/verification failure before target, predictor, cohort support or artifact publication. |
| Changed/extra/missing/duplicate Feature 003 or 004 row, wrong role, source or reference | Exact admission/alignment failure; no partial successful artifact. |
| Single-class training, insufficient groups or required correctness support | `INSUFFICIENT_EVIDENCE`; optional descriptive baseline is not a successful estimator. |
| `invalid`/`not_ready` signal, required all-missing feature, unapproved non-value state | Explicit non-success; no fabricated numeric zero. |
| Logistic convergence/numerical failure | Safe failed-candidate status; no silent parameter change. Remaining-candidate handling follows the predeclared protocol. |
| Calibration/protected data or patient/group keys injected into predictors/artifact | Rejected or absent from all ordinary matrix, result, error and serialization surfaces. |
| Artifact for incompatible classifier/version/label, schema or fitted reference | Fail-closed compatibility rejection. |

## Planned verification commands

Execute after implementation and after the test files actually exist:

```powershell
python -m pip install -e .
python -c "import sklearn, numpy, scipy, joblib, threadpoolctl; print(sklearn.__version__, numpy.__version__, scipy.__version__, joblib.__version__, threadpoolctl.__version__)"
python -m pytest -q tests/test_training_records.py tests/test_training_verification.py tests/test_training_features.py tests/test_training_candidates.py tests/test_training_acceptance.py
python -m pytest -q tests/test_registry_acceptance.py tests/test_collection_acceptance.py tests/test_dataset_acceptance.py tests/test_signals_acceptance.py tests/test_model_adapter.py tests/test_safety_context.py tests/test_assessment.py
python -m pytest -q
git diff --check
```

File names are proposed test ownership; `$speckit-tasks` may refine them. No Feature 005 tests have been run or counted in this planning step. A synthetic pass establishes software behavior only. It does not validate the estimator clinically, provide independent final performance, authenticate an arbitrary host-injected verifier, or establish durable artifact persistence. Validation was spent on candidate selection; later calibration and policy need separately authorized evidence.
