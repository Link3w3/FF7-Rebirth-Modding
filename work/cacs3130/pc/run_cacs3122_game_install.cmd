@echo off
title Create a Character System 3.12.2 - building the game mod and installing it, please leave this window open
rem Create a Character System 3.12.2 (close the game first; the editor can stay open):
rem   1. builds the game mod 3.12.2 (main.dll) from Tools\RebirthSkelCompat\src and installs it (build_dll.py --install:
rem      the old main.dll is kept as dlls\main.dll.bak-<time>): a combo picked on the COMBO page reaches the forms worn
rem      with a skin too; a form's "state_effects" (the game's special state effects: the boss Sephiroth's feelers) and
rem      "watch_damage" (the log counts a move's bullets);
rem   2. gives WINGED and FLYING the boss's feelers on the sword and the wing in both Sephiroth forms files
rem      (patch_feelers_3122.py; each file kept first as <name>.before3122).
rem Status: Tools\RebirthSkelCompat\build\install3122_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\install3122_status.txt"
set "COMPAT=C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH\End\Binaries\Win64\ue4ss\Mods\RebirthSkelCompat\compat"
echo Create a Character System 3.12.2 game mod install, started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close the game ^(%%P^) first, then run this again>> "%STATUS%"
    goto :done
  )
)
for %%F in (build_dll.py patch_feelers_3122.py) do (
  if not exist "%~dp0%%F" (
    echo FAILED: %%F is missing ^(tell Sandalphon^)>> "%STATUS%"
    goto :done
  )
)
findstr /L /C:"= L\"3.12.2\";" "%~dp0src\RebirthSkelCompat.cpp" >nul
if errorlevel 1 (
  echo FAILED: src\RebirthSkelCompat.cpp is not 3.12.2 ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
call :findpython
echo 1/2 building the game mod 3.12.2 ^(main.dll^) and installing it...>> "%STATUS%"
type "%STATUS%"
%PY% "%~dp0build_dll.py" --install > "%~dp0build\install3122_dll.log" 2>&1
if errorlevel 1 (
  echo FAILED: the game mod did not build ^(build\install3122_dll.log^); nothing was changed>> "%STATUS%"
  goto :done
)
echo    game mod 3.12.2 installed.>> "%STATUS%"
echo 2/2 the boss's feelers on WINGED and FLYING ^(the forms files^)...>> "%STATUS%"
if not exist "%COMPAT%" (
  echo    ^(the mod's compat folder was not found: %COMPAT%; the forms files were not changed^)>> "%STATUS%"
  goto :finish
)
%PY% "%~dp0patch_feelers_3122.py" "%COMPAT%" > "%~dp0build\install3122_feelers.log" 2>&1
if errorlevel 1 (
  echo    ^(a forms file was not changed: build\install3122_feelers.log^)>> "%STATUS%"
) else (
  type "%~dp0build\install3122_feelers.log">> "%STATUS%"
)
:finish
echo DONE: start the game. The mod's log should say "RebirthSkelCompat 3.12.2 starting"; in battle, WINGED says "the game's special state effects BossSephiroth_FeelerSword ... on".>> "%STATUS%"
:done
echo FINISHED %DATE% %TIME%>> "%STATUS%"
type "%STATUS%"
pause
exit /b

:findpython
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python399\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python399\python.exe"
if not defined PY set "PY=python"
exit /b
