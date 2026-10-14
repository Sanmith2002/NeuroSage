# Explainable Co-Pathology Signal Estimation in Parkinson's Disease Using PPMI Data

Individual research component of NeuroSage. It lives entirely under
`components/pd_copathology/` and is independent of the frontend code in the
rest of the repository.

## Purpose

Estimate, for a participant with Parkinson's disease, how strongly their
multimodal profile resembles three co-pathology patterns, and explain which
features drive each estimate.

## Outputs

Three probabilities per participant:

| Signal          | Meaning                                         |
| --------------- | ----------------------------------------------- |
| `pd_type`       | PD-type probability                             |
| `ad_like`       | AD-like cognitive/biomarker probability         |
| `vascular_risk` | Vascular-risk probability                       |

These are **research proxy signals, not clinical diagnoses**. The targets are
constructed from PPMI variables (see `targets/` and `docs/leakage_matrix.md`)
and must not be read as a diagnosis of Alzheimer's disease, vascular disease,
or a PD subtype.

## Approach

- **Inputs:** multimodal PPMI data (the exact modalities and tables are fixed
  during the dataset audit).
- **Fusion:** feature-level multimodal fusion - modalities are combined into
  one feature table before modelling.
- **Explainability:** SHAP feature attributions for each of the three signals.
- **Evaluation and validation:** a major research work package in its own
  right, not a final step. The protocol is in `docs/selection_protocol.md`.

## Relationship to the rest of NeuroSage

The output of this component (see `docs/output_schema.md`) will later feed the
Clinical Predictive Safety Framework.

Out-of-distribution detection and TRUST / CAUTION / DEFER decisions are **not
implemented inside this component**. They belong to the downstream Safety
Framework.

## Current phase

**Phase 1 - Dataset audit, cohort definition, target construction, modelling,
evaluation, validation and final-model selection.**

Frontend and database development will happen later, after the final model and
the inference contract are frozen.

## Data protection

**PPMI participant-level data must never be committed to Git.**

Raw PPMI data are stored outside the repository and read, read-only, from the
directory named by `PPMI_DATA_ROOT` (see `.env.example`). `data/raw/` is
intentionally unused and stays empty.

Everything under `data/raw/`, `data/interim/`, `data/processed/` and
`data/splits/` is ignored by the repository `.gitignore`, as is
`models/final/`. Notebook outputs are stripped on commit by `nbstripout`. See
`data/README.md` before placing any file in this component, and check
`git status` before every commit.

## Layout

```
configs/      paths, cohort, feature sets, model and experiment configs
targets/      versioned target definitions and target cards
data/         local-only PPMI data (ignored by Git)
notebooks/    numbered analysis notebooks
src/copath/   Python package
experiments/  experiment registry
models/       trained-model location (no binaries tracked yet)
reports/      audit, evaluation, figures, explainability outputs
tests/        pytest tests
docs/         selection protocol, leakage matrix, output schema, decisions log
```

## Setup

Requires Python 3.11 or newer. From `components/pd_copathology/`:

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows; use `source .venv/bin/activate` elsewhere
pip install -e ".[dev]"
nbstripout --install          # once per clone: strips notebook outputs on commit
pytest
```

## Phase 1 dataset audit

The audit reads the PPMI download archives in place (read-only, nothing is
extracted into the repository), profiles each table in chunks and writes
aggregate, privacy-safe reports. It does not merge tables or build targets.

```bash
python -m copath.data.audit                              # uses PPMI_DATA_ROOT from .env
python -m copath.data.audit --skip-archive "Imaging*.zip"  # skip a large archive
python -m copath.data.audit --help
```

- Settings: `configs/audit.yaml` (suppression threshold, chunk size, archives
  to skip, reference-only files).
- Reviewed table decisions: `configs/domain_overrides.yaml` (analytic
  universes, excluded and diagnosis tables, modality overrides, known false
  matches, documentation tables to print, baseline-feasibility sources).
- Documentation tables that pass an identifier check are printed in full to
  `reports/audit/reference/`.
- Phase 1.5 feasibility outputs (baseline universe, by cohort) are built in
  `src/copath/data/phase15.py`: `bl_modality_overlap_by_cohort.csv`,
  `bl_label_feasibility_by_cohort.csv`, `medication_vascular_audit.md`,
  `fs7_aseg_wm_check.md` and the CSF assay maps under `reference/`. Drug-name
  lists for the medication audit are in `configs/drug_classes.yaml`. None of
  these define a label.
- Aggregate outputs: `reports/audit/` and `reports/figures/`. Counts below 5
  are written as `<5`. After writing, the run scans its own reports for every
  participant identifier it saw and deletes them if one is found.
- The only participant-level output is
  `data/interim/audit_participant_modality_availability.parquet`, which is
  ignored by Git.
- Tests use a synthetic download built by `tests/fixtures/build_fixtures.py`;
  they never read PPMI data.

## Phase 2: cohort, labels and frozen split

```bash
python -m copath.phase2
```

Builds the analytic baseline table from the Curated Data Cut plus the approved
sources, the labels defined by the cards in `targets/`, and the frozen 80/20
split with five development folds. No model is trained. The Phase 2.1 corrections
(limit flags, vascular masking, two tiers, one re-freeze) are in `docs/decisions_log.md`.

- Specification: `docs/phase1_final_decisions_v1.md`; implementation notes in
  `docs/decisions_log.md`.
- Participant-level outputs (git-ignored): `data/processed/analytic_bl_v1.parquet`,
  `analytic_bl_v1_dev.parquet`, `data/splits/`.
- Aggregate reports: `reports/phase2/`.
- Leakage control: `configs/leakage_matrix.csv` is authoritative. After editing
  it run `python -m copath.features.leakage_guard` to regenerate
  `docs/leakage_matrix.md` and `configs/feature_sets/`.
- Training code loads data with `copath.data.split.load_analytic`, which
  returns development rows only unless final-evaluation mode is switched on.

## Phase 3: training, selection and evaluation

```bash
python -m copath.phase3 cv                          # 1. baselines + candidates, primary tier, nested CV (long)
python -m copath.phase3 select --stage preliminary  # 2. gates, Brier Skill Score ranking, 1-SE tie sets
python -m copath.phase3 robustness                  # 3. strict tier, 3 seeds, SHAP stability (tie-set models)
python -m copath.phase3 select --stage final        # 4. tie-breakers; freezes configs/frozen/selected_models_v1.yaml
python -m copath.phase3 extras                      # 5. ablation, sensitivity labels, calibration comparison
python -m copath.phase3 explain                     # 6. SHAP reports for the selected models
# ---- human review of reports/phase3 ----
python -m copath.phase3 final --final               # 7. single test-set evaluation (locked, see below)
python -m copath.phase3 report-final               # read-only held-out reports/figures from the predictions `final` saved
python -m copath.phase3 missingness-audit           # pd_type_v1: PD vs HC availability per feature + low-gap-features run
python -m copath.phase3 reset-cv --confirm          # restart cv from scratch (removes ONLY the cv outputs; see below)
```

- Protocol: `docs/selection_protocol.md` (written before any real run); expected
  features: `docs/expected_features.md`; settings: `configs/phase3.yaml`.
- Every command except an approved `final` loads development rows only. A model
  sees the eligible (non-masked) participants of its label and the features of
  `configs/feature_sets/<label>_<tier>.yaml`.
- Runs are recorded in `experiments/registry.csv` (one row per run) with details
  in `experiments/phase3/`. A restarted command skips finished runs. `cv` accepts
  `--label` and `--model`.
- Every model pipeline starts with a fold-safe step that drops columns with fewer than two distinct non-missing
  values in the training rows; the dropped names are in `reports/phase3/dropped_features.csv`. A run in which every
  outer fold fails is registered as `failed` without metrics, and `cv` exits with code 4 after finishing the others.
- `reset-cv --confirm` removes the cv registry rows, the cv run details, `data/processed/oof/` and the cv report files;
  it leaves Phase 2 outputs, the split and the Lumipulse threshold alone and refuses once a final run or lock file
  exists or when robustness, extras, selection or SHAP results derived from the cv runs exist.
- Participant-level outputs (git-ignored): `data/processed/oof/` (out-of-fold
  predictions), `data/processed/shap/`, `data/processed/final/`, `models/final/`.
- Aggregate reports and figures: `reports/phase3/`, scanned for identifiers
  after every command.
- **`final` is locked.** It runs only with `--final` and a file
  `configs/frozen/final_approval.yaml` that the reviewer writes by hand:

  ```yaml
  approved: true
  reviewer: <name>
  date: <YYYY-MM-DD>
  selected_models_sha256: <printed by `select --stage final` and in reports/phase3/selection_final.md>
  ```

  If the selection is PROVISIONAL for any label (no candidate passed every gate), the file must also contain
  `acknowledge_provisional: [<label ids>]` listing every provisional label, otherwise `final` stays locked.
  After it has run once a lock file blocks any second run.
- Once a Phase 3 run exists, `python -m copath.phase2 --refreeze` refuses to run.
- `configs/frozen/lumipulse_gmm_v1.json` is derived from participant data and is not tracked in Git. Its SHA-256 is
  recorded in `reports/phase2/phase2_manifest.json`; a normal Phase 2 run verifies it and never regenerates it
  (a missing file or hash stops the run and asks for `--refreeze`).
