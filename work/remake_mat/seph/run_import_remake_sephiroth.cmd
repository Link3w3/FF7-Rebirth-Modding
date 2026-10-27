@echo off
title Remake Sephiroth - importing, please leave this window open
rem FF7 Remake's Sephiroth models in the End project, with his Remake material instances (run run_import_remake_mis.cmd
rem first). Close the End editor first; the editor opens and closes by itself.
rem   /Game/GameContents/Character/Enemy/EB0021_00_Sephiroth_Standard/Model/EB0021_00 (+ EB0021_00_Skeleton)
rem   /Game/GameContents/Character/Enemy/EB0021_01_Sephiroth_Transform/Model/EB0021_01_Body and EB0021_01_Wing
rem Status: build\status_seph.txt   Results: C:\FF7R2UProj\Saved\RemakeMaterials\sephiroth_result.json
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\status_seph.txt"
echo Remake Sephiroth: started %DATE% %TIME%> "%STATUS%"
tasklist /FI "IMAGENAME eq UE4Editor.exe" 2>nul | find /I "UE4Editor.exe" >nul
if not errorlevel 1 (
  echo REFUSED: close the End editor first, then run this again>> "%STATUS%"
  goto :done
)
echo importing his models ^(the editor opens and closes by itself, a few minutes^)...>> "%STATUS%"
type "%STATUS%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_import_remake_sephiroth.ps1"
>> "%STATUS%" echo    editor step exit=%ERRORLEVEL%
:done
echo FINISHED %DATE% %TIME%>> "%STATUS%"
cls
type "%STATUS%"
pause
exit /b
