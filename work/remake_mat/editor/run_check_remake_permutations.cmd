@echo off
title Remake materials - building and compiling every permutation, please leave this window open
rem The same as run_build_remake_materials.cmd, then every one of the game's 385 static permutations of the masters
rem compiled in the editor (transient instances) and any compile errors listed: Saved\RemakeMaterials\permutations.json
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\status.txt"
echo Remake materials + permutations: started %DATE% %TIME%> "%STATUS%"
tasklist /FI "IMAGENAME eq UE4Editor.exe" 2>nul | find /I "UE4Editor.exe" >nul
if not errorlevel 1 (
  echo REFUSED: close the End editor first, then run this again>> "%STATUS%"
  goto :done
)
echo building and compiling ^(the editor opens and closes by itself^)...>> "%STATUS%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_build_remake_materials.ps1" -Permutations
>> "%STATUS%" echo    editor step exit=%ERRORLEVEL%
:done
echo FINISHED %DATE% %TIME%>> "%STATUS%"
type "%STATUS%"
pause
exit /b
