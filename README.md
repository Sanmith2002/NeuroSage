# NeuroSage

Explainable, safety-aware clinical AI research platform. The AD co-pathology component (IT23174276) runs the
trained models locally on this computer's CPU; there is no static or mock patient data.

**Research prototype — not for clinical use.**

## Project layout

```
NeuroSage/
├── frontend/                 web app (Next.js API on Vite via vinext)
│   ├── app/                  routes
│   ├── components/platform/  shared shell, dashboard, workflow page, status badges
│   ├── components/ad/        AD co-pathology UI: patient form, result pages
│   ├── components/ui/        UI primitives (shadcn / Base UI)
│   ├── lib/assessment.ts     shared view types and assessment stages
│   └── lib/ad/               AD client: API calls, response types, case store
├── backend/                  AD co-pathology API (FastAPI) that runs the models
│   ├── app/                  feature engineering, inference, SHAP, MRI pipeline
│   ├── tests/                backend tests
│   ├── setup-service.cmd     one-time Python setup
│   └── run-service.cmd       starts http://127.0.0.1:8000
└── models/                   trained model files (gitignored, never committed)
```

## Prerequisites

- [Node.js](https://nodejs.org/) 22.13.0 or newer
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (installs Python 3.11 for the backend)
- The model files in `models/`: `model_defs.py`, `nacc_multilabel_best.joblib`, `adni_ad_clin_best.joblib`,
  `adni_ad_bio_best.joblib` (and optionally `adni_ad_bio_fusion.joblib`)

## Run locally (Windows)

Clone the repository first:

```bash
git clone https://github.com/Sanmith2002/NeuroSage.git
cd NeuroSage
```

1. **Backend, once:** `backend\setup-service.cmd` (installs Python 3.11 and all packages into `backend\`;
   ~5–10 min).
2. **Backend, each time:** `backend\run-service.cmd`. Leave it running. When it prints
   `Application startup complete`, <http://127.0.0.1:8000/health> should say `"status":"ok"` and list the loaded
   models; <http://127.0.0.1:8000/docs> is the interactive API.
3. **Frontend, once:** `cd frontend`, `npm install`, then copy `.env.example` to `.env.local`
   (it already points at `http://127.0.0.1:8000`).
4. **Frontend, each time:** in a second terminal, `cd frontend` and `npm run dev`, then open
   <http://localhost:3000>. If PowerShell blocks scripts, use `npm.cmd install` / `npm.cmd run dev`.

## Running an assessment

New assessment → enter a patient (or *Load example patient*) → *Run assessment*, then step through the stages:

| Stage | What you see |
|---|---|
| Patient | Entered visits and modality status (clinical, APOE, CSF, MRI) |
| Harmonization | MoCA → MMSE crosswalk and derived longitudinal features (slopes, deltas, follow-up) |
| AI predictions | AD / LBD / VD probabilities with thresholds and fold-SD whiskers, SHAP chart per label, MRI panel |
| Safety gate | The component's reliability signals and the provisional status |
| Clinical report | Template summary, *Download JSON* (the shared `neurosage.multilabel/v1` document), *About the model* |

The dashboard lists the patients assessed in the current browser tab (`sessionStorage`; nothing is stored on the
server). The Parkinson's component is not connected yet, and the safety status is a provisional placeholder until
the Safety component (IT23147850) is integrated.

## Routes

- `/` - dashboard
- `/assessment/new` - enter a patient and run the models
- `/assessment/:caseId/:stage` - patient, harmonization, predictions, safety and report stages
- `/workflow` - workflow overview

## Checks

```bash
cd frontend
npm run lint
npm run build
```

Backend tests (from `backend\`): `.venv\Scripts\python.exe -m pytest -q`. See [backend/README.md](backend/README.md)
for the API, settings and model details.
