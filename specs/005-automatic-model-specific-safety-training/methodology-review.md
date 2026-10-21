# Feature 005 Scientific Methodology Review

**Status**: Pre-clarification research recommendations; none are approved implementation decisions.
**Reviewed**: 2026-10-21
**Scope**: Candidate correctness estimators, label architecture, Feature 004 signal encoding, leakage-safe selection, and frozen estimator handoff.

This document evaluates the five open research decisions in [spec.md](spec.md) against Constitution v3.0.0 and the implemented Feature 001–004 contracts. It does not approve an algorithm, dependency, parameter, sample minimum, performance threshold, or clinical claim. The academic references below were checked against publisher, journal, author, or institutional pages during this review. A published method is not thereby validated for Safira or a clinical AI setting.

## Executive Recommendation

The smallest defensible V1 to clarify is:

1. One constant prevalence baseline and one regularized logistic correctness estimator, fitted separately for each exact `(model_id, model_version, label_id)` scope.
2. A modest, protocol-declared predictor schema using eligible numeric Feature 004 values and a limited allowlist of categorical availability outputs. Explanation applicability/provenance remains descriptive metadata and is not converted to a numeric feature.
3. Feature 003 training rows for fitting, using Feature 004's patient-grouped cross-fitted training values; Feature 003 validation rows for a small, predeclared candidate comparison only. Fit all Feature 005 preprocessing on training rows and apply it unchanged to validation rows.
4. Do not perform a second cross-validation split inside the Feature 003 training matrix in V1. Feature 004 reference values were already constructed using its own cross-fitting scheme, and a new Feature 005 split does not isolate its held-out fold from all reference states used to generate other training rows. Candidate selection against Feature 003 validation avoids this particular cross-fold interaction because Feature 004 fits its final reference on Feature 003 training only and applies it to validation.
5. Treat validation used to choose the estimator as selection data, not as independent final evaluation or later policy-selection evidence. Reserve different authorized evidence for later policy work, or explicitly accept that the study cannot make an independent policy-performance claim. Keep calibration and protected final-test partitions unavailable to Feature 005.

This V1 is feasible only after an approved scientific protocol and an implementation dependency decision. The repository's `pyproject.toml` declares no runtime dependencies, and the inspected environment has no NumPy, scikit-learn, or XGBoost installed. Safira should not implement a new optimizer or tree learner from scratch to avoid a dependency decision. The baseline can use standard Python arithmetic; a tested regularized logistic implementation would require an explicitly approved numerical/ML dependency or another already approved library.

## A. Candidate Estimators and Selection

The target is Feature 003's binary `correctness_target`: 1 means the exact registered primary classifier's mapped predicted class matches independently verified ground truth; 0 means it does not. This target is used only as `y`. Feature 005's estimator estimates correctness from Feature 004 predictors. It does not re-evaluate the primary prediction or change the correctness definition.

### Candidate comparison matrix

| Candidate | Recommendation | Input and support assumptions | Advantages for this feature | Limitations and decision notes |
|---|---|---|---|---|
| Training-prevalence / intercept-only baseline | **RECOMMENDED FOR V1** | Uses only the training-scope target prevalence; no signal fields. For a non-degenerate estimated probability, training must contain both target classes. | Establishes whether any feature estimator improves over the base correctness rate. Very low complexity, transparent, reproducible, and dependency-free. | A constant score has no useful ranking. AUROC is conventionally 0.5 with ties (depending on implementation convention); AP for correctness equals its prevalence. If a class is absent, probability endpoints make log loss infinite for opposite validation outcomes; report the metric limitation and do not silently clip. The protocol must say whether a one-class scope is ineligible or permits only a degenerate descriptive baseline. |
| Regularized logistic regression (prefer a declared L2-penalized candidate for a minimal comparison) | **RECOMMENDED FOR V1, conditional on dependency and protocol approval** | Numeric design matrix after fold-local preprocessing; both correctness classes are ordinarily required. Categorical/state values require an approved encoding. Parameter count and effective information must be considered at the exact scope. | A well-established binary probabilistic estimator; relatively small candidate/configuration space; coefficients can be inspected for gross behavior; regularization constrains extreme fit. | Small samples, rare correctness errors, correlated predictors, separation, feature selection and many degrees of freedom can produce unstable fits. Regularization does not fix insufficient independent patients or validate the feature relationship. Output is not automatically calibrated. Avoid automatic univariate screening and unrestricted hyperparameter search. Sample-size guidance rejects a universal events-per-variable rule in favor of context-specific criteria [Riley et al.; van Smeden et al.]. Firth logistic addresses separation/bias in specific settings but is a distinct estimator and implementation choice, not a default implied by this review [Firth; Heinze & Schemper]. |
| Single constrained decision tree | **CONDITIONAL / OPTIONAL** | Encoded finite inputs; protocol must specify depth/leaf constraints and the fitting implementation. | Captures simple nonlinearities and interactions, and can be inspected as a small rule structure. | High variance and split instability in small samples; a tree can isolate a few patients and appear perfect. Constraints and their rationale must be predeclared. Tree leaf fractions are not calibrated correctness probabilities. Do not use as the only candidate. |
| Random forest | **CONDITIONAL / OPTIONAL; defer from minimal V1 unless cohort and dependency justify it** | Numeric/encoded inputs; enough independent groups to support a flexible ensemble; deterministic seed and implementation/version. | Can represent nonlinear relationships and feature interactions without manual functional forms. | More effective capacity and tuning choices increase selection burden; probability-like tree vote fractions are not calibrated estimates. Feature importance can be biased or unstable. Requires an additional established library not currently declared or installed. Small-scope performance is uncertain; only compare with a predeclared small configuration and sufficient data. Breiman's paper establishes the method, not its suitability to Safira cohort sizes [Breiman]. |
| XGBoost / gradient-boosted trees | **DEFERRED / UNSUPPORTED FOR MINIMAL V1** | Encoded data and a substantially predeclared search space; implementation, CPU/runtime, seed and version control. | Flexible nonlinear estimator; XGBoost is an established scalable tree-boosting system [Chen & Guestrin]. | The feature space and hyperparameter choices can be large relative to a small per-label cohort. Adds XGBoost and its dependency surface; tree output still requires later calibration if calibration is required. Historical mention of XGBoost is not approval. Add only after an independent study justifies incremental value and a nested or reserved selection design is feasible. |

### Selection and metrics

Candidate families, any hyperparameter values, the primary metric, metric direction, candidate ordering, and deterministic tie-break must be fixed in a versioned protocol before validation outcomes are examined. Do not select the metric or search space after observing favorable validation performance. A simpler model can be the predeclared tie-break, but no arbitrary performance margin or universal pass threshold is justified here.

For a correctness probability estimate `p_i` and binary target `y_i`, relevant descriptive metrics include:

- **AUROC**: pairwise ranking discrimination between `y=1` and `y=0`; it is not a probability-calibration measure. It is undefined when an evaluation partition has only one class. A constant prevalence baseline has no ranking information.
- **Average precision / PR area**: summarizes precision-recall performance with a specified positive class. With correctness defined as positive, report the validation correctness prevalence as its reference; if estimating missed-error detection is also a research question, an error-oriented analysis must be explicitly named and protocol-approved rather than silently changing the target. PR analysis can be more informative than ROC plots under class skew, but depends on prevalence [Davis & Goadrich; Saito & Rehmsmeier].
- **Brier score**: `mean((p_i - y_i)^2)` for binary probability estimates. It is a proper score for overall probability forecasts, but combines calibration, discrimination/resolution, and outcome uncertainty; it is not a standalone calibration report [Brier; Gneiting & Raftery].
- **Log loss**: `-mean(y_i log(p_i) + (1-y_i) log(1-p_i))`; a proper score that heavily penalizes confident errors. Exact endpoint probabilities on contradictory outcomes yield infinite loss. No undocumented epsilon clipping is permitted. A protocol must state any mathematically necessary numerical handling and preserve its effect in the record [Gneiting & Raftery].

No metric alone answers whether the safety estimator is safe or clinically useful. AUROC/AP measure ranking; Brier/log loss assess probabilistic predictions as a whole. Feature 005 artifacts remain explicitly uncalibrated even when a proper score is reported. Report exact class counts or safe aggregate summaries only as allowed by the Feature 003 protocol. If a partition lacks a required class, mark the affected metric undefined/not estimable; never substitute zero or an arbitrary score. Metrics over repeated visits are not independent observations. Group patients for splitting and uncertainty analysis; if the prototype cannot estimate patient-clustered uncertainty credibly, report descriptive point estimates with that limitation rather than row-independent confidence claims.

**Recommended clarification for Decision A**: approve prevalence baseline plus one regularized logistic candidate, but only after choosing and documenting the logistic implementation/dependency, a small fixed configuration, a primary selection metric, supporting metrics, undefined-metric behavior, and tie-break before running on validation. Keep constrained tree comparison optional. Defer forests and XGBoost for V1 unless a scoped feasibility study supports the extra model capacity and dependency.

## B. Multi-Label and Contributor Architecture

### Independent per-label versus shared label-aware training

| Design | Benefits | Risks / feasibility |
|---|---|---|
| Independent estimator for each exact classifier/version/label | Directly matches Feature 001/003/004's source key and correctness target; each label has its own prevalence, available feature schema, adequacy and failure state; simplest compatibility and audit story. | Less data per estimator; some labels may be infeasible. Feature 003 adequacy already uses exact source scope and should be used without relaxing criteria. |
| Shared label-aware estimator across labels of one registered classifier/version | May share parameters and use examples where an individual label is sparse; can model label identity explicitly. | Requires a justified label representation and loss, compatible feature schemas, safeguards against a dominant label, patient grouping across labels, per-label evaluation and calibration later. A common label name does not establish shared predictor behavior. It is a materially different statistical model, not merely a storage optimization. |
| Shared estimator across independently registered contributors or versions | Potential apparent sample pooling. | **Reject** for this scope. It conflicts with exact classifier/version compatibility and can transfer correctness behavior across models. A component is not an estimator compatibility scope. |

**Recommended clarification for Decision B**: use independent estimator artifacts for every exact `(model_id, model_version, label_id)` in V1. A one-label registered classifier has one scope; a multi-label classifier has separately eligible scopes; a multi-model component keeps every contributor separate even when labels overlap. If some label lacks independent patient/class support, return its own insufficient outcome rather than borrow another label's or model's records. Shared label-aware training can be reconsidered only with a separately justified study protocol and artifact semantics.

## C. Feature Encoding and Missingness

Feature 004's implemented `SignalFeatureRecord` contains an opaque `SignalRowKey`, exact `SignalSourceKey`, and a tuple of `SignalResult` values. A `SignalResult` is immutable and includes method/version/parameters, a `SignalState`, a value for available results, safe reason code for non-value results, evidence/provenance metadata, and the original primary output. Values are heterogeneous: numeric entropy, distance, JSD or repeated-output variance; structured evidence coverage; categorical `seen`/`unseen`; and explanation applicability metadata. Feature 004's explanations are not a numerical explanation-reliability measurement. The primary output is copied for traceability, but it is not a correctness-target predictor merely because it appears in the signal result.

### Recommended candidate feature treatment

| Feature 004 material | V1 treatment to consider | Safeguard |
|---|---|---|
| Available finite numeric entropy, kNN distance, modality JSD, repeated-output variance | Admit only under a versioned per-scope feature schema with declared units/meaning and exact method lineage. Transform only if protocol justified. | Do not mix scores with different method versions, log bases, preprocessing, modalities, or fitted-reference identities. OOD distance has no universal scale or cutoff. |
| Domain familiarity `seen` / `unseen` | Treat as nominal category (one-hot or an explicitly declared binary category representation); category map must be identical to Feature 004 approved mapping. | Never expose the raw category/site name. `unseen` is not automatically “unsafe” or a probability. |
| Evidence coverage and permitted evidence availability states | Preserve as a vector of declared categorical states for only protocol-approved evidence fields. If used, distinguish unsupported, missing, unavailable and other approved states; do not make states ordinal. | Missingness may be systematic by site, workflow, subgroup, or device. It may add predictive association without causal or safety meaning. Require source-scope review and held-out subgroup checks if authorized. |
| Signal values in missing/unavailable state | Candidate may use a typed state indicator and, for numeric values, a separate missing-value representation only if declared and fitted within fold. A typical option is training-fold median imputation plus an explicit missingness indicator. | The imputed placeholder is a computational fill, not a measured zero; the indicator preserves the state distinction. Learned median/category vocabulary is training-fold-only. The research protocol must decide whether `unsupported` is a predictor or a scope-level capability (prefer scope-level schema exclusion when universally unsupported). |
| Invalid or not-ready signal result | Do not train from an invalid source or unresolved trust/compatibility prerequisite. Exclude the affected row/scope or mark it `NOT_READY` under an explicit rule. | Do not allow malformed or unverified evidence to become a learned “invalid” predictor that rewards data failures. |
| `insufficient_evidence` reference result | Treat according to the declared method contract; it is a non-value condition, not a numerical distance. For V1, prefer state handling only where the status denotes valid scope-level support and the approved schema explicitly allows it. | A single fold's reference insufficiency may make the feature schema/row incomplete; do not replace it with zero or label it as low OOD. |
| Explanation method, target, output space, calibration relation, provenance | Retain in artifact/traceability metadata only, not as a predictor. | Presence or SHAP magnitude does not prove explanation reliability. Explanation-derived numeric predictors require separate supported methodology and approval. |
| Entire dimension unsupported for a scope | Omit its value column from that scope's frozen feature schema and record the exact omission/reason; a categorical capability flag is a separate approval. | Do not create an all-zero dimension or force comparable schema across independent classifiers. |
| Constant, invalid or all-missing feature | Constant finite columns can be documented and handled by a predeclared schema rule; all-missing/invalid required fields make the scope or candidate infeasible. | No post-hoc dropping based on validation or protected-test results. No feature selection on the final test. |

**Recommended clarification for Decision C**: treat `available` numeric values as numeric; `seen`/`unseen` as nominal; encode only an allowlist of availability states as separate categorical/missing indicators; omit universally unsupported dimensions per exact scope; and reject invalid/unverified rows rather than train on invalidity. Explanation metadata stays non-predictive. If imputation, scaling, or category encoding is approved, fit its state inside the candidate's training data only and store it with the estimator. This is a candidate strategy, not an approved categorical encoding, missingness assumption, or claim that missingness is informative.

## D. Patient-Grouped Model Selection and Feature 004 Cross-Fitting

### Existing contract facts

Feature 003 returns `DatasetBuildResult.development` partitions for `train`, `validation`, and `calibration`; its protected final-test artifact is outside ordinary results. `DatasetExample` includes a binary correctness target and a controlled `patient_group_ref`. The Feature 003 trusted integration verifies outcome, independence, linkage and exact row scope; an ordinary dataclass or caller digest is not source proof. Feature 003 group assignment keeps every visit, label and contributor record for one verified person in one partition.

Feature 004's `SignalFeatureSet` separately exposes immutable `training`, `validation`, and `calibration` feature-record tuples aligned using `SignalRowKey`, plus a privacy-safe manifest and separate cohort-support metadata. A feature record itself contains predictor `SignalResult`s and exact source key, not its patient group, partition, correctness, or outcome. `build_feature_set` checks the full Feature 003 development inventory and embedded Feature 002 admission before publication. Reference-based training rows use Feature 004's deterministic patient-grouped cross-fitting; then a final reference is fitted on eligible Feature 003 training predictor evidence and applied to validation/calibration. Feature 004 does not expose a public arbitrary-subset reference-fit interface.

### Cross-fit interaction: material leakage finding

Patient-level self-exclusion in Feature 004 is necessary but does **not** guarantee independence for a new Feature 005 cross-validation split.

For each Feature 004 training row, a reference signal is calculated from other Feature 004 folds, excluding the scored patient's Feature 004 fold. Suppose Feature 005 now labels some groups as its candidate-evaluation fold. A Feature 004 training row from a different Feature 004 fold can have a kNN/domain reference whose fitted population includes that Feature 005 evaluation patient's representation. Thus evaluation-fold predictor evidence can influence the already-generated Feature 004 value used to fit the candidate, even though the evaluation patient's own Feature 004 row is not in the estimator fit and no correctness target entered the reference. This is **unlabeled cross-fold covariate influence**, not direct target leakage; it can make a CV evaluation estimate a different, transductive procedure than the eventual train-to-new-patient application.

Aligning Feature 005's split to the Feature 004 fold IDs alone is insufficient: a row in another Feature 004 fold is scored against a reference that may include the candidate evaluation fold. Preventing this would require reference features for each candidate fitting fold to be rebuilt using only that fold's permitted training groups, with another level of patient-group exclusion, then applied to its evaluation groups. Current Feature 004's public API constructs its feature set from the whole verified Feature 003 training partition and has no public scoped refit/re-extraction operation. Reimplementing the signal algorithm inside Feature 005 would violate the contract boundary. Nested/fold-aligned F004 recomputation is therefore not a V1 option without a separately approved Feature 004 contract change.

This dependency must be captured in Feature 005 clarification and planning. Testing should construct deliberately separated Feature 004 and candidate folds, perturb only candidate-evaluation representations, and verify that a proposed candidate-training feature matrix cannot be claimed independent when those upstream values changed. A clean train/validation protocol instead tests that Feature 003 validation never enters the Feature 004 training reference, and that the final reference is fit only on Feature 003 train.

### Model-selection alternatives

| Design | Advantages | Risks / contract fit | Recommendation |
|---|---|---|---|
| New patient-grouped CV inside Feature 003 train | Uses more rows for repeated development comparisons and exposes instability across splits. | The already-created Feature 004 cross-fitted reference features can depend on the candidate validation groups' representations. Candidate-level preprocessing can be fold-local but cannot repair this upstream dependency. Nested Feature 004 refitting is unavailable in its public contract. Small patient counts also make fold class support difficult. | **Do not use for the initial estimator comparison.** A future method needs a corrected feature-generation design, not just a group splitter. |
| Fit candidates on Feature 003 train; choose among a small predeclared candidate set on Feature 003 validation | Fits current partitions/contracts. Feature 004's final reference is derived from training data and applied to validation; Feature 005 preprocessing is fit on train and only applied to validation. Grouped split between train and validation already happened in Feature 003. | Validation comparisons are selection-tuned. Repeated candidate/hyperparameter exploration increases optimism. Validation metrics are not an independent final estimate after selection. Feature004 crossfit training values remain subject to their specified upstream construction, but validation data do not influence them. | **RECOMMENDED FOR V1 if selection evidence is explicitly spent/reserved.** Fix a small candidate set and tie-break beforehand; report selection metrics as selection metrics. |
| Nested or fold-aligned estimator selection with Feature 004 refitting inside every outer fold | In principle can estimate the complete pipeline's performance under each outer holdout. | Requires a trusted Feature 004 operation to make fold-specific, verified training-only reference states and cross-fitted train rows; current contract exposes no such operation. Multi-label/contributor scopes and limited groups multiply fit cost and infeasible folds. Cannot be approximated by merely reusing existing Feature 004 training rows. | **DEFERRED.** Consider only after separately approved integration changes and a feasibility study. |

For the recommended train/validation V1, keep candidate set small and parameters fixed or tightly predeclared. No alternate seeds or favorable allocation search. Missing group/class support under the approved Feature 003 partitions means `INSUFFICIENT_EVIDENCE` or `NOT_READY`, not a relaxed split. Repeated visits remain grouped. For all contributors/labels, Feature 003's global patient assignment remains authoritative; within each exact model/version/label fit, metrics should not treat visits as independent patients. An all-one-class validation set makes AUROC undefined and may also make a chosen PR metric uninformative; other scores can be reported only with class composition and uncertainty limitations.

**Recommended clarification for Decision D**: use the existing Feature 003 train/validation boundary for a small predeclared estimator comparison in V1; no new internal CV that reuses Feature 004 cross-fitted training features. Require one approved split/configuration and no seed search. If validation lacks required support or feasibility, do not train/select a deployable artifact. A future fully nested CV design requires Feature 004-compatible fold-specific feature generation and should not be improvised inside Feature 005.

## E. Frozen Estimator Artifact and Later Workflow

### Minimum research artifact content

An accepted artifact should be immutable and contain only what is needed for controlled reproduction and later compatibility checking:

- Artifact ID/version and status that clearly says `uncalibrated` and `not a deployable safety package`.
- Exact primary `model_id`, `model_version`, `label_id`, registry compatibility fingerprint, and any declared preprocessing/model identity compatibility material; a component version is not a substitute.
- Estimator family, exact implementation and dependency versions, fixed parameters, random-state configuration, fit result and convergence/unsupported reason if applicable.
- Ordered feature schema: field/method ID and version, semantic type/units, availability-state policy, missing-value handling, feature-scope inclusion/omission, and any frozen transform state.
- Feature 004 dataset/protocol/manifest reference, `SignalRunManifest` identity/digest, and exact `FittedStateReference` identities used. Do not copy raw patient rows, group IDs, protected manifest contents, full reference vectors or domain vocabularies into ordinary artifacts.
- Feature 003 dataset/protocol/manifest references, correctness target version and trusted lineage references, exact partition roles used, grouped split design, and a statement that only training plus allowed selection-validation evidence was consumed.
- Candidate set, primary/secondary metrics, handling of undefined metrics, selection rule/tie-break, aggregate class support under allowed reporting policy, reproducibility configuration, software version/commit, limitations and known nondeterminism.

Training artifacts should be versioned and immutable; if later altered feature semantics, candidate family, fit protocol, data manifest, exact primary model/version/label, preprocessor, dependency implementation or Feature 004 reference identity changes, make a new artifact version/ID and rerun compatibility checks. Compatibility must not infer that a newer primary model is “close enough.” Any persistence/serialization format and safe loading policy must be addressed in planning; never load an untrusted executable model artifact as ordinary data.

### Calibration and policy separation

Feature 005 may select a candidate against a development validation partition only if the approved protocol permits it. After the choice, those validation outcomes have been used for selection. Reporting the winner's score on those same data as an unbiased final estimate is not defensible. Reusing that partition later to select a TRUST/CAUTION/DEFER policy is also a second adaptive use. Calling the reuse “approved” does not restore independence.

Recommended evidence lifecycle:

1. Feature 005 fits candidate estimators on the Feature 003 training partition and uses a small predeclared set on a separately assigned estimator-selection partition only if available.
2. Freeze the selected estimator and all preprocessing before handing it to later stages.
3. Use distinct reserved evidence for later reliability calibration and policy selection as required by the constitution; if Feature 003's current partitions cannot provide independent evidence for both, report that limitation and require an approved protocol amendment/new cohort or an explicitly justified nested evaluation design.
4. Keep the protected final-test outcomes untouched until estimator, preprocessing, calibration and policy are all fixed. Feature 005 must not request protected rows or submit them to a custodian handoff.

The existing Feature 003 split labels include `train`, `validation`, `calibration`, and `protected_test`, while constitutional workflow reserves held-out evidence for both calibration and policy selection. The feature specifications must not leave the roles in tension. **This is a research design issue for Decision E**, not authority to repurpose calibration or protected data. Recommend reserving an additional development subset or a later independent cohort for policy selection if Feature 005 consumes the only validation set for estimator selection.

**Recommended clarification for Decision E**: define the artifact as frozen estimator plus frozen preprocessor and traceable Feature 003/004 references, but explicitly uncalibrated and not deployable. Allow Feature 005 model selection to consume only its designated training and estimator-selection data. Mark that selection data as unavailable for a later independent policy-selection claim. Require separate policy-selection evidence; if it does not exist in the present split, return a workflow limitation rather than reuse protected test or claim independent policy validity.

## Exact Dependencies on Features 003 and 004

### Feature 003: target, grouping, and partitions

- Input target is the accepted `CorrectnessExample.correctness_target`, not the binary disease ground truth itself and not a re-thresholded primary score.
- Outcome verification, exact target/model/label binding, model-development independence, source-qualified patient linkage, and partition assignment are already Feature 003 responsibilities. Feature 005 verifies the trusted exact-scope evidence boundary and does not redo those decisions.
- `DatasetBuildResult` ordinarily contains development `train`, `validation`, and `calibration` records; protected-test rows/outcomes/correctness are absent from the ordinary result and serializers. Feature 005 should consume only approved development rows and should fail closed if a request attempts to use calibration or protected test contrary to its protocol.
- The controlled `patient_group_ref` and partition role are permitted only for grouping, exact partition eligibility and split integrity. They are not predictors, preprocessor inputs, model coefficients, feature-selection variables, or estimator outputs.
- Feature 003 cohort adequacy metadata is support/provenance, not a patient predictor. Use it only for exact source-scope feasibility under approved criteria.

### Feature 004: predictor values, signal state, and reference compatibility

- Align rows using `SignalRowKey` and the independently verified Feature 003 development inventory; verify matching dataset, protocol, manifest, row fingerprint, association and exact `SignalSourceKey`.
- Consume the `SignalResult` semantics as emitted. `available` may contain numeric, categorical or structured values; non-available states have no numeric value. Preserve `method_id`, `method_version`, parameters and provenance in the feature schema and artifact.
- Do not treat `SignalResult.primary_output` (primary disease probability/score) as a safety feature by default. Any use of primary score semantics requires an explicitly approved predictor schema; correctness still comes only from the Feature 003 target.
- Keep explanation provenance and applicability metadata non-numeric in V1. Do not flatten SHAP or other attribution payloads into new features absent separate approved methods.
- Preserve Feature 004's training-row cross-fit reference features. Do not replace them with full-training in-sample scores, fit references in Feature 005, or pool incompatible source keys/reference states.
- Validation feature rows are transformed by Feature 004's final reference state trained only from Feature 003 training predictors. Calibration rows are available as a separate Feature 004 partition but excluded from Feature 005 fitting, selection and preprocessing.

## Scientific Assumptions, Limits, and Empirical Validation

- Feature 005 estimates correctness conditional on its admitted predictors and study cohort. It does not establish causal explanations of errors, model-independent “safety,” generalization to new sites, or clinical benefit.
- Each model/version/label may have a different correctness prevalence, predictor schema and data support. Performance in one exact scope does not validate another scope or later model version.
- Repeated predictions for one patient can be correlated. Patient-grouped partitions prevent group overlap but do not make repeated rows independent for uncertainty calculations.
- A small selected cohort can make even logistic regression unstable; feature count, category expansion, class counts, group count, predictor prevalence and validation support all matter. The clinical prediction-model literature argues against a universal events-per-variable rule and recommends study-specific sample-size calculations [van Smeden et al.; Riley et al.]. Safira must not import those formulas mechanically without deciding whether their assumptions match correctness-target estimation and its grouped data.
- Missingness may be systematically associated with acquisition workflow or patient/site characteristics. A missingness indicator can itself encode a proxy; it is not automatically a legitimate or transportable safety signal. Require protocol rationale, privacy approval, cohort-scope review and empirical sensitivity analysis.
- Tree-based probabilities and logistic outputs are not automatically calibrated. Feature 005 may compare them with proper scoring rules but cannot label them reliable probabilities before later calibration and external validation.
- Synthetic acceptance tests establish arithmetic, scope checks, no-leakage boundaries, deterministic configuration and serialization behavior. They cannot show that any estimator improves correctness estimation in real data.
- Empirical work should report each exact source scope, group and correctness-class support, missingness profile, features used, candidate selection process, baseline comparison, point estimates and uncertainty limits. If support is insufficient, the scientific result is “not estimable”/`INSUFFICIENT_EVIDENCE`, not a fabricated score.

## Answers and Options for Clarification Decisions A–E

These are recommendations to discuss, not approvals.

### A — Estimator family and criteria

**Recommend**: prevalence/intercept baseline plus L2-regularized logistic regression; keep one constrained shallow tree optional and defer Random Forest/XGBoost from the minimum set. Choose a primary metric and fixed tie-break before validation. Compare discrimination and probability scores only where defined; report prevalence and class support. Do not require a universal target score.

**Alternative**: include a small Random Forest candidate if an approved package is acceptable and exact-scope patient support can justify its complexity. XGBoost remains a later optional experiment. Avoid an unrestricted grid or data-driven metric selection.

### B — Label architecture

**Recommend**: independent estimator per exact model/version/label. Simpler identity, feature, readiness, target, and evaluation scopes; less data but no label pooling. A shared label-aware estimator is a separate research hypothesis and needs explicit label encoding, weighting and cross-label leakage evaluation.

### C — Features and missingness

**Recommend**: numeric values only where Feature 004 marks available and method semantics are compatible; nominal categories for declared `seen`/`unseen` and allowlisted evidence-state outputs; separate missingness indicators only when protocol-approved; omit universally unsupported dimensions; invalid/unverified/not-ready evidence blocks use. Explanation metadata is provenance only. All learned imputation/encoding/scaling is fit on each estimator-training partition and recorded.

**Alternative**: complete-case fitting for a narrow proof-of-concept. It is simpler but can discard many patients and induce selection bias; it still needs a documented eligibility rule and cannot silently drop rows after observing validation results.

### D — Candidate selection

**Recommend**: Feature 003 train for fitting, Feature 003 validation for a small predeclared candidate comparison, no nested Feature 005 CV in V1, no alternate seed search. This is the only option directly compatible with the current Feature 004 one-time feature-set API without recomputing reference signals. It yields selection metrics, not unbiased final performance estimates. Separate later policy evidence.

**Alternative**: nested/grouped CV only after an approved Feature 004-compatible fold-specific reference generation contract is added and its computational/sample feasibility is demonstrated. It is not satisfied by grouping a second splitter or by aligning fold IDs alone.

### E — Artifact and next-stage evidence

**Recommend**: immutable exact-scope estimator and preprocessor artifact with versioned feature schema, dataset/protocol/manifest references, Feature 004 fitted-state identities, candidate method/metrics/reproducibility records and safe limitations. Artifact status remains uncalibrated and not deployable. A validation set consumed to select an estimator cannot later be represented as an independent policy-selection or final evaluation set. Reserve different evidence or declare the later claim unavailable.

## Specification Corrections Needed Before Technical Planning

1. **Resolve FR-004/FR-015 split-key tension.** FR-004 currently forbids patient/group identity in “candidate selection inputs,” while FR-015 requires patient groups for all fit/evaluation splits. Replace the broad prohibition with: patient-group references may be read by the authorized splitter solely to assign groups and verify disjointness/count independent groups; they must not enter predictor matrices, preprocessing, estimator fitting, candidate scores, learned representations, public model outputs, or routine diagnostics. Partition roles may gate row eligibility but cannot be predictors.
2. **Make selection evidence lifecycle binding.** FR-018 permits Feature 003 validation for candidate selection and FR-019 currently allows its later reuse under a separately approved protocol. A protocol cannot make reused observations statistically independent. Clarify that once used to choose a candidate, those outcomes are selection data; reuse for later policy selection must be described as reuse and cannot support an independent policy estimate. Prefer reserve separate authorized policy evidence or state that policy selection is not feasible in that dataset version.
3. **Record the Feature 004 cross-fit limitation in normative wording.** Add that existing Feature 004 training records cannot be freely re-split for unbiased Feature 005 CV unless the whole signal-generation/reference process is valid for each outer fold. Do not implement inner CV by merely applying a new grouped splitter to the already-built `SignalFeatureSet`.
4. **Specify group keys as controlled metadata.** Keep the group key available through the trusted Feature 003 split boundary, but remove it from the predictor/estimator input and any ordinary artifact or diagnostic. If Feature 005 needs source-safe group hashes for reproducibility, their storage and release policy must remain custodian-controlled.
5. **Avoid ambiguity about primary output and explanation metadata.** Explicitly state that the copied primary output in `SignalResult` is traceability metadata and is not an estimator predictor unless separately approved; explanation applicability/provenance is non-numeric and non-predictive in initial scope.
6. **Clarify training success versus package readiness.** A selected estimator is an intermediate `uncalibrated` artifact only. It is not a completed constitutional safety package until independent calibration, policy selection and protected final evaluation are completed under later approved specifications.

## References

All publication metadata below was checked against publisher, journal, author, or institutional records on 2026-10-21.

1. Brier, G. W. (1950). “Verification of Forecasts Expressed in Terms of Probability.” *Monthly Weather Review*, 78(1), 1–3. [https://doi.org/10.1175/1520-0493(1950)078%3C0001:VOFEIT%3E2.0.CO;2](https://doi.org/10.1175/1520-0493(1950)078%3C0001:VOFEIT%3E2.0.CO;2).
2. Breiman, L. (2001). “Random Forests.” *Machine Learning*, 45, 5–32. [https://doi.org/10.1023/A:1010933404324](https://doi.org/10.1023/A:1010933404324).
3. Chen, T., & Guestrin, C. (2016). “XGBoost: A Scalable Tree Boosting System.” *Proceedings of the 22nd ACM SIGKDD Conference on Knowledge Discovery and Data Mining*, 785–794. [https://doi.org/10.1145/2939672.2939785](https://doi.org/10.1145/2939672.2939785). Open preprint: [https://doi.org/10.48550/arXiv.1603.02754](https://doi.org/10.48550/arXiv.1603.02754).
4. Davis, J., & Goadrich, M. (2006). “The Relationship Between Precision-Recall and ROC Curves.” *Proceedings of the 23rd International Conference on Machine Learning*, 233–240. [https://doi.org/10.1145/1143844.1143874](https://doi.org/10.1145/1143844.1143874).
5. Firth, D. (1993). “Bias Reduction of Maximum Likelihood Estimates.” *Biometrika*, 80(1), 27–38. [https://doi.org/10.1093/biomet/80.1.27](https://doi.org/10.1093/biomet/80.1.27).
6. Gneiting, T., & Raftery, A. E. (2007). “Strictly Proper Scoring Rules, Prediction, and Estimation.” *Journal of the American Statistical Association*, 102(477), 359–378. [https://doi.org/10.1198/016214506000001437](https://doi.org/10.1198/016214506000001437).
7. Heinze, G., & Schemper, M. (2002). “A Solution to the Problem of Separation in Logistic Regression.” *Statistics in Medicine*, 21(16), 2409–2419. [https://doi.org/10.1002/sim.1047](https://doi.org/10.1002/sim.1047).
8. Riley, R. D., Ensor, J., Snell, K. I. E., Harrell, F. E., Martin, G. P., Reitsma, J. B., et al. (2020). “Calculating the Sample Size Required for Developing a Clinical Prediction Model.” *BMJ*, 368, m441. [https://doi.org/10.1136/bmj.m441](https://doi.org/10.1136/bmj.m441).
9. Roberts, D. R., Bahn, V., Ciuti, S., Boyce, M. S., Elith, J., Guillera-Arroita, G., et al. (2017). “Cross-validation Strategies for Data with Temporal, Spatial, Hierarchical, or Phylogenetic Structure.” *Ecography*, 40(8), 913–929. [https://doi.org/10.1111/ecog.02881](https://doi.org/10.1111/ecog.02881).
10. Saito, T., & Rehmsmeier, M. (2015). “The Precision-Recall Plot Is More Informative than the ROC Plot When Evaluating Binary Classifiers on Imbalanced Datasets.” *PLOS ONE*, 10(3), e0118432. [https://doi.org/10.1371/journal.pone.0118432](https://doi.org/10.1371/journal.pone.0118432).
11. Steyerberg, E. W., & Harrell, F. E. Jr. (2016). “Prediction Models Need Appropriate Internal, Internal-External, and External Validation.” *Journal of Clinical Epidemiology*, 69, 245–247. [https://doi.org/10.1016/j.jclinepi.2015.04.005](https://doi.org/10.1016/j.jclinepi.2015.04.005).
12. van Smeden, M., Moons, K. G. M., de Groot, J. A. H., Collins, G. S., Altman, D. G., Eijkemans, M. J. C., & Reitsma, J. B. (2019). “Sample Size for Binary Logistic Prediction Models: Beyond Events per Variable Criteria.” *Statistical Methods in Medical Research*, 28(8), 2455–2474. [https://doi.org/10.1177/0962280218784726](https://doi.org/10.1177/0962280218784726).
13. Varma, S., & Simon, R. (2006). “Bias in Error Estimation When Using Cross-Validation for Model Selection.” *BMC Bioinformatics*, 7, 91. [https://doi.org/10.1186/1471-2105-7-91](https://doi.org/10.1186/1471-2105-7-91).

### Technical implementation guidance (not academic validation)

- scikit-learn's [GroupKFold documentation](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupKFold.html) describes non-overlapping groups and the requirement that distinct groups be at least the fold count. This is implementation guidance; Safira must use Feature 003's approved assignment rather than silently choose library defaults.
- scikit-learn's [cross-validation guide for grouped data](https://scikit-learn.org/stable/modules/cross_validation.html#cross-validation-iterators-for-grouped-data) explains why repeated records from one subject must not appear in both paired train and validation folds.
- scikit-learn's [SimpleImputer documentation](https://scikit-learn.org/stable/modules/generated/sklearn.impute.SimpleImputer.html) describes training-statistic imputation and optional missingness indicators. This illustrates a possible explicit representation, not an approved Safira missingness policy.
- scikit-learn's [logistic regression documentation](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html) documents regularized logistic candidate behavior and solver/version details. Safira's project currently declares and installs no scikit-learn dependency; adopting it requires a separate reviewed plan decision.
