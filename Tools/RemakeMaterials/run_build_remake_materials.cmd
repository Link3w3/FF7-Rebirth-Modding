@echo off
title Remake materials - building, please leave this window open
rem FF7 Remake's material masters in the End project (close the End editor first; the editor opens and closes by itself):
rem   /Game/GameContents/Renderer/Texture           the masters' default textures
rem   /Game/GameContents/Renderer/MaterialFunction  the material functions
rem   /Game/GameContents/Renderer/Material          the 21 EndMaterial masters, each compiled
rem run_check_remake_permutations.cmd also compiles every one of the game's 385 static permutations of them (longer).
rem Status: build\status.txt   Results: C:\FF7R2UProj\Saved\RemakeMaterials\build_result.json
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\status.txt"
echo Remake materials: started %DATE% %TIME%> "%STATUS%"
tasklist /FI "IMAGENAME eq UE4Editor.exe" 2>nul | find /I "UE4Editor.exe" >nul
if not errorlevel 1 (
  echo REFUSED: close the End editor first, then run this again>> "%STATUS%"
  goto :done
)
echo building the textures, functions and masters ^(the editor opens and closes by itself^)...>> "%STATUS%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_build_remake_materials.ps1"
>> "%STATUS%" echo    editor step exit=%ERRORLEVEL%
:done
echo FINISHED %DATE% %TIME%>> "%STATUS%"
type "%STATUS%"
pause
exit /b
