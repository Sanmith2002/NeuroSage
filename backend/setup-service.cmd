@echo off
rem One-time setup of the AD backend's Python environment (about 5-10 minutes, ~3 GB download).
rem Needs uv (https://docs.astral.sh/uv/). Python 3.11 is installed INSIDE this folder (.python) so the .venv
rem works from any terminal. Safe to re-run: it rebuilds .venv from scratch.
setlocal
cd /d "%~dp0"
where uv >nul 2>nul || (echo uv is not installed: see https://docs.astral.sh/uv/getting-started/installation/ & exit /b 1)
set "UV_PYTHON_INSTALL_DIR=%~dp0.python"
uv python install 3.11 || exit /b 1
uv venv .venv --clear --python 3.11 --python-preference only-managed || exit /b 1
uv pip install --python .venv torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu || exit /b 1
uv pip install --python .venv --no-deps monai==1.6.1 || exit /b 1
uv pip install --python .venv -r requirements.txt || exit /b 1
.venv\Scripts\python.exe -c "import sklearn, torch, ants; print('AD service environment ready: scikit-learn', sklearn.__version__, '| torch', torch.__version__)"
