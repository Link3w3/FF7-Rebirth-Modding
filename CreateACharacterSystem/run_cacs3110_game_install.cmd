@echo off
title Create a Character System 3.11.0 (Customization) - building the game mod, please leave this window open
rem Create a Character System 3.11.0 (close the game first; the editor can stay open): builds the game mod 3.11.0
rem (main.dll) from Tools\RebirthSkelCompat\src and installs it into the game (build_dll.py --install: the old main.dll
rem is kept as dlls\main.dll.bak-<time>), then writes the Customization screen's catalog again
rem (make_customization_catalog.py: your newest materials and skins in it; the old catalog is kept as catalog.json.bak).
rem 3.11.0: the main menu gets a "Customization" item: materials, models, skins and parts of the character you control
rem (L2 / R2: the rest of the party), with a little preview of the character; Triangle / F saves the look.
rem Status: Tools\RebirthSkelCompat\build\install3110_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\install3110_status.txt"
echo Create a Character System 3.11.0 game mod install, started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close the game ^(%%P^) first, then run this again>> "%STATUS%"
    goto :done
  )
)
call :findpython
echo building the game mod 3.11.0 ^(main.dll^) and installing it...>> "%STATUS%"
type "%STATUS%"
%PY% "%~dp0build_dll.py" --install > "%~dp0build\install3110_dll.log" 2>&1
if errorlevel 1 (
  echo FAILED: the game mod did not build ^(build\install3110_dll.log^); nothing was changed>> "%STATUS%"
  goto :done
)
echo game mod 3.11.0 installed.>> "%STATUS%"
echo writing the Customization catalog...>> "%STATUS%"
%PY% "%~dp0make_customization_catalog.py" > "%~dp0build\install3110_catalog.log" 2>&1
if errorlevel 1 (
  echo   ^(the catalog was not written again: build\install3110_catalog.log; the one there stays^)>> "%STATUS%"
) else (
  echo   catalog written ^(build\install3110_catalog.log^)>> "%STATUS%"
)
echo DONE: start the game. The mod's log ^(ue4ss\Mods\RebirthSkelCompat\RebirthSkelCompat.log^) should say "RebirthSkelCompat 3.11.0 starting" and that the main menu gets a Customization item. Open the main menu: Customization is its last item.>> "%STATUS%"
:done
echo FINISHED %DATE% %TIME%>> "%STATUS%"
cls
type "%STATUS%"
pause
exit /b

:findpython
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python399\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python399\python.exe"
if not defined PY set "PY=python"
exit /b
