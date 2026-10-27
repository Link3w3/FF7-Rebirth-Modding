@echo off
title Remake masters patch - please leave this window open
rem Rebuilds a few FF7 Remake masters in place (close the End editor first; the editor opens and closes by itself):
rem   EndMaterial_Skin, EndMaterial_Blood   no subsurface colour (the game stores none; white washed the skin out)
rem   EndMaterial_Hair                      the game's hair data for the engine's recovered hair lighting
rem then puts the game's static switches back on their renderer instances and compiles those and Sephiroth's.
rem With the editor open instead: Output Log > Cmd: py "C:/FF7R2UProj/Tools/RemakeMaterials/patch_remake_masters.py"
rem Status: build\status_patch.txt   Results: C:\FF7R2UProj\Saved\RemakeMaterials\patch_result.json
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\status_patch.txt"
echo Remake masters patch: started %DATE% %TIME%> "%STATUS%"
tasklist /FI "IMAGENAME eq UE4Editor.exe" 2>nul | find /I "UE4Editor.exe" >nul
if not errorlevel 1 (
  echo REFUSED: close the End editor first, then run this again>> "%STATUS%"
  goto :done
)
echo rebuilding the masters ^(the editor opens and closes by itself, a few minutes^)...>> "%STATUS%"
type "%STATUS%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_patch_remake_masters.ps1"
>> "%STATUS%" echo    editor step exit=%ERRORLEVEL%
:done
echo FINISHED %DATE% %TIME%>> "%STATUS%"
cls
type "%STATUS%"
pause
exit /b
