@echo off
title Create a Character System 3.11.1 (Customization: menu fixes and VOICES) - building the game mod, please leave this window open
rem Create a Character System 3.11.1 (close the game first; the editor can stay open): builds the game mod 3.11.1
rem (main.dll) from Tools\RebirthSkelCompat\src and installs it into the game (build_dll.py --install: the old main.dll
rem is kept as dlls\main.dll.bak-<time>), then writes the Customization screen's catalog again
rem (make_customization_catalog.py: now with the voices; the old catalog is kept as catalog.json.bak).
rem 3.11.1: the screen runs every frame in the paused menu (no lag) and opens for the character you control; the
rem preview's lights no longer burn the characters out white; young Sephiroth's skins show; and a VOICES page: the
rem voice a character speaks with (Classic Sephiroth, Young Sephiroth, or any party member's).
rem The Classic Sephiroth voice (ClassicSephirothVoice_P) is already in ~mods\FullyPlayableSephirothPaks.
rem Status: Tools\RebirthSkelCompat\build\install3111_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\install3111_status.txt"
echo Create a Character System 3.11.1 game mod install, started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close the game ^(%%P^) first, then run this again>> "%STATUS%"
    goto :done
  )
)
call :findpython
echo building the game mod 3.11.1 ^(main.dll^) and installing it...>> "%STATUS%"
type "%STATUS%"
%PY% "%~dp0build_dll.py" --install > "%~dp0build\install3111_dll.log" 2>&1
if errorlevel 1 (
  echo FAILED: the game mod did not build ^(build\install3111_dll.log^); nothing was changed>> "%STATUS%"
  goto :done
)
echo game mod 3.11.1 installed.>> "%STATUS%"
echo writing the Customization catalog...>> "%STATUS%"
%PY% "%~dp0make_customization_catalog.py" > "%~dp0build\install3111_catalog.log" 2>&1
if errorlevel 1 (
  echo   ^(the catalog was not written again: build\install3111_catalog.log; the one there stays^)>> "%STATUS%"
) else (
  echo   catalog written ^(build\install3111_catalog.log^)>> "%STATUS%"
)
echo DONE: start the game. The mod's log ^(ue4ss\Mods\RebirthSkelCompat\RebirthSkelCompat.log^) should say "RebirthSkelCompat 3.11.1 starting". Open the main menu, Customization: VOICES is the fourth page ^(L1 R1 / Q E^); Cross / Enter speaks with a voice, Triangle / F saves it.>> "%STATUS%"
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
