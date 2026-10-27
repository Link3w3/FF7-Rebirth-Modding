@echo off
title DISSIDIA NT form - building Sephiroth's Dissidia NT moves, please leave this window open
rem DISSIDIA NT (close the End editor and the game first):
rem   1. imports Dissidia NT Sephiroth's animations (keys) and builds the form's 18 moves from them in an editor
rem      commandlet, with Rebirth Sephiroth's damage and timing on Dissidia NT's blows and a sword trail and swing sound on each slash (a move that
rem      stops the editor is left out and the others go on),
rem   2. cooks them with the engine's cook commandlet and packs them with IoStore into DissidiaNTFormMoves.utoc/.ucas
rem      for Sandalphon to put into the mods.
rem Status: build\dnt_status.txt. Results: C:\FF7R2UProj\Saved\RebirthSkelCompat\DissidiaNTForm\
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\dnt_status.txt"
echo DISSIDIA NT form, started %DATE% %TIME%> "%STATUS%"
for %%P in (UE4Editor.exe UE4Editor-Cmd.exe ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close %%P first ^(the End editor or the game^), then run this again>> "%STATUS%"
    goto :done
  )
)
for %%F in (build_dnt_form.py run_dnt_form.ps1 make_container_dnt.py) do (
  if not exist "%~dp0%%F" (
    echo FAILED: %%F is missing>> "%STATUS%"
    goto :done
  )
)
if not exist "C:\FF7R2UProj\Saved\RebirthSkelCompat\DissidiaNTForm\cmd\plan.json" (
  echo FAILED: Saved\RebirthSkelCompat\DissidiaNTForm\cmd\plan.json is missing ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
echo 1/2 building the moves in the editor...>> "%STATUS%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_dnt_form.ps1"
if errorlevel 1 (
  echo FAILED: the editor step ^(build\dnt_editor.log, Saved\RebirthSkelCompat\DissidiaNTForm\build_result.json and progress.json^)>> "%STATUS%"
  goto :done
)
echo 2/2 cooking the moves and packing them with IoStore...>> "%STATUS%"
call :findpython
%PY% "%~dp0make_container_dnt.py" >> "%STATUS%" 2>&1
if errorlevel 1 (
  echo FAILED: the cook or the container ^(Saved\RebirthSkelCompat\DissidiaNTForm\_work\cook.log and iostore.log^)>> "%STATUS%"
  goto :done
)
echo    done: tell Sandalphon, who puts the moves into the mods>> "%STATUS%"
:done
echo DISSIDIA NT FORM STEP COMPLETE %DATE% %TIME%>> "%STATUS%"
type "%STATUS%"
pause
exit /b

:findpython
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python399\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python399\python.exe"
if not defined PY set "PY=python"
exit /b
