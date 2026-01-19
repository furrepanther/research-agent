@echo off
:: Launch Reconstruction (Background, Intentionally Invisible)
start "" pythonw tools/maintenance/reconstruct_db.py

:: Give it a moment to initialize logging
timeout /t 2 >nul

:: Launch Log Viewer (GUI)
start "" pythonw tools/maintenance/log_viewer.py

:: Exit launcher immediately
exit
