@echo off
setlocal
title Stop AI Server 8081
echo Stopping AI Server on port 8081...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8081 ^| findstr LISTENING 2^>nul') do (
    taskkill /f /pid %%a >nul 2>&1
)
echo [OK] Port 8081 freed successfully.
ping 127.0.0.1 -n 2 >nul
