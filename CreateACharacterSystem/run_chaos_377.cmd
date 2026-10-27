@echo off
rem Create a Character System 3.7.7, Vincent's CHAOS form. Builds the mod's DLL from src (a form's own shooter, the
rem Death Penalty on his gun, his motions in the air) and installs it; then, only if that worked, puts in place what the
rem CHAOS form needs:
rem   the mod's compat folder: VincentGalian.json (the forms NORMAL, GALIAN BEAST, CHAOS) and VincentChaos.json (Chaos's
rem   model in the Cloud family); ~mods\FullyPlayableVincentPaks: FullyPlayableVincentAssets_P (the Death Penalty's
rem   beam rows). What they replace goes to Tools\_backup\chaos377 first (the first run only: a second run keeps those).
rem Close the game first. Output: build\chaos377.log ("ALL DONE" at the end when everything went in).
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "LOG=%~dp0build\chaos377.log"
set "GAME=C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH"
set "MODDIR=%GAME%\End\Binaries\Win64\ue4ss\Mods\RebirthSkelCompat"
set "PAKS=%GAME%\End\Content\Paks\~mods\FullyPlayableVincentPaks"
set "STAGE=%~dp0stage377"
set "BACK=%~dp0..\_backup\chaos377"
echo Create a Character System 3.7.7 (CHAOS), started %DATE% %TIME% > "%LOG%"
echo Building and installing Create a Character System 3.7.7 (CHAOS); this takes a minute or two...
call :findpython
echo 1/2 building and installing the DLL with %PY%... >> "%LOG%"
%PY% "%~dp0build_dll.py" --install --pack-headers >> "%LOG%" 2>&1
set "RC=%ERRORLEVEL%"
echo    build exit=%RC% >> "%LOG%"
if not "%RC%"=="0" goto :buildfail
echo 2/2 the CHAOS form's files... >> "%LOG%"
if not exist "%BACK%" mkdir "%BACK%"
for %%F in (VincentGalian.json VincentChaos.json) do (
  if not exist "%BACK%\%%F" if exist "%MODDIR%\compat\%%F" copy /y "%MODDIR%\compat\%%F" "%BACK%\%%F" >nul
  copy /y "%STAGE%\compat\%%F" "%MODDIR%\compat\%%F" >nul || goto :copyfail
  echo    compat\%%F >> "%LOG%"
)
for %%E in (utoc ucas pak) do (
  if not exist "%BACK%\FullyPlayableVincentAssets_P.%%E" if exist "%PAKS%\FullyPlayableVincentAssets_P.%%E" copy /y "%PAKS%\FullyPlayableVincentAssets_P.%%E" "%BACK%\FullyPlayableVincentAssets_P.%%E" >nul
  copy /y "%STAGE%\paks\FullyPlayableVincentAssets_P.%%E" "%PAKS%\FullyPlayableVincentAssets_P.%%E" >nul || goto :copyfail
  echo    FullyPlayableVincentAssets_P.%%E >> "%LOG%"
)
echo ALL DONE %DATE% %TIME% >> "%LOG%"
echo.
echo Done: everything is in. (build\chaos377.log has the details.)
pause
exit /b 0

:buildfail
echo FAILED: the DLL did not build or install (is the game running?); nothing else was changed: tell Sandalphon >> "%LOG%"
echo.
echo FAILED: see build\chaos377.log
pause
exit /b 1

:copyfail
echo FAILED: a file could not be copied (is the game running?): tell Sandalphon >> "%LOG%"
echo.
echo FAILED: see build\chaos377.log
pause
exit /b 1

:findpython
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python399\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python399\python.exe"
if not defined PY set "PY=python"
exit /b
