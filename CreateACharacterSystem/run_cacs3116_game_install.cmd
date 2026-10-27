@echo off
title Create a Character System 3.11.6 (skins only where they can run) - building the game mod, please leave this window open
rem Create a Character System 3.11.6 (close the game first; the editor can stay open): builds the game mod 3.11.6
rem (main.dll) from Tools\RebirthSkelCompat\src and installs it into the game (build_dll.py --install: the old main.dll
rem is kept as dlls\main.dll.bak-<time>), then writes the Customization screen's catalog again (the skins and voices in it).
rem 3.11.6: a skin goes on only on a character whose AnimBlueprint runs on its model's skeleton (the Sephiroth skins on
rem Cloud without Fully Playable Sephiroth stood in their bind pose and could crash the game); with 3.11.5's no looks on rides.
rem Status: Tools\RebirthSkelCompat\build\install3116_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\install3116_status.txt"
echo Create a Character System 3.11.6 game mod install, started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close the game ^(%%P^) first, then run this again>> "%STATUS%"
    goto :done
  )
)
call :findpython
echo building the game mod 3.11.6 ^(main.dll^) and installing it...>> "%STATUS%"
type "%STATUS%"
%PY% "%~dp0build_dll.py" --install > "%~dp0build\install3116_dll.log" 2>&1
if errorlevel 1 (
  echo FAILED: the game mod did not build ^(build\install3116_dll.log^); nothing was changed>> "%STATUS%"
  goto :done
)
echo game mod 3.11.6 installed.>> "%STATUS%"
echo writing the Customization catalog...>> "%STATUS%"
%PY% "%~dp0make_customization_catalog.py" > "%~dp0build\install3116_catalog.log" 2>&1
if errorlevel 1 (
  echo   ^(the catalog was not written again: build\install3116_catalog.log; the one there stays^)>> "%STATUS%"
) else (
  echo   catalog written ^(build\install3116_catalog.log^)>> "%STATUS%"
)
echo DONE: start the game. The mod's log should say "RebirthSkelCompat 3.11.6 starting". A skin that cannot run on a character says so in the log ("NOT put on") instead of going on.>> "%STATUS%"
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
