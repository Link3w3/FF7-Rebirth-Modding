@echo off
title Remake Sephiroth skin with Remake's Masamune - installing, please leave this window open
rem Installs the Remake Sephiroth skin with Remake's Masamune into the game (close the game first; the editor can stay open):
rem   * skins\RemakeSephiroth: the skin as it is installed now, plus the Remake Masamune (WE1021_00: its mesh, its skeleton
rem     with the game's 13 weapon sockets, and its weapon blueprint WE1021_00_SephirothIllusion_Masamune, which keeps its
rem     name); skin.json's weapon is that blueprint;
rem   * ~mods\CreateACharacterSkins_P written again from every skin folder (the installed one plus those 3 packages);
rem   * ~mods\RebirthGameMaterials_P: the installed one byte for byte, plus the Masamune's own Remake material
rem     (WE1021_00_Body, compiled for the game) and its 4 textures.
rem What it replaces is moved first to C:\FF7R2UProj\_mod_backups\RemakeMasamune_<UTC time>\ (put back if a step fails),
rem then the Customization screen's catalog is written again.
rem Status: Tools\RebirthSkelCompat\build\remake_masamune_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\remake_masamune_status.txt"
set "PROJ=%~dp0..\.."
echo Remake Masamune install, started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close the game ^(%%P^) first, then run this again. Nothing was changed.>> "%STATUS%"
    goto :done
  )
)
call :findpython
%PY% "%~dp0install_skin_update.py" --name RemakeMasamune --project "%PROJ%" --skin "%PROJ%\Saved\RebirthSkelCompat\Skins\_work\RemakeMasamune\stage\RemakeSephiroth" --gm "%PROJ%\Saved\RebirthGameMaterials\mod" >> "%STATUS%" 2>&1
if errorlevel 1 (
  echo FAILED: see the lines above. The game's files are as they were.>> "%STATUS%"
  goto :done
)
%PY% "%~dp0make_customization_catalog.py" > "%~dp0build\remake_masamune_catalog.log" 2>&1
if errorlevel 1 (
  echo   ^(the Customization catalog was not written again: build\remake_masamune_catalog.log; the one there stays^)>> "%STATUS%"
) else (
  echo   Customization catalog written again>> "%STATUS%"
)
echo DONE: start the game. The mod's log should say "Skin Remake Sephiroth ... weapon: WE1021_00_SephirothIllusion_Masamune_C; 7 package(s)".>> "%STATUS%"
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
