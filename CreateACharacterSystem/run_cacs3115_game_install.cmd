@echo off
title Create a Character System 3.11.5 (no looks on rides) - building the game mod, please leave this window open
rem Create a Character System 3.11.5 (close the game first; the editor can stay open): builds the game mod 3.11.5
rem (main.dll) from Tools\RebirthSkelCompat\src and installs it into the game (build_dll.py --install: the old main.dll
rem is kept as dlls\main.dll.bak-<time>), then writes the Customization screen's catalog again (the skins and voices in it).
rem 3.11.5: Customization puts no looks on rides (a vehicle or a mount you control: the rental bike, a chocobo, the
rem Tiny Bronco, ...): on one, the screen is for the one riding; a saved look for a ride's model is left out.
rem Status: Tools\RebirthSkelCompat\build\install3115_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\install3115_status.txt"
echo Create a Character System 3.11.5 game mod install, started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close the game ^(%%P^) first, then run this again>> "%STATUS%"
    goto :done
  )
)
call :findpython
echo building the game mod 3.11.5 ^(main.dll^) and installing it...>> "%STATUS%"
type "%STATUS%"
%PY% "%~dp0build_dll.py" --install > "%~dp0build\install3115_dll.log" 2>&1
if errorlevel 1 (
  echo FAILED: the game mod did not build ^(build\install3115_dll.log^); nothing was changed>> "%STATUS%"
  goto :done
)
echo game mod 3.11.5 installed.>> "%STATUS%"
echo writing the Customization catalog...>> "%STATUS%"
%PY% "%~dp0make_customization_catalog.py" > "%~dp0build\install3115_catalog.log" 2>&1
if errorlevel 1 (
  echo   ^(the catalog was not written again: build\install3115_catalog.log; the one there stays^)>> "%STATUS%"
) else (
  echo   catalog written ^(build\install3115_catalog.log^)>> "%STATUS%"
)
echo DONE: start the game. The mod's log should say "RebirthSkelCompat 3.11.5 starting". Customization opened while you ride something is for the one riding.>> "%STATUS%"
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
