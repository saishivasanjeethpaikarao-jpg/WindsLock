@echo off
cd /d "%~dp0"
".venv\Scripts\mitmweb.exe" --listen-host 127.0.0.1 --listen-port 8080 -s proxy_addon.py
