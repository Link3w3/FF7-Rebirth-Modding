@echo off
title Bizarro Sephiroth summon - installing his own moves
rem Puts Bizarro Sephiroth's own moves for his summon into the game. Close the game first.
rem   FullyPlayableSephirothDataAssets_P (.ucas, .utoc): the summon's abilities play his attacks, with his damage
rem   BizarroSummon.json: his own battle sets for the summon (Create a Character System)
rem The previous files are in C:\FF7R2UProj\Tools\SephirothForms-backups\backup-20261015d.
rem Status: build\install_moves_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\install_moves_status.txt"
echo Bizarro summon moves install started %DATE% %TIME%> "%STATUS%"
tasklist /FI "IMAGENAME eq ff7rebirth_.exe" 2>nul | find /I "ff7rebirth_.exe" >nul
if not errorlevel 1 goto :running
tasklist /FI "IMAGENAME eq ff7rebirth.exe" 2>nul | find /I "ff7rebirth.exe" >nul
if not errorlevel 1 goto :running
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_bizarro_moves.ps1"
>> "%STATUS%" echo install exit=%ERRORLEVEL%
goto :done
:running
echo REFUSED: the game is running. Close FINAL FANTASY VII REBIRTH, then run this again.>> "%STATUS%"
:done
echo.
type "%STATUS%"
pause
exit /b
