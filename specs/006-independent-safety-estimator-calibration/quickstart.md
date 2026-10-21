# Feature 006 Quickstart and Verification Guide

**Status**: Batch A (T001–T020) is implemented and verified. Batch B (T021–T035) and Batch C (T036–T048) remain planned. The executed Batch A results are recorded below; later-phase commands remain plans, not passing results.

## Prerequisites and limits

- Python 3.11 or later and the existing project dependencies, including the approved `scikit-learn==1.7.1` pin in `pyproject.toml`.
- A versioned `CalibrationProtocol` with approved exact-scope support, solver, convergence, separation, slope-ambiguity, deterministic and disclosure settings. Without it, fitting returns `NOT_READY`.
- A trusted host integration that independently verifies Feature 001 registration, Feature 002 prediction admission, Feature 003 dataset/manifest and calibration inventory, Feature 004 calibration row/run/reference identities, and Feature 005 artifact origin. No production ledger or artifact custodian is configured in this repository.
- Test fixtures must be synthetic. Never place patient records or restricted source evidence in fixtures or ordinary reports.

Feature 006 does not call the original classifier, rebuild outcomes/signals, refit Feature 005, access protected final-test data, evaluate calibration quality, or expose calibrated per-patient inference. A successful artifact is `CALIBRATOR_FITTED_UNEVALUATED`; it is non-deployable and not clinically validated.

## Planned end-to-end synthetic validation sequence

Batch C will add the public service flow that creates a Feature 001 registration, synthetic Feature 002 admitted records, a manifest-bound Feature 003 calibration partition, aligned Feature 004 calibration records and a frozen Feature 005 selected artifact. Batch A currently supplies the immutable records and internal trusted admission/readiness gates. Synthetic test ledgers independently record admission and artifact-origin evidence before submitted Python objects are verified.

The service sequence is:

1. Call `CalibrationService.calibrate(dataset, signals, artifacts)` with its configured protocol and injected test verifier.
2. Verify that complete shared admission and one-to-one calibration row alignment finish before any score or fitter helper executes.
3. For a logistic base, apply its exact stored Feature 005 schema/preprocessing and reconstruct `z`, then fit only `sigmoid(a + b*z)` with the approved unpenalized protocol.
4. For a baseline, verify strict-interior `p0`, then fit only the constant offset mapping to the occurrence-weighted calibration prevalence.
5. Inspect only the exact-scope status, safe convergence/lifecycle metadata and detached allowlisted artifact. No per-patient calibrated values are returned.

Expected synthetic results:

- Valid, adequately supported scope: one `CALIBRATOR_FITTED_UNEVALUATED` artifact bound to that exact model/version/label and the exact verified inputs.
- Missing verifier/origin record or missing required protocol approval: `NOT_READY` or a typed shared verification failure, with no scope artifact.
- Approved support/class/score-variation criterion unmet: `INSUFFICIENT_EVIDENCE` for that exact scope; unrelated scopes remain independent.
- Required signal unavailable: `UNAVAILABLE_REQUIRED_EVIDENCE`.
- Altered or malformed content: `INVALID_INPUT`; exact version/schema/source mismatch: `INCOMPATIBLE_INPUT`.
- Separation, nonconvergence, non-finite fit, or non-positive slope: explicit numerical non-success; no fallback method or successful artifact.

## Planned later-phase test commands

The score, fitting, artifact, and final integration test modules below are planned for Batch B and Batch C; they do not exist yet.

```powershell
python -m pytest -q tests/test_calibration_records.py tests/test_calibration_admission.py
python -m pytest -q tests/test_calibration_scores.py tests/test_calibration_fitting.py
python -m pytest -q tests/test_calibration_artifacts.py tests/test_calibration_acceptance.py
python -m pytest -q tests/test_calibration_regression.py
python -m pytest -q
```

The planned commands cover frozen-score parity, baseline formula, logistic likelihood, weighting, support, separation, safe artifacts, final service privacy, and regression tests once those later batches are implemented.

## Batch A verification record — executed 2026-10-21

Commands executed with the repository virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_calibration_records.py tests/test_calibration_admission.py tests/test_calibration_registry_compatibility.py tests/test_calibration_dataset_admission.py tests/test_calibration_signal_alignment.py tests/test_calibration_artifact_admission.py tests/test_calibration_readiness.py tests/test_calibration_bundle_gate.py tests/test_calibration_acceptance.py
$targets = Get-ChildItem tests -File | Where-Object { $_.Name -match '^test_(registry|collection|dataset|signals|training|model_adapter|adapter_capabilities)' } | ForEach-Object { $_.FullName }; .\.venv\Scripts\python.exe -m pytest -q $targets
.\.venv\Scripts\python.exe -m pytest -q
git diff --check
```

Results: **40 Batch A tests passed**; **699 repository tests passed, 0 failed, 0 skipped**. The existing Feature 001–005 compatibility suites also passed: **647 tests**. `git diff --check` passed. These are software verification results only; they do not establish scientific or clinical calibration effectiveness.

Batch A verifies exact Feature 001 scope and registered prediction semantics, independently ledger-backed Feature 002 admission, complete Feature 003 ordinary inventory and prediction lineage, Feature 004 one-to-one signal alignment, Feature 005 exact artifact origin and input binding, protocol-specific support, and internal admission-only scope readiness. No score reconstruction, fitting, calibration artifact, public service, or per-patient application API is implemented in Batch A.

## Review checklist for a run report

- Record protocol ID/version/digest, Feature 003 dataset/manifest/protocol/builder identity, Feature 004 run and fitted-reference identities, exact Feature 005 artifact digest/family, and dependency/runtime versions without exposing restricted row information.
- Report counts only when the protocol permits disclosure; identify them as unique verified patient groups versus prediction occurrences.
- Mark calibration data spent for fitting. Feature 005 validation is already spent for candidate selection. Do not claim independent calibration evaluation, a reliability threshold, a policy choice, or a protected-test result.
- A Python artifact/digest is not proof of host origin or persistence. The repository has no production origin ledger or durable custodian.

## Known limitations

Software tests can establish the declared method, trust-boundary behavior, privacy, compatibility and deterministic behavior in a controlled environment. They cannot establish statistical adequacy for a target population, external transportability, independent performance, clinical safety or effectiveness. Repeated predictions are occurrence-weighted and may give higher influence to patients with more occurrences; grouped uncertainty estimation is deferred. Platform numerical-library variation may prevent bitwise cross-platform reproducibility.
