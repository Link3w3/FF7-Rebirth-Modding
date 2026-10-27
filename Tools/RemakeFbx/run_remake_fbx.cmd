@echo off
title Remake Sephiroth on PC0010_00 as FBX - please leave this window open
rem Remake Sephiroth's animations (Battle00, Battle01, Neutral00, Reaction00) retargeted onto Rebirth Sephiroth's
rem PC0010_00 skeleton and exported as FBX files (close the End editor and the game first):
rem   C:\FF7R2UProj\Saved\RemakeSephirothFBX\<Folder>\<Animation>.fbx, and all of them in
rem   C:\FF7R2UProj\Saved\RemakeSephirothFBX.zip
rem Status: build\remake_fbx_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\remake_fbx_status.txt"
echo Remake Sephiroth FBX, started %DATE% %TIME%> "%STATUS%"
for %%P in (UE4Editor.exe UE4Editor-Cmd.exe ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close %%P first ^(the End editor or the game^), then run this again>> "%STATUS%"
    goto :done
  )
)
for %%F in (build_remake_fbx.py run_remake_fbx.ps1) do (
  if not exist "%~dp0%%F" (
    echo FAILED: %%F is missing>> "%STATUS%"
    goto :done
  )
)
echo retargeting and exporting in the editor ^(a few minutes^)...>> "%STATUS%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_remake_fbx.ps1"
if errorlevel 1 (
  echo FAILED: the editor step ^(build\remake_fbx_editor.log, Saved\RemakeSephirothFBX\_build\build_result.json^)>> "%STATUS%"
  goto :done
)
echo    done: C:\FF7R2UProj\Saved\RemakeSephirothFBX.zip>> "%STATUS%"
:done
echo REMAKE FBX STEP COMPLETE %DATE% %TIME%>> "%STATUS%"
type "%STATUS%"
pause
exit /b
