# PD Co-Pathology Component — Progress Log

**Project:** Explainable Co-Pathology Signal Estimation in Parkinson's Disease Using PPMI Data (J26-DS-306)

**Branch / worktree:** `feature/pd-copathology` in `NeuroSage-pd-copathology`

**Status at 16 Oct 2026:** The standalone component is complete for team integration. Model development, the one-time held-out evaluation, read-only held-out reporting (Phase 3b), frozen-bundle provenance packaging (Phase 4A.0), and the frozen inference package with input/output JSON contracts and CLI (Phase 4A) are finished and committed. API, database, frontend, and Safety Framework integration are pending a team architecture decision.

**Companion document:** `docs/phase1_final_decisions_v1.md`, which holds the authoritative scientific decisions. This log records **what was done, in what order, and why**.

**Place in repo:** `components/pd_copathology/docs/PROGRESS_LOG.md`

---

## 1. Timeline

| # | Stage | What was done | Outcome |
|---|---|---|---|
| 0 | Planning | Read the proposal; defined scope, outputs, risks, and a fast-track plan | The component outputs three research proxy probabilities plus SHAP explanations and metadata. OOD/TRUST–CAUTION–DEFER belongs to the Safety Framework |
| 1 | Environment | Git worktree, component skeleton, `.venv`, editable `copath` package, `.env` with `PPMI_DATA_ROOT`, nbstripout, and Git protections for research data/model artifacts | An isolated, reproducible workspace |
| 2 | Governance | Development and testing use synthetic fixtures only; real-data commands are run locally by the student; reports are aggregate only, counts below 5 are suppressed, and participant IDs are excluded from shared outputs | Participant-level PPMI data remains inside the local real-data workflow |
| 3 | Audit v1 | Inventory of 9 archives/files, 131 tables, keys, event codes, long-format biomarkers, and censored values | 35,903 IDs in the download, mostly remote-only arms; the old Colab merge was unreliable |
| 4 | Audit v1.1 | Baseline universe, domain-classification fixes, `Medical_Conditions_Log` | Universe is 5,019 in-clinic participants; the medical-conditions table holds category codes only |
| 5 | Audit v1.2 | Per-cohort overlap, label feasibility, medication audit, FreeSurfer white-matter check, CSF assay map | Medication log and BP usable for vascular; real white-matter hypointensity fields exist |
| 6 | Methods documents | Read PPMI methods for projects 125, 159, and 283 | 125/159 = Roche Elecsys (UPenn, same scale); 283 = Fujirebio Lumipulse; never pooled |
| 7 | Cut-off | Read Hansson et al. 2018 | AD-like cut-off = Elecsys p-tau181/Aβ42 > **0.025** (ADNI-derived, same lab and kits as PPMI) |
| 8 | Decisions frozen v1 | `phase1_final_decisions_v1.md` and the target cards | Labels, leakage tiers, features, split, and selection protocol fixed |
| 9 | Phase 2 | Cohort builder, six label variants, machine-readable leakage matrix, frozen split, test-set guard | 5,019 × 385 table; balanced 4,015 / 1,004 split |
| 10 | Phase 2 review | Two independent reviews of the aggregate reports | Found the AD-like censoring bias and smaller issues described below |
| 11 | Phase 2.1 | Fixes plus re-freeze (the only re-freeze allowed) | AD-like eligible 1,029 → 1,277; split rebuilt and locked |
| 12 | Phase 3 harness | Nested CV, two-stage selection, robustness, extras, SHAP, locked final evaluation | 113 synthetic tests passed at this point; five candidate models |
| 13 | Git checkpoint | Checkpoint commits created on the feature branch; branch later pushed for pull-request review on 16 Oct 2026 | Development history preserved for review |
| 13b | Phase 3 stability fix | HGB failed on all-NaN / constant features inside some folds. Added fold-safe `DropDegenerateColumns` (pipeline version 2), fail-loud handling for all-failed trials, and `reset-cv` to discard the old CV run | CV restarted cleanly; 127 synthetic tests passed |
| 14 | Phase 3 training and selection | Nested CV of 5 candidates + 2 baselines; two-stage selection; robustness, ablation, sensitivity labels, SHAP; PD missingness audit | RF / elastic-net LR / RF selected; all gates passed |
| 15 | Pre-test review | `phase3_development_review.md` written and committed before test access; local final-evaluation approval file created on 2026-10-14 | Caveats recorded before test access; selection frozen for held-out evaluation |
| 16 | Final evaluation | One-time held-out test evaluation | Held-out results consistent with development estimates; models frozen; final-evaluation lock written |
| 17 | Phase 3b | Read-only held-out reporting (`report-final`): test curves with development overlays, dev-vs-test table, supplementary counts; privacy scan made schema-aware | Figures and tables written from saved predictions only; no new prediction pass |
| 18 | Phase 4A.0 | Additive packaging of the frozen bundle: manifest (file, feature-list and lock hashes; library versions), explainer specs; local SHAP-convention verification on development data | `--verify` passes; max SHAP difference ≤ 1.3e-15 for all three signals |
| 19 | Phase 4A | Frozen inference package, strict input validation, input/output JSON contracts v1.0, CLI, synthetic demo, contract check against the bundle | 222 synthetic tests pass; real-bundle smoke test on a synthetic record passes; component ready for team integration |
| 20 | Next integration stage | Shared API, database, frontend, and Safety Framework integration | Pending team architecture decision |

---

## 2. Key changes from the original proposal

| Area | Original | Final | Why |
|---|---|---|---|
| Model | Deep fusion with attention, open-set layer | Feature-level fusion; linear and tree models; open-set moved to the Safety Framework | Tabular data, sample size, defensibility |
| Data | Exploratory Colab merge | Rebuilt from the PPMI Curated Data Cut plus approved source tables | The old merge had duplicate keys, pooled assays, and remote participants |
| PD-type | Not specified | PD vs HC (primary); SAA status (sensitivity) | PD vs HC is near-trivial; SAA adds biology |
| AD-like | "Aβ42/pTau literature threshold" | Elecsys p-tau181/Aβ42 > 0.025 | Assay identified from the methods documents; Aβ42 alone is not specific |
| Vascular | HTN/DM/lipid/CVD history | Treated or measured risk-factor burden (≥2 of HTN, DM, DYSLIP from medications ongoing at BL and BP) | The medical-conditions table has no condition names |
| WMH | Possible label | Feature only (FreeSurfer T1 hypointensities) | Not FLAIR; about 1,700 participants |
| Tiers | Full / primary / strict | Primary and strict | Full equalled primary once defining features were always excluded |
| Candidates | Many, including MLP | 5 candidates + 2 baselines | Deadline; evidence-based comparison |

---

## 3. Problems found and fixed

| Problem | How it was found | Fix |
|---|---|---|
| Remote-only participants inflated the counts (35,903) | Audit v1 overlap figure | Universe restricted to the curated baseline cut (5,019) |
| Modality misclassification (FS7 classed as DAT; AE forms as imaging) | Audit review | Domain overrides |
| False vascular matches (CACNA1C, cerebellar white matter) | Audit review | Removed |
| Medical-conditions table cannot identify diagnoses | Audit v1.1 | Vascular construct changed to medications + BP |
| Cut-off initially 0.023 from a commercial-test website | Reading Hansson 2018 | Changed to 0.025 (ADNI, same lab and assay) |
| **Curated cut deletes Aβ42 ≥ 1475.4 / < 200 and p-tau ≤ 8, keeping only flags.** This masked clearly amyloid-negative people | Phase 2 report showed 0 values at the limits; confirmed in the curated data dictionary | Boundary substitution from the flags (card v1.1); `ad_like_v1_uncensored` sensitivity label |
| Vascular masked people who could not reach the threshold | Implementation review | Mask only when the unknown HTN component could change the result |
| Measured normal BP recorded as missing | Implementation review | `htn_bp = 0` |
| SAA strongly tied to PD diagnosis | Phase 2 prevalence | SAA fields are near-proxies for PD-type |
| Limit flags could leak cohort | Review | Flags set to `never` as predictors |
| Lumipulse GMM could silently re-fit | Traceability review | Hash recorded in the manifest; a normal run fails if the file is missing or changed |
| Smoke tests could write into the tracked registry | Review | Smoke runs use scratch paths; the registry is checked unchanged |
| Privacy scan flagged genuine metrics as participant IDs (a decimal such as 0.7310 was split into the token 7310) | First real `report-final` run | Schema-aware scan: declared aggregate columns are not compared with IDs; undeclared columns stay strict; identifier-named columns always fail; no value whitelisted |
| Final bundle lacked library versions, file hashes, and an explicit SHAP specification | Phase 4A B0 source-code check | Additive packaging step (`package-final-bundle`); models untouched; elastic-net zero-reference convention verified on development data |
| Committed input contract was generated from the 302-feature tier list instead of the 300-feature frozen bundle | Real-bundle smoke test | The frozen bundle's raw feature union is authoritative; `--check-contracts --from-bundle` verifies it locally |
| HGB crashed on features that were all-missing or constant within a training fold | First real CV run (ValueError) | Fold-safe `DropDegenerateColumns` fitted inside each fold; pipeline version 2; fail-loud if all trials fail; old CV discarded with `reset-cv` and re-run |
| PD model could learn from missingness patterns | Phase 3 review (missingness-only check) | Missingness audit plus low-missingness re-run: strict BSS 0.760 vs 0.768, so the PD signal does not depend on missingness |

---

## 4. Frozen dataset after Phase 2.1 (re-freeze, 11 Oct 2026)

**Universe:** 5,019 participants (PD 1,684, HC 336, Prodromal 2,935, SWEDD 64). Final table: 5,019 × 387. The drift guard passed.

**Split:** 4,015 development / 1,004 test (seed 20261011). Cohorts and primary labels are within 0.1 percentage points across development, test, and all five folds. **The split is now permanently locked.**

**Primary labels:**

| Label | Eligible | Positive (%) | Development positives | Positives per fold |
|---|---:|---:|---:|---:|
| pd_type_v1 | 2,020 | 1,684 (83.4%) | 1,347 of 1,616 | ~270 |
| ad_like_v1 | 1,277 | 142 (11.1%) | 114 of 1,022 | 22–23 |
| vascular_v1 | 5,012 | 1,407 (28.1%) | 1,126 of 4,010 | ~225 |

**Sensitivity labels:**

| Label | Eligible | Positive (%) |
|---|---:|---:|
| pd_type_saa_v1 | 3,467 | 63.7% |
| ad_like_v1_cut028 | 1,277 | 8.0% |
| ad_like_v1_cut022 | 1,277 | 15.2% |
| ad_like_v1_greyzone | 1,245 | 10.0% |
| ad_like_v1_uncensored | 1,029 | 12.3% |
| ad_like_lumipulse_v1 | 1,919 | 21.8% (GMM threshold Aβ42/40 = 0.0745, fitted on development data only) |
| vascular_v2 | 5,004 | 66.9% |
| ad_like_v1_amyloid_only | 1,277 | 60.8% — exploratory only, because it is not specific in PPMI |

**AD-like censoring:** 248 eligible participants carry a boundary substitution (148 Aβ42 at 1475.4, 100 p-tau at 8, fewer than 5 Aβ42 at 200). Positives rose only from 127 to 142, so the restored participants are mostly negative, as expected for high-Aβ42 people.

**Vascular components (all 5,019):** HTN 53.8%, DYSLIP 37.5%, DM 8.2%. BP was measured at BL for 98.4% (SC fallback 0.9%, missing 0.7%). 233 participants have no medication-log record; all are negative for `vascular_v1` by construction, which is why the medication-record sensitivity check exists.

**Construct validity (development set):**

- AD-like positives vs negatives: APOE ε4 carriers 47.4% vs 20.4%; mean age 67.3 vs 61.2; MoCA 26.6 vs 27.1 (cognition barely separates the groups at baseline).
- Vascular positives vs negatives: mean age 68.8 vs 64.2; median WM-hypointensity volume 2,072 vs 1,505 mm³.

**Cross-platform agreement (pre-2.1 run):** Elecsys and Lumipulse AD-like labels agree in 91.9% of 627 participants measured on both (κ ≈ 0.70).

---

## 5. Phase 3 methodology and run protocol (completed)

**Candidates (per label, binary relevance):**

1. L2 logistic regression
2. Elastic-net logistic regression
3. Random Forest
4. XGBoost
5. HistGradientBoosting

**Baselines:** prevalence; age + sex logistic regression. A missingness-only model is run as a leakage check.

**Validation:**

- Nested CV on the development set. The outer loop is the 5 frozen folds. The inner loop is Optuna with stratified 3-fold CV, minimising log loss with fixed budgets (25 trials for RF, XGBoost and HGB; 15 for the logistic regressions).
- Sigmoid calibration inside the training folds.
- Thresholds chosen inside the training folds.

**Selection (pre-registered in `docs/selection_protocol.md`):**

1. **Gates:** calibration slope 0.7–1.3; Brier better than prevalence; AUPRC better than age + sex; no failed folds.
2. **Ranking:** Brier Skill Score.
3. **Tie set:** models within 1 SE of the best.
4. **Tie-breakers, in order:** calibration slope, SHAP top-10 stability, strict-tier drop, simplicity.
5. A label where no model passes every gate is marked PROVISIONAL. PD-type was initially expected to be provisional because of near-perfect separation.

**Run order:**

| # | Command | Expected time |
|---|---|---|
| 1 | `python -m copath.phase3 cv` | 4–8 h (overnight; resumable) |
| 2 | `python -m copath.phase3 select --stage preliminary` | < 1 min |
| 3 | `python -m copath.phase3 robustness` | 30–90 min |
| 4 | `python -m copath.phase3 select --stage final` | < 1 min |
| 5 | `python -m copath.phase3 extras` | 1–4 h |
| 6 | `python -m copath.phase3 explain` | 5–30 min |
| — | **Human review of `reports/phase3/`** | — |
| 7 | `python -m copath.phase3 final --final` | 20–60 min; only after `configs/frozen/final_approval.yaml` exists (with `acknowledge_provisional` if needed). Runs once. |

---

## 6. Git state

| Commit | Content |
|---|---|
| `7fec318` | Component skeleton, audit, Phase 2/2.1 pipeline, Phase 3 harness |
| `d8bd487` | `.gitattributes` (nbstripout), `data/README.md`; Lumipulse GMM file untracked |
| `b8b23ce` | L2 LR candidate, never-flag censoring indicators, provisional lock, GMM hash traceability |
| `4b635cf` | Progress log updated through the Phase 2.1 re-freeze |
| `6bb881a` | Fold-safe degenerate-column handling (`DropDegenerateColumns`) and Phase 3 CV restart support (`reset-cv`) |
| `2dea454` | PD missingness audit and low-missingness re-run |
| `dc307f3` | Phase 3 pre-test development review; selection frozen for held-out evaluation |
| `3711f06` | Progress log: Phase 3 results, status, and wording rules |
| `db321b3` | Phase 3b: read-only held-out reporting; schema-aware privacy scan |
| `7852c00` | Phase 4A.0: frozen-bundle provenance packaging and explainer-spec verification |
| `0c67e55` | Phase 4A: frozen inference package, input/output JSON contracts v1.0 |
| `09c44c8` | Progress log updated for Phase 3b, Phase 4A.0, and Phase 4A completion |
| `dfa143e` | Frozen-model environment requirements lock added |

Repository staging, commits, and pushes are performed manually by the student.

**Excluded from Git:** participant-level PPMI data, generated research reports, local Phase 3 experiment outputs, out-of-fold predictions, final trained-model binaries, data-derived frozen thresholds, and final-evaluation approval/lock files. Safe README files and `.gitkeep` directory placeholders remain tracked where required.

The `feature/pd-copathology` branch was pushed for pull-request review on 16 Oct 2026.

---

## 7. Open items and reminders

- **Dissertation housekeeping:** update Figure 2 and Table 4 to remove the open-set layer from this component; fix the PACOS and Belnavis citation numbering.

- **Limitations to state:**
  - all three signals are proxy labels;
  - the vascular label reflects treated or measured risk and is affected by low blood pressure in PD;
  - AD cut-offs come from ADNI and assume similar sample handling;
  - only 336 healthy controls;
  - MRI covers about a third of participants;
  - no external validation.

- **Done:** Phase 3b reporting, Phase 4A.0 packaging, and Phase 4A inference + JSON contracts + CLI completed on 15 Oct 2026.

- **Next (team):** take `docs/input_schema_v1.json`, `docs/output_schema_v1.json`, `docs/output_schema.md`, and `docs/integration_open_questions.md` to the team architecture discussion.

- **Later, after the team architecture decision:** shared API, database persistence, frontend integration, and integration with the Clinical Predictive Safety Framework.

- **Student to complete:** feature descriptions in `docs/input_features_v1.md` (currently `"TBD"`) using public PPMI documentation.

- **Additional limitations to state:** input contract v1 checks presence and numeric type only. It does not currently enforce range or categorical-code validation; out-of-range or implausible inputs may therefore still be processed by the frozen models and may produce unreliable probabilities. Implausible-input detection belongs to the Safety Framework. Final-fit library versions are taken from the selected CV run record and confirmed by an exact scikit-learn match when the model files load. Near-duplicate inputs (`hy`/`NHY`, `age`/`age_at_visit`, two plasma p-tau217 assays) can share attribution in explanations.

---

## 8. Phase 3 results (development CV, 11–13 Oct; held-out test, 14 Oct 2026)

**Selected models** (frozen selection SHA-256 `07ff5edb…d090646`; local final-evaluation approval file dated 2026-10-14):

- PD-type: Random Forest
- AD-like: elastic-net logistic regression
- Vascular: Random Forest

All gates passed, so no label was provisional. The caveats in `docs/phase3_development_review.md` were recorded **before** test access.

| Signal | Metric | Development (out-of-fold) | Held-out test (95% bootstrap CI) |
|---|---|---:|---:|
| PD-type (n test 404) | AUROC | 0.9997 | 0.998 (0.995–1.000) |
| | BSS | 0.961 | 0.965 (0.923–0.999) |
| | Calibration slope | 1.30 (pooled; fold-wise unstable) | 1.15 (0.96–4.49) |
| AD-like (n test 255, ~28 positives) | AUROC | 0.801 | 0.799 (0.682–0.897) |
| | AUPRC (prevalence ≈ 0.11) | 0.434 | 0.457 (0.290–0.662) |
| | BSS | 0.185 | 0.206 (0.076–0.325) |
| | Calibration slope | 1.12 | 1.23 (0.74–1.90) |
| Vascular (n test 1,002) | AUROC | 0.711 | 0.731 (0.694–0.764) |
| | AUPRC (prevalence ≈ 0.28) | 0.475 | 0.473 (0.418–0.539) |
| | BSS | 0.110 | 0.122 (0.084–0.159) |
| | Calibration slope | 1.10 | 1.17 (0.96–1.39) |
| System | Macro BSS | 0.418 | 0.431 |
| Eligible for all three labels | Hamming loss / macro-F1 | 0.158 / 0.659 | 0.166 / 0.661 (n = 165) |

**Interpretation:**

- Held-out performance was consistent with the development estimates for all three signals, with no material evidence of overfitting or optimistic model selection.
- AD-like and vascular BSS confidence intervals exclude 0, so both signals perform better than predicting prevalence on unseen participants.
- The AD-like intervals are wide because of the small number of positives.
- The calibration-slope intervals for AD-like and vascular include 1. The PD-type slope interval is wide because of near-perfect separation.
- The vascular threshold favours recall (0.86) over precision (0.38).
- The interpretation caveats from the development review still apply.

Final models are saved in `models/final/v1.0/` (Git-ignored), and the final-evaluation lock is written. **No further model changes are allowed.**

**Wording rules for the dissertation and viva:**

- "Estimates an AD-like research proxy signal", not "diagnoses Alzheimer's disease".
- "Estimates treated or measured vascular risk-factor burden", not "detects vascular disease".
- "Held-out performance was consistent with development estimates", not "no overfitting occurred".
- "MRI features contributed to individual predictions, but ablation showed little unique incremental contribution", not "MRI is essential because SHAP is high".
- No new baseline was fitted on the held-out set after test access; held-out comparison with the prevalence reference is given by the Brier Skill Score.

---

## 9. Phase 3b / 4A results (15 Oct 2026)

**AD-like target-adjacent biomarkers.** Plasma p-tau217 (`ptau217_plasma`, `Lilly_ptau217p`, `Lilly_ptau217p_LLOD`) and `bd_tau_plasma` were classified `near_proxy` for `ad_like_v1` before training. They are in the primary tier and excluded from the strict tier. Development CV (selected elastic-net model): primary BSS 0.185, strict-tier BSS 0.121 (drop 0.064). That is still above the prevalence reference and the highest strict-tier BSS in the AD tie set (HGB 0.100, XGB 0.091, L2-LR 0.077). The strict tier was assessed in development CV only; the held-out test evaluated the primary model.

**Explanation convention (verified on development data, 15 Oct 2026):**

- PD-type and vascular (RF): TreeExplainer, tree-path-dependent, no background; probability space of the uncalibrated model. Base value + SHAP reproduces the model output (max difference 9.4e-16 and 1.3e-15).
- AD-like (elastic-net): contribution = coefficient × scaled value, base value = intercept, uncalibrated log-odds; equivalent to LinearExplainer with the full training background (max difference 4.4e-16; max |mean scaled background| 3.4e-15).
- SHAP explains the uncalibrated score, not the calibrated probability. A per-record additivity guard (1e-6) runs at inference.

**Inference package:**

- Loads only after the frozen bundle passes verification (file, feature-list, and lock hashes; exact scikit-learn version; version warnings treated as errors). No fallback.
- Output JSON v1.0: three calibrated research-proxy probabilities, up to 5 observed top features per signal, `cohort_in_training_scope`, completeness (overall, per modality, per signal), and a fixed disclaimer. No thresholds, class decisions, diagnoses, or TRUST/CAUTION/DEFER/OOD fields.
- Input contract v1.0: the frozen bundle's 300 raw pre-pipeline features; strict numeric validation; `--check-contracts --from-bundle` passes.
- Real-bundle smoke test (synthetic record `SYNTHETIC_DEMO_001` only): bundle verified, three signals produced, repeat runs identical, cohort scope correct (PD → true for all; Prodromal → false for PD-type only). The synthetic values are deliberately unrealistic, so its probabilities have no clinical meaning.
- 222 synthetic tests pass.