@echo off
title Create a Character System 3.18.0 (KawaiiPhysics 1.21, skins with their own moves) and editor 1.21 - installing, please leave this window open
rem Create a Character System 3.18.0: the rest of KawaiiPhysics 1.21 in Kawaii Dynamic Motions: external forces (basic,
rem gravity, curve, wind, procedural wind with gusts and presets), the level's wind, the files' reusable sets, mirrored
rem shapes, the model's physics asset as shapes, the floor and the level's collision, world collision sweeps, shared
rem collision and winds, and animation triggers by the montage the character plays. Your kawaii files keep running as
rem before (what they do not name is off). Also skins that carry their own moves: a skin.json's "pack" and "sets"
rem (the CRISIS CORE skins' Battle10 and field set, the Dissidia NT skins' Battle12), written by editor 1.21.
rem Close the game AND the End editor first. Six steps:
rem   1. 3.17.0's step, not run yet: your kawaii files with sync bones and the feet (install_kawaii_jsons.py from
rem      stage_kawaii_3170: YoungSephirothKawaii, SephirothKawaii, CrisisCoreSephirothKawaii and
rem      BahamutFusedSephirothKawaii .json; each file there kept first in the game's _mod_backups\ue4ss\kawaii_3170_<time>;
rem      one you changed since is left alone);
rem   2. the game mod 3.18.0 (main.dll, built from Tools\RebirthSkelCompat\src: build_dll.py --install; the old main.dll
rem      is kept as dlls\main.dll.bak-<time>, the mod's README.txt updated);
rem   3. the End editor's plugin Kawaii Dynamic Motions 1.11 (install_kawaii_plugin.py from stage_kawaii_plugin111, the
rem      plugin there kept first in Tools\RebirthSkelCompat\_mod_backups\KawaiiPhysics_<time>);
rem   4. its build (build_kawaii_plugin.py): the node's forces, wind, sets, physics asset, mirror, shared and world
rem      collision, and the entry's animation triggers in Export / Import For Game;
rem   5. the editor plugin Create a Character System 1.21 (install_editor121.py from stage121: the data object's skins
rem      get Pack and Sets; the old files into C:\FF7R2UProj\_mod_backups\before_121_<time>);
rem   6. its build (build_editor_module.py RebirthSkelCompatEditor).
rem A step that fails is said; the others still go (4 needs 3, 6 needs 5).
rem Status: Tools\RebirthSkelCompat\build\cacs3180_install_status.txt
rem Leave the window open until it says FINISHED (5 - 15 minutes; Ctrl+C stops it half way).
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\cacs3180_install_status.txt"
echo Create a Character System 3.18.0 install ^(KawaiiPhysics 1.21^), started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe UE4Editor.exe UE4Editor-Cmd.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close %%P first ^(the game or the End editor^), then run this again>> "%STATUS%"
    goto :done
  )
)
for %%F in (build_dll.py src\RebirthSkelCompat.cpp src\SkelCompatCore.hpp src\KawaiiSolver.hpp mod\README.txt install_kawaii_jsons.py stage_kawaii_3170\manifest.json install_kawaii_plugin.py build_kawaii_plugin.py stage_kawaii_plugin111\manifest.json install_editor121.py build_editor_module.py stage121\manifest.json) do (
  if not exist "%~dp0%%F" (
    echo FAILED: %%F is missing ^(tell Sandalphon^)>> "%STATUS%"
    goto :done
  )
)
findstr /L /C:"= L\"3.18.0\";" "%~dp0src\RebirthSkelCompat.cpp" >nul
if errorlevel 1 (
  echo FAILED: src\RebirthSkelCompat.cpp is not 3.18.0 ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
findstr /L /C:"SkinPackUsable" "%~dp0src\RebirthSkelCompat.cpp" >nul
if errorlevel 1 (
  echo FAILED: src\RebirthSkelCompat.cpp is not 3.18.0's with skins' own moves ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
findstr /L /C:"\"1.21.0\"" "%~dp0stage121\manifest.json" >nul
if errorlevel 1 (
  echo FAILED: stage121 is not the editor 1.21.0 ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
findstr /L /C:"AdjustByWorldCollision" "%~dp0src\KawaiiSolver.hpp" >nul
if errorlevel 1 (
  echo FAILED: src\KawaiiSolver.hpp is not 3.18.0's ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
findstr /L /C:"KawaiiTriggerJson" "%~dp0src\SkelCompatCore.hpp" >nul
if errorlevel 1 (
  echo FAILED: src\SkelCompatCore.hpp is not 3.18.0's ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
findstr /L /C:"Create a Character System 3.18.0" "%~dp0mod\README.txt" >nul
if errorlevel 1 (
  echo FAILED: mod\README.txt is not 3.18.0's ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
findstr /L /C:"1.11.0-cacs3.18" "%~dp0stage_kawaii_plugin111\manifest.json" >nul
if errorlevel 1 (
  echo FAILED: stage_kawaii_plugin111 is not the plugin 1.11 ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
call :findpython
set "PROBLEMS="
echo 1/6 3.17.0's step: your kawaii files with sync bones and the feet...>> "%STATUS%"
type "%STATUS%"
%PY% "%~dp0install_kawaii_jsons.py" "%~dp0stage_kawaii_3170" >> "%STATUS%" 2>&1
if errorlevel 1 set "PROBLEMS=1"
echo 2/6 building the game mod 3.18.0 ^(main.dll^) and installing it ^(a few minutes^)...>> "%STATUS%"
type "%STATUS%"
%PY% "%~dp0build_dll.py" --install > "%~dp0build\install3180_dll.log" 2>&1
if errorlevel 1 (
  echo    FAILED: the game mod did not build ^(build\install3180_dll.log^); the installed one was not changed>> "%STATUS%"
  set "PROBLEMS=1"
) else (
  echo    game mod 3.18.0 installed.>> "%STATUS%"
)
echo 3/6 the editor plugin Kawaii Dynamic Motions 1.11 ^(its files^)...>> "%STATUS%"
type "%STATUS%"
%PY% "%~dp0install_kawaii_plugin.py" "%~dp0stage_kawaii_plugin111" "C:\FF7R2UProj\Plugins" "%~dp0_mod_backups" >> "%STATUS%" 2>&1
if errorlevel 1 (
  echo    FAILED: the plugin's files did not all go in ^(above^); not built: tell Sandalphon>> "%STATUS%"
  set "PROBLEMS=1"
  goto :editor121
)
echo 4/6 building the editor plugin 1.11 ^(a few minutes^)...>> "%STATUS%"
type "%STATUS%"
%PY% "%~dp0build_kawaii_plugin.py" > "%~dp0build\kawaii_plugin111_build.log" 2>&1
if errorlevel 1 (
  echo    FAILED: the plugin did not build ^(build\kawaii_plugin111_build.log^): tell Sandalphon>> "%STATUS%"
  set "PROBLEMS=1"
  goto :editor121
)
echo    plugin 1.11 built.>> "%STATUS%"
:editor121
if not exist "C:\FF7R2UProj\_mod_backups" mkdir "C:\FF7R2UProj\_mod_backups"
echo 5/6 the editor plugin Create a Character System 1.21 ^(its files^)...>> "%STATUS%"
type "%STATUS%"
%PY% "%~dp0install_editor121.py" "%~dp0stage121" "C:\FF7R2UProj\Plugins\RebirthSkelCompat" "%~dp0." "C:\FF7R2UProj\_mod_backups" >> "%STATUS%" 2>&1
if errorlevel 1 (
  echo    FAILED: the editor 1.21 files did not all go in ^(above^); not built: tell Sandalphon>> "%STATUS%"
  set "PROBLEMS=1"
  goto :summary
)
echo 6/6 building the editor plugin 1.21 ^(a few minutes^)...>> "%STATUS%"
type "%STATUS%"
%PY% "%~dp0build_editor_module.py" RebirthSkelCompatEditor "%~dp0build\plugin121_build.log" > "%~dp0build\plugin121_result.txt" 2>&1
if errorlevel 1 (
  type "%~dp0build\plugin121_result.txt" >> "%STATUS%"
  echo    FAILED: the editor plugin 1.21 did not build ^(build\plugin121_build.log^): tell Sandalphon. Its old files are in C:\FF7R2UProj\_mod_backups\before_121_*.>> "%STATUS%"
  set "PROBLEMS=1"
  goto :summary
)
echo    editor plugin 1.21 built.>> "%STATUS%"
:summary
if defined PROBLEMS (
  echo NOT ALL DONE: see the FAILED lines above, and tell Sandalphon>> "%STATUS%"
) else (
  echo DONE. The game: the log should say "RebirthSkelCompat 3.18.0 starting"; your kawaii files run as before, with>> "%STATUS%"
  echo   3.17.0's sync bones ^(the coats follow the knees^). The new keys are in the mod's README.txt ^(3.18.0^). The editor:>> "%STATUS%"
  echo   a Kawaii node's details have External Forces, Wind, Physics Asset Limits, Mirror Limits, Shared and World Collision,>> "%STATUS%"
  echo   and Export For Game the entry's Animation Triggers, Shared Winds and World Wind. The data object's skins have>> "%STATUS%"
  echo   Pack and Sets ^(editor 1.21^): open the editor and run Tools\Dissidia\morning_editor_1027.py next.>> "%STATUS%"
)
:done
echo FINISHED %DATE% %TIME%>> "%STATUS%"
type "%STATUS%"
pause
exit /b

:findpython
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python399\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python399\python.exe"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python39\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python39\python.exe"
if not defined PY set "PY=python"
exit /b
