# -*- coding: utf-8 -*-
# Medical AI PowerShell Launcher
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
try { $OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

$ProjectTitle  = "منظومة رداك للتشخيص الشعاعي بالذكاء الاصطناعي (Radiology AI Workstation)"
$ColleagueName = "الزميل 1: تخصص الأشعة والتصوير المقطعي (Radiology Dark Theme)"
$Port          = 8081
$ServerUrl     = "http://localhost:$Port/"
$HealthUrl     = "http://localhost:$Port/health"

try { $host.UI.RawUI.WindowTitle = "[AI Station] " + $ProjectTitle + " (Port " + $Port + ")" } catch {}
Clear-Host

# 1. Clean Port
try {
    $lines = netstat -ano | Select-String (":$Port\s+.*LISTENING")
    foreach ($line in $lines) {
        $parts = ($line -split '\s+') | Where-Object { $_ -ne '' }
        if ($parts.Length -ge 5) {
            Stop-Process -Id ([int]$parts[-1]) -Force -ErrorAction SilentlyContinue
        }
    }
} catch {}

# 2. Locate Python
$selectedPython = $null
$localVenvPy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (Test-Path $localVenvPy) {
    $selectedPython = $localVenvPy
} else {
    $cands = @("py", "python", "$env:LocalAppData\Programs\Python\Python310\python.exe", "$env:ProgramFiles\Python310\python.exe")
    foreach ($c in $cands) {
        try {
            $cmd = Get-Command $c -ErrorAction SilentlyContinue
            if ($cmd) { $selectedPython = $c; break }
        } catch {}
    }
}

if (-not $selectedPython) {
    Write-Host "[!] Python not found. Please install Python 3.10." -ForegroundColor Red
    Start-Process "https://www.python.org/downloads/"
    pause
    exit 1
}

# 3. Launch via launch.py or app.py
$launchPy = Join-Path $PSScriptRoot "launch.py"
if (Test-Path $launchPy) {
    & $selectedPython $launchPy
} else {
    & $selectedPython (Join-Path $PSScriptRoot "app.py")
}
