# PD Co-Pathology Component — Phase 1 Summary and Frozen Decisions (v1)

**Project:** Explainable Co-Pathology Signal Estimation in Parkinson's Disease Using PPMI Data (J26-DS-306)
**Status:** Phase 1 (audit + feasibility) complete. Decisions below are frozen as **v1**, pending supervisor sign-off.
**Date:** 11 October 2026
**Place in repo:** `components/pd_copathology/docs/phase1_final_decisions_v1.md`

---

## 1. What this component does (unchanged)

For one PPMI participant at baseline, return three independent, non-mutually-exclusive **research proxy signal probabilities**: PD-type, AD-like and vascular-risk. Each comes with label-specific SHAP explanations and data-completeness metadata, delivered as a versioned JSON record to the Clinical Predictive Safety Framework.

Open-set recognition, OOD detection and TRUST/CAUTION/DEFER decisions are **not** part of this component. The outputs are research proxies, **not diagnoses**.

---

## 2. What was done

| Step | Outcome |
|---|---|
| Environment | Isolated git worktree `feature/pd-copathology`, component skeleton under `components/pd_copathology/`, `.venv`, editable package `copath`, `.env` with `PPMI_DATA_ROOT`, nbstripout, data/model folders git-ignored |
| Data governance | Raw PPMI data stays on Google Drive and is read-only. Claude Code builds and tests on **synthetic fixtures only**; the student runs real-data jobs locally. Reports are aggregate only, counts below 5 are suppressed, and no participant IDs appear anywhere under `reports/` |
| Audit v1 | 9 archives/files, 131 source tables, 6 dictionaries and 1 derived file profiled. Duplicate downloads turned out to be identical content. Table granularity, key uniqueness, event codes, long-format biomarkers and special/censored values were all inventoried |
| Audit v1.1 | Baseline universe defined. Medical_Conditions_Log examined: category codes only. Domain classification errors fixed |
| Audit v1.2 | Per-cohort baseline overlap, label feasibility, medication/vascular audit, FreeSurfer white-matter check, CSF assay map, reference dictionaries |
| Methods documents | PPMI biospecimen methods for projects 125, 159 and 283 obtained and reviewed |

---

## 3. Key audit findings that drove the decisions

1. **Most "participants" in the download are not the study population.** The 35,903 IDs seen across tables include remote/online arms (ST-Direct, myPPMI). The analytic universe is the **5,019 in-clinic participants with a baseline row in the PPMI Curated Data Cut**: PD 1,684, HC 336, Prodromal 2,935, SWEDD 64.
2. **The old exploratory merge (`final_multimodal_dataset.csv`) is retired.** PATNO+EVENT_ID is not unique (7,815 duplicate rows), it covers 19,662 IDs including remote participants, and it pools three different Aβ42 assays.
3. **The PPMI Curated Data Cut is the backbone.** It is PPMI's official harmonised table with one row per participant-visit (unique key), already aligns DAT and MoCA to BL, and documents its own derivations.
4. **CSF Alzheimer's biomarkers come from three projects on two platforms:**
   - Project 125 (2017) and project 159 (2021): **Roche Elecsys**, UPenn. 159 was re-scaled to the 125 scale, and the curated `abeta`/`tau`/`ptau` columns merge both, giving about 1,280 participants at BL.
   - Project 283 (2025): **Fujirebio Lumipulse**, Indiana/NCRAD. Aβ42, Aβ40 and pTau181 for 1,919 participants at BL. Different platform, so it is never pooled with Elecsys.
5. **Medical_Conditions_Log has no condition names**, only broad category codes such as "cardiovascular" or "metabolic/endocrine". Hypertension, diabetes, hyperlipidaemia and stroke cannot be identified from it.
6. **The concomitant medication log is usable for vascular risk.** Drug names, start dates (99.9% usable) and stop dates support an "ongoing at baseline" rule. There is no ATC or class code, so classes come from a curated drug list. Several drugs are ambiguous in PD and need indication-based handling: propranolol (tremor), alpha-blockers (prostate), and midodrine, fludrocortisone and droxidopa (orthostatic hypotension).
7. **Supine BP is available at BL for 98% of participants.** About 34.5% have BP ≥140/90.
8. **Lab vascular measures are effectively absent** (lipids and glucose in about 254 people). Stroke/TIA (10) and cardiac disease (54) are too sparse to use.
9. **FreeSurfer T1 white-matter hypointensity volumes exist** (`WM_hypointensities`, about 1,691 at BL). They are a proxy for lesion burden, not FLAIR WMH.
10. **SAA status at BL is available for 3,553 participants:** positive 2,269, negative 1,297, inconclusive 75, conflicting 81.
11. **Data availability is associated with cohort** (Cramér's V ≈ 0.3 for CSF, DAT, MoCA and others). Missingness indicators would leak cohort membership.

---

## 4. What changed from the original proposal, and why

| Area | Original plan | Final (v1) | Reason |
|---|---|---|---|
| Model architecture | Deep multimodal fusion with attention, open-set layer | Feature-level fusion with linear and tree models; open-set/OOD moved to the Safety Framework | Finalised methodology; tabular data; sample size; defensibility |
| Dataset | Exploratory Colab merge | Rebuilt from the Curated Data Cut plus selected source tables by repository code | Non-unique keys, pooled assays and remote participants in the old merge |
| Population | All PPMI IDs | 5,019 in-clinic participants with a BL curated row | Remote-only participants have no clinical data |
| Index visit | Not fixed | BL. SC used only as a recorded fallback for source-table additions | Curated cut already aligns BL |
| PD-type label | Not specified | Primary: PD vs HC. Sensitivity: SAA biological definition | PD vs HC is near-trivial; SAA adds a non-trivial, biology-based check |
| AD-like label | Aβ42/pTau "literature threshold" | Elecsys p-tau181/Aβ42 ratio > 0.025 (primary; Hansson 2018 ADNI cut-off). Lumipulse 283 as replication | Assay identified; ADNI was measured in the same UPenn lab on the same Elecsys research assays as PPMI; Aβ42 alone is not AD-specific (about 30% of PD and HC are "low") |
| Vascular label | History of HTN/DM/hyperlipidaemia/CVD | **Treated or measured vascular risk-factor burden** (medications ongoing at BL + BP) | Medical history has no condition names; stroke/cardiac too sparse |
| Vascular imaging | WMH as possible label component | FreeSurfer WM hypointensities as a **feature**, used for plausibility checks | T1 hypointensity, not FLAIR; only about 1,700 people |
| Missing data | Missingness indicators considered | Excluded by default | Availability predicts cohort (leakage) |
| Candidate models | Many, including MLP and LightGBM | LR (elastic net), Random Forest, XGBoost, HistGradientBoosting; chains optional | 3-day training deadline; HistGB covers LightGBM's niche; MLP unlikely to win on this n |

---

## 5. Frozen decisions (v1)

### 5.1 Analytic universe and sources
- **Universe:** PPMI Curated Data Cut, `EVENT_ID = BL`, one row per participant (n = 5,019).
- **Added sources:**
  - FS7_ASEG_VOL and FS7_APARC_CTH at BL;
  - iu_genetic_consensus (participant level);
  - SAA_Biospecimen_Analysis_Results (SAA status at BL);
  - Current_Biospecimen_Analysis_Results, project 283 only (Lumipulse CSF at BL);
  - Vital_Signs (supine BP at BL, SC fallback);
  - Concomitant_Medication_Log (drug flags ongoing at BL).
- **Biospecimen versions:** Current results only. Pilot and Deprecated tables are not used.
- **Join rule:** every join must keep one row per participant. Tables of different granularity are aggregated before joining, never outer-joined.

### 5.2 Labels (each is 1 / 0 / masked; masked ≠ negative)

| Label | Primary definition | Eligible | Sensitivity variant(s) |
|---|---|---|---|
| **PD-type** (`pd_type_v1`) | COHORT PD = 1, HC = 0; Prodromal and SWEDD masked (scored as an exploratory application) | 2,020 | `pd_type_saa_v1`: SAA Positive = 1, Negative = 0, all cohorts; inconclusive/conflicting masked (~3,470) |
| **AD-like** (`ad_like_v1`) | Elecsys p-tau181 / min(Aβ42, 1700) > **0.025** at BL (Hansson 2018, ADNI-derived); missing = masked | ~1,280 | cut-offs 0.028 (Hansson prespecified, ADNI-transferred) and 0.022 (BioFINDER); ±5% grey zone masked; amyloid-only Aβ42 ≤ 977 pg/mL; `ad_like_lumipulse_v1` (project 283 Aβ42/Aβ40, 2-component mixture cut-off) |
| **Vascular-risk** (`vascular_v1`) | ≥2 of {HTN, DM, DYSLIP} | ~5,000 | `vascular_v2`: ≥1 component |

**Vascular components** ("ongoing at BL" = start month ≤ BL month and no stop before the BL month):
- **HTN:**
  - **Counts:** an ongoing definite antihypertensive (ACE inhibitor, ARB, calcium-channel blocker, thiazide/thiazide-like, spironolactone, triamterene, hydralazine); **or** an ongoing beta-blocker, alpha-blocker (except tamsulosin and silodosin) or loop diuretic **with a hypertension indication**; **or** supine SBP ≥140 or DBP ≥90 at BL.
  - **Never counts:** midodrine, fludrocortisone and droxidopa. Clonidine counts only with a hypertension indication.
- **DM:** an ongoing antidiabetic drug.
- **DYSLIP:** an ongoing lipid-lowering drug.

### 5.3 Leakage control

| Applies to | Never a feature | Also excluded in the strict tier |
|---|---|---|
| All labels | COHORT, subgroup, analytic_subgroup, enroll_phase/enroll_source, PRIMDIAG, NSD-ISS fields, CGI, PGI, LEDD, PDTRTMNT, duration, agediag, ageonset, sym_*, td_pigd, milestone (pm_*) variables, study_status, death fields, SITE, dates, missingness indicators | — |
| PD-type | — | DAT SBRs, UPDRS III, H&Y |
| PD-type (SAA variant) | CSFSAA, asyn, SAA status | — |
| AD-like | abeta/tau/ptau (+LLOD/ULOD), IU_* CSF, C2N, MTBR-tau | plasma pTau217, plasma bd-tau |
| Vascular | supine/standing BP, `orthostasis`, every cardiovascular/antidiabetic/lipid drug flag | Medical_Conditions_Log categories |

**Tiers:**
- **Full:** sanity check only; shows circularity.
- **Primary:** never-features removed.
- **Strict:** near-proxies also removed.

A missingness-only model is used as a leakage check.

### 5.4 Features (BL)
- **Demographics:** age, sex, education, BMI.
- **Genetics:** APOE ε4, polygenic scores, GBA/LRRK2 carrier status.
- **Cognition:** MoCA and the normed neuropsychological scores.
- **Non-motor scales:** UPDRS I–III, ESS, GDS, STAI, SCOPA-AUT, RBD questionnaire, QUIP, UPSIT.
- **Imaging:** DAT SBRs; FS7 volumes and cortical thickness, including WM hypointensities.
- **Biofluids:** plasma NfL/GFAP, serum NfL, urate; SAA where allowed.

**Missing data:** tree models use native NaN handling; linear models use median imputation fitted inside training folds.

### 5.5 Split and validation
- **Split:** participant-level 80/20, stratified on cohort × label-availability × label values, fixed seed. The **test set is used once**, after model selection.
- **Development set:** outer 5-fold CV. Inner 3-fold tuning (Optuna, equal trial budget per model) and calibration (Platt by default, isotonic as a comparison) happen inside training folds only.
- **Metrics:**
  - per label: AUROC, AUPRC, Brier and Brier Skill Score, calibration slope/intercept, F1 at a fold-chosen threshold;
  - multi-label: macro-F1, Hamming loss;
  - bootstrap 95% CIs on the test set.

### 5.6 Candidate models and selection
- **Baselines:**
  - B0: prevalence; age + sex logistic regression.
  - B1: logistic regression.
  - B2: Random Forest.
  - B3: XGBoost.
  - Full-tier sanity runs.
- **Candidates:** elastic-net logistic regression, Random Forest, XGBoost and HistGradientBoosting, as **binary relevance per label** (each label with its own eligible population and leakage tier). An ensemble of classifier chains on the complete-label subset is optional.
- **Selection protocol (pre-registered):**
  1. **Gates:** leakage test passed; calibration slope 0.7–1.3; beats the prevalence Brier score; beats the age + sex baseline in AUPRC.
  2. **Primary ranking:** macro Brier Skill Score of calibrated out-of-fold predictions.
  3. **Tie set:** models within 1 SE of the best.
  4. **Tie-breakers, in order:** worst-label performance, calibration, SHAP stability, robustness (strict tier and proxy variants), simplicity.

### 5.7 Explainability
- **Methods:** TreeSHAP or LinearExplainer on the uncalibrated model's log-odds, computed per label.
- **Outputs:** global importance; local top-k features; modality-grouped contribution.
- **Stability:** across outer folds and 3 seeds (top-10 Jaccard, Kendall τ).
- **Plausibility:** compared against an expected-features table written before results:
  - AD-like ↔ APOE ε4, cognition, age;
  - vascular ↔ age, BMI, WM hypointensities;
  - PD-type ↔ UPSIT, RBD, DAT.
- **Storage:** participant-level SHAP values stay in git-ignored folders; only aggregates go to `reports/`.

---

## 6. Known limitations to state in the dissertation
- All three signals are **proxy labels**; no clinical or neuropathological ground truth.
- The vascular proxy reflects **treated or measured risk factors**. It under-captures untreated disease and is affected by PD-related low blood pressure, and it depends on medication recording quality.
- AD-like cut-offs come from AD/amyloid-PET cohorts (ADNI, BioFINDER), not from PPMI. Elecsys Aβ42 depends on CSF handling (~24% shift between protocols in Hansson 2018); the ADNI cut-off is used because ADNI and PPMI share the UPenn lab and research-use assays, but PPMI handling is assumed rather than proven to match ADNI. Sensitivity cut-offs (0.022, 0.028) address this.
- PD vs HC is easy to separate. The strict tier and the SAA variant are the scientifically informative results.
- Only 336 healthy controls; class imbalance for PD-type.
- MRI covers only about a third of participants.
- PPMI is a research cohort, and there is **no external validation**.

---

## 7. Plan to the training deadline (3 days)

| Day | Work | Done when |
|---|---|---|
| 1 | Phase 2: target cards, label builders, leakage matrix, cohort build, frozen split (run locally) | Label prevalence by cohort reviewed; test set frozen |
| 1 (evening) | Training harness on synthetic data | Smoke test passes |
| 2 | Baselines and candidates for all labels × tiers (overnight) | All runs logged |
| 3 | Selection, single test evaluation, calibration, SHAP and stability, modality ablation, sensitivity labels, figures | Every research question has a table or figure |

**After the deadline:** API (FastAPI), prototype view, integration contract with the Safety Framework.

---

## 8. Decision log entries to add (`docs/decisions_log.md`)
1. Universe = Curated Data Cut BL (n = 5,019); remote-only participants excluded.
2. `final_multimodal_dataset.csv` retired (reference only).
3. Current biospecimen results only; Pilot and Deprecated excluded.
4. PD-type v1 = PD vs HC; SAA variant as sensitivity.
5. AD-like v1 = Elecsys p-tau181/Aβ42 > 0.025 (Hansson 2018, ADNI-derived; same UPenn lab and assay generation as PPMI); 0.022 and 0.028 as sensitivity; Lumipulse 283 never pooled, used as replication.
6. Vascular construct changed to treated or measured risk-factor burden (supervisor informed; change is justified by the data).
7. Medication "ongoing at BL" rule and drug-class lists frozen in `configs/drug_classes.yaml`.
8. Missingness indicators excluded from features.
9. Candidate set reduced for the deadline (MLP and LightGBM dropped).
10. Test set used once, after selection.
