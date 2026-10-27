@echo off
rem Builds RebirthSkelCompat main.dll, verifies it against the installed UE4SS.dll, installs it into the game.
rem Output: build\run-dll.log
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "LOG=%~dp0build\run-dll.log"
call :findpython
echo RebirthSkelCompat DLL build with %PY% > "%LOG%"
%PY% "%~dp0build_dll.py" --install --pack-headers >> "%LOG%" 2>&1
echo RUN COMPLETE exit=%ERRORLEVEL%>> "%LOG%"
exit /b

:findpython
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python399\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python399\python.exe"
if not defined PY set "PY=python"
exit /b
