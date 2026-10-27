@echo off
title Create a Character System editor 1.19 - taking the AnimBlueprint test container out, please leave this window open
rem Takes the AnimBlueprint test container CACS_AnimTemplateTest_P out of the game's ~mods folder again (close the game
rem first): its files are moved to C:\FF7R2UProj\_mod_backups\abp_test_<UTC time>\, and Cloud moves with the game's own
rem AnimBlueprint again.
rem Status: Tools\RebirthSkelCompat\build\abp_test_install_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\abp_test_install_status.txt"
echo AnimBlueprint test container removal, started %DATE% %TIME%> "%STATUS%"
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
%PY% "%~dp0abp_test_container.py" remove >> "%STATUS%" 2>&1
if errorlevel 1 (
  echo FAILED: see the line above.>> "%STATUS%"
  goto :done
)
echo DONE: the test container is out of ~mods.>> "%STATUS%"
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
