@echo off
title Create a Character System 3.12.0 - building the game mod and installing its files, please leave this window open
rem Create a Character System 3.12.0 (close the game first; the editor can stay open):
rem   1. builds the game mod 3.12.0 (main.dll) from Tools\RebirthSkelCompat\src and installs it (build_dll.py --install:
rem      the old main.dll is kept as dlls\main.dll.bak-<time>): the Customization screen's WEAPONS, COMBO and PARTY pages,
rem      Skewer's carry (Impale), clipped chains, less frame work, the review's fixes;
rem   2. copies the forms files (compat\SephirothForms.json, compat\YoungSephirothForms.json: YOUNG SEPHIROTH's own
rem      moves, the winged whispers), the Lua mods (SephirothForms: main, ForceGrabs 2.0, MeteorStrike; RebirthLiveLink:
rem      main) and the mod's README into the game (the old ones into ue4ss\_mod_backups\cacs3120_<time>\);
rem   3. updates the installed Fully Playable (Young) Sephiroth data containers (the old files into Paks\_mod_backups\);
rem   4. writes the Customization screen's catalog again (the weapons in it).
rem Status: Tools\RebirthSkelCompat\build\install3120_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\install3120_status.txt"
set "GAME=C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH"
set "STAGE=%~dp0stage3120"
echo Create a Character System 3.12.0 game mod install, started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close the game ^(%%P^) first, then run this again>> "%STATUS%"
    goto :done
  )
)
for %%F in (build_dll.py install_cacs3120_files.py install_data_tail.py make_customization_catalog.py) do (
  if not exist "%~dp0%%F" (
    echo FAILED: %%F is missing ^(tell Sandalphon^)>> "%STATUS%"
    goto :done
  )
)
if not exist "%STAGE%\manifest.json" (
  echo FAILED: stage3120\manifest.json is missing ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
call :findpython
echo 1/4 building the game mod 3.12.0 ^(main.dll^) and installing it...>> "%STATUS%"
type "%STATUS%"
%PY% "%~dp0build_dll.py" --install > "%~dp0build\install3120_dll.log" 2>&1
if errorlevel 1 (
  echo FAILED: the game mod did not build ^(build\install3120_dll.log^); nothing was changed>> "%STATUS%"
  goto :done
)
echo    game mod 3.12.0 installed.>> "%STATUS%"
echo 2/4 and 3/4 the forms files, the Lua mods, the README and the data containers...>> "%STATUS%"
%PY% "%~dp0install_cacs3120_files.py" "%GAME%" "%STAGE%" >> "%STATUS%" 2>&1
if errorlevel 1 (
  echo    SOME FILES WERE NOT INSTALLED ^(above^): tell Sandalphon>> "%STATUS%"
) else (
  echo    all in.>> "%STATUS%"
)
echo 4/4 writing the Customization catalog...>> "%STATUS%"
%PY% "%~dp0make_customization_catalog.py" > "%~dp0build\install3120_catalog.log" 2>&1
if errorlevel 1 (
  echo    ^(the catalog was not written again: build\install3120_catalog.log; the one there stays^)>> "%STATUS%"
) else (
  echo    catalog written ^(build\install3120_catalog.log^)>> "%STATUS%"
)
echo DONE: start the game. The mod's log should say "RebirthSkelCompat 3.12.0 starting". Young Sephiroth: his normal form plays his own moves; the Customization screen has WEAPONS, COMBO and PARTY.>> "%STATUS%"
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
