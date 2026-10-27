@echo off
title Eye fix - please leave this window open
rem Fixes the eyes in the End editor (close the End editor first):
rem   1. builds the RebirthMaterialPreview plugin (the game's AlphaCompositeColored blend mode maps to AlphaComposite, so
rem      instances like RMI_Surface_Crystal_Convex_Wide_Character no longer crash the editor's preview),
rem   2. puts the game's shared eye textures (Common_Eye_Player_C/NG/NI/NO/N/O/Dark_C/MoreDark_C) in
rem      /Game/Character/Common/Eye/Texture, where the game's eye instances look for them (the four placeholder files there go
rem      to C:\FF7R2UProj\_mod_backups),
rem   3. opens the End editor once to fill the editable eye instances' empty slots (Color, GazeNormal, Normal, ScrelaNormal)
rem      with those textures, as the game's own eye instances have them; the editor closes by itself.
rem Status: build\eyefix_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\eyefix_status.txt"
echo Eye fix: started %DATE% %TIME%> "%STATUS%"
tasklist /FI "IMAGENAME eq UE4Editor.exe" 2>nul | find /I "UE4Editor.exe" >nul
if not errorlevel 1 (
  echo REFUSED: close the End editor first, then run this again>> "%STATUS%"
  goto :done
)
call :findpython
echo 1/2 building the RebirthMaterialPreview plugin...>> "%STATUS%"
%PY% "C:\FF7R2UProj\Tools\RebirthMaterialPreviewFix\build_material_preview.py" > "%~dp0build\eyefix_plugin.log" 2>&1
if errorlevel 1 (
  echo FAILED: the plugin did not build ^(build\eyefix_plugin.log, Tools\RebirthMaterialPreviewFix\build\latest.json^); the previous plugin is back in place>> "%STATUS%"
  goto :done
)
echo    plugin built>> "%STATUS%"
echo 2/2 eye textures and the eye instances ^(the editor opens and closes by itself^)...>> "%STATUS%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0fix_eyes.ps1"
>> "%STATUS%" echo    eye step exit=%ERRORLEVEL%
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
