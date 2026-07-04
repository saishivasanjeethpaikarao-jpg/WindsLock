@echo off
cd /d "%~dp0"
start "" ".venv\Scripts\pythonw.exe" tray_app.py
start "" ".venv\Scripts\pythonw.exe" gui.py
