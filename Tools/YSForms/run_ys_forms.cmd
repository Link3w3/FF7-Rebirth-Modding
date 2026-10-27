@echo off
title Sephiroth forms - building Young Sephiroth's moves and the winged feelers, please leave this window open
rem Fully Playable (Young) Sephiroth forms update (close the End editor and the game first):
rem   1. builds YOUNG SEPHIROTH's own Ever Crisis moves (88, the Battle07 pack) and WINGED's moves again with the
rem      transformed Sephiroth's feelers (32) in an editor commandlet (a move that stops the editor is left out and the
rem      others go on),
rem   2. cooks them with the engine's cook commandlet and packs them with IoStore into YSFormsMoves.utoc/.ucas
rem      for Sandalphon to put into the mods.
rem Status: build\ys_status.txt. Results: C:\FF7R2UProj\Saved\RebirthSkelCompat\YSForms\
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\ys_status.txt"
echo Sephiroth forms, started %DATE% %TIME%> "%STATUS%"
for %%P in (UE4Editor.exe UE4Editor-Cmd.exe ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close %%P first ^(the End editor or the game^), then run this again>> "%STATUS%"
    goto :done
  )
)
for %%F in (build_ys_forms.py run_ys_forms.ps1 make_container.py) do (
  if not exist "%~dp0%%F" (
    echo FAILED: %%F is missing>> "%STATUS%"
    goto :done
  )
)
for %%F in (plan.json ysf_build.py) do (
  if not exist "C:\FF7R2UProj\Saved\RebirthSkelCompat\YSForms\cmd\%%F" (
    echo FAILED: Saved\RebirthSkelCompat\YSForms\cmd\%%F is missing ^(tell Sandalphon^)>> "%STATUS%"
    goto :done
  )
)
echo 1/2 building the moves in the editor...>> "%STATUS%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_ys_forms.ps1"
if errorlevel 1 (
  echo FAILED: the editor step ^(build\ys_editor.log, Saved\RebirthSkelCompat\YSForms\build_result.json and progress.json^)>> "%STATUS%"
  goto :done
)
echo 2/2 cooking the moves and packing them with IoStore...>> "%STATUS%"
call :findpython
%PY% "%~dp0make_container.py" >> "%STATUS%" 2>&1
if errorlevel 1 (
  echo FAILED: the cook or the container ^(Saved\RebirthSkelCompat\YSForms\_work\cook.log and iostore.log^)>> "%STATUS%"
  goto :done
)
echo    done: tell Sandalphon, who puts the moves into the mods>> "%STATUS%"
:done
echo SEPHIROTH FORMS STEP COMPLETE %DATE% %TIME%>> "%STATUS%"
type "%STATUS%"
pause
exit /b

:findpython
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python399\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python399\python.exe"
if not defined PY set "PY=python"
exit /b
