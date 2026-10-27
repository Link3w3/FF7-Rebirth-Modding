@echo off
title Create a Character System 3.14.2 - building the game mod and installing it, please leave this window open
rem Create a Character System 3.14.2 (close the game first; the editor can stay open):
rem   1. builds the game mod 3.14.2 (main.dll) from Tools\RebirthSkelCompat\src and installs it (build_dll.py --install:
rem      the old main.dll is kept as dlls\main.dll.bak-<time>): 64 KawaiiPhysics nodes a model (16 before), fixed
rem      substeps that no longer shake above their step rate, and the log says why GetBoneLocation was not used;
rem   2. puts Young Sephiroth's new KawaiiPhysics file into compat (install_kawaii_3140.py: compat\YoungSephirothKawaii.json,
rem      a node a strand, strip, collar piece and feather, each with settings a little its own; the coat's strips untied).
rem      Only after the mod built: 3.14.1 reads 16 nodes of it.
rem Status: Tools\RebirthSkelCompat\build\install3142_status.txt
rem Leave the window open until it says FINISHED (the build takes a few minutes; Ctrl+C stops it half way).
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\install3142_status.txt"
set "COMPAT=C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH\End\Binaries\Win64\ue4ss\Mods\RebirthSkelCompat\compat"
echo Create a Character System 3.14.2 game mod install, started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close the game ^(%%P^) first, then run this again>> "%STATUS%"
    goto :done
  )
)
for %%F in (build_dll.py install_kawaii_3140.py src\RebirthSkelCompat.cpp src\SkelCompatCore.hpp src\KawaiiSolver.hpp compat_3140\YoungSephirothKawaii.json) do (
  if not exist "%~dp0%%F" (
    echo FAILED: %%F is missing ^(tell Sandalphon^)>> "%STATUS%"
    goto :done
  )
)
findstr /L /C:"= L\"3.14.2\";" "%~dp0src\RebirthSkelCompat.cpp" >nul
if errorlevel 1 (
  echo FAILED: src\RebirthSkelCompat.cpp is not 3.14.2 ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
findstr /L /C:"MaxKawaiiNodes = 64" "%~dp0src\SkelCompatCore.hpp" >nul
if errorlevel 1 (
  echo FAILED: src\SkelCompatCore.hpp is not 3.14.2's ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
findstr /L /C:"KawaiiSolver.hpp" "%~dp0build_dll.py" >nul
if errorlevel 1 (
  echo FAILED: build_dll.py is not the 3.14.0 one ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
call :findpython
echo 1/2 building the game mod 3.14.2 ^(main.dll^) and installing it ^(a few minutes^)...>> "%STATUS%"
type "%STATUS%"
%PY% "%~dp0build_dll.py" --install > "%~dp0build\install3142_dll.log" 2>&1
if errorlevel 1 goto :dllfailed
echo    game mod 3.14.2 installed.>> "%STATUS%"
echo 2/2 Young Sephiroth's KawaiiPhysics file ^(a node a chain^)...>> "%STATUS%"
rem (the folder's path has parentheses in it: it is only ever used in quotes, never inside a ( ) block)
if not exist "%COMPAT%\" goto :nocompat
%PY% "%~dp0install_kawaii_3140.py" "%COMPAT%" > "%~dp0build\install3142_kawaii.log" 2>&1
if errorlevel 1 goto :kawaiifailed
type "%~dp0build\install3142_kawaii.log">> "%STATUS%"
echo DONE: start the game. The mod's log should say "RebirthSkelCompat 3.14.2 starting" and, once Young Sephiroth shows, a "Kawaii: ..." line naming his 39 nodes ^(hair C_HairF ... wing K^).>> "%STATUS%"
goto :done
:nocompat
echo FAILED: the mod's compat folder was not found; the file was not put in ^(tell Sandalphon^)>> "%STATUS%"
goto :done
:kawaiifailed
echo FAILED: the file was not put in ^(build\install3142_kawaii.log^): tell Sandalphon>> "%STATUS%"
goto :done
:dllfailed
echo FAILED: the game mod did not build ^(build\install3142_dll.log^); nothing was changed: tell Sandalphon>> "%STATUS%"
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
