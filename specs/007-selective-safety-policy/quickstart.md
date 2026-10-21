# Feature 007 Quickstart and Verification Guide

Feature 007 is planned but not implemented yet. These commands are the expected verification entry points after implementation; results must be recorded from the actual run and must not be represented as already executed.

## Prerequisites

- Python 3.11+ with the repository's approved development environment.
- Synthetic Feature 001 registry/classifier fixtures and synthetic Feature 002/003/004 records.
- Independently injected synthetic trusted verifiers for prediction admission, dataset/ground-truth verification, artifact origin, and patient disjointness.
- Synthetic Feature 005/006 artifacts with their original compatible provenance and a distinct synthetic policy-selection Feature 003 build.
- A versioned protocol with explicit synthetic risk ceiling, one patient index rule, support, candidate, equality, tie, and disclosure settings. These values are test-only fixtures and are not recommended clinical values.

## Commands

Focused Feature 007 verification:

```powershell
python -m pytest tests/test_policy_*.py -q
```

Feature 001–006 compatibility regression:

```powershell
python -m pytest tests -q
```

Whitespace/diff validation:

```powershell
git diff --check
```

## Expected synthetic scenario

1. Build a synthetic exact-scope Feature 005 estimator and Feature 006 calibrator, record their original Feature 003/004 bindings, and add them to a test-only trusted origin ledger.
2. Produce original Feature 004 reference outputs from synthetic original training rows. Construct a separate synthetic Feature 003 build whose validation partition is policy-only, patient-disjoint from every upstream/protected membership, and independently admitted before synthetic outcomes are released to selection.
3. Verify Feature 007 reconstructs the exact original Feature 004 reference digest, derives each policy signal row from its admitted prediction using the original method configuration, and applies the exact frozen Feature 005 schema/preprocessing and Feature 006 mapping. Caller-constructed signal rows are not trusted, no refitting occurs on policy evidence, and no individual score is returned.
4. Calculate patient-level empirical risk/coverage, apply the frozen protocol's candidate/equality/tie rules, and select maximum feasible coverage under the test-only empirical ceiling.
5. Freeze an immutable `SELECTED_UNEVALUATED` artifact with separated original vs policy provenance, marked policy evidence spent, non-deployable, not independently evaluated, and not clinically validated.

Expected output: one scope-level outcome/artifact or an explicit safe non-success; no patient rows, patient scores, targets, group identifiers, raw evidence, restricted manifests, or protected content.

## Required negative checks

- Reject spent Feature 005 validation and Feature 006 calibration evidence.
- Reject missing or assertion-only verification, altered prediction or ground-truth content, stale/mismatched manifest, incomplete inventory, invalid row alignment, cross-scope/version artifact, changed preprocessing/method/reference digest, and unknown patient overlap.
- Return `NOT_READY` if original Feature 004 reconstruction inputs, trusted artifact-origin evidence, independent policy cohort, or approved protocol settings are absent.
- Ensure policy evidence never changes original fitted state, estimator, schema, preprocessing, or calibration mapping.
- Treat empty TRUST risk as undefined and fail rather than report zero risk. Constant scores may only produce all-or-none selection under the same empirical ceiling and support rule.
- Inspect every ordinary result and serialization surface for patient data, row-level outcomes/scores, protected data, and verifier payloads.
- Confirm there is no public per-patient `predict`, `apply`, calibrated-score, `SafetyContext`, `SafetyAssessment`, or runtime operation.

## Current limitations

- No real policy-selection dataset, numeric protocol, trusted origin ledger, patient linkage service, or custodian integration is configured.
- Existing Features 004–006 public interfaces do not provide the new-cohort scoring path. Feature 007 must implement the documented private bridge and prove exact original reference reproduction; otherwise it returns `NOT_READY`.
- The policy-selection empirical risk ceiling is not a statistical guarantee. Policy-selection data are spent. A separate later feature must evaluate the frozen policy on independent final-test evidence.
- No clinical or deployment validity is established. Feature 008 runtime assessment remains provisional and is outside this feature.
