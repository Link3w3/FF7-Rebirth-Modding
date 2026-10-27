@echo off
title Create a Character System editor 1.19 - installing the AnimBlueprint test container, please leave this window open
rem The in-game test of editor 1.19's editable AnimBlueprints (close the game first; the editor can stay open):
rem   copies the test container Tools\RebirthSkelCompat\abp\out\CACS_AnimTemplateTest_P (.utoc/.ucas/.pak) into the
rem   game's ~mods folder, after checking it is the one Sandalphon decoded and compared with the game's own. It holds Cloud's
rem   player AnimBlueprint (/Game/BluePrint/Animation/Player/PC0000_00_Cloud_Standard_Animation) as the editor rebuilt it
rem   from its template, so Cloud moves with it in the game. A copy already in ~mods is moved to
rem   C:\FF7R2UProj\_mod_backups\abp_test_<UTC time>\ first. run_abp_template_test_remove.cmd takes it out again.
rem Status: Tools\RebirthSkelCompat\build\abp_test_install_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\abp_test_install_status.txt"
echo AnimBlueprint test container install, started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close the game ^(%%P^) first, then run this again. Nothing was changed.>> "%STATUS%"
    goto :done
  )
)
if not exist "%~dp0abp_test_container.py" (
  echo FAILED: abp_test_container.py is missing ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
call :findpython
%PY% "%~dp0abp_test_container.py" install >> "%STATUS%" 2>&1
if errorlevel 1 (
  echo FAILED: see the line above. Nothing was changed.>> "%STATUS%"
  goto :done
)
echo DONE: start the game and play as Cloud: stand, walk, run, dash, turn on the spot and while running, stop from each,>> "%STATUS%"
echo   strafe, then attack and use abilities ^(montages on DefaultSlot^) and watch his face in a scene ^(FacialSlot^).>> "%STATUS%"
echo   Tell Sandalphon what differs from before. run_abp_template_test_remove.cmd ^(the game closed^) takes the test out.>> "%STATUS%"
:done
echo FINISHED %DATE% %TIME%>> "%STATUS%"
type "%STATUS%"
pause
exit /b

:findpython
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python399\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python399\python.exe"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python39\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python39\python.exe"
if not defined PY set "PY=python"
exit /b
