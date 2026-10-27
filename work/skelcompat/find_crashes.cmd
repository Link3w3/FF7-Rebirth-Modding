@echo off
rem RebirthSkelCompat: finds the game's recent crash reports and copies them into .\crashes so they can be read.
setlocal
set "DST=%~dp0crashes"
if not exist "%DST%" mkdir "%DST%"
echo Looking for recent FF7 Rebirth crash reports, this can take a minute...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0find_crashes.ps1" -Dest "%DST%" > "%DST%\find.txt" 2>&1
echo RUN COMPLETE exit=%ERRORLEVEL%>> "%DST%\find.txt"
exit /b 0
