@echo off
title Create a Character System 3.10.1 (skins) - building the game mod, please leave this window open
rem Create a Character System 3.10.1 (close the game first; the editor can stay open): builds the game mod 3.10.1
rem (main.dll) from Tools\RebirthSkelCompat\src and installs it into the game (build_dll.py --install: the old main.dll
rem is kept as dlls\main.dll.bak-<time>). 3.10: skins (ue4ss\Mods\RebirthSkelCompat\skins\<folder>\skin.json, their
rem packages in ~mods\CreateACharacterSkins_P): each skin's skeleton joins its family and its characters wear its model
rem in the field and in battle, with its voice and weapon. 3.10.1: a model a skin or form puts on shows all its parts (the
rem part numbers the old model had hidden no longer hide the new model's: Remake Sephiroth's face).
rem Status: Tools\RebirthSkelCompat\build\install3101_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\install3101_status.txt"
echo Create a Character System 3.10.1 game mod install, started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close the game ^(%%P^) first, then run this again>> "%STATUS%"
    goto :done
  )
)
call :findpython
echo building the game mod 3.10.1 ^(main.dll^) and installing it...>> "%STATUS%"
type "%STATUS%"
%PY% "%~dp0build_dll.py" --install > "%~dp0build\install3101_dll.log" 2>&1
if errorlevel 1 (
  echo FAILED: the game mod did not build ^(build\install3101_dll.log^); nothing was changed>> "%STATUS%"
  goto :done
)
echo DONE: game mod 3.10.1 installed. Start the game: the mod's log ^(ue4ss\Mods\RebirthSkelCompat\RebirthSkelCompat.log^) should say "RebirthSkelCompat 3.10.1 starting" and "Skins: ...">> "%STATUS%"
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
