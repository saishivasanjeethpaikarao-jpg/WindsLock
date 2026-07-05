@echo off
cd /d "%~dp0"
echo Building Windslock portable executables...
".venv\Scripts\pyinstaller.exe" --noconfirm --windowed --icon assets\windslock.ico --add-data "assets;assets" --name Windslock gui.py
".venv\Scripts\pyinstaller.exe" --noconfirm --windowed --icon assets\windslock.ico --add-data "assets;assets" --name WindslockTray tray_app.py
".venv\Scripts\pyinstaller.exe" --noconfirm --console --icon assets\windslock.ico --add-data "assets;assets" --add-data "proxy_addon.py;." --name WindslockProxy proxy_runner.py
echo.
echo Build output:
echo   %~dp0dist\Windslock\Windslock.exe
echo   %~dp0dist\WindslockTray\WindslockTray.exe
echo   %~dp0dist\WindslockProxy\WindslockProxy.exe
if "%CI%"=="" pause
