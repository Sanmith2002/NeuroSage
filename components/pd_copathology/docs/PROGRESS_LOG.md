# PD Co-Pathology Component — Progress Log

**Project:** Explainable Co-Pathology Signal Estimation in Parkinson's Disease Using PPMI Data (J26-DS-306)
**Branch / worktree:** `feature/pd-copathology` in `NeuroSage-pd-copathology`
**Status at 11 Oct 2026, 16:45:** Phase 2 is permanently frozen and Phase 3 training is ready to start.
**Companion document:** `docs/phase1_final_decisions_v1.md`, which holds the authoritative scientific decisions. This log records *what was done, in what order, and why*.
**Place in repo:** `components/pd_copathology/docs/PROGRESS_LOG.md`

---

## 1. Timeline

| # | Stage | What was done | Outcome |
|---|---|---|---|
| 0 | Planning | Read the proposal; defined scope, outputs, risks and a fast-track plan | The component outputs three research proxy probabilities plus SHAP explanations and metadata. OOD/TRUST–CAUTION–DEFER belongs to the Safety Framework |
| 1 | Environment | Git worktree, component skeleton, `.venv`, editable `copath` package, `.env` with `PPMI_DATA_ROOT`, nbstripout, data/model folders git-ignored | An isolated, reproducible workspace |
| 2 | Governance | Claude Code builds and tests on synthetic fixtures only; the student runs real-data commands; reports are aggregate only, counts below 5 suppressed, no participant IDs | No participant-level PPMI data has been shared with any AI tool |
| 3 | Audit v1 | Inventory of 9 archives/files, 131 tables, keys, event codes, long-format biomarkers and censored values | 35,903 IDs in the download, mostly remote-only arms; the old Colab merge was unreliable |
| 4 | Audit v1.1 | Baseline universe, domain-classification fixes, Medical_Conditions_Log | Universe is 5,019 in-clinic participants; the medical-conditions table holds category codes only |
| 5 | Audit v1.2 | Per-cohort overlap, label feasibility, medication audit, FreeSurfer white-matter check, CSF assay map | Medication log and BP usable for vascular; real white-matter hypointensity fields exist |
| 6 | Methods documents | Read PPMI methods for projects 125, 159 and 283 | 125/159 = Roche Elecsys (UPenn, same scale); 283 = Fujirebio Lumipulse; never pooled |
| 7 | Cut-off | Read Hansson et al. 2018 | AD-like cut-off = Elecsys p-tau181/Aβ42 > **0.025** (ADNI-derived, same lab and kits as PPMI) |
| 8 | Decisions frozen v1 | `phase1_final_decisions_v1.md` and the target cards | Labels, leakage tiers, features, split and selection protocol fixed |
| 9 | Phase 2 | Cohort builder, six label variants, machine-readable leakage matrix, frozen split, test-set guard | 5,019 × 385 table; balanced 4,015 / 1,004 split |
| 10 | Phase 2 review | Two independent reviews of the aggregate reports | Found the AD-like censoring bias and smaller issues (below) |
| 11 | Phase 2.1 | Fixes plus re-freeze (the only re-freeze allowed) | AD-like eligible 1,029 → 1,277; split rebuilt and locked |
| 12 | Phase 3 harness | Nested CV, two-stage selection, robustness, extras, SHAP, locked final evaluation | 113 synthetic tests pass; five candidate models |
| 13 | Git | Four local commits; nothing pushed | Checkpoint safe |

---

## 2. Key changes from the original proposal

| Area | Original | Final | Why |
|---|---|---|---|
| Model | Deep fusion with attention, open-set layer | Feature-level fusion; linear and tree models; open-set moved to the Safety Framework | Tabular data, sample size, defensibility |
| Data | Exploratory Colab merge | Rebuilt from the PPMI Curated Data Cut plus approved source tables | The old merge had duplicate keys, pooled assays and remote participants |
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
| Vascular masked people who could not reach the threshold | Claude Code interpretation note | Mask only when the unknown HTN component could change the result |
| Measured normal BP recorded as missing | Claude Code interpretation note | `htn_bp = 0` |
| SAA strongly tied to PD diagnosis | Phase 2 prevalence | SAA fields are near-proxies for PD-type |
| Limit flags could leak cohort | Supporter review | Flags set to `never` as predictors |
| Lumipulse GMM could silently re-fit | Claude Code traceability check | Hash recorded in the manifest; a normal run fails if the file is missing or changed |
| Smoke tests could write into the tracked registry | Supporter review | Smoke runs use scratch paths; the registry is checked unchanged |

---

## 4. Frozen dataset after Phase 2.1 (re-freeze, 11 Oct 2026)

**Universe:** 5,019 participants (PD 1,684, HC 336, Prodromal 2,935, SWEDD 64). Final table: 5,019 × 387. The drift guard passed.
**Split:** 4,015 development / 1,004 test (seed 20261011). Cohorts and primary labels are within 0.1 percentage points across development, test and all five folds. **The split is now permanently locked.**

**Primary labels:**

| Label | Eligible | Positive (%) | Development positives | Positives per fold |
|---|---|---|---|---|
| pd_type_v1 | 2,020 | 1,684 (83.4%) | 1,347 of 1,616 | ~270 |
| ad_like_v1 | 1,277 | 142 (11.1%) | 114 of 1,022 | 22–23 |
| vascular_v1 | 5,012 | 1,407 (28.1%) | 1,126 of 4,010 | ~225 |

**Sensitivity labels:**

| Label | Eligible | Positive (%) |
|---|---|---|
| pd_type_saa_v1 | 3,467 | 63.7% |
| ad_like_v1_cut028 | 1,277 | 8.0% |
| ad_like_v1_cut022 | 1,277 | 15.2% |
| ad_like_v1_greyzone | 1,245 | 10.0% |
| ad_like_v1_uncensored | 1,029 | 12.3% |
| ad_like_lumipulse_v1 | 1,919 | 21.8% (GMM threshold Aβ42/40 = 0.0745, fitted on development data only) |
| vascular_v2 | 5,004 | 66.9% |
| ad_like_v1_amyloid_only | 1,277 | 60.8% — exploratory only, because it is not specific in PPMI |

**AD-like censoring:** 248 eligible participants carry a boundary substitution (148 Aβ42 at 1475.4, 100 p-tau at 8, fewer than 5 Aβ42 at 200). Positives rose only from 127 to 142, so the restored participants are mostly negative, as expected for high-Aβ42 people.

**Vascular components (all 5,019):** HTN 53.8%, DYSLIP 37.5%, DM 8.2%. BP was measured at BL for 98.4% (SC fallback 0.9%, missing 0.7%). 233 participants have no medication-log record; all are negative for vascular_v1 by construction, which is why the medication-record sensitivity check exists.

**Construct validity (development set):**
- AD-like positives vs negatives: APOE ε4 carriers 47.4% vs 20.4%; mean age 67.3 vs 61.2; MoCA 26.6 vs 27.1 (cognition barely separates the groups at baseline).
- Vascular positives vs negatives: mean age 68.8 vs 64.2; median WM-hypointensity volume 2,072 vs 1,505 mm³.

**Cross-platform agreement (pre-2.1 run):** Elecsys and Lumipulse AD-like labels agree in 91.9% of 627 participants measured on both (κ ≈ 0.70).

---

## 5. Phase 3 plan (ready to run)

**Candidates (per label, binary relevance):**
1. L2 logistic regression
2. Elastic-net logistic regression
3. Random Forest
4. XGBoost
5. HistGradientBoosting

**Baselines:** prevalence; age + sex logistic regression. A missingness-only model is run as a leakage check.

**Validation:**
- Nested CV on the development set. The outer loop is the 5 frozen folds. The inner loop is Optuna with stratified 3-fold CV, minimising log loss with equal budgets (25 trials; 15 for the logistic regressions).
- Sigmoid calibration inside the training folds.
- Thresholds chosen inside the training folds.

**Selection (pre-registered in `docs/selection_protocol.md`):**
1. **Gates:** calibration slope 0.7–1.3; Brier better than prevalence; AUPRC better than age + sex; no failed folds.
2. **Ranking:** Brier Skill Score.
3. **Tie set:** models within 1 SE of the best.
4. **Tie-breakers, in order:** calibration slope, SHAP top-10 stability, strict-tier drop, simplicity.
5. A label where no model passes every gate is marked PROVISIONAL. PD-type is expected to be provisional because of near-perfect separation.

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
| `769c789` | Component skeleton, audit, Phase 2/2.1 pipeline, Phase 3 harness |
| `602a806` | `.gitattributes` (nbstripout), `data/README.md`; Lumipulse GMM file untracked |
| `48aa388` | L2 LR candidate, never-flag censoring indicators, provisional lock, GMM hash traceability |

- **Not tracked:** `data/`, `reports/`, `models/final/`, `configs/frozen/lumipulse_gmm_v*.json`, approval and lock files.
- **Not pushed.** Before any push, confirm with the supervisor what PPMI-derived material may be shared.

---

## 7. Open items and reminders
- **Supervisor:** send `phase1_final_decisions_v1.md` and this log (vascular construct change, AD cut-off, censoring fix).
- **Dissertation housekeeping:** update Figure 2 and Table 4 (remove the open-set layer from this component); fix the PACOS and Belnavis citation numbering.
- **Limitations to state:**
  - all three signals are proxy labels;
  - the vascular label reflects treated or measured risk and is affected by low blood pressure in PD;
  - AD cut-offs come from ADNI and assume similar sample handling;
  - only 336 healthy controls;
  - MRI covers about a third of participants;
  - no external validation.
- **After the deadline:** FastAPI inference endpoint, prototype view, and the JSON contract with the Safety Framework.
