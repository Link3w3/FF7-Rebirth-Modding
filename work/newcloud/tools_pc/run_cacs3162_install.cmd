@echo off
title Create a Character System 3.16.2 - installing, please leave this window open
rem Create a Character System 3.16.2 (close the game first; the editor can stay open):
rem   builds the game mod 3.16.2 (main.dll) from Tools\RebirthSkelCompat\src and installs it (build_dll.py --install:
rem   the old main.dll is kept as dlls\main.dll.bak-<time>, the mod's README.txt updated). CLOUD's files are in from
rem   the 3.16.1 install: nothing else changes.
rem 3.16.2: CLOUD's changes go into the game's own table rows too (the game spawns a party member from the PlayerTable
rem row it found as it started, so 3.16.1's CLOUD still spawned Sephiroth); a CHARACTER page choice goes in at once
rem (after the battle when made in one): load a save and the party spawns with it; the log says which CharaSpec row
rem the character you control spawned.
rem Status: Tools\CloudCharacter\build\install3162_status.txt
rem Leave the window open until it says FINISHED (the build takes a few minutes; Ctrl+C stops it half way).
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\install3162_status.txt"
set "CACS=C:\FF7R2UProj\Tools\RebirthSkelCompat"
echo Create a Character System 3.16.2 install, started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close the game ^(%%P^) first, then run this again>> "%STATUS%"
    goto :done
  )
)
for %%F in (build_dll.py src\RebirthSkelCompat.cpp src\SkelCompatCore.hpp src\KawaiiSolver.hpp mod\README.txt) do (
  if not exist "%CACS%\%%F" (
    echo FAILED: Tools\RebirthSkelCompat\%%F is missing ^(tell Sandalphon^)>> "%STATUS%"
    goto :done
  )
)
findstr /L /C:"= L\"3.16.2\";" "%CACS%\src\RebirthSkelCompat.cpp" >nul
if errorlevel 1 (
  echo FAILED: Tools\RebirthSkelCompat\src\RebirthSkelCompat.cpp is not 3.16.2 ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
findstr /L /C:"int32_t Mirror(const Copy& copy" "%CACS%\src\RebirthSkelCompat.cpp" >nul
if errorlevel 1 (
  echo FAILED: Tools\RebirthSkelCompat\src\RebirthSkelCompat.cpp is not 3.16.2's ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
findstr /L /C:"Create a Character System 3.16.2" "%CACS%\mod\README.txt" >nul
if errorlevel 1 (
  echo FAILED: Tools\RebirthSkelCompat\mod\README.txt is not 3.16.2's ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
call :findpython
echo 1/2 building the game mod 3.16.2 ^(main.dll^) and installing it ^(a few minutes^)...>> "%STATUS%"
type "%STATUS%"
%PY% "%CACS%\build_dll.py" --install > "%~dp0build\install3162_dll.log" 2>&1
if errorlevel 1 (
  echo FAILED: the game mod did not build ^(Tools\CloudCharacter\build\install3162_dll.log^); nothing was changed: tell Sandalphon>> "%STATUS%"
  goto :done
)
echo    game mod 3.16.2 installed.>> "%STATUS%"
echo 2/2 done.>> "%STATUS%"
echo DONE: start the game. The log should say "RebirthSkelCompat 3.16.2 starting".>> "%STATUS%"
echo Then: Customization, CHARACTER, CLOUD ^(Cross^), back to the game, and load a save.>> "%STATUS%"
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
