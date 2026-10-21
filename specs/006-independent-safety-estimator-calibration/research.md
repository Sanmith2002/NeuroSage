# Feature 006 Research and Design Decisions

**Stage**: Planning, following approval of research Decisions A–G
**Authority**: `spec.md`, `decision-record.md`, Constitution v3.0.0
**Scope**: Software choices implementing the approved calibration method; this document does not claim empirical or clinical validation.

## Decision 1 — One fixed mapping per exact source scope

**Decision**: Use one approved logistic recalibration rule determined by the selected Feature 005 estimator family. Calibrate independently by exact `(model_id, model_version, label_id)`.

**Rationale**: Feature 005 already performs candidate selection using validation. Choosing among calibrators using the only remaining development partition would reuse calibration outcomes for both fitting and selection. Family-specific parameterization avoids an unidentifiable two-parameter map for a constant score. Separate scopes preserve model/version compatibility and do not merge independently trained contributors.

**Alternatives considered**: Isotonic regression was deferred because it adds flexibility and may overfit the available calibration sample; comparing sigmoid and isotonic on the fitting data is not an independent selection design. Identity mapping is not a calibration and cannot create a successful calibrated artifact. These are excluded by Decision A.

## Decision 2 — Reconstruct the frozen Feature 005 score privately

**Decision**: Build a Feature 006-private score path that validates the allowlisted Feature 005 artifact, reconstructs its typed feature schema/preprocessing representation from the artifact's frozen fields, and reuses Feature 005's production encoding/transformation semantics to obtain `z`. Compute `z = intercept + Σ(coef_j * x_j)` in the artifact's active coefficient order using finite-value checks and a stable sigmoid only where needed. Do not call a primary classifier or expose an inference method.

The current production transforms are `build_feature_schema`, `encode_rows`, `transform_rows`, and `FrozenFeatureSchema`/`FrozenPreprocessingState` in `src/safira/training/features.py`. The artifact persists safe mappings rather than those internal Python instances and has no public deserializer to typed transform state. Feature 006 therefore needs a narrowly scoped compatibility parser for the existing allowlisted Feature 005 representation, followed by reuse of the production transformation functions. It must not copy/maintain a second transformation algorithm or use `_reproduce_probability_for_test`, which is explicitly test-only in `src/safira/training/artifacts.py`.

**Validation**: Test one-row and multiple-row parity against the original frozen scikit-learn logistic artifact in test-only fixtures, including column ordering, active indices, missing-state encoding, class order `(0, 1)`, finite dimensions, and a baseline constant. Compare numeric results using a test-declared tolerance; do not turn that test tolerance into a runtime clinical threshold.

**Alternatives considered**: Calling the primary model violates the post-hoc boundary and would not reproduce the selected correctness estimator. Importing Feature 005's test-only helper would turn a test operation into a public inference contract. Duplicating the transform logic risks semantic drift. Changing Feature 005 public contracts is unnecessary; a private Feature 006 adapter around the existing persisted schema is the smallest compatible choice.

## Decision 3 — Logistic fitting and numerical feasibility

**Decision**: Use `sklearn.linear_model.LogisticRegression` only as a numerical optimizer for the approved one-dimensional recalibration design. Set the fixed binary class order `(0, 1)`, `penalty=None`, `solver="lbfgs"`, `fit_intercept=True`, no class weights, no warm start, unit per-occurrence sample weights (or omit `sample_weight`), and protocol-declared `tol` and `max_iter`. Do not depend on scikit-learn defaults for penalty or class weighting. Record exact dependency versions already carried by the Feature 005 artifact and the runtime environment relevant to reproducibility.

scikit-learn 1.7.1 is pinned in `pyproject.toml` and is installed in the inspected environment. Its supported `lbfgs` implementation accepts `penalty=None`, which disables regularization. The API exposes convergence warnings and iteration information but does not independently certify a finite maximum-likelihood solution or diagnose all separation cases. A successful fit therefore requires explicit structural and protocol-approved feasibility checks before and after optimization.

**Rank and score degeneracy**: Since the recalibration predictor is the scalar frozen score `z`, test its finite input and nonconstant design with intercept before fitting. No arbitrary near-constant tolerance is introduced; if a protocol requires a tolerance-based adequacy rule, it must specify and approve it before outcomes are examined. An absent class is insufficient evidence.

**Separation check**: Use the exact one-dimensional threshold-separation condition before calling the optimizer. Let `[m0, M0] = [min(z0), max(z0)]` and `[m1, M1] = [min(z1), max(z1)]` for the two correctness classes. Complete or quasi-complete separation exists exactly when `M0 <= m1` or `M1 <= m0` (after both classes and a full-rank intercept-plus-score design are established). A finite-MLE design requires both strict cross-endpoint inequalities `M0 > m1` and `M1 > m0`. Equality is quasi-separation; strict inequality in the separating direction is complete separation. This does not require the closed ranges to intersect with positive width: if one class has a singleton score strictly inside the other class's range, both strict cross-endpoint inequalities hold and it is not separated. A constant score is instead caught as rank deficient before this test. Use exact comparisons on the admitted represented scores; add no threshold or tolerance to the separation condition. The protocol records this criterion/version and any separate numerical ambiguity policy. Treat a convergence warning, iteration-limit result, rank failure, nonfinite coefficient, failed protocol criterion, or non-positive fitted slope as non-success; never retry using another solver/penalty/configuration.

**Rationale**: The approved feature method is unpenalized MLE; an L2 fallback would silently change that method. scikit-learn is already an approved dependency. Because the calibrator has one scalar predictor and an intercept, the exact range-ordering test is a simple form of the linear-separation condition and avoids adding a general separation service. The overlapping-range counterexample is retained as a required synthetic test.

**Alternatives considered**: `C=np.inf`/default penalty behavior is not used; explicit `penalty=None` expresses the approved unpenalized method. Firth correction or ridge regularization would change the approved estimator and is not an automatic fallback. A general linear-programming separation package/service would be disproportionate for a one-dimensional score and add complexity or dependencies. Protocol-required edge policies remain explicit, not hidden.

## Decision 4 — Closed-form baseline offset

**Decision**: For baseline probability `p0`, compute the equal-occurrence unpenalized offset from the calibration correctness prevalence `p_cal = mean(y)`:

```text
a = logit(p_cal) - logit(p0)
q = sigmoid(logit(p0) + a) = p_cal
```

Require finite strict-interior `p0` and both target classes, making `p_cal` interior. Use stable `log`/`log1p` arithmetic; do not clip or add pseudo-counts. The result is exactly constant for every occurrence and does not add individualized discrimination. Support adequacy is based on unique patient groups and protocol criteria, not the row count used by the occurrence-weighted objective.

**Rationale**: This is the unique intercept MLE for the approved unit-weight objective and avoids an unnecessary optimizer call. It is an algebraic implementation of Decision A, not another candidate method.

**Alternatives considered**: Fitting an unidentified slope is invalid. Pseudo-counts, smoothing, patient-equal weights, or a prior would change the approved estimand/method.

## Decision 5 — Trust and complete input admission

**Decision**: The public calibration service requires an explicitly injected `CalibrationInputVerifier`; it does not accept caller-supplied verification results as proof and has no hidden global provider. The host constructs that verifier from independently controlled admission records. The service invokes it and locally recomputes exact scope, canonical fingerprints, row keys, roles, inventories, registry compatibility, and Feature 004 method/reference identity before score reconstruction.

The verifier must establish:

1. Exact Feature 001 registration for every requested model/version/label, including classifier artifact, adapter and preprocessing identities.
2. Independently executed Feature 002 admission evidence for each prediction embedded in the ordinary Feature 003 dataset, bound to its record content and association.
3. Exact Feature 003 dataset, protocol, manifest reference/digest, builder version, complete ordinary development inventory and calibration target authorization. The identity is the existing manifest-bound tuple; there is no `dataset_version` field.
4. Exact Feature 004 `SignalFeatureSet` dataset reference, complete calibration row alignment, method IDs/versions/parameters, run identity and fitted-reference identities.
5. Feature 005 selected artifact compatibility and independently authorized origin, for both an in-memory artifact and a safely loaded artifact. The host ledger must independently recognize its payload digest, exact source key and artifact version. A newly created object without such an accepted host record is `NOT_READY`; a digest or receipt supplied only by the caller cannot create that record.

The exact matched pairs are `DatasetBuildResult.development.calibration` and `SignalFeatureSet.calibration`. The entire visible dataset/manifest and its lineage are checked, but only this matched calibration partition may enter the score/fitting path. A shared trust or inventory failure aborts the public request before any per-scope result is published. After shared admission succeeds, an insufficient individual scope does not prevent results for independently eligible scopes.

**Rationale**: Feature 005's trusted input and origin verification patterns and Feature 003/004 data models provide reusable record-level concepts. Their internal service verification tokens are private implementation details, so Feature 006 uses its own narrow aggregate result while reusing public immutable record contracts. In-process interfaces cannot authenticate arbitrary malicious Python controlling the trusted host.

**Alternatives considered**: A matching digest, dataclass instance, caller Boolean, `accepted` string, or verifier result passed into `fit` is not an independent trust boundary. Global provider lookup hides authority and risks request-controlled verifier replacement. Modifying Feature 001–005 verification contracts is outside scope and unnecessary.

## Decision 6 — Immutable artifacts and no false evaluation claims

**Decision**: Store only finite mapping parameters, exact method/configuration, source and protocol references, base artifact/schema/preprocessing identity, Feature 003/004 provenance, dependency versions, and approved aggregate convergence/adequacy metadata. Use frozen records with deep defensive copying and an allowlisted JSON-compatible representation. Do not pickle estimators or include any fitted scikit-learn object.

`CALIBRATOR_FITTED_UNEVALUATED` means only that the fixed mapping was fit. Do not report default calibration-fit Brier, log loss, ECE, reliability diagrams, or independent performance. Fit-set convergence is not a performance estimate. Feature 005 validation remains spent; Feature 003 calibration is spent on fit; protected final test is inaccessible. Future evaluation and policy selection need separately authorized evidence. Export or digest does not imply persistence; no external custodian is configured.

**Alternatives considered**: Retaining sklearn objects or joblib/pickle would introduce executable deserialization and version-coupled artifacts. Adding an evaluation, inference, policy, or persistence service would exceed Feature 006 scope.

## Decision 7 — Scope of software verification

**Decision**: Test-first pytest coverage uses only synthetic records and independently controlled test ledgers. Tests establish software behavior: exact admission, same-source row alignment, formulas, numerical failure states, immutable compatibility-bound artifact, privacy, and regressions. They do not establish empirical calibration quality, transportability, clinical validity, or future safety-package readiness.

**Alternatives considered**: Real patient records, reuse of protected test values, or presenting successful software checks as clinical evidence are prohibited by the Constitution and Feature 006 lifecycle.

## Existing contract findings and dependencies

- Feature 003 `CorrectnessExample` includes the admitted prediction, target definition/version, verified binary outcome and correctness target, opaque patient group and partition role. Feature 006 consumes the correctness target; it does not recalculate it.
- `DatasetBuildResult` exposes train, validation and calibration development rows and omits protected rows. The manifest-bound identity is dataset ID, reference/digest, protocol ID/version and builder version, plus verified content inventory.
- Feature 004 `SignalFeatureSet` has a separate calibration tuple and `Feature003DatasetReference`, run manifest, exact source keys, methods and fitted-reference references.
- Feature 005 `SafetyEstimatorArtifact` has exact scope/family, frozen feature schema/preprocessing, baseline probability or logistic coefficients/intercept/classes, Feature 003 reference, Feature 004 run/method/fitted-state identities, digest and an uncalibrated/non-deployable lifecycle.
- Feature 005's `validate_artifact` checks canonical payload, exact compatibility and an injected `ArtifactOriginVerifier`; its `_reproduce_probability_for_test` is test-only. Production transforms live in `src/safira/training/features.py`.
- The repository's installed scikit-learn version is 1.7.1, matching `pyproject.toml`; planning performed no installation or code changes.

## References

- Cox, D. R. (1958). “The Regression Analysis of Binary Sequences.” *Journal of the Royal Statistical Society: Series B*, 20(2), 215–232. [doi:10.1111/j.2517-6161.1958.tb00292.x](https://doi.org/10.1111/j.2517-6161.1958.tb00292.x).
- Albert, A., & Anderson, J. A. (1984). “On the existence of maximum likelihood estimates in logistic regression models.” *Biometrika*, 71(1), 1–10. [doi:10.1093/biomet/71.1.1](https://doi.org/10.1093/biomet/71.1.1). Separation feasibility theory; not clinical validation.
- Steyerberg, E. W., et al. (2004). “Validation and updating of predictive logistic regression models: a study on sample size and shrinkage.” *Statistics in Medicine*, 23, 2567–2586. [doi:10.1002/sim.1844](https://doi.org/10.1002/sim.1844).
- Van Calster, B., et al. (2019). “Calibration: the Achilles heel of predictive analytics.” *BMC Medicine*, 17, 230. [doi:10.1186/s12916-019-1466-7](https://doi.org/10.1186/s12916-019-1466-7).
- scikit-learn developers. [LogisticRegression API, 1.7 documentation](https://scikit-learn.org/1.7/modules/generated/sklearn.linear_model.LogisticRegression.html) and [scikit-learn 1.7.1 logistic implementation](https://github.com/scikit-learn/scikit-learn/blob/1.7.1/sklearn/linear_model/_logistic.py). The versioned API/source confirm explicit `penalty=None` with `lbfgs`; convergence alone does not establish scientific validity.

These sources motivate methods and describe software behavior; none validates Feature 006 for Safira's target populations or clinical use. See the preserved [methodology review](methodology-review.md) for the broader method-selection analysis and references.
