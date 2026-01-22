@echo off
echo ==========================================
echo Building AGL Research Agent Executables
echo ==========================================

REM Ensure we are in the repo root
cd /d "%~dp0\.."

echo.
echo [1/2] Building Research Viewer...
pyinstaller --onefile --windowed ^
    --icon="C:\Users\furre\OneDrive\Documents\Icons\Lumicons\Reader Adobe PDF.ico" ^
    --name="Research Viewer" ^
    --noconfirm --clean ^
    --distpath="dist" ^
    --workpath="build" ^
    --specpath="tools" ^
    "research_viewer.py"

if %ERRORLEVEL% NEQ 0 (
    echo Error building Research Viewer!
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [2/2] Building AGL Research Engine (Main GUI)...
echo Note: Excluding heavy ML libraries (torch, tensorflow, etc.)
pyinstaller --onefile --windowed ^
    --icon="assets\app_icon.ico" ^
    --name="AGL Research Engine" ^
    --exclude-module torch ^
    --exclude-module tensorflow ^
    --exclude-module numpy ^
    --exclude-module scipy ^
    --exclude-module pandas ^
    --exclude-module matplotlib ^
    --exclude-module PyQt5 ^
    --exclude-module PyQt6 ^
    --exclude-module PySide2 ^
    --exclude-module PySide6 ^
    --noconfirm --clean ^
    --distpath="dist" ^
    --workpath="build" ^
    --specpath="tools" ^
    "gui.py"

if %ERRORLEVEL% NEQ 0 (
    echo Error building AGL Research Engine!
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ==========================================
echo Build Complete!
echo Executables are in: %CD%\dist
echo ==========================================
pause
