@echo off
title Create a Character System 3.9.3 - building and installing, please leave this window open
rem Create a Character System 3.9.3 (close the game first): builds the game mod 3.9.3 (main.dll) from
rem Tools\RebirthSkelCompat\src and installs it into the game (build_dll.py --install: the old main.dll is kept as
rem dlls\main.dll.bak-<time>). 3.9.3: ability pages - a form's ATB abilities 5 at a time, L1 / R1 turn the page while
rem the battle command menu is open (WINGED: 4 pages, FLYING: 2).
rem Status: Tools\RebirthSkelCompat\build\install393_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\install393_status.txt"
echo Create a Character System 3.9.3 install, started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close the game ^(%%P^) first, then run this again>> "%STATUS%"
    goto :done
  )
)
call :findpython
echo building the game mod 3.9.3 ^(main.dll^) and installing it...>> "%STATUS%"
%PY% "%~dp0build_dll.py" --install > "%~dp0build\install393_dll.log" 2>&1
if errorlevel 1 (
  echo FAILED: the game mod did not build ^(build\install393_dll.log^); nothing was changed>> "%STATUS%"
  goto :done
)
echo DONE: game mod 3.9.3 built and installed; start the game, the log should say "RebirthSkelCompat 3.9.3 starting">> "%STATUS%"
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
