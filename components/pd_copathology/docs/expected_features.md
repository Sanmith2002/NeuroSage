# Expected features per label

Written on **11 October 2026, before any model was trained** (decisions
document, section 5.7). The SHAP results of the selected models are compared
against this table by `python -m copath.phase3 explain`
(`reports/phase3/shap_plausibility.csv`). The machine-readable copy is
`configs/expected_features.yaml`; the two files must say the same thing.

The table is a plausibility check, not a test a model must pass. An expected
feature that ranks low, or an unexpected feature that ranks high, is reported
and discussed; it never changes the selection.

| Label | Expected to matter | Why |
|---|---|---|
| AD-like (`ad_like_v1`) | APOE e4 | strongest common genetic risk factor for amyloid pathology |
| | age | amyloid positivity rises with age |
| | memory / cognition | amyloid and tau pathology affect memory first; the effect at baseline is expected to be small |
| | plasma pTau217 (primary tier only) | blood marker of the same pathology; a near-proxy, removed in the strict tier |
| | NfL / GFAP | neurodegeneration and astroglial markers that rise with AD pathology |
| Vascular (`vascular_v1`) | age | vascular risk factors accumulate with age |
| | BMI | obesity is linked to hypertension, diabetes and dyslipidaemia |
| | WM hypointensities | T1 proxy of small-vessel lesion burden (measured in about a third of participants) |
| | sex | treated vascular risk differs by sex |
| PD-type (`pd_type_v1`) | UPSIT | hyposmia is an early, common feature of PD |
| | RBD questionnaire | REM sleep behaviour disorder is a prodromal marker |
| | DAT / UPDRS (primary tier only) | dopaminergic deficit and motor signs; near-proxies, removed in the strict tier |
| | autonomic (SCOPA-AUT) | autonomic dysfunction is common in PD |
| | non-motor clinical scales | mood, sleep and other non-motor symptoms |

Known limits of this check:

- SHAP describes what the model uses, not what causes the label.
- Correlated features share importance, so one expected feature may be
  represented by a neighbour (for example another memory score).
- For the vascular label, blood pressure and every drug flag define the label
  and are never features, so the model can only use indirect correlates.
