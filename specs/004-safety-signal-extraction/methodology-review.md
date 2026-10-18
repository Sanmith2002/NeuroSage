# Feature 004 Supplemental Methodology Review

**Purpose:** Pre-clarification scientific method-selection review for Safety Signal Extraction and Feature Engineering.  
**Status:** Research recommendations only; no algorithm, threshold, sample minimum, or clarification decision is approved by this document.  
**Scope:** Literature-grounded candidates for the six constitutional dimensions, evaluated against current Feature 001–003 contracts and Safira FYP feasibility.

## Executive assessment

Safira can define all six dimensions now, but current contracts do not support six universally available patient-level numeric features. A defensible small V1 should emit a result for every dimension while permitting `unsupported`, `missing`, `unavailable`, `invalid`, `insufficient evidence`, or `not ready` states. The result vocabulary already appears in the Feature 004 specification; its final mapping remains a clarification decision.

The most feasible V1 candidates are: a protocol-scoped evidence coverage profile for data sufficiency (with cohort adequacy kept outside predictors); binary predictive entropy only for registered probability outputs; a nearest-neighbour representation distance only when compatible representations and an approved independent reference exist; descriptive domain-category familiarity against a declared Feature 003 training cohort; and pairwise Jensen–Shannon disagreement only for comparable modality-specific probabilities. No per-patient explanation-reliability number is recommended for V1: current contracts can carry explanations but do not guarantee perturbation-linked explanations, an explanation method, or a model-execution interface for testing them. Explanation audits can be reported separately at the method/model level.

All fitted reference methods should use permitted predictor evidence from the Feature 003 **training** partition, not the primary classifier's original training population. Validation and calibration partitions may be transformed by frozen state under the approved protocol; they must not fit it. Protected-test information must remain outside ordinary Feature 004 APIs and serialized outputs. For training rows, an in-sample reference score can be optimistically biased, especially for nearest neighbours; use patient-grouped cross-fitting or exclude the scored patient's entire group from its reference. If the available cohort cannot support this, report the signal as insufficient rather than weakening grouping.

## Contract and evidence baseline

- **Feature 001** binds each signal to the exact `(model_id, model_version, label_id)`, registered score semantics, binary class mapping, preprocessing and compatible adapter. It supports standalone binary, multi-label and independent contributors. Separate contributors with overlapping labels remain separate; component membership does not make model outputs comparable.
- **Feature 002** supplies admitted `PredictionRecord` values, exact primary-output semantics, provenance and explicit optional-evidence states. Live collection may call `feature_representation`, `repeated_outputs`, `modality_outputs`, `domain_metadata`, `explanation`, `input_metadata`, and `available_modalities` only when declared and implemented. Precomputed records expose only what the source contract and trusted integration actually admitted. None of these categories is guaranteed for every model.
- **Feature 003** joins a prediction to verified independent binary outcome and derives the correctness target from the registered predicted class. Its ordinary result exposes training, validation and calibration records; protected final-test material is handled separately by a custodian integration. Patient-group references, outcomes, correctness targets, partition assignments, verification records, and protected-test details are controlled/supervisory data, never predictor values.
- Feature 003's training reference is the independent safety-supervision cohort. It is not equivalent to, and must not be silently replaced by, the primary classifier's original development/training data. Existing verifiers may report primary-model lineage and independence status, but real integrations are not configured in the repository. Their trustworthiness is an operational prerequisite, not something a method can infer from a passing synthetic test.
- Existing `SafetyContext` evidence fields are mutable convenience projections with simple Boolean availability. Five-state Feature 002 evidence remains authoritative. Feature 004 should consume validated records/dataset values and produce its own detached, traceable results without changing `SafetyContext` or `SafetyAssessment`.

The labels below describe **method suitability for a candidate V1**, not an approved implementation mandate. “Recommended for V1” is still conditional on an authorized clarification and the stated evidence prerequisites.

---

## 1. Data sufficiency

### Operational meaning and unit

Keep three questions separate:

1. **Evidence completeness/quality (record-level):** did this exact prediction have the method-required evidence, with acceptable Feature 002 state, source assurance, interpretation, timing, and preprocessing provenance? This is not a patient diagnosis or evidence that the prediction is correct.
2. **Cohort sample adequacy (cohort-level):** does the protocol-scoped independent Feature 003 training population provide the required number of unique patient groups and correctness-class support for the named method and exact model/version/label? It is not a patient feature.
3. **Prediction-time data sufficiency (patient-level):** does the current patient input contain enough information for a particular calculation? This is only supportable for explicitly declared input-quality or modality-completeness evidence; the current contracts do not define a universal clinical notion of “enough data.”

### Candidate methods

| Method and status | Definition/output | Evidence and fit behavior | Limitations and safeguards |
|---|---|---|---|
| **Protocol-scoped evidence coverage profile — RECOMMENDED FOR V1** | Return a structured per-record profile of required/optional evidence categories and their existing states, plus whether the declared calculation prerequisites are met. This is a vector of named states/coverage, not a fabricated scalar. | Stateless relative to a frozen, versioned method definition and protocol. Uses Feature 002 `EvidenceItem` state, source/interpretation/timing metadata and, where explicitly defined, input-quality or modality metadata. | The protocol must define which evidence a method requires. A present value is not necessarily high quality; quality can only be asserted through validated declarations. Do not compress the profile into a patient risk feature without a separate approved definition. |
| **Exact-scope cohort support report — RECOMMENDED FOR V1** | For each `(model_id, model_version, label_id)`, report eligible unique patient-group count and correct/incorrect target support, with readiness interpreted only against the approved protocol's criteria. Keep counts and outcome-derived values in controlled cohort metadata, not predictor rows. | Derived from Feature 003's verified training partition and exact scope. Stateless aggregation; no fitting. Patient group is the independent counting unit, not prediction rows or visits. | No universal minimum. Small counts and imbalance make estimates unstable; passing a protocol criterion does not prove validity. Never aggregate unrelated contributors by label name. Validation/calibration/test counts cannot be used to make training adequacy appear sufficient. |
| **Wilson score interval for cohort correctness proportion — CONDITIONAL / OPTIONAL** | For `x` correct out of `n` independent eligible patient groups, display a Wilson interval for the cohort proportion (Wilson, 1927), as descriptive uncertainty on a cohort report only. | Outcome-dependent, aggregate-only calculation over a fixed, exact-scope Feature 003 partition. No fitted predictor state. | It assumes a meaningful binomial unit and independent Bernoulli observations. Repeated visits/labels from one patient violate a naïve row-level `n`; with clustering or protocol strata, a different justified analysis is needed. It does not define adequacy or a pass/fail threshold. |
| **Universal per-patient “data sufficiency score” — DEFERRED / UNSUPPORTED** | No generic method can map heterogeneous missing modalities, evidence states and clinical input completeness to a universal numeric sufficiency score. | Current inputs may include `input_metadata`, `available_modalities`, and declared evidence states, but meanings vary by adapter and source contract. | A numeric score would require an approved operational definition and validated quality semantics. Do not encode missingness as zero, infer clinical eligibility, or mistake cohort size for per-patient information quality. |

**Recommended V1 interpretation:** expose (a) the existing five-state evidence coverage profile per record and (b) exact-scope cohort support/readiness metadata separately. Whether either belongs in the future predictor vector is unresolved; the defensible default for V1 is that cohort counts and correctness-class support do **not** become per-patient predictor features.

**Tests:** synthetic exact-scope counts with repeated visits must count unique groups; same label across two models/versions must not pool; changing outcomes must change only controlled support summaries, not predictor values; unsupported evidence remains a state and cannot turn into numeric zero; missing provenance/timing required by protocol makes support unavailable or not ready.

---

## 2. Distribution conformity / OOD

### Operational meaning and unit

Describe how a current record's representation differs from a named, compatible reference population in one specified feature space. This is representation atypicality relative to that reference, not disease abnormality, error probability, or clinical safety. It can be record-level after fitting a cohort reference; a population-level test answers a different question and should not be relabelled as a per-patient OOD score.

### Candidate methods

| Method and status | Definition/output | Evidence and fit behavior | Limitations and safeguards |
|---|---|---|---|
| **k-nearest-neighbour reference distance — RECOMMENDED FOR V1, conditional on representations** | Given current vector `z` and Feature 003 training reference vectors `Z`, report a declared neighbour distance such as the `k`th-nearest distance `d_k(z,Z)` (or the explicitly defined mean of the first `k` distances). It is a distance, not an OOD probability. | Requires finite fixed-dimensional `feature_representation` for query and reference, same exact model/version/label scope, preprocessing and evidence schema. Fit stores only approved Feature 003 **training** predictor representations. `k`, metric and transformations must be protocol/method-version parameters, not silently chosen from evaluation results. | Nonparametric; avoids a Gaussian feature-distribution assumption (Sun et al., 2022). Still depends on representation geometry, scale, dimension, cohort coverage and distance metric. High-dimensional distance concentration, duplicate records, small `n`, and retrieval cost can weaken meaning. It does not create a validated rejection threshold. Use grouped cross-fitting or whole-group self-exclusion when scoring training rows to avoid zero/self-neighbour optimism. |
| **Class-conditional Mahalanobis distance — CONDITIONAL / OPTIONAL** | For class `c`, with fitted mean `μ_c` and covariance `Σ` (often tied), compute `d_c(z)=sqrt((z−μ_c)^T Σ^{-1}(z−μ_c))`; a predeclared minimum/combination across classes is a confidence-like feature, not a probability. | Needs representations, valid class-conditional grouping and enough training observations to estimate stable covariance. Lee et al. (2018) demonstrated a deep-network feature method. | Gaussian/elliptical structure and covariance stability matter; singular covariance and small class counts require a justified regularization strategy. Their method is feature-layer/architecture-aware and includes input perturbation machinery that generic Safira adapters do not promise. Avoid an unapproved covariance fix or class-selection rule. Grouped out-of-fold scores are needed for training rows. |
| **MMD two-sample test — CONDITIONAL / OPTIONAL (cohort-level shift comparison)** | Maximum Mean Discrepancy compares two sample distributions in a kernel feature space, e.g. squared biased empirical form `|| (1/n)Σφ(x_i) − (1/m)Σφ(y_j) ||²`; a permutation procedure can assess a null of equal distributions. | Requires two sets of comparable representations, declared kernel/bandwidth and a valid exchangeability/permutation unit. It is cohort-level, not a score for one patient. | Test power and calibration depend on sample size, kernel, dependence and multiple testing. Patient groups, not rows, must be resampled. Selecting kernel or bandwidth on the same evaluation comparison can invalidate inference. Do not expose protected-test distribution summaries through ordinary APIs. Gretton et al. (2012). |
| **Generic Mahalanobis for arbitrary adapter outputs — DEFERRED / UNSUPPORTED** | Not a universal V1 default. | Contract permits representations, but does not promise a calibrated, Euclidean, class-conditional or Gaussian feature space. | A blanket Gaussian assumption is not justified for arbitrary supervised architectures. Prefer kNN as the research default where evidence supports either; retain Mahalanobis as a scoped comparator. |

**Reference population:** use the independent Feature 003 training partition to represent the population against which the future safety feature is learned. Do not assume the primary classifier's original training data are available, independent, or compatible. If the intended question is specifically “familiarity to the primary model's training population,” that needs separately verified source evidence and a different declared scope; current Feature 003 does not silently supply it.

**Tests:** changed validation/calibration/protected rows cannot affect fitted reference; exact dimension/preprocessing/version mismatch rejected; repeated patient records stay in one cross-fitting fold; training query is absent from its own reference; nonfinite/constant/wrong-dimension representation yields invalid/insufficient state; distance remains a raw distance with no arbitrary threshold.

---

## 3. Prediction uncertainty

### Operational meaning and unit

Distinguish (a) ambiguity in one declared predictive distribution, (b) variation across repeated outputs under a declared stochastic mechanism, and (c) calibration/correctness. They are not interchangeable. Any output is a property of a specific model/version/label and output space; none is Safira reliability or correctness likelihood unless independently calibrated and validated for that meaning.

### Candidate methods

| Method and status | Definition/output | Evidence and fit behavior | Limitations and safeguards |
|---|---|---|---|
| **Bernoulli predictive entropy — RECOMMENDED FOR V1 for probability labels only** | For registered probability `p`, `H(p)=−p log p−(1−p)log(1−p)`. With natural logs it is in `[0, ln 2]`; it is maximal at `p=0.5`. Preserve the log base and probability source. | Stateless; requires a finite, registered binary probability in `[0,1]` from Feature 001/002. Applies to standalone binary and each multi-label output independently. | It measures entropy of the reported Bernoulli output, not empirical error. Poorly calibrated probabilities remain poor probability semantics; calibration evidence must be preserved. No entropy from a non-probability score, mapped class alone, or arbitrary score normalization. Calibration assessment/calibration fitting is outside Feature 004 (Guo et al., 2017 informs why confidence and calibration are distinct). |
| **Repeated-output variance / entropy of a predictive mixture — CONDITIONAL / OPTIONAL** | If repeated values are compatible probabilities `p₁…p_R`, descriptive mean `p̄` and variance `R⁻¹Σ(p_r−p̄)²` may be reported; where a defined stochastic predictive mechanism applies, entropy of `p̄` and mean entropy of draws can be distinguished. | Requires multiple outputs for the same input, model/version, label, preprocessing and association, plus verified repeat provenance and declared stochastic source (e.g. MC-dropout sampling as in Gal & Ghahramani, 2016). | Merely receiving repeats does not identify epistemic vs aleatoric uncertainty. Results depend on number of draws and stochastic mechanism; the adapter contract does not promise repeats or Bayesian semantics. No arbitrary minimum `R`; if protocol needs a minimum it must justify it. A component's different classifiers are not repeated outputs of one classifier. |
| **Deep ensemble disagreement — CONDITIONAL / OPTIONAL** | For independently trained instances of the same defined predictor, compare probability spread or predictive distributions under a declared aggregation; ensemble members are model instances, not arbitrary component contributors. | Requires verified member relation, same label/target, comparable probability semantics and data/input scope. Can be reported statelessly from already supplied member outputs. | Safira's multi-model component contract deliberately keeps independently registered contributors distinct. Do not infer an ensemble, average contributors or call their disagreement within-model uncertainty. Training ensemble models is out of Feature 004 scope (Lakshminarayanan et al., 2017). |
| **Entropy or variance from non-probability scores — DEFERRED / UNSUPPORTED** | No calculation until an approved transformation with a justified scale exists. | Feature 001 preserves `score` semantics and mapping; it does not assert probabilistic interpretation. | A monotone score transformation can change entropy/variance arbitrarily. Do not apply a sigmoid or normalize undocumented scores. |

**Self-influence:** entropy itself is stateless and no cross-fitting is needed. Any learned scale transform or repeated-output reference must use training-only fit and patient-grouped cross-fitting for training rows. Do not compute/select entropy thresholds from protected-test outcomes.

**Tests:** boundary probabilities yield defined entropy; calibrated and uncalibrated labels retain their calibration metadata; scores do not enter entropy; repeated outputs with another seed/config/version reject or become unavailable; repeat count and stochastic setting are retained; separate component contributors never become ensemble members by default.

---

## 4. Modality agreement

### Operational meaning and unit

Measure descriptive consistency between at least two modality-specific outputs for the **same exact contributor, label, target, assessment occurrence and prediction-time scope**. Agreement is not correctness; disagreement does not identify which modality should be trusted. Comparing separate classifiers in a multi-model component is explicitly not modality agreement.

### Candidate methods

| Method and status | Definition/output | Evidence and fit behavior | Limitations and safeguards |
|---|---|---|---|
| **Pairwise Jensen–Shannon divergence of Bernoulli modality probabilities — RECOMMENDED FOR V1, conditional on comparable outputs** | Convert each modality probability `p_i` into Bernoulli distribution `P_i=(p_i,1−p_i)`. For a pair, `JSD(P_i,P_j)=H((P_i+P_j)/2)−[H(P_i)+H(P_j)]/2`; report pairwise values or a declared aggregate, with log base and modality set. In base 2 it is bounded by 1 bit. | Stateless; needs at least two valid modality-specific probability outputs with identical label/target, scale/calibration meaning, timing and case association from Feature 002 `modality_outputs`. Lin (1991) establishes entropy-based divergence; this is a descriptive application, not a new clinical method. | Different modality probabilities may still have different calibration or target semantics; if so, unavailable. Aggregating three or more modalities requires an explicit deterministic aggregation rule. Does not require reference fitting, but interpretation is cohort/model-specific. No missing modality is agreement. |
| **Pairwise absolute probability difference — CONDITIONAL / OPTIONAL** | `|p_i−p_j|` for a declared pair of comparable binary modality probabilities; bounded `[0,1]`. Preserve pairwise outputs or specify a transparent mean/max summary. | Stateless and simpler to interpret; same evidence constraints as above. | Less distribution-sensitive than JSD but still assumes identical calibrated semantics. Avoid selecting the pair/aggregation after observing outcomes. |
| **Agreement on mapped hard class — CONDITIONAL / OPTIONAL** | Indicator or proportion of equal registered mapped classes across comparable modality outputs. | Requires each modality output to have a defined compatible class mapping and same exact target/occurrence. | Loses continuous disagreement magnitude and can conceal near-boundary differences. Does not allow Safira to invent thresholds for modality-specific outputs; use only source-declared mappings. |
| **Cross-model contributor agreement or probability averaging — DEFERRED / UNSUPPORTED** | Not modality agreement and not part of V1. | Multi-model components preserve independent model provenance. | Classifier outputs can have different training data, calibration, labels or target meaning. Fusion/consensus requires its own approved feature and evaluation protocol. |

**Small sample:** no cohort fitting is required. A single observed record with two modalities supports a descriptive pair result, not a population statement about modality reliability. Any cohort summary must use patient grouping and report scope; do not treat repeated visits as independent.

**Tests:** matching synthetic modality probabilities produce known JSD; missing one modality returns a missing/unavailable state; scale/calibration/target mismatch rejects; same label from two models is not compared; missing modality never maps to zero disagreement.

---

## 5. Domain familiarity / cohort shift

### Operational meaning and unit

Separate **record-level domain-category familiarity** (“is this permitted, declared category represented in the approved reference?”) from **population-level distribution shift** (“do two cohorts differ statistically in a selected representation?”). Neither means clinical eligibility, harm, fairness, or OOD. Do not equate site, cohort, time, or domain labels unless their source contract explicitly says they mean the same thing.

### Candidate methods

| Method and status | Definition/output | Evidence and fit behavior | Limitations and safeguards |
|---|---|---|---|
| **Declared-category reference coverage — RECOMMENDED FOR V1 when domain metadata exists** | Against a named training-reference vocabulary, report category state `seen`, `unseen`, `missing`, or `invalid`, plus controlled support count only where permitted. For privacy, an outward predictor value may need a coarsened state rather than a site/category identifier. | Reference-fitted vocabulary/support table from permitted Feature 003 training predictor metadata only; apply to a new record without update. Exact model/version/label and cohort/time scope retained. Requires source-qualified, non-identifying domain category with documented meaning. | A category observed in a small sample is not statistically familiar; “seen” is not distributional equivalence. Rare site labels can identify a patient or reveal restricted cohort structure. Support counts should stay in controlled metadata and must not leak outcomes. Grouped self-exclusion/cross-fitting for training rows avoids a row establishing its own category support. |
| **MMD two-sample comparison — CONDITIONAL / OPTIONAL, cohort-level only** | Compare a named reference set and current cohort in a compatible representation using MMD; report statistic and, only under a predeclared valid permutation protocol, a p-value. | Same primary requirements as OOD MMD: compatible features, two cohorts, kernel configuration, patient-group permutation unit, adequate study design. | It detects a distribution difference in the selected representation, not necessarily clinically relevant shift; failure to reject is not proof of equality. Small cohorts have low power; high-dimensional kernel and multiple-comparison choices matter. Cohort-level output must not be misrepresented as one patient's familiarity. |
| **Domain-classifier discrimination — CONDITIONAL / OPTIONAL research comparator** | Train a classifier to distinguish reference vs target-domain records; predictive discrimination can indicate separability under a declared cross-validation design. | Needs two well-defined cohorts, source domain labels and patient-grouped internal validation. Fitted from development data only. | Adds another learned model and validation choices; confounding by label prevalence, site/time sampling and duplicate patients can dominate. Not recommended for minimal FYP V1. |
| **Domain familiarity inferred from model confidence, label prevalence, or patient identity — DEFERRED / UNSUPPORTED** | No defensible generic transformation. | Such evidence is not a domain-membership measure. | Would conflate prediction semantics with cohort scope or introduce prohibited identity leakage. |

**Reference population:** use a declared Feature 003 training cohort's allowed domain metadata, not the primary model's presumed training population. If domain metadata describe only source export rather than patient population, record that limitation. Site isolation or time scope is protocol provenance, not automatically a predictor.

**Tests:** categories mapped only through declared aliases; unseen/missing differs from invalid; changing patient group reference cannot alter domain feature; reference vocabulary unchanged by held-out records; logs and ordinary serialization contain no raw site/person identifiers; MMD never emits a per-patient result.

---

## 6. Explanation reliability

### Operational meaning and unit

“Explanation reliability” is broader than stability. Candidate properties include sensitivity to small input changes, fidelity to the model's output behavior under a specified perturbation distribution, and dependence on learned model parameters/data. These properties answer different questions and should never be collapsed into a generic reliability score. An explanation's target output may be an uncalibrated model score even when a delivered probability is calibrated; Feature 002 provenance must retain the exact explanation target and output space.

### Candidate methods

| Method and status | Definition/output | Evidence and fit behavior | Limitations and safeguards |
|---|---|---|---|
| **No universal per-record numeric reliability value; explicit state/metadata — RECOMMENDED FOR V1** | Preserve whether explanation exists and its method, target, output space, calibration relationship and provenance; return unsupported/not-ready for a reliability measurement unless a supported test is explicitly configured. | Stateless record characterization from Feature 002 explanation evidence. No model fitting. Existing `explain()` returns explanation content but does not promise perturbation explanations or score access. | Presence, visual plausibility, magnitude, or a source claim does not establish faithfulness. This keeps the constitutional dimension visible without inventing a metric. |
| **Perturbation sensitivity and infidelity — CONDITIONAL / OPTIONAL research method** | Yeh et al. (2019) define explanation sensitivity and infidelity using a declared perturbation distribution. Sensitivity summarizes explanation change under nearby inputs; infidelity compares explanation-attributed change with the model output change for a perturbation. | Requires the exact loaded model/version, repeatable explainer invocation, target score access, valid domain-preserving perturbations, declared output space and a pre-specified perturbation distribution. Requires model access/adapter capability not present in the current public contract. | Scores depend on perturbation distribution and metric; low sensitivity can describe a vacuous constant explanation, while fidelity is local to chosen perturbations. Clinical input perturbations can be invalid or unrealistic. No generic numeric acceptance cutoff. For Feature003 training feature rows, perturbation design must be fixed without using outcomes or protected tests. |
| **Model/data randomization sanity checks — CONDITIONAL / OPTIONAL method-level audit** | Adebayo et al. (2018) compare explanations under parameter randomization and label randomization to test whether a saliency method responds to learned model/data. Treat as a method/model audit report, not a patient-level feature. | Requires access to model state and ability to rerun the explanation procedure on randomized controls; best run during research characterization before choosing an explainer. | Passing these checks is not proof of local faithfulness, causal validity or clinical usefulness; failing them can disqualify a method for a claimed purpose. It cannot generally be calculated from a stored precomputed explanation alone. |
| **Stability from stored explanation/repeats without controlled perturbations — DEFERRED / UNSUPPORTED** | No stability value from mere repeated artifacts unless their input perturbations, explainer settings, target and association are all known and comparable. | Feature 002 may carry repeated outputs and explanations, but does not guarantee controlled repeated explanation evidence. | Repeated explanations can differ because of randomness, version, preprocessing or input changes. Comparing them without those controls is uninterpretable. |

**Feasibility:** the current FYP can implement provenance/state handling and synthetic tests for explanation semantics, but cannot claim empirical explanation reliability for arbitrary live or precomputed classifiers. A future scoped study could select one supported explanation family and one justified perturbation protocol. If a precomputed component provides SHAP for an uncalibrated score and a calibrated probability, preserve those as distinct output spaces; do not assess one as if it explained the other.

**Tests:** absent method/target/output space is not ready; calibrated-vs-uncalibrated target mismatch remains explicit; mutations do not alter explanation evidence; perturbation metrics require declared distribution and model-version binding; synthetic tests verify formulas and invariants, while no software test is described as scientific validation.

---

## Coherent minimal V1 proposal

This is a candidate for `$speckit-clarify`, not an approved decision.

| Dimension | Minimal V1 behavior | Patient-level numeric predictor? | Reference/fitting boundary |
|---|---|---:|---|
| Data sufficiency | Per-record evidence-state coverage profile; separate exact-scope cohort support/readiness report. | No cohort adequacy statistic by default. A declared completeness profile could be used only after protocol approval. | Coverage is stateless; cohort counts derive from verified Feature003 train examples and unique groups. |
| Distribution conformity/OOD | kNN distance in a compatible, fixed representation where available; otherwise explicit unavailable/unsupported. | Yes, conditional raw distance. | Feature003 training predictor representations only; patient-grouped cross-fitting/self-exclusion for training rows. |
| Prediction uncertainty | Binary entropy for a registered probability; preserve repeated-output variation only where stochastic provenance is adequate. | Yes, entropy; repeated statistic optional. | Entropy stateless; repeated-output reference only if later method needs it. |
| Modality agreement | Pairwise JSD of modality probabilities with matching declared semantics; otherwise unavailable. | Yes, if at least two comparable modality outputs. | Stateless; no cross-model comparison. |
| Domain familiarity/cohort shift | Seen/unseen/missing category against a declared training-reference vocabulary; cohort-level MMD remains optional research analysis. | Category state only if privacy and feature semantics are approved. | Vocabulary/support fitted from training-only domain metadata; grouped cross-fitting for training rows. |
| Explanation reliability | Preserve explanation provenance and explicit non-value state; run method/model-level randomization audit only if access permits. | No numeric per-record output in V1. | Stateless metadata; audit uses controlled model access, not protected-test observations. |

This set gives each dimension a defined role, supports all three classifier configurations when evidence exists, and does not imply that all six must yield a number. It is model-agnostic at the contracts and applicability boundary, but kNN and explanation audits necessarily depend on the evidence/model capabilities declared by a particular integration.

## Cross-cutting research safeguards and test design

1. **Identity and scope:** every result and every fitted state is keyed by exact model/version/label, method version, preprocessing and evidence schema. An independent component contributor is not a substitute reference for another contributor.
2. **Partitions:** fit only on Feature 003 training predictor evidence. Validation/calibration can be transformed only by frozen state under protocol. Never use correctness targets, outcomes, patient-group keys, assignment roles as values, protected-test rows or protected outcomes as predictors or fit inputs.
3. **Training-row self-influence:** for any reference-based training features, grouped K-fold cross-fitting or whole-group leave-out is needed so a patient's own visits/labels do not create an artificially close reference or category support. Fold design must be deterministic and patient-grouped. If the cohort is too small for the chosen split, report insufficient evidence; do not split patients or seek a favorable seed.
4. **Small samples and class imbalance:** report exact independent support and method assumptions; keep method-specific adequacy criteria in a versioned protocol. Do not invent global sample minima or use a passing software fixture as evidence of statistical adequacy.
5. **Missingness:** a missing, unsupported, invalid or unavailable signal is not numeric zero. Optional signal failure must not erase a valid independent signal. The eventual estimator can consume missingness only through an explicitly approved encoding and held-out evaluation; Feature 004 itself should preserve typed states.
6. **Synthetic acceptance tests:** include exact mathematical fixtures for entropy/JSD/distance; independent-contributor and overlapping-label keys; all optional-evidence states; deterministic repeated runs; invalid shapes/nonfinite values; self-influence/cross-fitting; exact model/version/preprocessing rejection; partition leakage mutation tests; and privacy inspection of results/errors/serialization. Also include a positive case for each classifier configuration and live/precomputed provenance mode. Synthetic tests verify code paths and arithmetic, not empirical effectiveness.
7. **Empirical validation later:** compare kNN and Mahalanobis on an appropriately independent cohort only if representations support the question; assess uncertainty against independent correctness outcomes without using those outcomes to fit signal values; validate modality comparability and missingness; quantify category/support stability; and evaluate explanation measures against a declared perturbation protocol. Keep a final evaluation partition protected until methods are fixed. Report uncertainty, subgroup scope and limitations, not clinical safety claims.
8. **Complexity:** the proposed V1 can use standard-library arithmetic and NumPy/scikit-learn only if already present and approved by the plan. MMD permutation inference, general Mahalanobis regularization, domain classifiers, explanation perturbation engines and multiple testing are optional research extensions, not prerequisites for the FYP minimum.

## Unresolved research questions for `$speckit-clarify`

These questions remain open; the recommendations above do not answer them on behalf of the project:

1. **Data sufficiency:** which outputs are controlled cohort metadata only, which may be patient-level predictor features, and what precisely constitutes acceptable record-level evidence quality under an approved protocol?
2. **OOD reference:** should V1 adopt raw kNN distance when a compatible representation exists, and which metric/representation normalization/reference population are supportable for the actual adapters? Is Mahalanobis retained only as a scoped comparator?
3. **Uncertainty:** should V1 include only predictive entropy, or also repeated-output dispersion? Which registered probability semantics and stochastic provenance are enough for any decomposition claim?
4. **Modality agreement:** approve pairwise JSD, absolute difference, or a source-defined method; specify aggregation for more than two modalities and how calibration comparability is established.
5. **Domain familiarity:** approve a seen/unseen reference category as a signal; decide whether any category values/counts can be exposed to later model training without privacy or site-leakage concerns. Keep MMD as cohort-level analysis unless a specific study justifies it.
6. **Explanation reliability:** should the V1 dimension remain explicitly unavailable except for provenance, or should a narrowly scoped perturbation metric be selected? Which models can be rerun, what perturbations preserve valid input semantics, and which output space is the target?
7. **Fitted features and cross-fitting:** choose patient-grouped fold/self-exclusion behavior for training rows and define how limited cohorts yield insufficient evidence. Feature 003's approved protocol and actual available training examples must be sufficient; no protected-test shortcut is available through ordinary APIs.
8. **Availability/readiness state mapping:** settle how `unsupported`, `missing`, `unavailable`, `invalid`, `insufficient evidence`, and `not ready` map to persisted Feature004 results without changing Feature002's evidence states.

## References

Primary publisher/proceedings records are linked for verification. The short descriptions above are paraphrases of the cited works; the references do not by themselves validate an application to Safira's cohorts.

1. Gretton, A., Borgwardt, K. M., Rasch, M. J., Schölkopf, B., & Smola, A. (2012). **A Kernel Two-Sample Test.** *Journal of Machine Learning Research*, 13(25), 723–773. [JMLR article](https://www.jmlr.org/papers/v13/gretton12a.html).
2. Sun, Y., Ming, Y., Zhu, X., & Li, Y. (2022). **Out-of-Distribution Detection with Deep Nearest Neighbors.** *Proceedings of the 39th International Conference on Machine Learning*, PMLR 162, 20827–20840. [PMLR article](https://proceedings.mlr.press/v162/sun22d.html).
3. Lee, K., Lee, K., Lee, H., & Shin, J. (2018). **A Simple Unified Framework for Detecting Out-of-Distribution Samples and Adversarial Attacks.** *Advances in Neural Information Processing Systems 31*, 7167–7177. [NeurIPS paper](https://proceedings.neurips.cc/paper_files/paper/2018/hash/abdeb6f575ac5c6676b747bca8d09cc2-Abstract.html).
4. Shannon, C. E. (1948). **A Mathematical Theory of Communication.** *Bell System Technical Journal*, 27(3), 379–423; 27(4), 623–656. [DOI 10.1002/j.1538-7305.1948.tb01338.x](https://doi.org/10.1002/j.1538-7305.1948.tb01338.x) and [DOI 10.1002/j.1538-7305.1948.tb00917.x](https://doi.org/10.1002/j.1538-7305.1948.tb00917.x).
5. Guo, C., Pleiss, G., Sun, Y., & Weinberger, K. Q. (2017). **On Calibration of Modern Neural Networks.** *Proceedings of the 34th International Conference on Machine Learning*, PMLR 70, 1321–1330. [PMLR article](https://proceedings.mlr.press/v70/guo17a.html).
6. Gal, Y., & Ghahramani, Z. (2016). **Dropout as a Bayesian Approximation: Representing Model Uncertainty in Deep Learning.** *Proceedings of the 33rd International Conference on Machine Learning*, PMLR 48, 1050–1059. [PMLR article](https://proceedings.mlr.press/v48/gal16.html).
7. Lin, J. (1991). **Divergence Measures Based on the Shannon Entropy.** *IEEE Transactions on Information Theory*, 37(1), 145–151. [IEEE Xplore record](https://ieeexplore.ieee.org/document/61115), DOI [10.1109/18.61115](https://doi.org/10.1109/18.61115).
8. Wilson, E. B. (1927). **Probable Inference, the Law of Succession, and Statistical Inference.** *Journal of the American Statistical Association*, 22(158), 209–212. DOI [10.1080/01621459.1927.10502953](https://doi.org/10.1080/01621459.1927.10502953).
9. Yeh, C.-K., Hsieh, C.-Y., Suggala, A. S., Inouye, D. I., & Ravikumar, P. (2019). **On the (In)fidelity and Sensitivity of Explanations.** *Advances in Neural Information Processing Systems 32*. [NeurIPS paper](https://proceedings.neurips.cc/paper/2019/hash/a7471fdc77b3435276507cc8f2dc2569-Abstract.html).
10. Adebayo, J., Gilmer, J., Muelly, M., Goodfellow, I., Hardt, M., & Kim, B. (2018). **Sanity Checks for Saliency Maps.** *Advances in Neural Information Processing Systems 31*, 9505–9515. [NeurIPS paper](https://proceedings.neurips.cc/paper/2018/hash/294a8ed24b1ad22ec2e7efea049b8737-Abstract.html).

## Review boundary

This document supplements the Feature 004 specification for research discussion. It does not amend Constitution v3.0.0, approve the open specification decisions, revise Feature 001–003 contracts, establish thresholds or sample minima, authorize a protected-test pathway, or claim that the proposed methods are valid for clinical use. Technical planning should begin only after the project resolves material method and evidence questions through its approved clarification workflow.
