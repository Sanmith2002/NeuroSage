# Feature 006 Quickstart and Verification Guide

**Status**: Batch A (T001–T020) and Batch B (T021–T035) are implemented and verified. Batch C (T036–T048) remains planned. Batch B provides private numerical helpers only; there is still no public calibration service, successful calibrator artifact, or patient-scoring API.

## Prerequisites and limits

- Python 3.11 or later and the existing project dependencies, including the approved `scikit-learn==1.7.1` pin in `pyproject.toml`.
- A versioned `CalibrationProtocol` with approved exact-scope support, solver, convergence, separation, slope-ambiguity, deterministic and disclosure settings. Without it, fitting returns `NOT_READY`.
- A trusted host integration that independently verifies Feature 001 registration, Feature 002 prediction admission, Feature 003 dataset/manifest and calibration inventory, Feature 004 calibration row/run/reference identities, and Feature 005 artifact origin. No production ledger or artifact custodian is configured in this repository.
- Test fixtures must be synthetic. Never place patient records or restricted source evidence in fixtures or ordinary reports.

Feature 006 does not call the original classifier, rebuild outcomes/signals, refit Feature 005, access protected final-test data, evaluate calibration quality, or expose calibrated per-patient inference. A successful artifact is `CALIBRATOR_FITTED_UNEVALUATED`; it is non-deployable and not clinically validated.

## Planned Batch C end-to-end synthetic validation sequence

Batch C is expected to add the public service flow that creates a Feature 001 registration, synthetic Feature 002 admitted records, a manifest-bound Feature 003 calibration partition, aligned Feature 004 calibration records and a frozen Feature 005 selected artifact. Batches A and B supply immutable records, internal trusted admission/readiness gates, private score reconstruction and internal numerical fit helpers. Synthetic test ledgers independently record admission and artifact-origin evidence before submitted Python objects are verified.

The service sequence is:

1. Create the public service call using the configured protocol and injected trusted host verifier.
2. Verify complete shared admission and one-to-one calibration alignment before private score or fit helpers run.
3. For a logistic base, apply its exact stored Feature 005 schema/preprocessing and reconstruct `z`, then fit only `sigmoid(a + b*z)` using the approved unpenalized protocol.
4. For a baseline, verify strict-interior `p0`, then fit only the constant offset mapping to occurrence-weighted calibration prevalence.
5. Inspect only exact-scope status, safe lifecycle metadata and the detached allowlisted artifact. No per-patient calibrated values are returned.

Expected synthetic results:

- Valid, adequately supported scope: one `CALIBRATOR_FITTED_UNEVALUATED` artifact bound to that exact model/version/label and the exact verified inputs.
- Missing verifier/origin record or missing required protocol approval: `NOT_READY` or a typed shared verification failure, with no scope artifact.
- Approved support/class/score-variation criterion unmet: `INSUFFICIENT_EVIDENCE` for that exact scope; unrelated scopes remain independent.
- Required signal unavailable: `UNAVAILABLE_REQUIRED_EVIDENCE`.
- Altered or malformed content: `INVALID_INPUT`; exact version/schema/source mismatch: `INCOMPATIBLE_INPUT`.
- Separation, nonconvergence, non-finite fit, or non-positive slope: explicit numerical non-success; no fallback method or successful artifact.

## Batch B focused test command — executed

Run the private frozen-score and numerical test suites with the repository virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_calibration_scores.py tests/test_calibration_fitting.py tests/test_calibration_separation.py tests/test_calibration_logistic.py tests/test_calibration_baseline.py
```

The executed command passed **32 tests**. It covers frozen schema/preprocessing reconstruction, no-fit guards, score parity, unavailable evidence, occurrence weighting, repeated visits and unique-patient support, exact scalar separation, fixed logistic fitting, closed-form baseline offset and numerical failures.

## Batch B verification record — executed 2026-10-21

Commands executed:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_calibration_scores.py tests/test_calibration_fitting.py tests/test_calibration_separation.py tests/test_calibration_logistic.py tests/test_calibration_baseline.py
.\.venv\Scripts\python.exe -m pytest -q tests/test_calibration_records.py tests/test_calibration_admission.py tests/test_calibration_registry_compatibility.py tests/test_calibration_dataset_admission.py tests/test_calibration_signal_alignment.py tests/test_calibration_artifact_admission.py tests/test_calibration_readiness.py tests/test_calibration_bundle_gate.py tests/test_calibration_acceptance.py
$files = Get-ChildItem tests -File | Where-Object { $_.Name -notlike 'test_calibration_*' } | ForEach-Object { $_.FullName }; .\.venv\Scripts\python.exe -m pytest -q $files
.\.venv\Scripts\python.exe -m pytest -q
git diff --check
```

Results: **32 Batch B focused tests passed**; **40 Batch A focused tests passed**; **659 non-Feature-006 regression tests passed**; **731 total tests passed, 0 failed, 0 skipped**. The combined Feature 006 suites contained **72 passing tests**. `git diff --check` passed. Runtime scikit-learn was **1.7.1**, matching the approved pin. These are software verification results, not scientific or clinical validation.

### Synthetic numerical checks

- Frozen logistic reconstruction used the stored ordered coefficient `(0.7205499399734128,)`, intercept `-0.3601598107328854`, and the production Feature 005 transform. For a synthetic calibration row with transformed value `0`, reconstructed `z` was `-0.3601598107328854`; the test independently evaluated `intercept + coefficient × transformed_row` and matched within test tolerance `1e-12`.
- Logistic recalibration on synthetic scores `(0, 1, 2, 1, 1.5)` and targets `(0, 0, 0, 1, 1)` returned `a=-1.0740042442582705`, `b=0.592518459370526`, in 7 iterations. The fitted slope is positive; no probability or performance claim follows from this synthetic fit.
- Baseline example with `p0=0.25` and occurrences `(0, 0, 1)` gave `p_cal=1/3` and offset `a=0.40546510810816416`; its mapping remains constant across occurrences.
- Geometry checks reported singleton-interior as finite-MLE geometry (`None`), complete and quasi separation as `separated`, and a constant-score design as `rank_deficient`. The negative-direction overlap fit returned a negative slope and a numerical non-success. A one-iteration fit was rejected for nonconvergence.
- Artifact snapshots were unchanged after reconstruction/vectorization/fitting. The helpers remain private; they create no successful calibrator artifact, public inference method, service, evaluation, or policy behavior.

## Batch A verification record — executed 2026-10-21

Prior Batch A execution record (rerun in this Batch B session):

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_calibration_records.py tests/test_calibration_admission.py tests/test_calibration_registry_compatibility.py tests/test_calibration_dataset_admission.py tests/test_calibration_signal_alignment.py tests/test_calibration_artifact_admission.py tests/test_calibration_readiness.py tests/test_calibration_bundle_gate.py tests/test_calibration_acceptance.py
$targets = Get-ChildItem tests -File | Where-Object { $_.Name -match '^test_(registry|collection|dataset|signals|training|model_adapter|adapter_capabilities)' } | ForEach-Object { $_.FullName }; .\.venv\Scripts\python.exe -m pytest -q $targets
.\.venv\Scripts\python.exe -m pytest -q
git diff --check
```

The Batch A focused command was rerun in this session and passed **40 tests**. Its earlier full-suite figures (699 total and 647 existing-feature compatibility tests) describe the pre-Batch-B state; current combined results are recorded in the Batch B verification section above. These are software verification results only; they do not establish scientific or clinical calibration effectiveness.

Batch A verifies exact Feature 001 scope and registered prediction semantics, independently ledger-backed Feature 002 admission, complete Feature 003 ordinary inventory and prediction lineage, Feature 004 one-to-one signal alignment, Feature 005 exact artifact origin and input binding, protocol-specific support, and internal admission-only scope readiness. No score reconstruction, fitting, calibration artifact, public service, or per-patient application API is implemented in Batch A.

## Review checklist for a run report

- Record protocol ID/version/digest, Feature 003 dataset/manifest/protocol/builder identity, Feature 004 run and fitted-reference identities, exact Feature 005 artifact digest/family, and dependency/runtime versions without exposing restricted row information.
- Report counts only when the protocol permits disclosure; identify them as unique verified patient groups versus prediction occurrences.
- Mark calibration data spent for fitting. Feature 005 validation is already spent for candidate selection. Do not claim independent calibration evaluation, a reliability threshold, a policy choice, or a protected-test result.
- A Python artifact/digest is not proof of host origin or persistence. The repository has no production origin ledger or durable custodian.

## Known limitations

Software tests can establish the declared method, trust-boundary behavior, privacy, compatibility and deterministic behavior in a controlled environment. They cannot establish statistical adequacy for a target population, external transportability, independent performance, clinical safety or effectiveness. Repeated predictions are occurrence-weighted and may give higher influence to patients with more occurrences; grouped uncertainty estimation is deferred. Platform numerical-library variation may prevent bitwise cross-platform reproducibility.
