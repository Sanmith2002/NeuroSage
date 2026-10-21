# Feature 008 Implementation Context

Read this handoff before exploring unrelated source. Authority order: Constitution v3.0.0, [spec.md](spec.md), approved boundary in [research.md](research.md), then [plan.md](plan.md), [data-model.md](data-model.md), and [contracts/runtime-python.md](contracts/runtime-python.md).

## Approved boundary

- V1 is internal synthetic-fixture simulation only.
- Do not accept real patient data or export a general runtime assessment API.
- Do not create or project a result through legacy `SafetyAssessment` or `SafetyContext`.
- The only emitted object is an internal immutable result tagged `SYNTHETIC_TEST_ONLY`; it omits the calibrated score and raw identifiers.
- Feature 007 policy lifecycle remains `SELECTED_UNEVALUATED`, non-deployable, not independently evaluated, and not clinically validated.
- Tests use synthetic fixture inputs and test-only verifiers. These doubles demonstrate software behavior only.

## Reuse and boundaries

- Feature 001: use `ModelRegistry.resolve_usable` and exact registered model/version/label, classifier, adapter, and preprocessing identity.
- Feature 002: accept a `PredictionRecord`; execute `verify_prediction` and local registration/evidence validation against the exact prediction association.
- Feature 003: original dataset admission is trusted-host controlled. The runtime query is not wrapped in a correctness example and no target is built.
- Feature 004: `SignalExtractor.extract_record` handles configured stateless signals. The runtime bridge must apply reference-based signals from exact reconstructed Feature 004 state without calling `build_feature_set` on the query.
- Feature 005: `SafetyEstimatorArtifact` is a frozen intermediate artifact, not a public inference API. Use only its exact schema/preprocessing/family and reconstruction path.
- Feature 006: `CalibratorArtifact` binds to exact Feature 005 digest/family/schema. Apply its frozen mapping only; never call the calibration fitter.
- Feature 007: `SelectivePolicyArtifact` is exact-scope and binds estimator/calibrator digests, policy protocol digest, cutoff comparison, and selected-but-unevaluated lifecycle. Verify origin and protocol; never access the selection cohort, correctness targets, or change the cutoff.

## Critical implementation facts

- `FittedStateReference` carries identity/digest metadata, not portable fitted vectors or domain vocabulary.
- `safira.policy.references.reconstruct_original_references` rebuilds Feature 004 reference state from original training examples and verifies its frozen digest. It is private and currently accepts a dataset and a feature-set-like manifest container.
- `safira.policy.signals.build_policy_signal_rows` is validation-dataset and `CorrectnessExample` oriented. Do not feed it a runtime prediction or fabricate correctness targets. Create a private single-record query bridge.
- `safira.policy.scoring.reconstruct_calibrated_scores` consumes private signal rows and returns individual scores. Keep score and row values inside the private call; never log or serialize them.
- Use existing `ArtifactOriginCheck`-shaped ledger results for estimator, calibrator, and policy. Recompute exact scope and digest bindings locally. Do not trust flags or caller-created check objects.
- `AdapterCapabilities` declares which evidence can be supplied; only admitted `PredictionRecord` evidence proves what was supplied for this prediction.
- Current `SafetyAssessment` is mutable and serializes its fields; `SafetyContext` can contain raw patient data. Neither belongs in the approved result path.
- Existing project contracts include domain failures, but unexpected programming exceptions must remain distinguishable and must not be broadly mapped to ordinary `DEFER`.

## Required adversarial tests

- Forged prediction, incomplete original dataset admission, policy protocol mismatch, altered origin, scope substitution, estimator/calibrator mismatch, and modified reference digest all fail before score reconstruction.
- Missing, invalid, unsupported, and optional evidence preserve the exact Feature 004/005 state behavior; required unavailable values defer without imputation or alternate schema.
- The runtime query never appears among reference training vectors/categories; signal rows cannot be caller-substituted.
- Frozen estimator and calibrator parity is checked for each supported estimator family. Cutoff boundary equality follows the exact frozen comparison.
- Multi-scope scenarios preserve independent artifacts, query associations, methods, results, and ordering.
- Inspect result, `repr`, `str`, serializer, and exception surfaces for patient/group/assessment IDs, raw targets, individual scores, explanation payloads, and verifier response text.
- Assert there is no public runtime export and no use of protected-test data, target construction, training, recalibration, policy selection, or `SafetyAssessment` projection.

## Test-first implementation order

Follow [tasks.md](tasks.md): shared immutable contract tests; admission tests before admission code; reference/signal/scoring tests before each bridge; policy boundary and privacy tests before orchestration; then synthetic end-to-end and Features 001–007 regression. Do not implement Feature 009 or production integration.
