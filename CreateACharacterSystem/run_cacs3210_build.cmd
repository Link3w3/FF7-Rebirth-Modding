@echo off
rem Create a Character System 3.21.0: builds main.dll and checks it (exports, UE4SS imports). Nothing is installed:
rem the build is in build\<stamp>\ (build\latest.txt names it). Log: build\cacs3210_build.log
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "LOG=%~dp0build\cacs3210_build.log"
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY set "PY=python"
echo Create a Character System 3.21.0 build (not installed), started %DATE% %TIME% > "%LOG%"
%PY% "%~dp0build_dll.py" >> "%LOG%" 2>&1
echo RUN COMPLETE exit=%ERRORLEVEL%>> "%LOG%"
exit /b
