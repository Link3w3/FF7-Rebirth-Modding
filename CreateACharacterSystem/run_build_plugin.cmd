@echo off
rem Builds the RebirthSkelCompat End editor plugin with RebirthEngineV5's UnrealBuildTool (plugin module only).
rem Output: build\run-plugin.log
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "LOG=%~dp0build\run-plugin.log"
call :findpython
echo RebirthSkelCompat plugin build with %PY% > "%LOG%"
%PY% "%~dp0build_plugin.py" >> "%LOG%" 2>&1
echo RUN COMPLETE exit=%ERRORLEVEL%>> "%LOG%"
exit /b

:findpython
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python399\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python399\python.exe"
if not defined PY set "PY=python"
exit /b
