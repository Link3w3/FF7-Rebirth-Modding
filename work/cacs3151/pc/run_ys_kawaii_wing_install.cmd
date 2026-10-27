@echo off
title Young Sephiroth on KawaiiPhysics only - installing, please leave this window open
rem Young Sephiroth on KawaiiPhysics only (Create a Character System 3.14.0; close the game first):
rem   1. YoungSephiroth_P: his model PC0010_13 without its two BNMs (his body's PC0010_13_BNM and his wing's
rem      PC0010_13_Wing_BNM), its KDI (PC0010_13_KDI, the wing's KineDriver) kept (install_ys_kawaii_wing.py: the old
rem      files go to the game's _mod_backups\Paks\YoungSephiroth_P_<time>\);
rem   2. compat\YoungSephirothKawaii.json: his hair, coat, collar and wing on KawaiiPhysics, each swinging about the pose
rem      the KDI gives it (the one there kept as YoungSephirothKawaii.json.before_wing).
rem Status: Tools\RebirthSkelCompat\build\yswing_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\yswing_status.txt"
set "GAMEPAKS=C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH\End\Content\Paks"
set "COMPAT=C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH\End\Binaries\Win64\ue4ss\Mods\RebirthSkelCompat\compat"
echo Young Sephiroth on KawaiiPhysics only, started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close the game ^(%%P^) first, then run this again>> "%STATUS%"
    goto :done
  )
)
for %%F in (install_ys_kawaii_wing.py stage_yswing\YoungSephiroth_P.ucas.mid stage_yswing\YoungSephiroth_P.utoc stage_yswing\YoungSephirothKawaii.json) do (
  if not exist "%~dp0%%F" (
    echo FAILED: %%F is missing ^(tell Sandalphon^)>> "%STATUS%"
    goto :done
  )
)
call :findpython
%PY% "%~dp0install_ys_kawaii_wing.py" "%GAMEPAKS%" "%COMPAT%" >> "%STATUS%" 2>&1
if errorlevel 1 (
  echo FAILED: see above ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
echo DONE: start the game. The mod's log should say "Kawaii: ... hair 47 bone(s), coat 55 bone(s), collar 8 bone(s), wing 58 bone(s); Bonamik: no Bonamik on the model".>> "%STATUS%"
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
