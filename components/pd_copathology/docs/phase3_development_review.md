# Phase 3 Development Review (before the final test)

**Date:** 13 October 2026
**Status:** Development-set results reviewed and selection approved. Written **before** the one-time held-out test evaluation, so none of these points were influenced by test results.
**Selection file:** `configs/frozen/selected_models_v1.yaml` (SHA-256 `07ff5edb0b0aafcacf5b8e34551ef7266fc909809ca944256714e3c61d090646`)
**Reviewers:** the student, plus two independent AI-assisted reviews whose conclusions agreed.

---

## 1. Selected models (correct under the frozen protocol)

| Signal | Model | Mean fold BSS | AUROC | AUPRC | Selection path |
|---|---|---|---|---|---|
| PD-type (`pd_type_v1`) | Random Forest | 0.961 | 0.9997 | 0.9999 | The only candidate passing the calibration gate (pooled slope 1.295); tie set of one |
| AD-like (`ad_like_v1`) | Elastic-net LR | 0.185 | 0.801 | 0.434 | Tie set {enet, XGB, L2, HGB}; (a) calibration kept {enet, HGB}; (b) SHAP stability kept enet. L2 had higher Jaccard but was already eliminated by (a) |
| Vascular (`vascular_v1`) | Random Forest | 0.110 | 0.711 | 0.475 | Tie set {HGB, XGB, RF}; all within the calibration tolerance; SHAP stability chose RF (0.63 vs 0.45/0.47) |

All three labels passed every gate, so no label is provisional. System macro BSS is 0.418. For the 642 participants eligible for all three labels: Hamming loss 0.158, macro-F1 0.659.

## 2. Interpretation caveats (recorded before the test)

1. **The primary PD-type result is near the ceiling and must not be presented as the main scientific finding.** A missingness-only model reaches AUROC 0.954, and several features differ strongly in availability between PD and HC (for example `MSEADLG` by 58 percentage points). The scientifically informative PD evidence is:
   - **strict tier:** BSS 0.768, AUROC 0.976;
   - **strict tier restricted to features with availability gaps under 10 points:** BSS 0.760, so availability patterns do not explain the strict result;
   - **SAA biological label:** BSS 0.553, AUROC 0.923.
2. **Calibration wording.** All selected models satisfied the pre-specified **pooled** calibration criterion. For PD-type, fold-wise calibration slopes were unstable (mean 15.3, SD 20.2) because near-perfect separation makes slope estimation unreliable. Do not describe PD-type as simply "well calibrated". Vascular (slope 1.10) and AD-like (1.12) calibration is reasonable.
3. **AD-like performance and stability are moderate.** Fold-level BSS varies considerably (SD 0.14) and the SHAP top-10 Jaccard is 0.53, both consistent with the small number of positives (114 in development). Describe the result as a meaningful improvement over baselines, not as highly stable.
4. **SHAP attribution is not modality necessity.** SHAP measures which features a model *uses*; ablation measures the *unique incremental contribution* of a modality. For AD-like, MRI receives about 22% of summed mean |SHAP|, but removing MRI changes BSS by only −0.002, because correlated modalities compensate. Claims about which modalities are necessary rely on ablation.
5. **Duplicate features are grouped in interpretation, not removed.** The pairs `age`/`age_at_visit` and `hy`/`NHY` split their SHAP credit. Removing them after selection would be post-hoc, so they are kept in the frozen pipeline and grouped in figures and discussion.
6. **CSF α-synuclein (`asyn`) is the third most important AD-like feature.** It is described as an associated predictive feature (CSF α-synuclein is known to correlate with CSF tau), not as evidence that it causes the AD-like signal.
7. **`MSEADLG` (Schwab & England ADL)** behaves like a PD near-proxy in hindsight (available for 99.9% of PD vs 41.6% of HC). It was not reclassified after seeing results; the low-missingness run shows it does not drive the strict result.

## 3. Key development findings, by research question

| RQ | Finding |
|---|---|
| 1. Beats baselines? | Yes for all three signals. AD-like AUPRC 0.43 vs 0.19 (age + sex); vascular 0.48 vs 0.40 |
| 2. Best strategy? | Per-signal model families (binary relevance): RF / elastic-net / RF |
| 3. Does fusion add value? | AD-like: yes; clinical + demographics alone drops BSS from 0.185 to 0.029. Vascular: no; clinical + demographics alone loses only 0.003. PD-type: motor features dominate |
| 4. Which modalities? (ablation) | AD-like: biofluid (−0.097), genetics (−0.050). Vascular: demographics (−0.056). PD-type: motor (−0.159) |
| 5. Calibrated? | Pooled gate met by all; sigmoid ≥ isotonic for the small AD-like label; PD fold-wise slopes unstable (caveat 2) |
| 6. Robust to label definition? | AD-like cut-offs 0.022/0.028 and the uncensored variant: BSS 0.16–0.23; Lumipulse AUROC 0.85, BSS 0.34; vascular_v2 BSS 0.14; medication-record restriction BSS 0.107 vs 0.110 |
| 7. Robust to leakage control? | AD-like strict (plasma pTau217 removed): BSS 0.121, still well above age + sex (0.034). PD strict and low-missingness results: see caveat 1 |
| 8. Explanations stable and plausible? | AD-like: APOE ε4, plasma pTau217, age, ventricular volume, GFAP/NfL. Vascular: BMI, age, sex. PD-type: H&Y, UPDRS III, DAT putamen. Top-10 Jaccard: PD 0.88, vascular 0.63, AD 0.53 |

## 4. Expectation for the held-out test
The AD-like test set has about 28 positives, so its AUPRC, sensitivity and confidence intervals may move noticeably from the development estimates. Whatever the test shows will be reported as it is. No model, feature, threshold or label will be changed after the test.
