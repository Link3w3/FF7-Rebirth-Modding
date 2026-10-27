@echo off
title Create a Character System editor 1.20 - the weapon Blueprint test again: please leave this window open
rem The weapon Blueprint test of editor 1.20 again (close the End editor first; the game can stay open), now with the
rem cooked-load guard on (-RebirthSafeLoad, as in the editor): the first run's commandlet crashed loading the Essence
rem Shard's material chain without it. The plugin is already built: this only runs the test.
rem Status: Tools\RebirthSkelCompat\build\editor120_status.txt (log: build\weapon_template_editor.log)
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\editor120_status.txt"
echo The weapon Blueprint test again, started %DATE% %TIME%> "%STATUS%"
tasklist /FI "IMAGENAME eq UE4Editor.exe" 2>nul | find /I "UE4Editor.exe" >nul
if not errorlevel 1 goto editoropen
echo the weapon Blueprint test in an editor commandlet (a few minutes)...>> "%STATUS%"
type "%STATUS%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_weapon_template_test.ps1"
if errorlevel 1 goto notall
echo DONE: the Seraph weapon Blueprint is in your project. Tell Sandalphon: it checks the test container.>> "%STATUS%"
goto done
:editoropen
echo REFUSED: close the End editor (UE4Editor.exe) first, then run this again>> "%STATUS%"
goto done
:notall
echo NOT ALL OF THE TEST WENT THROUGH (above): tell Sandalphon.>> "%STATUS%"
:done
echo FINISHED %DATE% %TIME%>> "%STATUS%"
type "%STATUS%"
pause
