@echo off
rem Starts the NeuroSage AD co-pathology backend on http://127.0.0.1:8000 (extra arguments go to uvicorn).
rem Run setup-service.cmd once first. A .cmd file is not blocked by the PowerShell script execution policy.
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo The Python environment is missing: run setup-service.cmd first.
  exit /b 1
)
set "PYTHONIOENCODING=utf-8"
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 %*
