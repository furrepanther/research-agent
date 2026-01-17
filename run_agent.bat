@echo off
if not "%minimized%"=="" goto :minimized
set minimized=true
start /min cmd /C "%~dpnx0"
goto :EOF

:minimized
cd /d %~dp0
call venv\Scripts\activate
python main.py
pause
