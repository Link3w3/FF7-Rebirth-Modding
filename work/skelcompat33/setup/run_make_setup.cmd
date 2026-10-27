@echo off
rem Packs Tools\Share\CreateACharacterSystem-Setup-<version>.exe (the Create a Character System Setup) from the latest builds:
rem   game mod:      Tools\RebirthSkelCompat\build\<latest>\main.dll, mod\README.txt, mod\compat\example.json.txt
rem   editor plugin: Plugins\RebirthSkelCompat (RebirthSkelCompat.uplugin, Binaries\Win64, Source)
rem Build both first: Tools\RebirthSkelCompat\run_build_dll.cmd (game closed) and
rem Tools\EndEditorPlugins\run_build_editor_plugins.cmd (editor closed).
rem Log: build\make_setup.log
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "LOG=%~dp0build\make_setup.log"
call :findpython
set "SC=%~dp0..\RebirthSkelCompat"
set "LATEST="
if exist "%SC%\build\latest.txt" set /p LATEST=<"%SC%\build\latest.txt"
if not defined LATEST (
  echo No DLL build found: run Tools\RebirthSkelCompat\run_build_dll.cmd first.> "%LOG%"
  goto :done
)
echo Create a Character System Setup, packed with %PY%> "%LOG%"
%PY% "%~dp0make_setup.py" --stub "%~dp0Setup.stub.exe" --main-dll "%LATEST%\main.dll" --readme "%SC%\mod\README.txt" --example "%SC%\mod\compat\example.json.txt" --source "%SC%\src\RebirthSkelCompat.cpp" --plugin "%~dp0..\..\Plugins\RebirthSkelCompat" --out-dir "%~dp0..\Share" >> "%LOG%" 2>&1
echo RUN COMPLETE exit=%ERRORLEVEL%>> "%LOG%"
:done
type "%LOG%"
pause
exit /b

:findpython
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python399\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python399\python.exe"
if not defined PY set "PY=python"
exit /b
