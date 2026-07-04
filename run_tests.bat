@echo off
cd /d "%~dp0"
set WINDSLOCK_APP_DIR=%~dp0test_appdata_tmp
".venv\Scripts\python.exe" -B -m unittest discover -s tests -v
