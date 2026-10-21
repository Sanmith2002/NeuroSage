# Feature 008 Synthetic Validation Guide

This guide records the validation completed for the synthetic-only Feature 008 implementation.

## Prerequisites

- Work from the Feature 008 branch with its approved synthetic fixtures.
- Use the repository `uv` environment and pinned scikit-learn dependency.
- Use only synthetic predictions, original training fixtures, and a test-only verifier. Do not load real patient data or protected final-test evidence.

## Completed validation

```powershell
uv run python -m pytest -q tests/test_runtime_records.py tests/test_runtime_admission.py tests/test_runtime_signals.py tests/test_runtime_scoring.py tests/test_runtime_policy.py tests/test_runtime_acceptance.py tests/test_runtime_privacy.py tests/test_runtime_boundaries.py
# 45 passed, 0 failed, 0 skipped

# Existing Feature 001–007 tests; test_runtime_*.py excluded.
$regressionFiles = Get-ChildItem tests -Filter 'test_*.py' | Where-Object { $_.Name -notlike 'test_runtime_*' } | ForEach-Object { $_.FullName }
uv run python -m pytest -q $regressionFiles
# 794 passed, 0 failed, 0 skipped

uv run python -m pytest -q
# 839 passed, 0 failed, 0 skipped
git diff --check
# passed
```

The 45 dedicated test nodes cover immutable lifecycle records, exact synthetic-only admission, target-free original predictor verification, kNN/domain reference reproduction, explanation availability states, logistic/baseline parity, exact cutoff behavior, safe `DEFER`, privacy, and non-exported API boundaries. The 794-test existing suite remained green; the complete suite collected and passed 839 tests.

All test data were synthetic. The test verifier is not production attestation. No independent performance, clinical validity, or deployment claim follows from these software tests.
