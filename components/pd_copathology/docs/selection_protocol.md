# Model selection protocol (v1)

Status: **written on 11 October 2026, before any model was trained on PPMI data.**
The code in `src/copath/evaluation/selection.py` implements this document and
nothing else; every threshold below is read from `configs/phase3.yaml`
(`selection:`). Changing this file after the first real `cv` run must be
recorded in `docs/decisions_log.md` with the reason.

Sources: `docs/phase1_final_decisions_v1.md` sections 5.5, 5.6 and 9.

## 1. What is selected

One model family per primary label (`pd_type_v1`, `ad_like_v1`,
`vascular_v1`), as binary relevance: each label has its own eligible
(non-masked) participants and its own feature set. Selection uses the
**primary** feature tier and the **development set only**. The test set is not
loaded by any step of this protocol.

Five candidates, all on the same fold-safe pipeline (median imputation and
standardisation inside the pipeline for the linear models; native missing-value
handling for XGBoost and histogram gradient boosting):

| Name | Model |
|---|---|
| `lr_l2` | standard L2 logistic regression on all features |
| `lr_enet` | elastic-net logistic regression (saga) |
| `rf` | random forest |
| `xgb` | XGBoost |
| `hgb` | histogram gradient boosting |

Baselines (never selectable, not candidates): prevalence (`b0a`), age + sex
logistic regression (`b0b`). The missingness-only model is a leakage check
(section 4.2), not a candidate.

Selection is **per label** (binary relevance), as in section 9 of the frozen
decisions; the macro Brier Skill Score over the three labels is reported next
to it. Assay limit flags (`abeta_LLOD`, `abeta_ULOD`, `ptau_LLOD`, `tau_LLOD`)
and `ad_like_v1_censored` may build the AD-like label internally but are
`never` in the leakage matrix for every label, so no feature set contains them.

## 2. Validation design

- Outer loop: the 5 frozen development folds (`data/splits/split_v1_dev_folds.csv`).
- Inner loop, inside each outer-training set only: Optuna TPE, stratified
  3-fold CV, objective mean log loss, 25 trials per model (15 for each logistic
  regression), fixed seed. Class weighting is a tuned hyperparameter. `lr_l2`
  tunes `C` (1e-3 to 1e2, log scale) and class weighting only; `lr_enet` also
  tunes `l1_ratio`.
- Calibration: `CalibratedClassifierCV(method="sigmoid", cv=3)` fitted on the
  outer-training set with the tuned hyperparameters.
- Threshold (for F1 and Hamming loss only): maximises F1 on inner
  out-of-fold calibrated predictions of the outer-training set, then applied
  unchanged to the outer-test fold. These predictions come from the three
  calibration folds: each member model of the calibrated ensemble predicts
  the third of the training rows it was not trained on.
- All preprocessing is inside the pipeline and is fitted on training rows only.

## 3. Metrics

All from calibrated out-of-fold predictions of the outer-test folds.

- **Primary metric: Brier Skill Score (BSS)** against the prevalence baseline
  (the training-fold prevalence): `1 - Brier(model) / Brier(prevalence)`.
  The score of a model for a label is the **mean of its five outer-fold BSS
  values**; its standard error is `SD / sqrt(5)`.
- Secondary: AUROC, AUPRC, Brier, calibration slope and intercept (logistic
  recalibration of the outcome on the logit of the prediction), ECE (10
  bins), F1 / precision / recall at the chosen threshold; pooled and per fold.
- System level (reported, not used to choose): macro BSS / AUROC / AUPRC / F1
  across the three labels; Hamming loss and macro-F1 on participants eligible
  for all three labels.

## 4. Stage 1 - preliminary selection (`select --stage preliminary`)

Uses only the `cv` results.

### 4.1 Gates (per label, per candidate)

| Gate | Passed when |
|---|---|
| G1 calibration | pooled calibration slope is between 0.7 and 1.3 (inclusive) |
| G2 beats prevalence | pooled Brier score is lower than the pooled Brier score of `b0a` |
| G3 beats age + sex | pooled AUPRC is higher than the pooled AUPRC of `b0b` |
| G4 complete | no outer fold failed |

A value that cannot be computed counts as a failed gate. Every candidate is
listed in the report with each gate result; failed models are reported, not
hidden.

### 4.2 Leakage check (per label)

A logistic regression on missingness indicators only is run in the same outer
folds. If its pooled AUROC is above 0.70 the label is **flagged**: which
measurements exist predicts the label. The flag is a property of the label,
not of a candidate, so it does not change the ranking; it is carried into
every selection report and `selected_models_v1.yaml`, and it must be
addressed in the human review before the final evaluation.

### 4.3 Ranking and tie set

1. Among the candidates that pass all four gates, the best is the one with
   the highest score (mean fold BSS).
2. The **tie set** is every gate-passing candidate whose score is at least
   `best score - SE(best)` (the 1-SE rule).

### 4.4 If no candidate passes all gates

The label is marked **provisional (gate failure)**. So that robustness and
explainability reports can still be produced for review, a provisional tie
set is formed by applying 4.3 to the candidates with the fewest failed gates
among those with no failed fold. A provisional selection is never silently
final: the reports and `selected_models_v1.yaml` carry `gates_passed: false`
and the failed gates, and the reviewer must accept or reject it explicitly.
If every candidate has a failed fold, nothing is selected for that label.

`selection_final.md` explains, for every provisional label, which gates each
candidate failed with the values behind them. **The final evaluation stays
locked for a provisional label** unless `configs/frozen/final_approval.yaml`
also contains `acknowledge_provisional: [<label ids>]` listing every
provisional label (also written in `selected_models_v1.yaml` as
`provisional_labels`). A label id that is not in the selection is an error.

## 5. Robustness of the tie-set models (`robustness`)

For every model in every tie set, reusing the per-fold hyperparameters of
`cv` (no re-tuning), on the same frozen outer folds:

- strict tier, base seed;
- primary tier with 3 seeds (base seed, +1, +2). The seed changes the model's
  random state and the calibration / threshold splits; the outer folds stay
  the frozen ones;
- SHAP on every outer-fold model of every run: mean |SHAP| per feature on the
  fold's test rows, top-10 Jaccard and Kendall tau between all pairs of the
  15 primary-tier rankings (5 folds x 3 seeds).

## 6. Stage 2 - final selection (`select --stage final`)

Refuses to run unless the robustness results exist for every tie-set model.
Within each tie set the tie-breakers are applied in this order; after each
one only the models within the stated tolerance of the best remain, and the
procedure stops as soon as one model remains.

| Order | Criterion | Better | Tolerance (still tied) |
|---|---|---|---|
| (a) | pooled calibration slope, distance from 1 | smaller | within 0.05 |
| (b) | SHAP top-10 stability: mean pairwise Jaccard | larger | within 0.05 |
| (c) | drop in score from primary to strict tier (base seed) | smaller | within 0.01 BSS |
| (d) | simplicity: `lr_l2` > `lr_enet` > `hgb` > `rf` > `xgb` | simpler | none (always decides) |

A tie set with one model is selected directly; its robustness results are
still recorded. The outcome is written to `reports/phase3/selection_final.md`
(full reasoning per label) and frozen in
`configs/frozen/selected_models_v1.yaml` (model family and hyperparameter
source per label).

## 7. Calibration

Sigmoid (Platt) calibration is the default and the only one used for
selection. Isotonic and no calibration are compared for the selected models
afterwards (`extras`) and are reported, not used to re-select.

## 8. Final held-out-test policy

- The test set is created by Phase 2 and frozen. No step before `final`
  loads test identifiers or test rows.
- `final` runs only with `--final` **and** a human-written
  `configs/frozen/final_approval.yaml` containing `approved: true`, the
  reviewer's name, the date and the SHA-256 of `selected_models_v1.yaml`
  (and `acknowledge_provisional` when a label is provisional, section 4.4).
  The software never creates this file.
- `final` refits each selected model on the whole development set (inner-CV
  tuning, then calibration, then the threshold), predicts the test set
  **once**, and reports the same metrics with 1,000-bootstrap 95% intervals.
- A lock file is written afterwards. A second run is refused unless it is
  forced with a written reason, which is logged.
