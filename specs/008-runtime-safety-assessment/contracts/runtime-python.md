# Internal Synthetic Runtime Python Contract

This is a planned internal contract for synthetic fixtures only. It is not a public inference API and has no compatibility guarantee outside this feature. Nothing in this contract authorizes real patient data or clinical use.

## Orchestration

```python
simulate_synthetic_assessment(
    request: SyntheticRuntimeRequest,
    *,
    registry: ModelRegistry,
    verifier: RuntimeVerifier,
) -> InternalResearchAssessmentResult
```

The function is private to the runtime implementation package and MUST NOT be re-exported by `safira`, `safira.models`, or another public module. It accepts one synthetic request, executes all shared trust checks before signal derivation, then applies the frozen package for that exact source scope. It does not accept `SafetyContext`, `SafetyAssessment`, caller-created signal rows, correctness targets, or protected-test inputs.

## Trust-provider operations

The trusted host must execute and return the existing exact-bound verification records for:

- Feature 002 prediction admission (`verify_prediction`).
- Complete original Feature 003 dataset admission and embedded prediction admission (`verify_dataset` pattern).
- Original Feature 004 protocol and frozen manifest identity.
- Estimator, calibrator, and policy origin through the existing `ArtifactOriginCheck` shape, bound to each artifact digest, exact scope, and artifact version.
- Feature 007 policy protocol approval; its verified digest must equal `policy.protocol_digest`.

The local core must recompute fingerprints and compatibility relationships and reject a returned check that does not exactly match the submitted values. A Boolean, status string, digest, or caller-constructed check alone is never proof. No production trust service or origin receipt is provided by this feature.

## Result behavior

- `TRUST`: a verified synthetic query has a finite calibrated score satisfying the stored policy comparison at the stored cutoff.
- `CAUTION`: a verified synthetic query has a finite calibrated score that does not satisfy that comparison.
- `DEFER`: a safe synthetic test result for a fully admitted bundle whose required runtime measurement is missing, unavailable, unsupported, invalid, incompatible, or not ready. An optional unavailable value may proceed only through its exact frozen Feature 005 missingness behavior.
- Atomic rejection: forged, unverified, unauthorized, malformed, or cross-scope shared prediction, protocol approval, origin, inventory, or provenance; return no result or accepted partial outcome.
- Unexpected programming exceptions: remain distinguishable and MUST NOT be converted to ordinary readiness outcomes.

The calibrated score and intermediate signals exist only in private local variables and are not returned, logged, serialized, or placed in exceptions. The result MUST carry the exact lifecycle constants in [data-model.md](../data-model.md).

## Non-goals

No public `assess()` method, REST/CLI integration, primary-model invocation, target construction, fitting, calibration, policy selection, protected-test access, independent performance claim, or `SafetyAssessment` projection.
