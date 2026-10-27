@echo off
title Sephiroth KH2 form - running, please leave this window open
rem Builds your playable Sephiroth's KH2 form (close the End editor first; it takes a while):
rem   1. the Create a Character System editor plugin (1.10: Import Key Animations),
rem   2. imports the KH2 animations onto his skeleton and builds the KH2 form's moves from them,
rem   3. packages the project (E:\FVIIREBIRTH\Pakage), so the moves are in pakchunk47.
rem Status: build\kh2_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\kh2_status.txt"
echo Sephiroth KH2 moves started %DATE% %TIME%> "%STATUS%"
tasklist /FI "IMAGENAME eq UE4Editor.exe" 2>nul | find /I "UE4Editor.exe" >nul
if not errorlevel 1 (
  echo REFUSED: close the End editor first, then run this again>> "%STATUS%"
  goto :done
)
call :findpython
echo 1/3 building the Create a Character System editor plugin...>> "%STATUS%"
%PY% "C:\FF7R2UProj\Tools\EndEditorPlugins\build_editor_plugins.py" RebirthSkelCompatEditor > "%~dp0build\kh2_plugin.log" 2>&1
if errorlevel 1 (
  echo FAILED: the plugin did not build ^(build\kh2_plugin.log, Tools\EndEditorPlugins\build\latest.json^)>> "%STATUS%"
  goto :done
)
echo    plugin built>> "%STATUS%"
echo 2/3 importing the KH2 animations and building his moves...>> "%STATUS%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_kh2_moves.ps1"
if errorlevel 1 (
  echo FAILED: the editor step ^(build\kh2_editor.log, Saved\RebirthSkelCompat\SephirothForms\kh2_result.json^)>> "%STATUS%"
  goto :done
)
echo 3/3 packaging the project ^(this is the long part^)...>> "%STATUS%"
call "C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Build\BatchFiles\RunUAT.bat" -ScriptsForProject=C:/FF7R2UProj/End.uproject BuildCookRun -nocompileeditor -installed -nop4 -project=C:/FF7R2UProj/End.uproject -cook -stage -archive -archivedirectory=E:/FVIIREBIRTH/Pakage -package -ue4exe=C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Binaries\Win64\UE4Editor-Cmd.exe -compressed -ddc=InstalledDerivedDataBackendGraph -iostore -pak -iostore -prereqs -manifests -targetplatform=Win64 -build -target=End -clientconfig=Shipping -utf8output > "%~dp0build\kh2_package.log" 2>&1
>> "%STATUS%" echo    package exit=%ERRORLEVEL%
:done
echo KH2 MOVES COMPLETE %DATE% %TIME%>> "%STATUS%"
type "%STATUS%"
pause
exit /b

:findpython
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python399\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python399\python.exe"
if not defined PY set "PY=python"
exit /b
