@echo off
title Vincent's Galian Beast - survey running, please leave this window open
rem Vincent's Galian Beast form, step 1 (close the End editor first; a few minutes): reads what the Galian boss's animations
rem (EB2160, added to the End project's Content) and the transformation cutscene's (EV_NIBLE_8310) have - lengths, notifies,
rem hits - into Saved\RebirthSkelCompat\GalianBeast\survey.json, for planning the form's moves. Nothing is changed or packaged.
rem Status: build\survey_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\survey_status.txt"
echo Galian Beast survey started %DATE% %TIME%> "%STATUS%"
tasklist /FI "IMAGENAME eq UE4Editor.exe" 2>nul | find /I "UE4Editor.exe" >nul
if not errorlevel 1 (
  echo REFUSED: close the End editor first, then run this again>> "%STATUS%"
  goto :done
)
echo reading the animations...>> "%STATUS%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_galian_survey.ps1"
if errorlevel 1 (
  echo FAILED: the editor step ^(build\survey_editor.log, Saved\RebirthSkelCompat\GalianBeast\survey_result.json^): tell Sandalphon>> "%STATUS%"
  goto :done
)
echo ALL DONE: tell Sandalphon the survey is finished>> "%STATUS%"
:done
echo SURVEY COMPLETE %DATE% %TIME%>> "%STATUS%"
type "%STATUS%"
pause
exit /b
