@echo off
rem Builds and installs Sandalphon's changes in one go (about 2 minutes):
rem   1. RebirthSkelCompat main.dll for the game (UE4SS mod). Works while the game runs: the new DLL loads next launch.
rem   2. The End editor plugins RebirthMaterialPreview and RebirthSkelCompat. Needs the End editor closed.
rem Output: build_all.log next to this file; details in RebirthSkelCompat\build and EndEditorPlugins\build\latest.json.
setlocal
cd /d "%~dp0"
set "LOG=%~dp0build_all.log"
call :findpython
echo Build all with %PY% (%DATE% %TIME%)> "%LOG%"
echo.>> "%LOG%"
echo === RebirthSkelCompat game mod DLL>> "%LOG%"
%PY% "%~dp0RebirthSkelCompat\build_dll.py" --install >> "%LOG%" 2>&1
echo MOD EXIT %ERRORLEVEL%>> "%LOG%"
echo.>> "%LOG%"
echo === End editor plugins>> "%LOG%"
%PY% "%~dp0EndEditorPlugins\build_editor_plugins.py" >> "%LOG%" 2>&1
echo PLUGINS EXIT %ERRORLEVEL%>> "%LOG%"
echo RUN COMPLETE>> "%LOG%"
exit /b

:findpython
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python399\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python399\python.exe"
if not defined PY set "PY=python"
exit /b
