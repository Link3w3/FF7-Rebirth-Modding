@echo off
title Create a Character System 3.15.0 - building the game mod and installing it, please leave this window open
rem Create a Character System 3.15.0 (close the game first; the editor can stay open):
rem   builds the game mod 3.15.0 (main.dll) from Tools\RebirthSkelCompat\src and installs it (build_dll.py --install:
rem   the old main.dll is kept as dlls\main.dll.bak-<time>, the mod's README.txt updated):
rem     - KawaiiPhysics animates bones too: a node's "pose_waves" (a tail's sway, a wing's slow beat) and
rem       "pose_animation" (a looping key animation, e.g. a creature's wing beat) turn the bones' pose before the
rem       physics runs, so chains move on their own with the physics on top (Bahamut Fused Sephiroth's tail and wings).
rem Status: Tools\RebirthSkelCompat\build\install3150_status.txt
rem Leave the window open until it says FINISHED (the build takes a few minutes; Ctrl+C stops it half way).
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\install3150_status.txt"
echo Create a Character System 3.15.0 game mod install, started %DATE% %TIME%> "%STATUS%"
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
findstr /L /C:"= L\"3.15.0\";" "%~dp0src\RebirthSkelCompat.cpp" >nul
if errorlevel 1 (
  echo FAILED: src\RebirthSkelCompat.cpp is not 3.15.0 ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
findstr /L /C:"AnimatePose" "%~dp0src\KawaiiSolver.hpp" >nul
if errorlevel 1 (
  echo FAILED: src\KawaiiSolver.hpp is not 3.15.0's ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
findstr /L /C:"ParseKawaiiPoseAnimation" "%~dp0src\SkelCompatCore.hpp" >nul
if errorlevel 1 (
  echo FAILED: src\SkelCompatCore.hpp is not 3.15.0's ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
findstr /L /C:"Create a Character System 3.15.0" "%~dp0mod\README.txt" >nul
if errorlevel 1 (
  echo FAILED: mod\README.txt is not 3.15.0's ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
call :findpython
echo building the game mod 3.15.0 ^(main.dll^) and installing it ^(a few minutes^)...>> "%STATUS%"
type "%STATUS%"
%PY% "%~dp0build_dll.py" --install > "%~dp0build\install3150_dll.log" 2>&1
if errorlevel 1 goto :dllfailed
echo    game mod 3.15.0 installed.>> "%STATUS%"
echo DONE: start the game and wear a Bahamut skin. The log should say "RebirthSkelCompat 3.15.0 starting"; his tail sways>> "%STATUS%"
echo   and his blade wings beat slowly even when he stands still.>> "%STATUS%"
goto :done
:dllfailed
echo FAILED: the game mod did not build ^(build\install3150_dll.log^); nothing was changed: tell Sandalphon>> "%STATUS%"
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
