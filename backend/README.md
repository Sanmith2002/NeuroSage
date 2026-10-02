# NeuroSage · AD co-pathology backend

**Component:** IT23174276, *Explainable AI for Alzheimer's, Lewy Body & Vascular Co-Pathology Detection* (J26-DS-306).
**Research prototype — not for clinical use.**

A FastAPI service that loads the already-trained Stage 4 models and serves calibrated multi-label predictions
(AD / LBD / VD), SHAP explanations, MRI-based clinical-AD and biomarker-AD estimates with Grad-CAM, and the
reliability signals consumed by the team's Safety component. Output follows the shared
`neurosage.multilabel/v1` schema (mirrored in [`frontend/lib/ad/types.ts`](../frontend/lib/ad/types.ts)).

## Architecture

```
POST /v1/clinical/predict ─► features.py (Stage 2a port) ─► clinical.py ─► schema_output.py ─► shared document
                                                              │ 5 fold models → Platt → threshold
                                                              │ per-fold calibrated SD, margin
                                                              │ TreeSHAP (mean of folds)
                                                              │ OOD / familiarity / sufficiency
POST /v1/mri/analyze (SSE) ─► mri/preprocess.py ─► mri/predict.py ─► mri/render.py ─► MriResult
                               dcm2niix → HD-BET → N4      cached torch nets   Grad-CAM + QC PNG
                               → MNI affine → crop → z      (built once)        (in memory, 30 min)
                               → 2 mm float16
POST /v1/assess ─► clinical document + MRI labels + modality agreement
```

| Module | Role |
|---|---|
| `app/registry.py` | Loads bundles once (RF lazily on first use if XGB is active); builds torch nets per fold at startup. |
| `app/features.py` | Pure, deterministic port of the 66 NACC participant features. Order always comes from `bundle["features"]`. |
| `app/clinical.py` | Probabilities (same arithmetic as `model_defs.predict_nacc`, single pass), fold SD, SHAP, reliability signals. |
| `app/mri/*` | Exact port of Stage 2b + 3 preprocessing (`PREPROC_SPEC`, returned by `/v1/models`), prediction, Grad-CAM. |
| `app/schema_output.py` | Builds the shared multi-label document. `clinicalHarmRisk` stays `null` (owned by the Safety component). |
| `app/form_spec.py` | Field definitions for the live form and feature display names. |

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | `{status, models_loaded, version}` |
| GET | `/v1/models` | Model card, loaded bundles, thresholds, preprocessing spec, caveats |
| GET | `/v1/form-spec` | Form definition (labels, units, ranges, options, high-impact flags) |
| POST | `/v1/clinical/features` | Debug: the engineered 66-feature vector + harmonisation log |
| POST | `/v1/clinical/predict` | Main clinical endpoint → shared document |
| POST | `/v1/mri/analyze` | Multipart (`file`, `fields` JSON) → Server-Sent Events: `stage`, then `result` or `error` |
| GET | `/v1/mri/artifacts/{token}.png` | Grad-CAM / QC image (in memory, expires after 30 min) |
| GET | `/v1/mri/demo-cases` | Preprocessed demo volumes in `DEMO_DIR` (empty if unset) |
| POST | `/v1/mri/demo-cases/{id}/predict` | Instant MRI prediction on a demo volume |
| POST | `/v1/assess` | `{clinical, mri_result?}` → one merged document with modality agreement |

## Model files (never committed)

Put these in the repo-root [`models/`](../models) folder (gitignored); `MODELS_DIR` overrides the location.

| From | Files |
|---|---|
| `S4_best_models.zip` | `nacc_multilabel_best.joblib`, `adni_ad_clin_best.joblib`, `adni_ad_bio_best.joblib`, `adni_ad_bio_fusion.joblib` (optional), `model_defs.py` |
| `S4c_app_artifacts.zip` | `nacc_multilabel_xgb.joblib`, `feature_stats.json`, `ood_nacc.joblib`, `model_card.json` |

`parity_fixture.json` goes in `tests/private/` (gitignored, local only). Without the S4c files the service still
runs on the RF bundle; the distribution-conformity and domain-familiarity signals then report `null` with a warning.

## Run locally

Windows (works from PowerShell even when `.ps1` scripts are blocked):

```bash
backend\setup-service.cmd     # once: Python 3.11 + packages into backend/.python and backend/.venv
backend\run-service.cmd       # starts http://127.0.0.1:8000 (API docs at /docs)
```

macOS / Linux:

```bash
cd backend
UV_PYTHON_INSTALL_DIR=.python uv venv .venv --python 3.11 --python-preference only-managed
uv pip install --python .venv torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu
uv pip install --python .venv --no-deps monai==1.6.1
uv pip install --python .venv -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --port 8000
```

Then put `NEXT_PUBLIC_AD_API_URL=http://127.0.0.1:8000` in `frontend/.env.local` and run `npm run dev` in
`frontend/`. Everything runs on this computer's CPU. MRI upload needs `dcm2niix` (for DICOM zips) and HD-BET (installed by
`requirements.txt`; it downloads its weights on first use).

### Settings (environment or `backend/.env`)

| Variable | Default | Meaning |
|---|---|---|
| `NACC_MODEL` | `auto` | `auto` uses XGBoost if `nacc_multilabel_xgb.joblib` exists, else RF. `rf` / `xgb` force one. |
| `LOAD_MRI` | `true` | `false` to skip the MRI models (faster startup, clinical only). |
| `LOAD_BIO_FUSION` | `false` | Also load the 330 MB MedicalNet ad_bio fusion bundle. |
| `CORS_ORIGINS` | localhost:3000 | Comma-separated frontend origins. |
| `DEMO_DIR` | unset | Folder of `<id>.npy` (80×96×80) + `<id>.json` (`description`, `fields`). |
| `HD_BET_DEVICE` | `cpu` | `cuda` if a GPU is available. |

## Tests

```bash
cd backend
.venv/Scripts/python -m pytest -q
```

| Test | Checks |
|---|---|
| `test_features.py` | Spec §10 cases (a)–(h): single visit, polyfit slope, short span → NaN, MoCA crosswalk, untestable last visit, vascular remote, race null, bundle order. |
| `test_parity.py` | Fixture rows → `predict_nacc` within 1e-6 for RF and XGB (skipped without the private fixture); the service's single-pass path equals `predict_nacc`. |
| `test_api.py` | 422 on out-of-range input, minimal and full requests, schema shape, exactly 3 NACC labels, disclaimer, `/v1/assess` merge, API key. |
| `test_mri_smoke.py` | MNI template through steps 3–10 (Dice ≥ 0.99, shape 80×96×80, finite), crop box = training, float16 round-trip, cached nets = `predict_adni`, Grad-CAM. |

MRI parity against `13_adni_test_predictions.csv` (spec §10) is a manual Colab check on 3 ADNI test scans.

## Measured performance (Windows laptop, CPU)

| Step | Time |
|---|---|
| Startup, RF + MRI bundles | ~14 s (RF unpickle ~5–7 s) |
| Clinical predict, RF, `explain=false` | ~0.7 s |
| Clinical predict, RF + SHAP, uncached | ~6–8 s (cached by input hash afterwards) |
| MRI analysis from raw NIfTI | ~4 min first run incl. HD-BET weight download; HD-BET dominates |

XGBoost + SHAP (< 5 s target) is not measured yet: `nacc_multilabel_xgb.joblib` comes from S4c.

## Known limitations

- The clinical model estimates **autopsy neuropathology** in NACC participants who later came to autopsy. It may not
  transfer to living memory-clinic populations, and it is not a diagnosis.
- Slopes need ≥ 3 visits over ≥ 1 year. Single-visit predictions are less accurate than the reported metrics.
- `ad_bio` from structural MRI is weak (image-only test AUROC ≈ 0.59–0.69), so the selected ad_bio model is tabular only.
- Open-set / OOD detection is **experimental** (AUROC ≈ 0.5). It is never used to reassure.
- CSF values are assay-specific and are not harmonised.
- Grad-CAM shows model attention (diffuse, ventricular / periventricular, some edge activation), not a lesion map.
- Prediction certainty, sufficiency weights and the provisional TRUST / CAUTION / DEFER rule are placeholders until
  the Safety component (IT23147850) defines its own.
- External validation on OASIS-3 is pending.

## Data-use compliance (NACC / ADNI)

No dataset rows, MRI volumes or the parity fixture are committed. Uploaded scans and patient inputs are
written only to a per-request temp directory that is deleted in a `finally:` block, and are never logged. The service runs only on this computer.
