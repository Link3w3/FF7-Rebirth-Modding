@echo off
title Create a Character System 3.14.1 - building the game mod and installing it, please leave this window open
rem Create a Character System 3.14.1 (close the game first; the editor can stay open):
rem   builds the game mod 3.14.1 (main.dll) from Tools\RebirthSkelCompat\src and installs it (build_dll.py --install: the
rem   old main.dll is kept as dlls\main.dll.bak-<time>). KawaiiPhysics finds the meshes' pose buffers by GetBoneLocation
rem   (exact wherever the character is: 3.14.0's search missed far from the map's origin and switched KawaiiPhysics off),
rem   and looks again every 5 s when it has not found them. Everything else is 3.14.0's (already installed).
rem Status: Tools\RebirthSkelCompat\build\install3141_status.txt
rem Leave the window open until it says FINISHED (the build takes a few minutes; Ctrl+C stops it half way).
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\install3141_status.txt"
echo Create a Character System 3.14.1 game mod install, started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close the game ^(%%P^) first, then run this again>> "%STATUS%"
    goto :done
  )
)
for %%F in (build_dll.py src\RebirthSkelCompat.cpp src\SkelCompatCore.hpp src\KawaiiSolver.hpp) do (
  if not exist "%~dp0%%F" (
    echo FAILED: %%F is missing ^(tell Sandalphon^)>> "%STATUS%"
    goto :done
  )
)
findstr /L /C:"= L\"3.14.1\";" "%~dp0src\RebirthSkelCompat.cpp" >nul
if errorlevel 1 (
  echo FAILED: src\RebirthSkelCompat.cpp is not 3.14.1 ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
findstr /L /C:"KawaiiSolver.hpp" "%~dp0build_dll.py" >nul
if errorlevel 1 (
  echo FAILED: build_dll.py is not the 3.14.0 one ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
call :findpython
echo building the game mod 3.14.1 ^(main.dll^) and installing it ^(a few minutes^)...>> "%STATUS%"
type "%STATUS%"
%PY% "%~dp0build_dll.py" --install > "%~dp0build\install3141_dll.log" 2>&1
if errorlevel 1 goto :dllfailed
echo DONE: game mod 3.14.1 installed. Start the game: the mod's log should say "RebirthSkelCompat 3.14.1 starting" and, once Young Sephiroth shows, "Kawaii: the meshes' pose buffers are at ... by GetBoneLocation".>> "%STATUS%"
goto :done
:dllfailed
echo FAILED: the game mod did not build ^(build\install3141_dll.log^); nothing was changed: tell Sandalphon>> "%STATUS%"
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
