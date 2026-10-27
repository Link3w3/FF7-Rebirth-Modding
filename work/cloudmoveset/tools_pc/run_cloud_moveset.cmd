@echo off
title CLOUD moveset - building Cloud's moves for Sephiroth, please leave this window open
rem CLOUD moveset (close the End editor and the game first):
rem   1. builds the moveset's 123 moves from Cloud's own battle animations in an editor commandlet, put on Sephiroth's
rem      skeleton, with Sephiroth's damage, combo and dodge windows on Cloud's blows and Cloud's own swing sounds, trails and
rem      footsteps (a move that stops the editor is left out and the others go on),
rem   2. cooks them with the engine's cook commandlet and packs them with IoStore into CloudMovesetMoves.utoc/.ucas
rem      for Sandalphon to make the mods container of.
rem Status: build\cloud_status.txt. Results: C:\FF7R2UProj\Saved\RebirthSkelCompat\CloudMoveset\
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\cloud_status.txt"
echo CLOUD moveset, started %DATE% %TIME%> "%STATUS%"
for %%P in (UE4Editor.exe UE4Editor-Cmd.exe ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close %%P first ^(the End editor or the game^), then run this again>> "%STATUS%"
    goto :done
  )
)
for %%F in (build_cloud_moveset.py run_cloud_moveset.ps1 make_container_cloud.py) do (
  if not exist "%~dp0%%F" (
    echo FAILED: %%F is missing>> "%STATUS%"
    goto :done
  )
)
if not exist "C:\FF7R2UProj\Saved\RebirthSkelCompat\CloudMoveset\cmd\plan.json" (
  echo FAILED: Saved\RebirthSkelCompat\CloudMoveset\cmd\plan.json is missing ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
if not exist "C:\FF7R2UProj\Saved\RebirthSkelCompat\CloudMoveset\cmd\cloud_build.py" (
  echo FAILED: Saved\RebirthSkelCompat\CloudMoveset\cmd\cloud_build.py is missing ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
echo 1/2 building the moves in the editor...>> "%STATUS%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_cloud_moveset.ps1"
if errorlevel 1 (
  echo FAILED: the editor step ^(build\cloud_editor.log, Saved\RebirthSkelCompat\CloudMoveset\build_result.json and progress.json^)>> "%STATUS%"
  goto :done
)
echo 2/2 cooking the moves and packing them with IoStore...>> "%STATUS%"
call :findpython
%PY% "%~dp0make_container_cloud.py" >> "%STATUS%" 2>&1
if errorlevel 1 (
  echo FAILED: the cook or the container ^(Saved\RebirthSkelCompat\CloudMoveset\_work\cook.log and iostore.log^)>> "%STATUS%"
  goto :done
)
echo    done: tell Sandalphon, who makes the mods container of the moves>> "%STATUS%"
:done
echo CLOUD MOVESET STEP COMPLETE %DATE% %TIME%>> "%STATUS%"
type "%STATUS%"
pause
exit /b

:findpython
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python399\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python399\python.exe"
if not defined PY set "PY=python"
exit /b
