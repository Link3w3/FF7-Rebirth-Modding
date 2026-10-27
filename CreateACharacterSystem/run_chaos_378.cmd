@echo off
rem Create a Character System 3.7.8. Builds the mod's DLL from src and installs it; then, only if that worked, puts the
rem new VincentGalian.json in the mod's compat folder:
rem   CHAOS goes on the game's own way ("as_look": the game sets his physics and bone tables up for Chaos's model, so the
rem   wings stop taking Vincent's leg and hip physics), and his beam is the transformed Sephiroth's feeler laser for this
rem   test (Aerith's effect pack is no longer added to Cloud's pack: the suspect of the crashes while the game loads).
rem What it replaces goes to Tools\_backup\chaos378 first (the first run only: a second run keeps those).
rem Close the game first. Output: build\chaos378.log ("ALL DONE" at the end when everything went in).
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "LOG=%~dp0build\chaos378.log"
set "GAME=C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH"
set "MODDIR=%GAME%\End\Binaries\Win64\ue4ss\Mods\RebirthSkelCompat"
set "STAGE=%~dp0stage378"
set "BACK=%~dp0..\_backup\chaos378"
echo Create a Character System 3.7.8, started %DATE% %TIME% > "%LOG%"
echo Building and installing Create a Character System 3.7.8; this takes a minute or two...
call :findpython
echo 1/2 building and installing the DLL with %PY%... >> "%LOG%"
%PY% "%~dp0build_dll.py" --install --pack-headers >> "%LOG%" 2>&1
set "RC=%ERRORLEVEL%"
echo    build exit=%RC% >> "%LOG%"
if not "%RC%"=="0" goto :buildfail
echo 2/2 VincentGalian.json... >> "%LOG%"
if not exist "%BACK%" mkdir "%BACK%"
if not exist "%BACK%\VincentGalian.json" if exist "%MODDIR%\compat\VincentGalian.json" copy /y "%MODDIR%\compat\VincentGalian.json" "%BACK%\VincentGalian.json" >nul
copy /y "%STAGE%\compat\VincentGalian.json" "%MODDIR%\compat\VincentGalian.json" >nul || goto :copyfail
echo    compat\VincentGalian.json >> "%LOG%"
echo ALL DONE %DATE% %TIME% >> "%LOG%"
echo.
echo Done: everything is in. (build\chaos378.log has the details.)
pause
exit /b 0

:buildfail
echo FAILED: the DLL did not build or install (is the game running?); nothing else was changed: tell Sandalphon >> "%LOG%"
echo.
echo FAILED: see build\chaos378.log
pause
exit /b 1

:copyfail
echo FAILED: a file could not be copied (is the game running?): tell Sandalphon >> "%LOG%"
echo.
echo FAILED: see build\chaos378.log
pause
exit /b 1

:findpython
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python399\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python399\python.exe"
if not defined PY set "PY=python"
exit /b
