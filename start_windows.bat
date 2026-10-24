@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if %errorlevel%==0 (
  set "PYTHON=py"
) else (
  set "PYTHON=python"
)
if not exist ".venv\Scripts\python.exe" (
  echo Creating isolated Python environment...
  %PYTHON% -m venv .venv || goto :fail
)
call ".venv\Scripts\activate.bat"
python -m pip install -r requirements.txt || goto :fail
echo Opening local workbench at http://127.0.0.1:8000
python run.py
exit /b %errorlevel%
:fail
echo Failed to start. Verify Python 3.11+ and internet access for first-time installation.
pause
exit /b 1
