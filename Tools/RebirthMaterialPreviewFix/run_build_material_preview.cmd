@echo off
rem Rebuilds the RebirthMaterialPreview End editor plugin (close the End editor first).
rem Output: build\run.log and build\latest.json
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "LOG=%~dp0build\run.log"
call :findpython
echo RebirthMaterialPreview plugin build with %PY% > "%LOG%"
%PY% "%~dp0build_material_preview.py" >> "%LOG%" 2>&1
echo RUN COMPLETE exit=%ERRORLEVEL%>> "%LOG%"
exit /b

:findpython
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python399\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python399\python.exe"
if not defined PY set "PY=python"
exit /b
