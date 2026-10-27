@echo off
rem Builds the Rebirth FX Live Link editor plugin (Plugins\RebirthFxLiveLink) for RebirthEngineV5. Close the End editor first.
rem About 2 minutes. Output: build\run_fxlink.log and build\latest.json
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "LOG=%~dp0build\run_fxlink.log"
call :findpython
echo Rebirth FX Live Link plugin build with %PY% (%DATE% %TIME%)> "%LOG%"
%PY% "%~dp0build_editor_plugins.py" RebirthFxLiveLink >> "%LOG%" 2>&1
echo RUN COMPLETE exit=%ERRORLEVEL%>> "%LOG%"
type "%LOG%"
pause
exit /b

:findpython
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python399\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python399\python.exe"
if not defined PY set "PY=python"
exit /b
