@echo off
title Remake material instances - please leave this window open
rem FF7 Remake's material instances in the End project (close the End editor first; the editor opens and closes by itself):
rem   1. rebuilds the RebirthMaterialPreview plugin (it now sets static switches on saved instances), about 3-5 minutes
rem   2. /Game/GameContents/Renderer/MaterialInstance            the game's 385 renderer instances on the Remake masters
rem      /Game/GameContents/Character/Enemy/EB0021_0x_.../Material  Sephiroth's 21 instances and their 37 textures
rem Status: build\status_mis.txt   Results: C:\FF7R2UProj\Saved\RemakeMaterials\mis_result.json
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\status_mis.txt"
echo Remake material instances: started %DATE% %TIME%> "%STATUS%"
tasklist /FI "IMAGENAME eq UE4Editor.exe" 2>nul | find /I "UE4Editor.exe" >nul
if not errorlevel 1 (
  echo REFUSED: close the End editor first, then run this again>> "%STATUS%"
  goto :done
)
call :findpython
echo step 1/2: building the RebirthMaterialPreview plugin with %PY% ...>> "%STATUS%"
type "%STATUS%"
%PY% "C:\FF7R2UProj\Tools\EndEditorPlugins\build_editor_plugins.py" RebirthMaterialPreview > "%~dp0build\plugin_build.log" 2>&1
set "BUILT=%ERRORLEVEL%"
>> "%STATUS%" echo    plugin build exit=%BUILT% (build\plugin_build.log, Tools\EndEditorPlugins\build\latest.json)
if not "%BUILT%"=="0" (
  echo PLUGIN BUILD FAILED: the instances were not made. Send me build\plugin_build.log>> "%STATUS%"
  goto :done
)
echo step 2/2: textures and instances ^(the editor opens and closes by itself^)...>> "%STATUS%"
type "%STATUS%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_import_remake_mis.ps1"
>> "%STATUS%" echo    editor step exit=%ERRORLEVEL%
:done
echo FINISHED %DATE% %TIME%>> "%STATUS%"
cls
type "%STATUS%"
pause
exit /b

:findpython
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python399\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python399\python.exe"
if not defined PY set "PY=python"
exit /b
