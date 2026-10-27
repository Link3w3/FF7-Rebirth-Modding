@echo off
title Create a Character System 3.10.0 + editor 1.15 (skins) - building, please leave this window open
rem Skins (close the game AND the End editor first):
rem   1. the game mod 3.10.0 (main.dll) from Tools\RebirthSkelCompat\src, installed into the game (build_dll.py --install:
rem      the old main.dll is kept as dlls\main.dll.bak-<time>): skins\<folder>\skin.json are read, each skin's skeleton
rem      joins its family and its characters wear its model (field and battle), with its voice and weapon.
rem   2. the editor plugin 1.15 (Plugins\RebirthSkelCompat): the Skins section and Build Skins in the Skeleton
rem      Compatibility data object.
rem Status: Tools\RebirthSkelCompat\build\install3100_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\install3100_status.txt"
echo Create a Character System 3.10.0 + editor 1.15, started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close the game ^(%%P^) first, then run this again>> "%STATUS%"
    goto :done
  )
)
tasklist /FI "IMAGENAME eq UE4Editor.exe" 2>nul | find /I "UE4Editor.exe" >nul
if not errorlevel 1 (
  echo REFUSED: close the End editor first ^(the plugin cannot be built while it runs^), then run this again>> "%STATUS%"
  goto :done
)
call :findpython
echo 1/2 building the game mod 3.10.0 ^(main.dll^) and installing it...>> "%STATUS%"
type "%STATUS%"
%PY% "%~dp0build_dll.py" --install > "%~dp0build\install3100_dll.log" 2>&1
if errorlevel 1 (
  echo FAILED: the game mod did not build ^(build\install3100_dll.log^); nothing was changed in the game>> "%STATUS%"
  goto :done
)
echo    OK: game mod 3.10.0 installed>> "%STATUS%"
echo 2/2 building the editor plugin 1.15...>> "%STATUS%"
cls
type "%STATUS%"
%PY% "%~dp0build_plugin.py" > "%~dp0build\install3100_plugin.log" 2>&1
if errorlevel 1 (
  echo FAILED: the editor plugin did not build ^(build\install3100_plugin.log^); the game mod is installed>> "%STATUS%"
  goto :done
)
echo    OK: editor plugin 1.15 built>> "%STATUS%"
echo DONE. Start the game: the mod's log ^(ue4ss\Mods\RebirthSkelCompat\RebirthSkelCompat.log^) should say "RebirthSkelCompat 3.10.0 starting" and "Skins: ...">> "%STATUS%"
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
