@echo off
cd /d "%~dp0"
echo Installing Windslock tray startup task...
schtasks /Create /TN WindslockEnforcer /SC ONLOGON /TR "\"%~dp0.venv\Scripts\pythonw.exe\" \"%~dp0tray_app.py\"" /RL HIGHEST /F
if errorlevel 1 (
  echo.
  echo Failed. Run this file as administrator if you want highest-privilege startup.
  pause
  exit /b 1
)
echo.
echo Installed. Windslock tray will start when you sign in.
pause
