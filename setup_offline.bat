@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title Setup-Offline-AI-8081

:: 1. Rebind .venv to local python_base
if exist "%~dp0python_base\python.exe" (
    (echo home = %~dp0python_base
     echo include-system-site-packages = false
     echo version = 3.10.22) > "%~dp0.venv\pyvenv.cfg" 2>nul
)

:: 2. Select Python executable
set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=%~dp0python_base\python.exe"

cls
"%PY%" "%~dp0verify_offline.py"
if %ERRORLEVEL% equ 0 (
    echo.
    set /p LAUNCH_CHOICE="Do you want to start the AI workstation right now? (Y/N): "
    if /i "!LAUNCH_CHOICE!"=="Y" (
        cls
        call "%~dp0run.bat"
    )
) else (
    echo.
    echo [!] Diagnostic verification failed.
    pause
)
