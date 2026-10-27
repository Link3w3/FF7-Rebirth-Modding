@echo off
title Create a Character System 3.11.2 (VOICES fix, skins with parts) - building the game mod, please leave this window open
rem Create a Character System 3.11.2 (close the game first; the editor can stay open): builds the game mod 3.11.2
rem (main.dll) from Tools\RebirthSkelCompat\src and installs it into the game (build_dll.py --install: the old main.dll
rem is kept as dlls\main.dll.bak-<time>), then writes the Customization screen's catalog again (the skins and voices in it).
rem 3.11.2: VOICES never loads a voice bank itself (the game does: a chosen voice speaks once the game has it loaded, the
rem screen says which ones are loaded now); a skin can wear extra meshes ("meshes": Remake Sephiroth's wing); the log
rem says where the screen's frames came from when it closes.
rem Already installed (game closed, backups in C:\FF7R2UProj\_mod_backups\install3112_before_20261022T192421Z):
rem   FullyPlayableYoungSephirothDataAssets_P v8 (the Classic Sephiroth voice in the 9 Cloud packs),
rem   CreateACharacterSkins_P and the 9 Sephiroth skins (ue4ss\Mods\RebirthSkelCompat\skins).
rem Status: Tools\RebirthSkelCompat\build\install3112_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\install3112_status.txt"
echo Create a Character System 3.11.2 game mod install, started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close the game ^(%%P^) first, then run this again>> "%STATUS%"
    goto :done
  )
)
call :findpython
echo building the game mod 3.11.2 ^(main.dll^) and installing it...>> "%STATUS%"
type "%STATUS%"
%PY% "%~dp0build_dll.py" --install > "%~dp0build\install3112_dll.log" 2>&1
if errorlevel 1 (
  echo FAILED: the game mod did not build ^(build\install3112_dll.log^); nothing was changed>> "%STATUS%"
  goto :done
)
echo game mod 3.11.2 installed.>> "%STATUS%"
echo writing the Customization catalog...>> "%STATUS%"
%PY% "%~dp0make_customization_catalog.py" > "%~dp0build\install3112_catalog.log" 2>&1
if errorlevel 1 (
  echo   ^(the catalog was not written again: build\install3112_catalog.log; the one there stays^)>> "%STATUS%"
) else (
  echo   catalog written ^(build\install3112_catalog.log^)>> "%STATUS%"
)
echo DONE: start the game. The mod's log should say "RebirthSkelCompat 3.11.2 starting". Customization: SKINS lists your 9 Sephiroths ^(Cross / Enter: wear, Triangle / F: save^); VOICES says which voices the game has loaded.>> "%STATUS%"
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
