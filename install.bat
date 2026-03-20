@echo off
setlocal

echo.
echo  ╔═══════════════════════════════════════╗
echo  ║         SRTFlow Installer             ║
echo  ╚═══════════════════════════════════════╝
echo.

REM ── 1. Install Python dependencies ─────────────────────────────────────────
echo  Installing Python dependencies...
pip install --quiet PyQt6 requests
if %ERRORLEVEL% NEQ 0 (
    echo  ERROR: pip install failed. Make sure Python 3 and pip are installed.
    pause
    exit /b 1
)
echo  [OK] PyQt6 and requests installed

REM ── 2. Detect DaVinci Resolve scripts folder ────────────────────────────────
set "DR_SCRIPTS=%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility"

REM ── 3. Create junction ──────────────────────────────────────────────────────
if exist "%DR_SCRIPTS%" (
    echo  DaVinci Resolve scripts folder found:
    echo  %DR_SCRIPTS%
    echo.

    set "TARGET=%DR_SCRIPTS%\SRTFlow"

    if exist "%TARGET%" (
        echo  Removing old version...
        rmdir /s /q "%TARGET%"
    )

    mklink /J "%TARGET%" "%~dp0"
    echo  [OK] Junction created: %TARGET%
    echo.
    echo  ═══════════════════════════════════════════
    echo  [OK] Installation complete!
    echo.
    echo  In DaVinci Resolve:
    echo  Workspace - Scripts - Utility - SRTFlow
    echo  ═══════════════════════════════════════════
) else (
    echo  WARNING: DaVinci Resolve scripts folder not found.
    echo  Manually place the SRTFlow folder in your Scripts\Utility directory.
    echo.
    echo  Expected path:
    echo  %DR_SCRIPTS%
)
echo.
pause
