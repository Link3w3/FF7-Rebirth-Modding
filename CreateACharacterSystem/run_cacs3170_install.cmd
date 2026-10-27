@echo off
title Create a Character System 3.17.0 (sync bones) - installing, please leave this window open
rem Create a Character System 3.17.0: Kawaii Dynamic Motions' sync bones (KawaiiPhysics' SyncBone: a coat's strips follow
rem the knees) and the feet as colliders, so a heel kicking back in a run or a kick goes through the cloth less often.
rem Close the game AND the End editor first. Four steps:
rem   1. the game mod 3.17.0 (main.dll, built from Tools\RebirthSkelCompat\src: build_dll.py --install; the old main.dll
rem      is kept as dlls\main.dll.bak-<time>, the mod's README.txt updated): "sync_bones", "interpolate_limits_in_substeps"
rem      and "keep_collision_side" in kawaii nodes;
rem   2. your kawaii files with sync bones and the feet (install_kawaii_jsons.py from stage_kawaii_3170:
rem      YoungSephirothKawaii, SephirothKawaii, CrisisCoreSephirothKawaii and BahamutFusedSephirothKawaii .json; each file
rem      there kept first in the game's _mod_backups\ue4ss\kawaii_3170_<time>; one you changed since is left alone);
rem   3. the End editor's plugin Kawaii Dynamic Motions 1.10 (install_kawaii_plugin.py from stage_kawaii_plugin110, the
rem      plugin there kept first in Tools\RebirthSkelCompat\_mod_backups\KawaiiPhysics_<time>);
rem   4. its build (build_kawaii_plugin.py): the node's Sync Bone settings, its preview, Export / Import For Game.
rem A step that fails is said; the others still go (4 needs 3).
rem Status: Tools\RebirthSkelCompat\build\cacs3170_install_status.txt
rem Leave the window open until it says FINISHED (5 - 15 minutes; Ctrl+C stops it half way).
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\cacs3170_install_status.txt"
echo Create a Character System 3.17.0 install ^(sync bones^), started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe UE4Editor.exe UE4Editor-Cmd.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close %%P first ^(the game or the End editor^), then run this again>> "%STATUS%"
    goto :done
  )
)
for %%F in (build_dll.py src\RebirthSkelCompat.cpp src\SkelCompatCore.hpp src\KawaiiSolver.hpp mod\README.txt install_kawaii_jsons.py stage_kawaii_3170\manifest.json install_kawaii_plugin.py build_kawaii_plugin.py stage_kawaii_plugin110\manifest.json) do (
  if not exist "%~dp0%%F" (
    echo FAILED: %%F is missing ^(tell Sandalphon^)>> "%STATUS%"
    goto :done
  )
)
findstr /L /C:"= L\"3.17.0\";" "%~dp0src\RebirthSkelCompat.cpp" >nul
if errorlevel 1 (
  echo FAILED: src\RebirthSkelCompat.cpp is not 3.17.0 ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
findstr /L /C:"ApplySyncBones" "%~dp0src\KawaiiSolver.hpp" >nul
if errorlevel 1 (
  echo FAILED: src\KawaiiSolver.hpp is not 3.17.0's ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
findstr /L /C:"ParseKawaiiSyncBones" "%~dp0src\SkelCompatCore.hpp" >nul
if errorlevel 1 (
  echo FAILED: src\SkelCompatCore.hpp is not 3.17.0's ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
findstr /L /C:"Create a Character System 3.17.0" "%~dp0mod\README.txt" >nul
if errorlevel 1 (
  echo FAILED: mod\README.txt is not 3.17.0's ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
call :findpython
set "PROBLEMS="
echo 1/4 building the game mod 3.17.0 ^(main.dll^) and installing it ^(a few minutes^)...>> "%STATUS%"
type "%STATUS%"
%PY% "%~dp0build_dll.py" --install > "%~dp0build\install3170_dll.log" 2>&1
if errorlevel 1 (
  echo    FAILED: the game mod did not build ^(build\install3170_dll.log^); the installed one was not changed>> "%STATUS%"
  set "PROBLEMS=1"
) else (
  echo    game mod 3.17.0 installed.>> "%STATUS%"
)
echo 2/4 your kawaii files with sync bones and the feet...>> "%STATUS%"
%PY% "%~dp0install_kawaii_jsons.py" "%~dp0stage_kawaii_3170" >> "%STATUS%" 2>&1
if errorlevel 1 set "PROBLEMS=1"
echo 3/4 the editor plugin Kawaii Dynamic Motions 1.10 ^(its files^)...>> "%STATUS%"
type "%STATUS%"
%PY% "%~dp0install_kawaii_plugin.py" "%~dp0stage_kawaii_plugin110" "C:\FF7R2UProj\Plugins" "%~dp0_mod_backups" >> "%STATUS%" 2>&1
if errorlevel 1 (
  echo    FAILED: the plugin's files did not all go in ^(above^); not built: tell Sandalphon>> "%STATUS%"
  set "PROBLEMS=1"
  goto :summary
)
echo 4/4 building the editor plugin 1.10 ^(a few minutes^)...>> "%STATUS%"
type "%STATUS%"
%PY% "%~dp0build_kawaii_plugin.py" > "%~dp0build\kawaii_plugin110_build.log" 2>&1
if errorlevel 1 (
  echo    FAILED: the plugin did not build ^(build\kawaii_plugin110_build.log^): tell Sandalphon>> "%STATUS%"
  set "PROBLEMS=1"
  goto :summary
)
echo    plugin 1.10 built.>> "%STATUS%"
:summary
if defined PROBLEMS (
  echo NOT ALL DONE: see the FAILED lines above, and tell Sandalphon>> "%STATUS%"
) else (
  echo DONE. The game: the log should say "RebirthSkelCompat 3.17.0 starting". Run and kick in a long coat: the coat>> "%STATUS%"
  echo   follows the knees and the heels no longer go through its back as often. The editor: a Kawaii node's details>> "%STATUS%"
  echo   have Sync Bone ^(Import From Game reads them from the kawaii files^).>> "%STATUS%"
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
