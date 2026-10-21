# Feature 006 Quickstart and Verification Guide

**Purpose**: Define the synthetic validation path for the future Feature 006 implementation. The Feature 006 package and test files described here are planned, not implemented yet; do not treat these commands as passing results.

## Prerequisites and limits

- Python 3.11 or later and the existing project dependencies, including the approved `scikit-learn==1.7.1` pin in `pyproject.toml`.
- A versioned `CalibrationProtocol` with approved exact-scope support, solver, convergence, separation, slope-ambiguity, deterministic and disclosure settings. Without it, fitting returns `NOT_READY`.
- A trusted host integration that independently verifies Feature 001 registration, Feature 002 prediction admission, Feature 003 dataset/manifest and calibration inventory, Feature 004 calibration row/run/reference identities, and Feature 005 artifact origin. No production ledger or artifact custodian is configured in this repository.
- Test fixtures must be synthetic. Never place patient records or restricted source evidence in fixtures or ordinary reports.

Feature 006 does not call the original classifier, rebuild outcomes/signals, refit Feature 005, access protected final-test data, evaluate calibration quality, or expose calibrated per-patient inference. A successful artifact is `CALIBRATOR_FITTED_UNEVALUATED`; it is non-deployable and not clinically validated.

## Planned synthetic validation sequence

After implementation, acceptance fixtures will create a Feature 001 registration, synthetic Feature 002 admitted records, a manifest-bound Feature 003 calibration partition, aligned Feature 004 calibration records and a frozen Feature 005 selected artifact. A separately controlled test ledger will issue the admission and artifact-origin evidence independently of the submitted Python objects.

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

## Planned test commands

These named test modules are planned for Feature 006. They do not exist yet.

```powershell
python -m pytest -q tests/test_calibration_records.py tests/test_calibration_admission.py
python -m pytest -q tests/test_calibration_scores.py tests/test_calibration_fitting.py
python -m pytest -q tests/test_calibration_artifacts.py tests/test_calibration_acceptance.py
python -m pytest -q tests/test_calibration_regression.py
python -m pytest -q
```

The first command covers immutable configuration, verifier execution, exact manifest/row inventory, Feature 002 lineage, Feature 005 origin, scope separation and fail-closed admission. The second covers frozen-score parity, baseline formula, logistic likelihood, weighting, support, separation, slope and convergence failures. The third covers safe artifacts, compatibility, full ordinary-result privacy and three classifier configurations. The last two cover Features 001–005 compatibility and the full repository regression suite.

## Review checklist for a run report

- Record protocol ID/version/digest, Feature 003 dataset/manifest/protocol/builder identity, Feature 004 run and fitted-reference identities, exact Feature 005 artifact digest/family, and dependency/runtime versions without exposing restricted row information.
- Report counts only when the protocol permits disclosure; identify them as unique verified patient groups versus prediction occurrences.
- Mark calibration data spent for fitting. Feature 005 validation is already spent for candidate selection. Do not claim independent calibration evaluation, a reliability threshold, a policy choice, or a protected-test result.
- A Python artifact/digest is not proof of host origin or persistence. The repository has no production origin ledger or durable custodian.

## Known limitations

Software tests can establish the declared method, trust-boundary behavior, privacy, compatibility and deterministic behavior in a controlled environment. They cannot establish statistical adequacy for a target population, external transportability, independent performance, clinical safety or effectiveness. Repeated predictions are occurrence-weighted and may give higher influence to patients with more occurrences; grouped uncertainty estimation is deferred. Platform numerical-library variation may prevent bitwise cross-platform reproducibility.
