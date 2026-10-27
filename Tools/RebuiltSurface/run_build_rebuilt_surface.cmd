@echo off
title RM_Surface rebuilt - building, please leave this window open
rem The editable RM_Surface for the End editor, in RM_Surface's own place (close the End editor first; it takes a while):
rem   1. builds the RebirthMaterialPreview editor plugin (its preview then renders the cooked RM_Surface instances through
rem      the rebuilt RM_Surface, each with its own static switches),
rem   2. moves the game's cooked RM_Surface into C:\FF7R2UProj\_mod_backups and opens the End editor once to build
rem      /Game/Renderer/Material/RM_Surface in its place and compile the game's 104 permutations of it; the editor closes by
rem      itself when it is done. Cooks leave the rebuilt RM_Surface out (the plugin's cook skip): the game has its own.
rem   restore_cooked_rm_surface.cmd puts the game's cooked RM_Surface back.
rem Status: build\status.txt   Results: C:\FF7R2UProj\Saved\RebirthSkelCompat\RebuiltSurface\build_result.json, permutations.json
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\status.txt"
echo RM_Surface rebuilt: started %DATE% %TIME%> "%STATUS%"
tasklist /FI "IMAGENAME eq UE4Editor.exe" 2>nul | find /I "UE4Editor.exe" >nul
if not errorlevel 1 (
  echo REFUSED: close the End editor first, then run this again>> "%STATUS%"
  goto :done
)
call :findpython
echo 1/2 building the RebirthMaterialPreview plugin...>> "%STATUS%"
%PY% "C:\FF7R2UProj\Tools\RebirthMaterialPreviewFix\build_material_preview.py" > "%~dp0build\plugin.log" 2>&1
if errorlevel 1 (
  echo FAILED: the plugin did not build ^(build\plugin.log, Tools\RebirthMaterialPreviewFix\build\latest.json^); the previous plugin is back in place>> "%STATUS%"
  goto :done
)
echo    plugin built>> "%STATUS%"
echo 2/2 building the rebuilt RM_Surface and compiling its permutations ^(the editor opens and closes by itself^)...>> "%STATUS%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_build_rebuilt_surface.ps1"
>> "%STATUS%" echo    editor step exit=%ERRORLEVEL%
:done
echo FINISHED %DATE% %TIME%>> "%STATUS%"
type "%STATUS%"
pause
exit /b

:findpython
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python399\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python399\python.exe"
if not defined PY set "PY=python"
exit /b
