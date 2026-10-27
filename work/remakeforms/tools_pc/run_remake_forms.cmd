@echo off
title REMAKE forms - building Sephiroth's Remake moves, please leave this window open
rem REMAKE and REMAKE WINGED (close the End editor and the game first):
rem   1. builds the 29 moves of the two forms from Remake Sephiroth's animations in an editor commandlet, with Rebirth
rem      Sephiroth's damage and timing on Remake's hits and Remake's sounds and effects (a move that stops the editor is
rem      left out and the others go on),
rem   2. cooks them with the engine's cook commandlet and packs them with IoStore into RemakeFormsMoves.utoc/.ucas
rem      for Sandalphon to put into the mods.
rem Status: build\remake_status.txt. Results: C:\FF7R2UProj\Saved\RebirthSkelCompat\RemakeForms\
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\remake_status.txt"
echo REMAKE forms, started %DATE% %TIME%> "%STATUS%"
for %%P in (UE4Editor.exe UE4Editor-Cmd.exe ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close %%P first ^(the End editor or the game^), then run this again>> "%STATUS%"
    goto :done
  )
)
for %%F in (build_remake_forms.py run_remake_forms.ps1 make_container.py) do (
  if not exist "%~dp0%%F" (
    echo FAILED: %%F is missing>> "%STATUS%"
    goto :done
  )
)
if not exist "C:\FF7R2UProj\Saved\RebirthSkelCompat\RemakeForms\cmd\plan.json" (
  echo FAILED: Saved\RebirthSkelCompat\RemakeForms\cmd\plan.json is missing ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
echo 1/2 building the moves in the editor...>> "%STATUS%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_remake_forms.ps1"
if errorlevel 1 (
  echo FAILED: the editor step ^(build\remake_editor.log, Saved\RebirthSkelCompat\RemakeForms\build_result.json and progress.json^)>> "%STATUS%"
  goto :done
)
echo 2/2 cooking the moves and packing them with IoStore...>> "%STATUS%"
call :findpython
%PY% "%~dp0make_container.py" >> "%STATUS%" 2>&1
if errorlevel 1 (
  echo FAILED: the cook or the container ^(Saved\RebirthSkelCompat\RemakeForms\_work\cook.log and iostore.log^)>> "%STATUS%"
  goto :done
)
echo    done: tell Sandalphon, who puts the moves into the mods>> "%STATUS%"
:done
echo REMAKE FORMS STEP COMPLETE %DATE% %TIME%>> "%STATUS%"
type "%STATUS%"
pause
exit /b

:findpython
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python399\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python399\python.exe"
if not defined PY set "PY=python"
exit /b
