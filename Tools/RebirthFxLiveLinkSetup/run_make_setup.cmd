@echo off
rem Packs Tools\Share\RebirthFxLiveLink-Setup-<version>.exe (the Rebirth FX Live Link Setup) from:
rem   editor plugin: Plugins\RebirthFxLiveLink (build it first: Tools\EndEditorPlugins\run_build_fxlink.cmd, editor closed)
rem   game mod:      mod\RebirthLiveLink (Scripts\main.lua, README.txt, enabled.txt)
rem Log: build\make_setup.log
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "LOG=%~dp0build\make_setup.log"
call :findpython
echo Rebirth FX Live Link Setup, packed with %PY%> "%LOG%"
%PY% "%~dp0tools\make_setup.py" --stub "%~dp0Setup.stub.exe" --game "%~dp0mod\RebirthLiveLink" --plugin "%~dp0..\..\Plugins\RebirthFxLiveLink" --out-dir "%~dp0..\Share" >> "%LOG%" 2>&1
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
