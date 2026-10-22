# Windows PowerShell quickstart

## Available now — Phase 1 verification only

```powershell
Set-Location 'C:\Users\User\Desktop\NeuroSage-Workspace\safira-demo'
git branch --show-current
git rev-parse HEAD
git merge-base --is-ancestor 4f31886f12f6df09cd3dc688b48fb9e20329a3ee HEAD
git status --short
```

Expected branch `demo/safira-fyp-showcase`; initial HEAD exact closure. Phase 1 has uncommitted new files only under `demo/`. Do not create another worktree over this directory or reset it.

The environment was successfully created as follows; repeat only when recreating it:

```powershell
uv venv .venv --python 3.11
uv pip install --python .venv/Scripts/python.exe -e . pytest==9.1.1
.\.venv\Scripts\python.exe -c "import safira, sklearn; print(safira.__file__); print(sklearn.__version__)"
.\.venv\Scripts\python.exe -m pytest -q tests/test_runtime_records.py tests/test_runtime_admission.py tests/test_runtime_signals.py tests/test_runtime_scoring.py tests/test_runtime_policy.py tests/test_runtime_acceptance.py tests/test_runtime_privacy.py tests/test_runtime_boundaries.py
git diff --check
```

Phase 1 observed 45 passed, no failures/skips. This does not rerun or replace historical 839-test evidence. Editable install imports `src/safira` from this checkout; if it resolves elsewhere, stop and repair the installation rather than changing `sys.path`. `.venv` is ignored and not shared with the original worktree. See environment snapshot for resolved versions; initial install command alone does not pin transitive dependencies.

## Planned commands — only after Batch A/B create the referenced files

The commands below are the required interface for Phase 2 implementation. They are **not runnable application instructions today**. A01/A06 must deliver backend lock/package and entry point; B01 must deliver frontend scripts/lock. Resolve supported exact Python/Node and package versions, then update this guide to match actual verified commands.

```powershell
Set-Location 'C:\Users\User\Desktop\NeuroSage-Workspace\safira-demo'
# Create a fresh demo .venv with the interpreter version recorded in the final lock evidence.
uv pip sync --python .venv/Scripts/python.exe --require-hashes demo/backend/requirements.lock
uv pip install --python .venv/Scripts/python.exe --no-deps -e . -e demo/backend
.\.venv\Scripts\python.exe -m pytest -q demo/backend/tests
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --app-dir demo/backend --host 127.0.0.1 --port 8000 --workers 1
```

Backend package must expose `app.main:create_app`; it validates loopback settings, starts a hidden prepared subprocess and stays not-ready until controlled fixtures are frozen. No reload in viva mode. Requirements lock must include all framework transitive dependencies (including sklearn 1.7.1) and test dependencies so `--no-deps` editable installs do not silently resolve another environment. Lock/install strategy is to be verified in D04, not claimed tested now.

In a second terminal after B01:

```powershell
Set-Location 'C:\Users\User\Desktop\NeuroSage-Workspace\safira-demo\demo\frontend'
npm ci
npm run test -- --run
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Open `http://127.0.0.1:5173`; browser uses Vite `/api` proxy to backend. Production build gate: `npm run build`; planned local preview uses `npm run preview -- --host 127.0.0.1 --port 5173 --strictPort` and must retain the same API proxy in Vite preview configuration. This is a local build rehearsal, not deployment authorization. No cloud, Docker or external database service required.

## Planned viva rehearsal and recovery

Open Dashboard and identify historical vs fresh software verification; select any stage; explain six evidence families and offline frozen preparation; select a qualified scenario, run, inspect actual outcome and host observations; finish at Evidence & Limitations. Only demonstrate natural outcomes that Batch A qualified. No guaranteed CAUTION/DEFER coverage before qualification. D05 creates the final tested viva script.

If package import fails, reinstall editable from current root using explicit venv Python. If an ID is unavailable, show its reason; do not edit a threshold or force the outcome. If a port is occupied, stop/reconfigure the local app deliberately; do not bind all interfaces. If the worker times out, show execution error and restart the backend to prepare fixtures; no automatic replay. Ctrl+C stops each terminal and closes worker/temporary registry resources. No private fixture contents, patient data or source exception payloads should appear in diagnostics.
