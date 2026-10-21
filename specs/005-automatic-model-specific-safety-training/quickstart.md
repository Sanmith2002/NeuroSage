# Feature 005 Batch A Quickstart and Verification

**Implemented status:** Batch A only (T001–T017). The current API verifies complete Feature 003/004 inputs and reports exact model/version/label eligibility. It does not construct a predictor matrix, fit candidates, select an estimator or publish an artifact.

## Environment

- Python 3.11+ in the repository root.
- Existing Feature 001–004 code and tests.
- No new runtime dependency is added in Batch A. The approved `scikit-learn==1.7.1` pin belongs to Batch B and is not required for this checkpoint.
- Production use requires a host-controlled `TrainingInputVerifier` that independently checks the complete Feature 003 dataset/build and Feature 004 run, and checks Feature 002 admission for every embedded prediction. No clinical ledger or custodian integration is configured in this repository.

## Current public preparation API

The only service operation available in Batch A is:

```python
from safira.training import SafetyTrainingService

service = SafetyTrainingService(registry, approved_training_protocol, trusted_input_verifier)
outcomes = service.prepare(dataset_build_result, signal_feature_set)
```

`prepare` takes the dataset identity from the Feature 004 `Feature003DatasetReference` and verifies it against an independently checked Feature 003 manifest digest, dataset ID, manifest reference, protocol ID/version, builder version and complete role inventory. It executes Feature 004's existing dataset/prediction admission checks, recomputes the established `SignalRowKey`, checks role-wise one-to-one alignment and validates each primary record against exact Feature 001 registration metadata.

`TrainingProtocol` declares exact `TrainingScope` entries, registered classifier/adapter/preprocessing identities, per-scope `TrainingSupportCriteria`, and required Feature 004 signal methods. Missing criteria or required-method policy returns `NOT_READY`. The protocol must not pool support across model IDs, versions or labels. The service returns `ELIGIBLE_FOR_CANDIDATE_FITTING`, `INSUFFICIENT_EVIDENCE`, `UNAVAILABLE_REQUIRED_EVIDENCE`, `INVALID_INPUT`, or `NOT_READY` as applicable. Shared verification failures raise privacy-safe typed errors. An eligible result is a preparation status only, not a trained estimator.

For synthetic development, `tests/training_fixtures.py` provides `build_inputs`, `training_scope`, and `SyntheticTrainingLedger`. The ledger must be populated separately with `ledger.admit(dataset, signals, reference)` before submitted objects can be verified. It and `SyntheticSignalVerifier` are test doubles, not production trust infrastructure.

## Verified Batch A commands

Run from the repository root in the configured virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_training_fixtures.py tests/test_training_records.py tests/test_training_verification.py tests/test_training_alignment.py tests/test_training_leakage.py tests/test_training_eligibility.py tests/test_training_privacy.py
.\.venv\Scripts\python.exe -m pytest -q tests/test_registry_acceptance.py tests/test_collection_acceptance.py tests/test_dataset_acceptance.py tests/test_signals_acceptance.py tests/test_model_adapter.py tests/test_safety_context.py tests/test_assessment.py
.\.venv\Scripts\python.exe -m pytest -q
git diff --check
```

Expected: focused Feature 005 tests, relevant Features 001–004 regression tests and the full suite pass; `git diff --check` reports no whitespace errors. Actual results are recorded in the implementation report for this batch.

Verified on the Batch A checkpoint: 38 focused Feature 005 tests passed; 38 selected Feature 001–004 regression tests passed; the full suite passed with 604 tests; `git diff --check` passed. No tests were skipped.

## Limits after Batch A

- No baseline or logistic estimator is fitted. No success status or estimator artifact is available.
- No preprocessing or predictor matrix is built. Feature 004 signal values are admitted and aligned but remain source records.
- The injected verifier is trusted-host supplied. Core checks compare its response against actual complete content and re-execute Feature 004 checks, but this does not authenticate arbitrary malicious code controlling the trusted Python host.
- Synthetic acceptance tests establish software behavior only. No scientific or clinical effectiveness is established.
- Calibration, protected final-test evidence, reliability calibration, policy selection and runtime assessment are outside this batch.
