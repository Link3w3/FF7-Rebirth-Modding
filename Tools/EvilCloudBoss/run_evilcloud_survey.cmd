@echo off
title Evil Cloud boss fights - survey running, please leave this window open
rem Evil Cloud's boss fights, step 1 (close the End editor first; a few minutes):
rem   reads what the boss Sephiroth's animations and Cloud's animations have (lengths, notifies, hits) into
rem   Saved\RebirthSkelCompat\EvilCloudBoss\survey.json, for planning Evil Cloud's moves. Nothing is changed or packaged.
rem Status: build\survey_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\survey_status.txt"
echo Evil Cloud boss survey started %DATE% %TIME%> "%STATUS%"
tasklist /FI "IMAGENAME eq UE4Editor.exe" 2>nul | find /I "UE4Editor.exe" >nul
if not errorlevel 1 (
  echo REFUSED: close the End editor first, then run this again>> "%STATUS%"
  goto :done
)
call :findpython
echo reading the animations ^(a few minutes^)...>> "%STATUS%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_evilcloud_survey.ps1"
if errorlevel 1 (
  echo FAILED: the editor step ^(build\survey_editor.log, Saved\RebirthSkelCompat\EvilCloudBoss\survey_result.json^)>> "%STATUS%"
  goto :done
)
:done
echo SURVEY COMPLETE %DATE% %TIME%>> "%STATUS%"
type "%STATUS%"
pause
exit /b

:findpython
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python399\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python399\python.exe"
if not defined PY set "PY=python"
exit /b
