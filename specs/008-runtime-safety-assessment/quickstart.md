# Feature 008 Synthetic Validation Guide

This guide describes validation to run after implementation. No Feature 008 runtime code exists yet.

## Prerequisites

- Work from the Feature 008 branch with its approved synthetic fixtures.
- Use the repository `uv` environment and pinned scikit-learn dependency.
- Use only synthetic predictions, original training fixtures, and a test-only verifier. Do not load real patient data or protected final-test evidence.

## Planned validation

```powershell
uv run python -m pytest -q tests/test_runtime_admission.py tests/test_runtime_signals.py
uv run python -m pytest -q tests/test_runtime_scoring.py tests/test_runtime_policy.py
uv run python -m pytest -q tests/test_runtime_privacy.py tests/test_runtime_acceptance.py
uv run python -m pytest -q
```

Expected behavior: exact synthetic bundles produce the frozen parity result and status required by their stored cutoff; altered or incomplete shared trust evidence is rejected atomically; documented runtime evidence/readiness failures yield only safe `DEFER`; no score, patient data, protected evidence, or public `SafetyAssessment` is produced.

These are planned commands, not completed test results.
