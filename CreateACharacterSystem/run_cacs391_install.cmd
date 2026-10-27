@echo off
title Create a Character System 3.9.1 - building and installing, please leave this window open
rem Create a Character System 3.9.1 for Fully Playable Young Sephiroth (close the game first):
rem   1. builds the game mod 3.9.1 (main.dll) from Tools\RebirthSkelCompat\src and installs it into the game
rem      (build_dll.py --install: the old main.dll is kept as dlls\main.dll.bak-<time>),
rem   2. puts YoungSephirothForms.json v4 in the mod's compat folder (the old one kept in _mod_backups):
rem      his voice per form, and Toad turns him into Cloud's frog ("looks_from").
rem Status: Tools\RebirthSkelCompat\build\install391_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\install391_status.txt"
set "GAME=C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH"
set "COMPAT=%GAME%\End\Binaries\Win64\ue4ss\Mods\RebirthSkelCompat\compat"
set "BACKUP=%GAME%\_mod_backups\cacs391_before_json"
echo Create a Character System 3.9.1 install, started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close the game ^(%%P^) first, then run this again>> "%STATUS%"
    goto :done
  )
)
if not exist "%~dp0_stage391\YoungSephirothForms.json" (
  echo FAILED: _stage391\YoungSephirothForms.json is missing>> "%STATUS%"
  goto :done
)
call :findpython
echo 1/2 building the game mod 3.9.1 ^(main.dll^) and installing it...>> "%STATUS%"
%PY% "%~dp0build_dll.py" --install > "%~dp0build\install391_dll.log" 2>&1
if errorlevel 1 (
  echo FAILED: the game mod did not build ^(build\install391_dll.log^); nothing was changed>> "%STATUS%"
  goto :done
)
echo    game mod 3.9.1 built and installed>> "%STATUS%"
echo 2/2 YoungSephirothForms.json v4...>> "%STATUS%"
if not exist "%BACKUP%" mkdir "%BACKUP%"
if exist "%COMPAT%\YoungSephirothForms.json" copy /Y "%COMPAT%\YoungSephirothForms.json" "%BACKUP%\YoungSephirothForms.json" >nul
copy /Y "%~dp0_stage391\YoungSephirothForms.json" "%COMPAT%\YoungSephirothForms.json" >nul
if errorlevel 1 (
  echo FAILED: the compat file was not copied>> "%STATUS%"
  goto :done
)
echo    compat file in place ^(the old one: _mod_backups\cacs391_before_json^)>> "%STATUS%"
echo DONE: start the game; the log should say "RebirthSkelCompat 3.9.1 starting">> "%STATUS%"
:done
echo INSTALL COMPLETE %DATE% %TIME%>> "%STATUS%"
type "%STATUS%"
pause
exit /b

:findpython
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python399\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python399\python.exe"
if not defined PY set "PY=python"
exit /b
