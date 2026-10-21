# Feature 005 Quickstart and Verification

Feature 005 Batch C (T029–T047) is implemented. `SafetyTrainingService.train(dataset, signals)` performs trusted input admission, independent per-scope training, one approved validation comparison and safe in-memory artifact construction. `prepare` remains the eligibility-only operation. The emitted artifacts are uncalibrated, non-deployable research results; there is no estimator inference, calibration, policy-selection, or `SafetyAssessment` API.

## Environment

- Python 3.11 or newer.
- Install the repository in the project virtual environment: `python -m pip install -e .`.
- Feature 005 pins `scikit-learn==1.7.1`. The verified environment used Python 3.11.0, scikit-learn 1.7.1, NumPy 2.4.6, SciPy 1.17.1, joblib 1.6.0 and threadpoolctl 3.7.0.
- Production integration must provide a host-controlled `TrainingInputVerifier` which independently verifies the exact Feature 003 dataset/build, the Feature 004 run and every embedded Feature 002 admission. The repository does not configure a clinical ledger or artifact custodian.

## Public training API

`TrainingProtocol` fixes the exact model/version/label scopes, support criteria, predictor schemas, training-only preprocessing, logistic parameters, validation support criteria and candidate-failure policy before validation is inspected.

```python
from safira.training import (
    CandidateFailurePolicy,
    FeatureKind,
    FeaturePolicy,
    FeatureSpec,
    LogisticCandidateConfig,
    PreprocessingPolicy,
    SafetyTrainingService,
    TrainingProtocol,
    TrainingScope,
    TrainingSupportCriteria,
    ValidationSupportCriteria,
)
from safira.signals import SignalDimension

# `scope` is built from Feature 001's exact registration and adapter metadata.
scope = TrainingScope(
    model_id="synthetic-model", model_version="v1", label_id="label-a",
    classifier_artifact_sha256=registered_classifier_sha256,
    adapter_id=registered_adapter_id, adapter_version=registered_adapter_version,
    adapter_fingerprint=registered_adapter_fingerprint,
    preprocessing_identity=registered_preprocessing_identity,
)
key = scope.source_key
protocol = TrainingProtocol(
    protocol_id="research-training", version="v1", scopes=(scope,),
    adequacy={key: TrainingSupportCriteria(4, {0: 2, 1: 2})},
    required_signal_methods={key: ("binary_entropy",)},
    feature_policies={key: FeaturePolicy((FeatureSpec(
        method_id="binary_entropy", method_version="v1",
        meaning="binary_predictive_entropy", dimension=SignalDimension.PREDICTION_UNCERTAINTY,
        kind=FeatureKind.NUMERIC, method_parameters={"base": "natural"},
        required=True, state_indicators=False),))},
    preprocessing_policies={key: PreprocessingPolicy(
        constant_features="keep", category_encoding="one_hot_seen_unseen",
        numeric_imputation={"binary_entropy": "none"},
        numeric_scaling={"binary_entropy": "standard"})},
    logistic_configs={key: LogisticCandidateConfig(approved=True, C=1.0, tol=1e-4, max_iter=200)},
    validation_adequacy={key: ValidationSupportCriteria(4, {0: 1, 1: 1})},
    candidate_failure_policies={key: CandidateFailurePolicy.REQUIRE_ALL},
)

service = SafetyTrainingService(registry, protocol, trusted_input_verifier)
outcomes = service.train(verified_feature_003_dataset, verified_feature_004_set)
for outcome in outcomes:
    print(outcome.scope.source_key, outcome.status.value, outcome.reason_code)
    if outcome.artifact is not None:
        safe_json_payload = outcome.artifact.to_dict()
```

The example metadata names are synthetic placeholders. The input objects and verifier must come from the host's authorized Feature 001–004 integration. A caller-created typed result, digest or Boolean is not admission. No validation result may be used to modify configuration, candidate set, preprocessing, seed or feature schema.

The selected status is `SELECTED_BASELINE` or `SELECTED_LOGISTIC`. Missing approval yields `NOT_READY`; unmet protocol support yields `INSUFFICIENT_EVIDENCE`; unusable required features, invalid inputs and undefined comparisons have distinct non-success results. A single-class training scope never produces a successful baseline artifact. Candidate fallback after logistic fitting failure is allowed only when its exact protocol declares `ALLOW_REMAINING`; invalid, incompatible or not-ready candidates are not silently dropped.

`prepare(dataset, signals)` performs the same full trust/alignment gate and returns only per-scope eligibility; it does not fit candidates. The candidate fitting, comparison and feature-matrix helper functions are internal and are not exported from `safira.training`.

## Artifact inspection and controlled validation

`SafetyEstimatorArtifact.to_dict()` returns a detached, allowlisted, JSON-compatible representation with a canonical digest. It records the exact registered model/version/label and adapter identity, Feature 005 protocol digest, Feature 003 manifest-bound dataset identity and content/inventory digests, Feature 004 run/method-parameter/fitted-reference identities, frozen predictor/preprocessing schema, estimator state, dependency versions, train metrics, validation selection metrics and lifecycle limitations.

`validate_artifact(payload, expected_compatibility, artifact_origin_verifier)` checks exact compatibility, payload digest, finite state dimensions and a host-controlled origin lookup. The origin provider must return an exact `ArtifactOriginCheck` binding the submitted digest, scope and artifact version; `True` or a matching digest alone is rejected. The configured host controls that provider. This check does not authenticate malicious Python controlling the trusted host or prove durable storage. No pickle/joblib loading is used.

Ordinary outcomes and artifacts omit patient/group identifiers, row keys, correctness targets, raw observations, restricted evidence, calibration values and protected-test content. Aggregate validation support appears only when explicitly allowed by the protocol. Artifacts mark validation selection as spent, calibration as reserved, protected-test access as false, and the result as uncalibrated and non-deployable. Validation metrics are selection evidence, not unbiased final performance estimates.

## Synthetic fixtures and tests

`tests/training_fixtures.py` supplies `build_inputs`, `training_scope` and `SyntheticTrainingLedger`. The fixture ledger and `SyntheticSignalVerifier` are test-only independently controlled doubles; they are not production trust infrastructure.

Run the Feature 005 suite from the repository root:

```powershell
$trainingTests = Get-ChildItem tests -File -Filter 'test_training_*.py' | ForEach-Object { $_.FullName }
.\.venv\Scripts\python.exe -m pytest @trainingTests -q
```

Run relevant Feature 001–004 and existing adapter/context/assessment regressions:

```powershell
$regressionTests = Get-ChildItem tests -File | Where-Object {
    $_.Name -match '^test_(registry|collection|dataset|signals).*\.py$' -or
    $_.Name -in @('test_adapter_capabilities.py','test_model_adapter.py','test_assessment.py','test_safety_context.py')
} | ForEach-Object { $_.FullName }
.\.venv\Scripts\python.exe -m pytest @regressionTests -q
```

Run the full suite and whitespace check:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
git diff --check
```

## Verified Batch C results

On the implementation environment above:

- Feature 005 training tests: **93 passed**.
- Relevant Features 001–004 and adapter/context/assessment regression tests: **566 passed**.
- Full pytest suite: **659 passed, 0 failed, 0 skipped**.
- `git diff --check`: passed.

The synthetic tests exercise standalone binary, multi-label and independent multi-model scopes; logistic and baseline selection including an exact tie; one insufficient label beside an eligible label; train-only fitting; exact admission and artifact compatibility; immutable/private export; untrusted origin rejection; test-only numerical reproduction; and guards against invoking primary prediction, target construction, signal extraction, protected evaluation or assessment APIs.

## Limitations

- No configured production trust ledger, clinical integration, or artifact custodian exists in this repository. The core executes the injected checks and verifies their exact content bindings, but relies on the trusted host to control verifier construction.
- In-memory artifact export does not claim durable persistence. A valid digest is integrity evidence, not proof of origin.
- The logistic estimator and prevalence baseline are correctness-estimator research candidates. Their selection results do not establish scientific or clinical effectiveness.
- Feature 005 does not use Feature 003 calibration or protected final-test evidence, calibrate Safira reliability, select a policy, expose estimator inference, or create TRUST/CAUTION/DEFER assessments. Later policy selection requires distinct independently authorized evidence because validation selection is spent.
