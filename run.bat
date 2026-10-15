@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title Medical-AI-Workstation-8081

:: 1. Auto-Repair / Rebind .venv to local python_base (Zero internet, 100% offline)
if exist "%~dp0python_base\python.exe" (
    (echo home = %~dp0python_base
     echo include-system-site-packages = false
     echo version = 3.10.22) > "%~dp0.venv\pyvenv.cfg" 2>nul
)

:: 2. Locate Best Python Runtime
set "PY="
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PY=%~dp0.venv\Scripts\python.exe"
    goto :LAUNCH_NOW
)
if exist "%~dp0python_base\python.exe" (
    set "PY=%~dp0python_base\python.exe"
    goto :LAUNCH_NOW
)
where py >nul 2>&1 && (set "PY=py" && goto :LAUNCH_NOW)
where python >nul 2>&1 && (set "PY=python" && goto :LAUNCH_NOW)

:: 3. Python missing entirely
echo ==============================================================================
echo [CRITICAL ERROR] Python runtime is missing!
echo Expected location: %~dp0python_base\python.exe
echo Please do not delete or rename the python_base folder.
echo ==============================================================================
pause
exit /b 1

:LAUNCH_NOW
"%PY%" "%~dp0launch.py"
if %ERRORLEVEL% neq 0 (
    echo.
    echo [!] Workstation process finished with return code %ERRORLEVEL%.
    pause
)
