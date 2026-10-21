# Feature 006 Methodology Review — Independent Safety Estimator Calibration

**Stage:** Research review before `$speckit-specify`
**Research status:** Recommendations only; none of the method choices below are approved yet.
**Scope:** Calibration of Feature 005 correctness estimators, per exact registered classifier/version/label scope.

## Executive recommendation

Treat the selected Feature 005 estimator as a frozen score generator for a binary target: whether that exact primary classifier prediction is correct under the Feature 003 target definition. Fit a separate, immutable calibration mapping for every `(model_id, model_version, label_id)` scope, using only its independently verified Feature 003 calibration rows and corresponding Feature 004 calibration signals.

The smallest defensible V1 candidate is one predeclared logistic-recalibration framework, with its identifiable form determined by the already selected Feature 005 artifact family:

- For a selected `l2_logistic` estimator, calculate its frozen linear predictor `z_i` using the Feature 005 ordered schema and preprocessing, and fit `q_i = sigmoid(a + b z_i)` by Bernoulli maximum likelihood on calibration correctness targets.
- For a selected constant `prevalence_baseline` estimator with probability `p0`, a free slope and intercept cannot both be identified. Fix the slope at one and fit only an offset: `q_i = sigmoid(logit(p0) + a)`. With ordinary unweighted rows, this reduces to the calibration-set correctness prevalence. It remains a constant score and adds no per-patient discrimination.

This is a fixed, artifact-family-specific method rule, not a comparison or selection among calibrators. If the protocol, provenance, class support, score variation or numerical fit is inadequate, return a non-success state and produce no calibrated artifact. Do not fall back to identity and label that result calibrated. Identity may be represented only as an explicit “calibration not performed; base artifact remains uncalibrated” result.

This method is a reasonable research-prototype starting point, not a claim that logistic recalibration is appropriate for every score distribution, cohort, or clinical use. The method, support criteria, repeated-patient weighting, optimizer and failure semantics require explicit research-owner approval before specification.

## What is being calibrated

For one exact Feature 005 scope, let `Y_i = correctness_target_i ∈ {0,1}` from independently verified Feature 003 evidence. It is not the primary disease label, primary classifier probability, diagnostic threshold, or a TRUST/CAUTION/DEFER decision.

For a Feature 005 logistic artifact, the frozen transform yields `x_i`; its stored coefficients and intercept give:

```text
z_i = b0 + Σ_j bj * x_ij
s_i = sigmoid(z_i)
```

`s_i` is an **uncalibrated Feature 005 estimate of correctness probability**. Feature 005 deliberately provides no public inference method. For a selected prevalence baseline, the artifact stores the training prevalence `p0` and `s_i = p0` for every row. Feature 005 only emits a successful baseline artifact if its approved training conditions permit that result.

The calibration target is the empirical conditional correctness frequency given the frozen score, within the declared target population and score scope. Informally, calibrated output `q` aims for `P(Y=1 | q) ≈ q` in that population. Calibration is population- and time-dependent; fitting a mapping does not guarantee this property on future or shifted data.

For a logistic base estimator, a numerically stable formulation uses its stored linear predictor rather than computing `logit(s_i)` from a rounded probability:

```text
q_i = sigmoid(a + c * z_i)
(a, c) = argmin Σ_i w_i [ log(1 + exp(a + c*z_i)) - Y_i(a + c*z_i) ]
```

The `w_i` weighting rule is not settled; see “Research approvals required.” It must not be selected after inspecting calibration results. The sigmoid implementation must be numerically stable. Coefficients, convergence evidence, method configuration and compatibility are frozen; source rows and patient/group values are not.

For a constant baseline, set `z0=logit(p0)` and fit only:

```text
q_i = sigmoid(a + z0)
a = argmin Σ_i w_i [ log(1 + exp(a + z0)) - Y_i(a + z0) ]
```

An unconstrained slope is not identifiable because all input scores are equal. The offset-only result is constant. Its unweighted maximum-likelihood estimate equals the observed calibration correctness fraction; it is not evidence that correctness varies with patient evidence. If either class is absent, a finite unpenalized intercept estimate does not exist; V1 should report insufficient evidence rather than introduce an unapproved prior or pseudo-count.

## Method-selection matrix

| Candidate | Classification | Mathematical behavior and applicability | Main assumptions and limitations |
|---|---|---|---|
| Logistic recalibration of a varying Feature 005 logistic score | **RECOMMENDED FOR V1, subject to approval** | `q=sigmoid(a+c*z)`, fit by binary log-likelihood on calibration outcomes. Uses the frozen estimator’s linear predictor, not its raw patient data. Two calibration parameters; preserves score ordering only if `c>0`. | Requires valid independently admitted binary correctness targets, both classes, adequate unique-patient support under the approved protocol, and enough score variation for an identifiable finite fit. Complete separation, near-constant scores, sparse groups, class imbalance or a negative slope may make the result unstable or scientifically concerning. A published method does not validate this Safira use. |
| Offset-only logistic recalibration of a constant prevalence baseline | **RECOMMENDED FOR V1, subject to approval** | `q=sigmoid(logit(p0)+a)`, one fitted parameter and a fixed unit slope. The fitted output remains constant across all patients. | Requires `0<p0<1` and appropriate calibration outcome support. It only updates the constant rate; it cannot add discrimination. Patient weighting changes which prevalence is estimated and must be predeclared. |
| Platt sigmoid using a separate arbitrary score or margin | **CONDITIONAL / OPTIONAL** | Standard sigmoid map `sigmoid(Af+B)`, historically applied to SVM decision values. For this feature the logistic estimator already exposes an exact linear score, making a separate score path unnecessary; using `z` is the proposed logistic-recalibration form above. | Do not mistake the SVM-specific empirical motivation for validation on Safira correctness scores. Requires independent calibration data and a fixed score definition. |
| Intercept-only correction for a varying logistic estimator | **CONDITIONAL / OPTIONAL** | `sigmoid(a+z)`, slope fixed to one; adjusts average level while preserving score differences. | Lower dimensional than fitting a slope, but may leave over/under-dispersion uncorrected. It cannot be selected against the two-parameter method on the same calibration outcomes without another authorized selection design. It could be a separately approved fixed protocol. |
| Isotonic regression | **DEFERRED FOR V1** | Nonparametric nondecreasing step function fitted to score/target pairs, often by pool-adjacent-violators minimization of squared error. It can represent more shapes and may introduce ties. | Flexible mappings can overfit sparse calibration data; the constant baseline gives no score ordering to learn. The scikit-learn documentation summarizes a large-sample heuristic, but Safira must not convert that heuristic into a universal sample minimum. Not suitable as an automatically selected alternative. |
| Identity/no adjustment | **NOT A CALIBRATION METHOD** | Leaves the Feature 005 score unchanged. It may be recorded as “not calibrated” if the research protocol explicitly elects to skip fitting. | No calibration parameters or evidence-based adjustment are produced. Must not create a calibrated artifact or calibrated-status claim. |

### Why a fixed method is preferable to calibration-method selection

Feature 005 already consumes train for fitting and validation for candidate selection; that validation is marked spent. Feature 003 calibration is the only authorized development partition left for fitting this mapping, while protected final-test data are forbidden to Feature 006. Fitting several calibrators and choosing among them on the same calibration records would use those records both to fit and select, with no independent estimate of selection performance. The minimal V1 should therefore commit to a single parameterized logistic-recalibration rule before examining calibration outcomes. Any future candidate comparison needs a separately approved calibration-method selection design and distinct evidence.

The family-specific intercept-only baseline form is a mathematical identifiability constraint, not an outcome-driven method choice. Whether that exception is acceptable is a research decision requiring approval.

## Alternatives and limitations

### Full logistic recalibration

Classical logistic recalibration regresses a binary outcome on a model’s logit prediction with an intercept and slope. Ideal calibration corresponds to intercept zero and slope one in an evaluation setting; when these are fit on the same calibration data used to estimate them, they are fitted parameters, not independent evidence of calibration quality. For a Feature 005 logistic estimator, its stored margin `z` is the numerically appropriate predictor for this transformation. An unpenalized fit may fail to have finite maximum-likelihood estimates under separation or degeneracy. No regularization, prior, clipping constant or coefficient constraint should be invented; the approved protocol must define them, or the fit fails safely.

### Isotonic regression

Isotonic regression makes fewer shape assumptions but fits a more flexible function. Small or imbalanced calibration sets can produce unstable steps and overfit. It also may change ranking by tying different scores. It is therefore deferred rather than offered as a free fallback. A future isotonic proposal would need a separate fixed method version, calibration-support plan and independent evaluation design.

### Baseline estimator

A baseline calibrator can only estimate a constant correctness rate. It cannot create individualized probabilities. The calibrator may update the constant rate from the independent calibration partition, but that estimate is based on that cohort’s verified outcomes and can be noisy or shifted. A baseline calibrator should be visibly identified as constant in all artifacts and examples.

## Calibration feasibility and non-success semantics

All criteria are protocol-specific and exact-scope; no universal patient minimum or class threshold is proposed.

| Condition | Proposed outcome | Explanation |
|---|---|---|
| Calibration protocol or trusted host verifier missing; no approved patient weighting, exact method parameters, or evidence authorization | `NOT_READY` | The required approval or provenance is not established. |
| Authorized calibration row lacks required compatible Feature 004 evidence, or required extraction state is unavailable under the frozen Feature 005 schema | `UNAVAILABLE_REQUIRED_EVIDENCE` | Do not impute a new value or refit Feature 004/Feature 005 transforms. Optional non-value states follow only Feature 005’s frozen, approved handling. |
| Feature 003/004 record, target, partition or provenance is malformed or altered | `INVALID_INPUT` or typed admission rejection | Must fail before score transformation or fitting. |
| Feature 001/005 artifact, model/version/label, preprocessing/schema, dataset/manifest, signal run or fitted reference does not match exactly | `INCOMPATIBLE_INPUT` or typed compatibility rejection | No pooling, transfer or silent migration. |
| Approved unique-patient support or correctness-class criteria are unmet; a required class is absent | `INSUFFICIENT_EVIDENCE` | Do not fit an infinite intercept or substitute an identity map. |
| Logistic base margin has insufficient distinct variation, design is rank-deficient, fitting diverges, no finite estimate exists, or the approved solver fails | `NUMERICAL_FAILURE` (or a specifically approved non-success state) | Preserve the diagnostic category without exposing rows or raw optimizer exception text. |
| Calibration succeeds under approved method | `CALIBRATOR_FITTED_UNEVALUATED` (proposed) | Means a mapping was fit on calibration evidence only. It does not mean independent calibration performance was demonstrated. |

Unique patient groups, not assessment-row counts alone, must be used for protocol support. Repeated visits within one patient group remain in the calibration partition and cannot be counted as independent people. A group with conflicting correctness targets must follow the Feature 003 target/eligibility contract; Feature 006 must not resolve or fabricate ground truth.

Repeated predictions create a separate estimand question: equal weight per prediction occurrence estimates performance across prediction events and gives more influence to patients with more observations; equal total weight per patient gives each patient comparable influence but changes the target population. The integration must not silently choose. The weighting rule and any uncertainty method must be fixed in the versioned protocol. V1 should avoid uncertainty claims that assume independent rows. No group identifier may be a predictor or ordinary artifact field.

## Evaluation and reporting

Separate three activities:

1. **Fit**: estimate the approved mapping from Feature 003 calibration scores and correctness targets only.
2. **Fit-data diagnostics**: optional descriptions of the fitting objective/convergence and calibration-set distributions, always labeled in-sample and descriptive. Calibration intercept/slope are partly the quantities fitted and cannot certify independent performance. In-sample Brier/log loss assess more than calibration alone and can look favorable because the same outcomes fit the map.
3. **Independent evaluation**: requires separately authorized, untouched evidence not used to fit the calibrator. Feature 005 validation is already spent on candidate selection, Feature 003 calibration is consumed for fitting, and the protected final-test partition is explicitly unavailable to Feature 006. No independent performance evaluation can be claimed from the current authorized Feature 003 lifecycle.

Brier score and log loss may be computed as descriptive proper scores only if an approved report policy permits, with the role and dependence structure stated; they combine calibration with other aspects of predictive performance. A reliability diagram requires prespecified smoothing/binning and counts; binned ECE depends on bin design and can be noisy or misleading for small/imbalanced data. A future independent evaluation should favor a prespecified calibration curve/intercept/slope and proper scores with uncertainty methods that respect patient grouping. No acceptance threshold is proposed here.

## Leakage and evidence lifecycle

| Feature 003/005 evidence | Use in Feature 006 |
|---|---|
| Train | Never read for calibration fit. Feature 005 fitted its estimator and transforms here. |
| Validation | Never reuse; already spent for Feature 005 model candidate selection. |
| Calibration | Sole V1 source of calibration Feature 004 signals, verified correctness targets, support checks, and calibrator fitting. Once used, it is spent for independent evaluation, method selection, threshold selection, and policy selection. |
| Protected final test | Completely inaccessible to Feature 006 APIs, summaries, diagnostics and outputs. Preserve it for an independently approved later evaluation after the full method/policy lifecycle is frozen. |
| Separate future evidence | Required for unbiased evaluation of the fitted calibrator and for later policy selection if authorized. It requires separately documented scope/provenance and patient-group independence; it is not available by repartitioning current records. |

For each exact scope, use only the already verified Feature 004 `calibration` feature rows aligned to Feature 003 `calibration` `CorrectnessExample` rows. Do not recompute signals, refit fitted reference states, re-run Feature 005 preprocessing fitting, alter the selected estimator, train the primary classifier, or derive correctness from model thresholds. Correctness targets, outcomes, patient groups, associations, partition role and verification material are eligibility/target metadata only, never calibrator predictors or exposed feature data.

## Assumptions and implementation facts

**Verified repository facts:** Feature 005 artifacts contain exact source scope, selected family, frozen schema, preprocessing, baseline probability or logistic coefficients/intercept/classes, Feature 003 manifest-bound build identity, Feature 004 method/run/fitted-state references, software versions and lifecycle markers. They are immutable JSON-compatible allowlisted values; safe loading checks exact compatibility and injected origin verification and does not use pickle/joblib. Feature 005 exposes `SafetyTrainingService.train` and eligibility-only `prepare`; it does not expose estimator inference. Feature 003 development results include train, validation and calibration rows; protected final-test records are outside ordinary results. Feature 004 `SignalFeatureSet` has a separate calibration tuple and frozen-reference provenance.

**Assumptions requiring a host integration:** An authorized calibration workflow can independently verify exact Feature 003/004 content and embedded Feature 002 admission; an authorized store/ledger can verify Feature 005 artifact origin and exact binding. The repository contains synthetic verifier fixtures, not a production evidence ledger, clinical source integration, artifact custodian or durable storage guarantee. Digests detect content changes but do not authenticate origin.

**Research recommendations are not approvals:** This review does not approve a calibration method, class/sample minimum, weighting policy, optimizer configuration, confidence interval method or clinical interpretation. Implementation feasibility is not empirical effectiveness.

## Research approvals required before specification

1. **V1 method rule:** Approve, revise or reject the fixed family-specific logistic-recalibration rule: full intercept/slope on the selected logistic margin and intercept-only offset for a constant baseline. Confirm there will be no calibrator comparison on the same calibration set and no identity-map success artifact.
2. **Patient/row estimand:** Specify the calibration unit and repeated-patient weighting (prediction-occurrence weighting, equal total patient weighting, or another justified rule); determine whether grouped uncertainty is reported or deferred. Patient IDs remain restricted metadata.
3. **Method feasibility:** Approve protocol-specific criteria for unique patient groups, both correctness classes, logistic score variation/identifiability, class imbalance handling, and behavior with conflicting/repeated outcomes. No universal minima.
4. **Numerical method:** Decide the exact fitting implementation and version, optimization/termination settings, separation handling, allowed slope sign, any regularization, and whether a failed/non-finite fit maps to a distinct numerical-failure status. No clipping, prior or fallback should be implicit.
5. **Feature/API boundary:** Confirm Feature 006 produces a frozen calibrator artifact plus only explicitly authorized calibration-set diagnostics, with no runtime calibrated-score or patient-inference API until a separately specified assessment feature. Decide whether fit-set Brier/log loss or reliability diagrams are included at all.
6. **Artifact trust and persistence:** Confirm how a Feature 005 artifact is admitted when it is newly created in-memory versus later reloaded, which existing verifier contracts may be composed without changing Features 001–005, and whether a custodian receipt is required for any persistence claim. No such guarantee exists in the current repository.
7. **Later evidence:** Confirm that current Feature 003 calibration is spent after fitting and that Feature 005 validation and protected final test remain inaccessible. Identify that future independent evaluation and policy-selection evidence require a separately approved data lifecycle.

## References

1. Cox, D. R. (1958). “The Regression Analysis of Binary Sequences.” *Journal of the Royal Statistical Society: Series B (Methodological)*, 20(2), 215–232. DOI: [10.1111/j.2517-6161.1958.tb00292.x](https://doi.org/10.1111/j.2517-6161.1958.tb00292.x). Basis for logistic likelihood and intercept/slope calibration formulation; not a clinical calibration validation study.
2. Steyerberg, E. W., Borsboom, G. J. J. M., van Houwelingen, H. C., Eijkemans, M. J. C., & Habbema, J. D. F. (2004). “Validation and updating of predictive logistic regression models: a study on sample size and shrinkage.” *Statistics in Medicine*, 23, 2567–2586. DOI: [10.1002/sim.1844](https://doi.org/10.1002/sim.1844). Supports caution about sample size and updating; it does not establish universal Feature 006 support cutoffs.
3. Van Calster, B., McLernon, D. J., van Smeden, M., Wynants, L., & Steyerberg, E. W. (2019). “Calibration: the Achilles heel of predictive analytics.” *BMC Medicine*, 17, 230. DOI: [10.1186/s12916-019-1466-7](https://doi.org/10.1186/s12916-019-1466-7). Clinical prediction methodology review on calibration definition, assessment, overfitting and sample size; not evidence that Safira outputs are clinically valid.
4. Platt, J. (1999). “Probabilistic Outputs for Support Vector Machines and Comparisons to Regularized Likelihood Methods.” In *Advances in Large Margin Classifiers*, 61–74. MIT Press. No DOI located for this book chapter. It motivates sigmoid mapping for SVM margins; its original task is not Safira correctness estimation.
5. Niculescu-Mizil, A., & Caruana, R. (2005). “Predicting Good Probabilities with Supervised Learning.” *Proceedings of the 22nd International Conference on Machine Learning*, 625–632. DOI: [10.1145/1102351.1102430](https://doi.org/10.1145/1102351.1102430). Empirically compares sigmoid and isotonic calibration and their data demands across benchmark classifiers; transfer to Safira remains untested.
6. Zadrozny, B., & Elkan, C. (2002). “Transforming Classifier Scores into Accurate Multiclass Probability Estimates.” *Proceedings of the Eighth ACM SIGKDD International Conference on Knowledge Discovery and Data Mining*, 694–699. DOI: [10.1145/775047.775151](https://doi.org/10.1145/775047.775151). Isotonic probability mapping reference; multiclass extensions are outside Feature 006's binary correctness target per exact label.
7. Dimitriadis, T., Gneiting, T., & Jordan, A. I. (2021). “Stable reliability diagrams for probabilistic classifiers.” *Proceedings of the National Academy of Sciences*, 118(8), e2016191118. DOI: [10.1073/pnas.2016191118](https://doi.org/10.1073/pnas.2016191118). Discusses stable reliability diagrams and uncertainty; applicability to clustered clinical calibration data needs study.
8. Scikit-learn developers. “Probability calibration,” scikit-learn 1.7 documentation. [Official user guide](https://scikit-learn.org/1.7/modules/calibration.html) (the path resolves to the 1.7.2 patch documentation, while Safira pins 1.7.1). Documents sigmoid and isotonic calibration, overfitting limitations, independent calibration data and the `FrozenEstimator` pattern. This is implementation guidance, not scientific approval.
9. Scikit-learn developers. “LogisticRegression,” scikit-learn 1.7 documentation. [Official API reference](https://scikit-learn.org/1.7/modules/generated/sklearn.linear_model.LogisticRegression.html). Documents `lbfgs` support for `penalty=None`; exact dependency and solver compatibility must still be checked against the pinned 1.7.1 environment during planning/implementation.

