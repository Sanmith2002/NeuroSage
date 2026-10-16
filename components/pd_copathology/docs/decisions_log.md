# Research decisions log

One entry per decision, newest first. Copy the template for each new entry.

## Template

```
Date:
Decision:
Evidence:
Alternatives considered:
Reason:
Impact:
```

## Entries

Scientific decisions are frozen in `docs/phase1_final_decisions_v1.md`. The
entries below record how Phase 2 implements them, including every
interpretation that had to be made where the frozen documents were silent.
Interpretations are marked **[interpretation]** and need confirmation.

### Phase 2.1 corrections and Phase 3 harness (11 October 2026)

These entries supersede the following Phase 2 entries further down: the `htn_bp` one-reading rule, the
vascular masking rule, the removal of eplerenone / methyldopa / aliskiren, the AD-like formula
`max(ptau, 8) / min(abeta, 1700)` and the three-tier definition.

```
Date: 2026-10-11
Decision: RE-FREEZE of the split (once). `python -m copath.phase2 --refreeze`, seed unchanged (20261011),
  rebuilds the development/test split and the five folds and refits the Lumipulse mixture on the new
  development set. From the first Phase 3 run onwards `--refreeze` refuses to run (it checks
  experiments/registry.csv).
Evidence: Phase 2 review. The 2.1 corrections change ad_like_v1 and vascular_v1, which are stratification inputs.
Alternatives considered: Keeping the old split (rejected: it was stratified on labels that are now different).
Reason: No model had been trained, so nothing had seen the old test set. Re-freezing is allowed now and never again.
Impact: data/splits/, configs/frozen/lumipulse_gmm_v1.json, every Phase 2 report; phase2.registry_has_runs.
```

```
Date: 2026-10-11
Decision: AD-like limit handling follows targets/ad_like_v1.yaml v1.1. The curated cut discards Elecsys
  values outside the assay range and keeps only flags, so: abeta_used = min(max(abeta, 200), 1475.4) when
  numeric, 1475.4 when abeta_ULOD = 1, 200 when abeta_LLOD = 1, else missing; ptau_used = max(ptau, 8) when
  numeric, 8 when ptau_LLOD = 1, else missing; ratio = ptau_used / abeta_used. The same rules apply to every
  Elecsys sensitivity variant. Limits and flag names are read from the card.
Evidence: Curated data dictionary (derivation notes of abeta and ptau); Phase 2 masked high-ABeta42 participants.
Alternatives considered: Leaving flagged participants masked (rejected: removes clearly amyloid-negative
  participants, a selection bias).
Reason: As frozen in the v1.1 card. The substituted values are BOUNDARY SUBSTITUTIONS for censored assay
  measurements, not the participants' true values. `ad_like_v1_censored` (participant level, never a feature)
  marks them; the sensitivity label `ad_like_v1_uncensored` masks them.
Impact: targets.builders.ad_like_parameters / ad_like_values / ad_like; cohort.add_labels; cohort_flow.md.
```

```
Date: 2026-10-11
Decision: [interpretation] (a) The card is version v1.1 but still defines the label `ad_like_v1`: a label id is
  the target id plus the MAJOR card version. (b) A numeric value <= 0 is not a measurement and is masked rather
  than raised to the floor. (c) `ad_like_v1_censored` is also 1 for a numeric value at or beyond a limit
  (which the curated cut should never contain); such values are counted separately in the report.
Evidence: The card's invalid_values line; the card says "came from a flag" for the indicator.
Alternatives considered: Renaming the label to v1.1 everywhere; raising 0 to 200.
Reason: Keeps every label id, feature-set file and report stable; never invents a measurement.
Impact: targets.builders.card_label, ad_like_values.
```

```
Date: 2026-10-11
Decision: Vascular masking: a participant is masked only when HTN is not evaluable AND the unknown HTN
  component could change the result. vascular_v1 (>= 2): masked if DM + DYSLIP = 1, negative if 0, positive
  if 2. vascular_v2 (>= 1): masked if DM + DYSLIP = 0, positive otherwise.
Evidence: Phase 2 review.
Alternatives considered: The earlier rule (masked whenever below the threshold and HTN unknown).
Reason: With DM + DYSLIP = 0, hypertension alone cannot reach two components, so the label is known.
Impact: targets.builders.vascular; targets/vascular_v1.yaml and vascular_v2.yaml (rule text).
```

```
Date: 2026-10-11
Decision: htn_bp = 0 whenever blood pressure was measured (either supine reading, BL or SC fallback) and is
  below the thresholds; it is missing only when no reading exists. Eplerenone, methyldopa and aliskiren are
  definite antihypertensives; diltiazem and verapamil stay as calcium-channel blockers.
Evidence: Phase 2 review.
Alternatives considered: The earlier one-reading rule; the narrower drug list.
Reason: A measured normal pressure is evidence of absence for this proxy; the three drugs have no other use.
Impact: medications.vascular_components; configs/drug_classes.yaml.
```

```
Date: 2026-10-11
Decision: CSFSAA, asyn and saa_status_bl are near-proxies for pd_type_v1. Only two tiers exist: primary
  (everything except defining and never) and strict (primary minus near-proxies). The full tier is dropped.
Evidence: About 88% of PD and 7% of HC are SAA-positive.
Alternatives considered: Keeping SAA as an ordinary feature; keeping a third tier equal to primary.
Reason: Decisions document section 9.
Impact: configs/leakage_matrix.csv; leakage_guard.TIERS; configs/feature_sets/ (12 files); docs/leakage_matrix.md.
```

```
Date: 2026-10-11
Decision: [interpretation] saa_status_bl is a text column. It is a near-proxy in the matrix as decided, but the
  numeric models cannot use text, so the harness leaves non-numeric tier features out and records them in each
  run (nonnumeric_tier_features_not_used). The curated numeric CSFSAA carries the same information.
Evidence: The analytic table stores the status as Positive / Negative / Inconclusive / Conflicting.
Alternatives considered: Encoding the text as categories (adds a hand-made encoding of a label-defining field).
Reason: Lean and transparent; nothing is silently used or silently dropped.
Impact: phase3.core.tier_features.
```

```
Date: 2026-10-11
Decision: Phase 3 selection follows docs/selection_protocol.md (written before any real run): per-label
  gates, score = mean outer-fold Brier Skill Score, 1-SE tie set, then tie-breakers (calibration slope,
  SHAP top-10 stability, primary-to-strict drop, simplicity).
Evidence: Decisions document sections 5.6 and 9; the Phase 3 specification.
Alternatives considered: The older section 5.6 wording (macro BSS ranking; worst-label tie-breaker).
Reason: Selection is per label (binary relevance), so the section 9 workflow is followed; macro BSS is reported.
Impact: evaluation/selection.py; configs/phase3.yaml (selection).
```

```
Date: 2026-10-11
Decision: [interpretation] Details the specification left open, all written into the protocol before any run:
  (1) tie-breaker tolerances: slope distance 0.05, Jaccard 0.05, strict-tier drop 0.01 BSS; without a
      tolerance tie-breaker (a) would always decide alone;
  (2) if no candidate passes every gate, the label is PROVISIONAL: the tie set is formed from the candidates
      with the fewest failed gates and no failed fold, and the reviewer must accept or reject it explicitly;
  (3) the missingness-only check (AUROC > 0.70) flags the LABEL in every report; it is not a per-candidate gate;
  (4) robustness seeds change the model's random state and the calibration / threshold splits; the outer
      folds stay the frozen ones, so the reused per-fold hyperparameters never saw their test fold;
  (5) baselines and the missingness model are neither tuned nor calibrated;
  (6) the Brier Skill Score reference is the training-fold prevalence (the B0a prediction);
  (7) sensitivity labels reuse the model family and per-fold hyperparameters of their primary label;
  (8) "clinical + demographics" = cognition, motor, non-motor clinical and demographics features;
  (9) a feature that no eligible participant has is not used; a run with fewer than 50 eligible participants
      or fewer than 10 of one class is skipped and reported.
Evidence: None in the frozen documents.
Alternatives considered: Listed in docs/selection_protocol.md where relevant.
Reason: Each had to be fixed before results exist. To be confirmed before the first real run.
Impact: docs/selection_protocol.md; configs/phase3.yaml; phase3/commands.py.
```

```
Date: 2026-10-11
Decision: SHAP explains the uncalibrated model, and the output space is verified per estimator instead of
  assumed: the harness checks whether the values add up to the model's margin (log-odds) or to its
  probability and records the result. A random forest is explained in probability, not log-odds.
Evidence: Decisions document section 5.7 says "log-odds"; TreeExplainer on a scikit-learn random forest
  attributes the predicted probability.
Alternatives considered: Converting forest output to log-odds (not additive).
Reason: Never claim a space the explainer does not produce. Sigmoid calibration is monotonic, so rankings hold.
Impact: explain/shap_explainer.py; shap_stability_tieset.csv and shap_summary.md state the space.
```

```
Date: 2026-10-11
Decision: The final test evaluation is locked. `final` needs --final AND configs/frozen/final_approval.yaml
  (approved: true, reviewer, date, selected_models_sha256) written by the student after reviewing
  reports/phase3. It runs once; a lock file blocks a second run unless forced with a logged reason.
Evidence: Decisions document sections 5.5 and 9.
Alternatives considered: An environment variable alone (too easy to leave switched on).
Reason: The test set is used once, after selection, on a human decision.
Impact: phase3/final.py; configs/frozen/final_evaluation_lock.json.
```

### Phase 2.2 and Phase 3 final patch (11 October 2026)

```
Date: 2026-10-11
Decision: Phase 2 traceability of the Lumipulse threshold. configs/frozen/lumipulse_gmm_v1.json is no longer
  tracked in Git (it is derived from real participant data and stays local; ignored as lumipulse_gmm_v*.json).
  The SHA-256 of the file is recorded in phase2_manifest.json (lumipulse_gmm_sha256). A normal Phase 2 run
  requires the file to exist and to match that hash and never regenerates it; a missing file, a missing
  manifest hash (a manifest written before this check) or a mismatch stops the run with the instruction to
  use --refreeze. --refreeze refits, saves and records the new hash. The very first freeze (no split exists
  yet) creates the file.
Evidence: Review of the clean-up commit: the manifest never recorded the file's hash.
Alternatives considered: Keeping the file tracked; silently refitting a missing file.
Reason: The threshold decides the Lumipulse label; a changed or regenerated file must never go unnoticed.
Impact: phase2._lumipulse, phase2.verify_frozen_gmm, phase2_manifest.json. The manifest of the existing real
  run has no hash, so the next Phase 2 run must be `--refreeze` (the planned re-freeze).
```

```
Date: 2026-10-11
Decision: Five candidates: lr_l2 (standard L2 logistic regression, tunes C and class weighting, 15 trials),
  lr_enet (the former `lr`; elastic net, 15 trials), rf, xgb, hgb. Same fold-safe median imputation and
  standardisation pipeline and the same validation framework. Prevalence and age + sex logistic regression stay
  baselines. Simplicity order for the last tie-breaker: lr_l2 > lr_enet > hgb > rf > xgb.
Evidence: Phase 3 final patch request.
Alternatives considered: Replacing lr_enet with lr_l2.
Reason: A plain L2 model is the simplest defensible comparator; elastic net adds sparsity.
Impact: models/candidates.py; configs/phase3.yaml; docs/selection_protocol.md. The model name `lr` was renamed
  `lr_enet` before any real run, so no registry entry is affected.
```

```
Date: 2026-10-11
Decision: abeta_LLOD, abeta_ULOD, ptau_LLOD, tau_LLOD and ad_like_v1_censored are `never` for every label.
  They may still build the AD-like label internally but never enter a feature set.
Evidence: Assay limit flags describe the measurement of the label-defining analytes and behave like
  availability indicators.
Alternatives considered: Leaving them as ordinary features for the PD-type and vascular labels.
Reason: They carry information about which participants had a CSF measurement and about the label itself.
Impact: configs/leakage_matrix.csv; regenerated configs/feature_sets/ and docs/leakage_matrix.md.
```

```
Date: 2026-10-11
Decision: A PROVISIONAL selection (no candidate passed every gate) keeps `final --final` locked unless
  configs/frozen/final_approval.yaml also contains `acknowledge_provisional: [<label ids>]` listing every
  provisional label. selection_final.md explains for each provisional label which gates each candidate failed,
  with the values.
Evidence: Synthetic runs: a near-perfectly separable label fails the calibration-slope gate.
Alternatives considered: Treating the approval hash as sufficient.
Reason: Approving the file must not silently accept a model that failed its gates.
Impact: phase3/final.check_unlocked; phase3/commands.cmd_select_final; selected_models_v1.yaml (provisional_labels).
```

```
Date: 2026-10-11
Decision: The following interpretations of the previous report are ACCEPTED: per-label selection with macro
  BSS also reported; the missingness check flags the label but does not gate; the SHAP output space is
  recorded per estimator (verified, not assumed); the PROVISIONAL fallback; tie-breaker tolerances 0.05
  (calibration slope), 0.05 (SHAP Jaccard) and 0.01 (strict-tier drop in BSS); the threshold is chosen on the
  calibration folds; sensitivity labels reuse the hyperparameters of their parent label.
Evidence: Review of the Phase 3 report.
Alternatives considered: See the entry "Details the specification left open" below.
Reason: Accepted by the student before the first real run.
Impact: docs/selection_protocol.md is the reference; no code change.
```

### Phase 3 bug fix: degenerate columns and failed trials (11 October 2026)

```
Date: 2026-10-11
Decision: Every candidate pipeline starts with DropDegenerateColumns (models/preprocessing.py), fitted on the
  training rows of whatever it is fitted on (inner tuning folds, calibration members, outer folds, robustness,
  extras, explain, final). It removes the columns with fewer than 2 distinct non-missing values (all missing or
  constant) and keeps exactly those columns at transform time. The dropped column names (names only) are recorded
  per outer fold in the run details and summarised in reports/phase3/dropped_features.csv. SHAP values are mapped
  back to the original feature names; a dropped column has SHAP value 0 for that fold. Not applied to the
  baselines: b0a uses no features, b0b selects age and sex by name, and the missingness-only check looks at which
  values exist, so a column that is constant among its non-missing values but sometimes missing must stay in it.
Evidence: The first real `cv` run: HistGradientBoostingClassifier raised "window shape cannot be larger than
  input array shape" in every trial of ad_like_v1 because a training fold had a column without two distinct values.
Alternatives considered: Dropping columns once on the whole development set (rejected: not fold-safe); handling
  only HGB (rejected: every model must see the same rule).
Reason: The decision must be made on training rows only and be identical for all models.
Impact: models/candidates.py, models/preprocessing.py, explain/shap_explainer.py, training/train.py,
  phase3/commands.py. configs/phase3.yaml gets pipeline_version: 2, which changes the configuration hash, so runs
  made with the earlier pipelines are never reused.
```

```
Date: 2026-10-11
Decision: Tuning counts failed Optuna trials per exception type and skips them; if every trial fails it raises
  TuningError, the outer fold fails, and a run in which every fold failed is registered with status `failed` and
  no metrics or out-of-fold file. The log names label, tier and model; `cv` continues with the next run, retries
  failed runs when started again, and the command line exits with code 4 when any run failed.
  `python -m copath.phase3 reset-cv --confirm` removes only the cv outputs (registry rows of stage cv, the cv run
  details, data/processed/oof/, the cv report files and cv curve figures). It refuses when a final run or the lock
  file exists, and when results derived from cv exist (robustness or extras runs, a selection, SHAP files).
Evidence: Same real run; the failure was recorded per fold but not explained.
Alternatives considered: Failing the whole command at the first failed run.
Reason: One broken model must not hide the results of the others, and nothing may be written for a run that
  produced no predictions.
Impact: training/tuning.py, phase3/core.py, phase3/reset.py, phase3/__main__.py.
```

### Phase 3 addition: PD-type missingness audit (11 October 2026)

```
Date: 2026-10-11
Decision: `python -m copath.phase3 missingness-audit` (pd_type_v1 only) writes reports/phase3/pd_missingness_audit.csv
  (% of PD and of HC development participants with each primary-tier feature available, absolute difference in
  percentage points, largest first) and runs one extra nested-CV run on the strict tier with the selected PD-type
  model family and its per-fold hyperparameters, restricted in each outer fold to the features whose availability
  differs by less than 10 points between PD and HC in that fold's training rows (pd_low_missingness_run.csv, with the
  primary-tier cv and the strict-tier robustness run as references). The run is an `extras` run in the registry.
Evidence: PD versus HC is separated almost perfectly; which measurements exist may carry part of that signal.
Alternatives considered: Choosing the features once on the whole development set (rejected: not fold-safe).
Reason: Shows how much of the PD-type result survives when only features that are about equally available in both
  groups are used. Exploratory; it does not change the selection.
Impact: phase3/missingness.py, training/train.py (optional per-fold column rule), phase3/core.run (optional `select`).
```

### Phase 3 development review (14 October 2026)

```
Date: 2026-10-14
Decision: Phase 3 development review completed; development-stage selection approved for held-out evaluation
  (rf / lr_enet / rf). Interpretation caveats were recorded in phase3_development_review.md before accessing
  the held-out test set.
Evidence: docs/phase3_development_review.md (written before the final test; selection file
  configs/frozen/selected_models_v1.yaml, SHA-256 recorded in that document).
Alternatives considered: None; the frozen protocol decided the selection.
Reason: Interpretation limits (PD-type near the ceiling, fold-wise calibration slopes, moderate AD-like stability,
  SHAP versus ablation) must be on record before the test result can influence the wording.
Impact: Documentation only. No code, configuration, label, feature set or frozen selection changed.
```

### Phase 4A.0 frozen-bundle packaging (15 October 2026)

```
Date: 2026-10-15
Decision: `package-final-bundle` adds bundle_manifest.json (SHA-256 of every bundle file, canonical raw feature-list hash,
  the hashes already in config.json, library versions, lock hash) and explainer_specs.json (the Phase 3 SHAP convention per
  signal) in models/final/<version>/packaging/. It is additive and idempotent, and never changes a model, threshold,
  bundle file or the lock. Training library versions are taken from the selected cv run records because the final run
  did not store versions; they are labelled as such, not as observed final-fit versions. An exact scikit-learn match
  and loading the frozen artifacts with InconsistentVersionWarning as an error are mandatory.
Evidence: Source review of phase3/final.py (no versions, explainer state or feature-list hash in the bundle) and of
  explain/shap_explainer.py (RF: TreeExplainer without data, probability of class 1; elastic net: LinearExplainer on
  the scaled training background, log-odds).
Alternatives considered: Rebuilding a background from development data at inference (rejected: no development data at
  inference); changing `final` (rejected: the modelling phase is closed).
Reason: Inference needs verifiable provenance and a reproducible explanation reference. For the elastic net the reference
  is the zero vector in scaled space (the mean of the final model's own training representation), valid only if every
  estimator input is centred by the fitted StandardScaler; packaging stops otherwise.
Impact: phase3/packaging.py; no model or evaluation result changes.
```

### Phase 4A frozen inference package (15 October 2026)

```
Date: 2026-10-15
Decision: copath.inference verifies the frozen bundle with the SAME function as `package-final-bundle --verify`
  (phase3.packaging.verify, now self-contained: it checks everything against the manifest, including the exact
  scikit-learn version recorded there), then loads it and answers one record (or a batch) with three calibrated
  probabilities, local explanations that obey explainer_specs.json (no fallback explainer), a runtime additivity guard
  (1e-6) and completeness computed before imputation. Input validation is strict; the output contract is versioned
  (schema_version 1.0). top_features contains observed features only. Nothing is persisted; the CLI refuses an --output
  path inside the git working tree that is not git-ignored. No API, UI, database or persistence is built.
Evidence: Phase 4A.0 packaging verified locally (explanation conventions agree with shap to ~1e-15).
Alternatives considered: A lenient input mode; rebuilding a background from development data; a second copy of the
  verification code (all rejected).
Reason: The JSON schemas and this package are the integration boundary until the team decides the shared architecture.
Impact: src/copath/inference/, docs/input_schema_v1.json, docs/input_features_v1.md, docs/output_schema_v1.json,
  docs/output_schema.md, docs/integration_open_questions.md; packaging.verify refactored (same checks, no dependence on
  development run records).
```

### Phase 2 — implementation (11 October 2026)

```
Date: 2026-10-11
Decision: The analytic universe is the Curated Data Cut at EVENT_ID = BL, one row per participant
  (expected 5,019: PD 1,684, HC 336, Prodromal 2,935, SWEDD 64). Phase 2 stops and writes
  reports/phase2/drift_report.md if these counts differ.
Evidence: Audit v1.1/v1.2 (analytic_universe.csv).
Alternatives considered: Building whatever population the download contains.
Reason: A silent change of population would invalidate the frozen split and every reported number.
Impact: configs/phase2.yaml (expected_counts); src/copath/data/cohort.py (check_drift).
```

```
Date: 2026-10-11
Decision: Only the approved sources are joined, each brought to participant level first, with
  one-row-per-participant and key-uniqueness assertions before and after every join. The newest
  copy of a table is used when a download contains several. Pilot and Deprecated biospecimen
  tables are refused by name.
Evidence: Audit v1 (duplicate downloads have identical content; table granularity inventory).
Alternatives considered: Outer joins of raw tables (rejected: row multiplication in the old merge).
Reason: Section 5.1 of the frozen decisions.
Impact: src/copath/data/sources.py, merge.py, cohort.py.
```

```
Date: 2026-10-11
Decision: The Concomitant Medication Log is treated as a complete list of current medications:
  no record of a drug class means the participant is not taking it.
Evidence: Audit v1.2 medication audit; no other source of treatment information exists.
Alternatives considered: Masking participants without any medication record.
Reason: Frozen implementation rule of 11 Oct 2026. The number of participants without any
  record is reported by cohort and label value; the >=1-record restriction is a Phase 3 sensitivity analysis.
Impact: targets/vascular_v1.yaml (assumption); reports/phase2/vascular_component_prevalence.csv.
```

```
Date: 2026-10-11
Decision: "Ongoing at baseline" = start month <= BL month and (no stop date or stop month >= BL
  month), at month precision against the curated BL visit month. Year-only start before the BL
  year counts; year-only start in the BL year is ambiguous and not counted; missing or
  unparseable start is not counted; year-only stop in the BL year counts as ongoing.
Evidence: Audit v1.2 (99.9% of start dates usable).
Alternatives considered: Counting ambiguous year-only starts.
Reason: Frozen rule. Counts of every excluded category are reported in cohort_flow.md.
Impact: src/copath/data/medications.py.
```

```
Date: 2026-10-11
Decision: [interpretation] A medication record whose stop date is present but unparseable is not counted.
Evidence: None in the frozen documents (they cover missing and year-only stop dates only).
Alternatives considered: Treating an unparseable stop as "no stop date" (would count it as ongoing).
Reason: The drug was stopped at an unknown time; counting it as ongoing would over-ascertain.
Impact: medications.ongoing_at_baseline; the count is reported.
```

```
Date: 2026-10-11
Decision: [interpretation] Drug lists: diltiazem and verapamil are kept as calcium-channel
  blockers (definite). Eplerenone, methyldopa and aliskiren, which were in the audit's list,
  are not in the frozen definite list and were removed. A hypertension indication is CMINDC = 14
  or indication text matching hypertension / high blood pressure / HTN, excluding pulmonary,
  ocular, intraocular and portal hypertension.
Evidence: Section 5.2 lists the definite classes; CMINDC 14 = Hypertension in the Code List.
Alternatives considered: Keeping the wider audit list.
Reason: The frozen list is explicit; anything not on it is not counted.
Impact: configs/drug_classes.yaml (include / conditional / exclude).
```

```
Date: 2026-10-11
Decision: [interpretation] htn_bp is 1 when supine SBP >= 140 or DBP >= 90, 0 when both readings are
  present and below, and missing when only one reading is present and below its threshold.
  Several readings at a visit are averaged; screening is used only when baseline has no reading.
Evidence: Frozen rule gives the thresholds, the mean and the SC fallback, not the one-reading case.
Alternatives considered: Treating a single normal reading as "not hypertensive".
Reason: One normal value says nothing about the other; unknown must not become absent.
Impact: medications.vascular_components.
```

```
Date: 2026-10-11
Decision: Vascular labels are masked only when the component count is below the positive
  threshold AND hypertension is not evaluable (no supine BP and no qualifying antihypertensive).
  A participant at or above the threshold is positive without BP.
Evidence: Frozen implementation rule of 11 Oct 2026.
Alternatives considered: None (the rule is given as concrete).
Reason: As frozen. Note: with the v1 threshold of 2, a participant with no DM and no DYSLIP
  evidence and unknown HTN is masked, although one more component could not make them positive.
Impact: targets.builders.vascular; targets/vascular_v1.yaml, vascular_v2.yaml.
```

```
Date: 2026-10-11
Decision: AD-like v1 is built from the card: ratio = max(ptau, 8) / min(abeta, 1700), positive
  above the card's cut-off (0.025). The build stops if the card lacks derived_value, abeta_used,
  ptau_used or cutoff, or if they disagree with each other. Non-numeric or <= 0 values are masked.
Evidence: targets/ad_like_v1.yaml.
Alternatives considered: Hard-coding the numbers.
Reason: The card is authoritative; a changed card must change the label, visibly.
Impact: targets.builders.ad_like_parameters / ad_like; sensitivity variants are read from the card.
```

```
Date: 2026-10-11
Decision: The Lumipulse label is built after the split. A 2-component Gaussian mixture is
  fitted to log(ABeta42/ABeta40) of eligible development-set participants only; the threshold
  is the equal-posterior point between the component means; positive = ratio below it. The
  parameters are frozen in configs/frozen/lumipulse_gmm_v1.json. Several BL results of one
  test are averaged.
Evidence: Frozen implementation rule of 11 Oct 2026.
Alternatives considered: Fitting on all participants (rejected: uses the test set).
Reason: As frozen.
Impact: targets.builders.fit_lumipulse_threshold; phase2._lumipulse.
```

```
Date: 2026-10-11
Decision: configs/leakage_matrix.csv is the single authoritative leakage file (one row per
  analytic column, one status per label). docs/leakage_matrix.md and configs/feature_sets/ are
  generated from it. Phase 2 fails if a column of the analytic dataset is not in the matrix or
  if the generated files are out of date.
Evidence: Section 5.3.
Alternatives considered: Rule patterns applied at run time (rejected: not reviewable).
Reason: One reviewable source; no handwritten parallel lists.
Impact: src/copath/features/leakage_guard.py.
```

```
Date: 2026-10-11
Decision: [interpretation] Additional columns marked "never" beyond the explicit list in section 5.3:
  HIQ_RBD (enrolment-route indicator), DOMSIDE (PD history), age_datscan / age_LP / age_upsit
  (procedure timing), ON-medication scores (updrs3_score_on, hy_on, NHY_ON, pigd_on,
  updrs_totscore_on), updrs4_score, CSFSAA_assay, the text APOE genotype (APOE_e4 is the
  feature), and the derived meta columns (bp_source, med_record_any, htn_evaluable for
  non-vascular labels). Near-proxy for PD-type beyond DAT, UPDRS III and H&Y: updrs_totscore
  (contains Part III) and pigd (derived from Part II/III items).
Evidence: Curated-cut data dictionary (reference export); Cramér's V of availability with cohort.
Alternatives considered: Leaving them as ordinary features.
Reason: Each either exists only for (treated) PD, encodes enrolment route, or is an availability
  indicator. Conservative; each row carries a note and can be changed in the CSV.
Impact: configs/leakage_matrix.csv.
```

```
Date: 2026-10-11
Decision: Tiers are implemented exactly as written: primary = all minus defining and never;
  strict = primary minus near-proxies; full = primary plus near-proxies.
Evidence: Section 5.3 and the Phase 2 specification.
Alternatives considered: primary = safe features only (then primary would equal strict).
Reason: The written rules are followed literally. Consequence: full and primary are the same
  set, because primary already contains the near-proxies. To be confirmed.
Impact: leakage_guard.tier_features; configs/feature_sets/.
```

```
Date: 2026-10-11
Decision: The development/test split (80/20) and 5 development folds use iterative
  stratification on cohort and on the availability and positive indicators of pd_type_v1,
  ad_like_v1 and vascular_v1 only. Indicators with fewer than 10 participants are merged
  (cohorts) or dropped. The split is frozen: a later run must reproduce it or fails. Test
  identifiers and rows load only with final_evaluation=True and COPATH_FINAL_EVALUATION=1.
Evidence: Section 5.5 and the 11 Oct 2026 rules.
Alternatives considered: Stratifying on sensitivity labels (forbidden).
Reason: As frozen.
Impact: src/copath/data/split.py; data/splits/ (git-ignored).
```

```
Date: 2026-10-11
Decision: [interpretation] Construct checks (MoCA, APOE e4, age, WM hypointensities by label status)
  are computed on the development set only.
Evidence: The specification asks for the checks but not on which participants.
Alternatives considered: All participants.
Reason: Keeps the test set untouched until the single final evaluation.
Impact: reports/phase2/construct_check.csv.
```
