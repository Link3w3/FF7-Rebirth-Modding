@echo off
rem Installs the Cloud (Rebirth) and Remake Cloud skins and the skins container that holds them. Close the game first.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_cloud_skins.ps1"
echo.
pause
