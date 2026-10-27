@echo off
rem RebirthSkelCompat: copies the game's recent crash reports into this folder so they can be read.
rem Reads %LOCALAPPDATA%\End\Saved (crash reports and logs of the last 2 days); changes nothing there.
setlocal
set "SRC=%LOCALAPPDATA%\End\Saved"
set "DST=%~dp0crashes"
if not exist "%DST%" mkdir "%DST%"
set "LIST=%DST%\listing.txt"
echo SRC=%SRC%> "%LIST%"
echo --- Saved folder>> "%LIST%"
dir /a "%SRC%" >> "%LIST%" 2>&1
echo --- Crashes, newest first>> "%LIST%"
dir /a /o-d /tw "%SRC%\Crashes" >> "%LIST%" 2>&1
echo --- Logs, newest first>> "%LIST%"
dir /a /o-d /tw "%SRC%\Logs" >> "%LIST%" 2>&1
echo --- Copy>> "%LIST%"
robocopy "%SRC%\Crashes" "%DST%\Crashes" /S /MAXAGE:2 /R:0 /W:0 /NP >> "%LIST%" 2>&1
robocopy "%SRC%\Logs" "%DST%\Logs" /S /MAXAGE:2 /R:0 /W:0 /NP >> "%LIST%" 2>&1
echo RUN COMPLETE>> "%LIST%"
exit /b 0
