@echo off
if not "%minimized%"=="" goto :minimized
set minimized=true
start /min cmd /C "%~dpnx0"
goto :EOF

:minimized
cd /d %~dp0
echo Starting Research Agent GUI...
call venv\Scripts\activate
python gui.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo Agent exited with error. Check logs.
    pause
)
