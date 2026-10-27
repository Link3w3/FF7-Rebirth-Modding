@echo off
title Create a Character System 3.14.6 - building the game mod and installing it, please leave this window open
rem Create a Character System 3.14.6 (close the game first; the editor can stay open):
rem   builds the game mod 3.14.6 (main.dll) from Tools\RebirthSkelCompat\src and installs it (build_dll.py --install:
rem   the old main.dll is kept as dlls\main.dll.bak-<time>, the mod's README.txt updated):
rem     - each form plays its own combo again: a form switch puts the character's pack list back before the form's pack
rem       goes on (the game's SetPrimaryAnimPack adds packs, and its animations come from the first pack that has them:
rem       WINGED, FLYING and the rest played the Square chain of Young Sephiroth's pack, put on as the battle starts);
rem     - the COMBO page sets a combo for one form or for every form (a prompt as it is picked).
rem Status: Tools\RebirthSkelCompat\build\install3146_status.txt
rem Leave the window open until it says FINISHED (the build takes a few minutes; Ctrl+C stops it half way).
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\install3146_status.txt"
echo Create a Character System 3.14.6 game mod install, started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close the game ^(%%P^) first, then run this again>> "%STATUS%"
    goto :done
  )
)
for %%F in (build_dll.py src\RebirthSkelCompat.cpp src\SkelCompatCore.hpp src\KawaiiSolver.hpp mod\README.txt) do (
  if not exist "%~dp0%%F" (
    echo FAILED: %%F is missing ^(tell Sandalphon^)>> "%STATUS%"
    goto :done
  )
)
findstr /L /C:"= L\"3.14.6\";" "%~dp0src\RebirthSkelCompat.cpp" >nul
if errorlevel 1 (
  echo FAILED: src\RebirthSkelCompat.cpp is not 3.14.6 ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
findstr /L /C:"FormCombos" "%~dp0src\SkelCompatCore.hpp" >nul
if errorlevel 1 (
  echo FAILED: src\SkelCompatCore.hpp is not 3.14.6's ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
findstr /L /C:"Create a Character System 3.14.6" "%~dp0mod\README.txt" >nul
if errorlevel 1 (
  echo FAILED: mod\README.txt is not 3.14.6's ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
call :findpython
echo building the game mod 3.14.6 ^(main.dll^) and installing it ^(a few minutes^)...>> "%STATUS%"
type "%STATUS%"
%PY% "%~dp0build_dll.py" --install > "%~dp0build\install3146_dll.log" 2>&1
if errorlevel 1 goto :dllfailed
echo    game mod 3.14.6 installed.>> "%STATUS%"
echo DONE: start the game. The log should say "RebirthSkelCompat 3.14.6 starting", and after each form switch "its packs now (the first that has an animation gives it): key 3: Battle02" ^(one pack^).>> "%STATUS%"
goto :done
:dllfailed
echo FAILED: the game mod did not build ^(build\install3146_dll.log^); nothing was changed: tell Sandalphon>> "%STATUS%"
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
