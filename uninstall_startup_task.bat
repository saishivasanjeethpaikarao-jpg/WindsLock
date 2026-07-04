@echo off
echo Removing Windslock startup task...
schtasks /Delete /TN WindslockEnforcer /F
echo.
echo Removed if it existed.
pause
