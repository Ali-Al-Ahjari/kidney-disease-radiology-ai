@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title Setup Medical AI Environment
echo ==============================================================================
echo   Setting up isolated virtual environment (.venv) for this laptop...
echo ==============================================================================

:: Find Base Python
set "BASE_PY="
where py >nul 2>&1 && set "BASE_PY=py"
if not defined BASE_PY where python >nul 2>&1 && set "BASE_PY=python"
if not defined BASE_PY (
    echo [!] Python not found. Opening python.org...
    start https://www.python.org/downloads/
    pause
    exit /b 1
)

if not exist "%~dp0.venv\Scripts\python.exe" (
    echo [+] Creating virtual environment (.venv)...
    %BASE_PY% -m venv "%~dp0.venv"
)

echo [+] Installing required AI packages from requirements.txt...
"%~dp0.venv\Scripts\python.exe" -m pip install --upgrade pip
"%~dp0.venv\Scripts\python.exe" -m pip install -r "%~dp0requirements.txt"

echo [OK] Setup complete! Launching project now...
call "%~dp0run.bat"
