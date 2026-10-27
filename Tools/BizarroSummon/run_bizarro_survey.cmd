@echo off
title Bizarro Sephiroth summon - survey running, please leave this window open
rem Bizarro Sephiroth summon, step 1 (close the End editor first; a few minutes):
rem   1. builds the Create a Character System editor plugin (1.10.2: Describe Animations),
rem   2. reads what Bizarro Sephiroth's and Alexander's animations have (lengths, notifies, hits) into
rem      Saved\RebirthSkelCompat\BizarroSummon\survey.json, for planning the summon's moves. Nothing is packaged.
rem Status: build\survey_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\survey_status.txt"
echo Bizarro summon survey started %DATE% %TIME%> "%STATUS%"
tasklist /FI "IMAGENAME eq UE4Editor.exe" 2>nul | find /I "UE4Editor.exe" >nul
if not errorlevel 1 (
  echo REFUSED: close the End editor first, then run this again>> "%STATUS%"
  goto :done
)
call :findpython
echo 1/2 building the Create a Character System editor plugin...>> "%STATUS%"
%PY% "C:\FF7R2UProj\Tools\EndEditorPlugins\build_editor_plugins.py" RebirthSkelCompatEditor > "%~dp0build\survey_plugin.log" 2>&1
if errorlevel 1 (
  echo FAILED: the plugin did not build ^(build\survey_plugin.log, Tools\EndEditorPlugins\build\latest.json^)>> "%STATUS%"
  goto :done
)
echo    plugin built>> "%STATUS%"
echo 2/2 reading the animations...>> "%STATUS%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_bizarro_survey.ps1"
if errorlevel 1 (
  echo FAILED: the editor step ^(build\survey_editor.log, Saved\RebirthSkelCompat\BizarroSummon\survey_result.json^)>> "%STATUS%"
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
