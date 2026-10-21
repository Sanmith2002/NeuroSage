# Feature 005 Technical Research and Decisions

**Status**: Technical planning decisions, 2026-10-21. The approved research scope is [spec.md](spec.md), Decisions A–E; [methodology-review.md](methodology-review.md) is background only where those decisions approved it.

## R1 — Runtime dependency and estimator

**Decision:** Add direct runtime pin `scikit-learn==1.7.1` during implementation. The repository requires Python 3.11+ and currently declares no runtime dependencies. The inspected Python 3.11 environment has scikit-learn 1.7.1, NumPy 2.1.3, SciPy 1.16.1, joblib 1.5.1 and threadpoolctl 3.6.0. The direct pin fixes the estimator API; the artifact records all actual transitive versions, and a reproducible experiment environment should also use a constraints/lock snapshot. Installation may use `python -m pip install -e .` once the dependency is declared; no dependency is installed as part of this planning step.

**Estimator:** `LogisticRegression(penalty='l2', solver='lbfgs', C=<approved>, tol=<approved>, max_iter=<approved>, fit_intercept=True, class_weight=None, warm_start=False)`. Require `C` and `tol` finite positive and `max_iter` positive integer in a versioned protocol before validation; never substitute unapproved library defaults as scientific settings. `random_state` is not the determinism mechanism for `lbfgs`; record solver/configuration, library/BLAS environment and numeric tolerance. A convergence warning, non-finite coefficients/probabilities or failed fit is candidate failure. No automatic retry with a different parameter or seed. The logistic output is an **uncalibrated estimate of correctness**, not a clinical reliability score or final Safira calibration.

**Rationale:** A fixed, established regularized linear method meets Decision A without a custom optimizer or broad AutoML surface. No silent `class_weight='balanced'`: weighting changes the fitted probability meaning and would require separate approval. Baseline plus logistic provides a transparent minimum comparison.

**Alternatives rejected:** Custom optimizer; forests/XGBoost/deep learning; hyperparameter grid/search; changing class weights or solver after observing validation; a loose unpinned scikit-learn requirement.

**Verified primary sources:** [scikit-learn 1.7 installation requirements](https://scikit-learn.org/1.7/install.html), [1.7 release notes](https://scikit-learn.org/1.7/whats_new/v1.7.html), [1.7 LogisticRegression API](https://scikit-learn.org/1.7/modules/generated/sklearn.linear_model.LogisticRegression.html). The 1.7 line supports Python 3.11 and requires NumPy, SciPy, joblib and threadpoolctl; a transitive minimum is not an exact research environment pin.

## R2 — Prevalence baseline and comparison semantics

**Decision:** Fit constant `p = sum(y_train)/n_train` per exact scope, with `y_train` solely Feature 003 `correctness_target`. When both classes exist and the protocol's independent-group/metric feasibility holds, fit logistic and compare eligible candidates on the same authorized validation rows. Validation Brier is `n_validation^-1 * Σ(p_i-y_i)^2`; lower wins, **exact** numeric tie chooses baseline. Record the Brier definition, row weighting, class support and candidate status. `roc_auc_score` and `average_precision_score` are descriptive secondary metrics only when their binary class support and definitions are met; otherwise record `undefined` with safe reason, never a numerical placeholder. Correctness class 1 is the positive class. No universal Brier cutoff or margin.

**Successful baseline selection:** Baseline winning a valid two-class comparison is a selected constant-estimator artifact, explicitly `SELECTED_BASELINE`, uncalibrated and non-deployable. It is not described as a signal-learning logistic estimator. **Baseline-only description:** Single-class training cannot produce a successfully fitted logistic candidate; its prevalence may be reported as a safe descriptive aggregate if approved, but no successful artifact is published. Candidate fitting failure and required-candidate policy are recorded in advance; a protocol may permit selection from remaining valid candidates, but may not rewrite the policy after validation.

**Limitations:** A constant baseline has no ranking; validation with one target class makes AUROC undefined and AP may be non-informative. Brier remains mathematically computable, but the protocol may require two-class validation for a valid comparison. Multiple visits are correlated; row-mean Brier is descriptive and does not give independent-patient uncertainty. Validation was used for selection, so these scores are not unbiased final performance estimates. No confidence interval is invented.

**Alternatives rejected:** Log loss as a silently substituted primary metric; post-hoc operating thresholds; using baseline on single-class training as a successful estimator; refitting selected model on validation; a second CV over existing Feature 004 cross-fitted values. See [methodology-review.md](methodology-review.md) for the cross-fit interaction.

## R3 — Exact trusted input boundary

**Decision:** A host-owned verifier injected per service instance consults independent accepted dataset/signal/admission evidence. It returns a typed, actual-content-bound check over exact Feature 003 dataset/protocol/version/manifest/builder, Feature 004 run/method/fitted-reference scope and full role-specific row inventory. Core recomputes content fingerprints and Feature 004 row keys, validates exact Feature 001 source and output semantics, requires role-wise bijection and group disjointness, and independently checks Feature 002 admission lineage for every embedded record before producing a matrix or public cohort support. A typed check cannot validate itself. Opaque group references are restricted to eligibility/disjointness verification.

**Rationale:** `DatasetBuildResult`, `SignalFeatureSet` and check dataclasses are constructible. A matching digest can detect mismatch, but cannot prove who produced the data. This follows the existing Feature 003/004 trusted-host model without changing their contracts. No supported untrusted application entrypoint is given provider selection rights. The core cannot defend against arbitrary malicious Python code controlling the trusted host; a real evidence ledger is an external integration.

**Alternatives rejected:** Caller-supplied `verified=True`; trusting the Feature 004 object or a bare manifest digest; hidden global verifier; new service/database; re-running Feature 004 signal extraction inside Feature 005.

## R4 — Frozen predictor encoding

**Decision:** The protocol enumerates exact source-scoped signal methods/versions/value meanings and permits only finite numeric values, nominal `seen`/`unseen` domain values, and explicitly allowlisted state indicators. All seven Feature 004 states remain distinct. `invalid`, `not_ready` and unverified values reject measurement use. Non-value `unsupported`, `missing`, `unavailable`, `insufficient_evidence` are handled only where the protocol permits them. Universally unsupported dimensions are omitted with reason; no six-column template. Non-predictive metadata, primary outputs and explanation provenance are excluded.

Numeric non-values, when approved, receive a training-only median computational fill paired with a typed one-hot state indicator. Numeric scaling, when approved, uses training mean/std; zero variance uses unit scale with a recorded constant-column policy. Fixed one-hot columns encode `seen` and `unseen`; this is not ordinal or confidence. Optional all-missing columns follow predeclared omit/fail; required all-missing columns prevent success. The ordered schema and fitted medians/scales are frozen. Validation never determines omission, fill, encoding or scale. If a protocol authorizes no non-value handling, the affected row/scope fails according to its policy.

**Rationale:** A numeric fill is mathematically necessary for scikit-learn but is never mistaken for observed zero. Typed indicators preserve why a value was absent. Simple fixed encodings reduce small-cohort degrees of freedom. Constant-column and optional-feature rules are predeclared, not learned by validation selection.

**Alternatives rejected:** Zero as evidence; ordinal mapping of seen/unseen; treating invalid or not-ready as informative predictor states; automatic validation-driven feature selection; learning explanation magnitude as generic reliability.

## R5 — Feature 004 reference lifecycle

**Decision:** Use the admitted Feature 004 training rows exactly as generated by patient-group cross-fitting. Validation rows use its compatible frozen full-training reference. Do not create a new Feature 005 CV split over those training rows: training features in a proposed inner fold may contain unlabeled reference evidence from that fold's held-out patients. The Feature 003 train/validation separation is the approved selection boundary. Feature 005 does not fit or update Feature 004 references. Check exact model/version/label, method parameters/version, evidence schema, preprocessing, dataset/protocol/manifest and fitted-reference IDs.

**Limitation:** Cross-fitted train values and frozen-full-training validation values may differ in distribution; record this and validate empirically later. Neither software tests nor Brier selection establish clinical effectiveness. Calibration and protected-test evidence remain untouched; separate policy-selection evidence is not provided by this feature.

## R6 — Artifact representation, provenance and persistence

**Decision:** Freeze a versioned allowlisted payload containing exact scope and registered compatibility identity, ordered schema and fitted preprocessing, selected baseline probability or finite logistic class order/coefficient/intercept/dimension, fixed candidate configuration, software versions, Feature 003 dataset/protocol/manifest, Feature 004 run/method/reference IDs, selection evidence labels and safe limitations. Deep-freeze nested state and detach serialized values. Canonical JSON plus digest checks accidental changes; controlled load validates format, finiteness, dimensions, digest and exact compatibility **and** independently controlled artifact source authorization. The host handles durable storage and any receipt verification; no persistence claim from export alone. Ordinary `pickle`/`joblib` loading is excluded because it may execute code. A future apply path can evaluate validated frozen coefficients without rebuilding scikit-learn internals; Feature 005 does not provide runtime patient assessment.

**Alternatives rejected:** Untrusted pickle/joblib, pretending an accepted Boolean/digest proves origin or durable custody, embedding raw row observations, reusing another model's fitted state, or claiming deployability.

**Verified primary source:** [scikit-learn model persistence guidance](https://scikit-learn.org/stable/model_persistence.html).

## Mandatory protocol approvals and integration prerequisites

The code may require a versioned protocol to supply exact independent-group/correctness-class support, source-scoped feature allowlist, state and optional-feature policy, preprocessing choice, logistic `C`/`tol`/`max_iter`, required-candidate and metric feasibility policy, deterministic execution controls and aggregate-disclosure policy. These are research approvals, not planning defaults. Missing approval is `NOT_READY`; unmet approved support is `INSUFFICIENT_EVIDENCE`. A genuine independently controlled Feature 003/004/002 evidence ledger and authorized artifact custody are not configured in the repository and must not be simulated as production guarantees.
