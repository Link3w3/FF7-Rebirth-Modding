@echo off
title Remake Sephiroth - materials and models, please leave this window open
rem Everything for Remake Sephiroth in the End project, in one go (close the End editor first):
rem   1. rebuilds the RebirthMaterialPreview plugin (static switches on saved material instances), about 3-5 minutes
rem   2. Remake's 385 renderer material instances, Sephiroth's 21 instances and his 37 textures (run_import_remake_mis.cmd)
rem   3. his models: EB0021_00 (standard) and EB0021_01_Body + EB0021_01_Wing (transformed) on EB0021_00_Skeleton
rem      (run_import_remake_sephiroth.cmd)
rem Status: build\status_all.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\status_all.txt"
echo Remake Sephiroth, materials and models: started %DATE% %TIME%> "%STATUS%"
tasklist /FI "IMAGENAME eq UE4Editor.exe" 2>nul | find /I "UE4Editor.exe" >nul
if not errorlevel 1 (
  echo REFUSED: close the End editor first, then run this again>> "%STATUS%"
  goto :done
)
call :findpython
echo step 1/3: building the RebirthMaterialPreview plugin with %PY% ...>> "%STATUS%"
cls
type "%STATUS%"
%PY% "C:\FF7R2UProj\Tools\EndEditorPlugins\build_editor_plugins.py" RebirthMaterialPreview > "%~dp0build\plugin_build.log" 2>&1
set "BUILT=%ERRORLEVEL%"
>> "%STATUS%" echo    plugin build exit=%BUILT% (build\plugin_build.log)
if not "%BUILT%"=="0" (
  echo PLUGIN BUILD FAILED: nothing was imported. Send me build\plugin_build.log>> "%STATUS%"
  goto :done
)
echo step 2/3: material instances and textures ^(the editor opens and closes by itself, 20-40 minutes^)...>> "%STATUS%"
cls
type "%STATUS%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_import_remake_mis.ps1"
>> "%STATUS%" echo    material instances exit=%ERRORLEVEL% (details: build\status_mis.txt)
if exist "%~dp0build\status_mis.txt" type "%~dp0build\status_mis.txt">> "%STATUS%"
echo step 3/3: his models ^(the editor opens and closes by itself, a few minutes^)...>> "%STATUS%"
cls
type "%STATUS%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_import_remake_sephiroth.ps1"
>> "%STATUS%" echo    models exit=%ERRORLEVEL% (details: build\status_seph.txt)
if exist "%~dp0build\status_seph.txt" type "%~dp0build\status_seph.txt">> "%STATUS%"
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
