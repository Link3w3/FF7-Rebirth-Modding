@echo off
title Kawaii Dynamic Motions (Create a Character System 3.15.0) - installing, please leave this window open
rem Kawaii Dynamic Motions: KawaiiPhysics, named so now that it moves bones on its own too (close the game AND the End
rem editor first). Four steps:
rem   1. the game mod 3.15.0 (main.dll, built from Tools\RebirthSkelCompat\src: build_dll.py --install; the old main.dll
rem      is kept as dlls\main.dll.bak-<time>, the mod's README.txt updated): a node's "pose_waves" and "pose_animation"
rem      move its bones' pose before the physics runs, so chains sway or beat on their own with the physics on top;
rem   2. Bahamut Fused Sephiroth's compat file with his tail's sway and his blade wings' beat (install_kdm_compat.py: the
rem      file there kept first in the game's _mod_backups\ue4ss);
rem   3. the End editor's plugin 1.9, Kawaii Dynamic Motions (install_kawaii_plugin.py from stage_kawaii_plugin19, the
rem      plugin there kept first in Tools\RebirthSkelCompat\_mod_backups\KawaiiPhysics_<time>; build_kawaii_plugin.py):
rem      the motions in the node (its preview, Export For Game, Import From Game), with 1.8's Import From Game;
rem   4. the example, made in an editor commandlet (stage_kdm_example\run_kdm_example.py): Content/KawaiiDynamicMotions/
rem      Examples/BahamutFusedSephiroth/ABP_BahamutFusedSephiroth_KawaiiDynamicMotions and his two animations.
rem A step that fails is said; the others still go (4 needs 3).
rem Status: Tools\RebirthSkelCompat\build\kdm_install_status.txt
rem Leave the window open until it says FINISHED (10 - 20 minutes; Ctrl+C stops it half way).
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\kdm_install_status.txt"
echo Kawaii Dynamic Motions install ^(Create a Character System 3.15.0^), started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe UE4Editor.exe UE4Editor-Cmd.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close %%P first ^(the game or the End editor^), then run this again>> "%STATUS%"
    goto :done
  )
)
for %%F in (build_dll.py src\RebirthSkelCompat.cpp src\SkelCompatCore.hpp src\KawaiiSolver.hpp mod\README.txt install_kdm_compat.py install_kawaii_plugin.py build_kawaii_plugin.py stage_kawaii_plugin19\manifest.json stage_kdm_example\manifest.json stage_kdm_example\run_kdm_example.py stage_kdm_example\make_kdm_example.py) do (
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
set "PROBLEMS="
echo 1/4 building the game mod 3.15.0 ^(main.dll^) and installing it ^(a few minutes^)...>> "%STATUS%"
type "%STATUS%"
%PY% "%~dp0build_dll.py" --install > "%~dp0build\install3150_dll.log" 2>&1
if errorlevel 1 (
  echo    FAILED: the game mod did not build ^(build\install3150_dll.log^); the installed one was not changed>> "%STATUS%"
  set "PROBLEMS=1"
) else (
  echo    game mod 3.15.0 installed.>> "%STATUS%"
)
echo 2/4 Bahamut Fused Sephiroth's compat file...>> "%STATUS%"
%PY% "%~dp0install_kdm_compat.py" "%~dp0stage_kdm_example" >> "%STATUS%" 2>&1
if errorlevel 1 set "PROBLEMS=1"
echo 3/4 the editor plugin Kawaii Dynamic Motions 1.9 ^(its files, then the build: a few minutes^)...>> "%STATUS%"
type "%STATUS%"
%PY% "%~dp0install_kawaii_plugin.py" "%~dp0stage_kawaii_plugin19" "C:\FF7R2UProj\Plugins" "%~dp0_mod_backups" >> "%STATUS%" 2>&1
if errorlevel 1 (
  echo    FAILED: the plugin's files did not all go in ^(above^); not built, no example: tell Sandalphon>> "%STATUS%"
  set "PROBLEMS=1"
  goto :summary
)
%PY% "%~dp0build_kawaii_plugin.py" > "%~dp0build\kawaii_plugin19_build.log" 2>&1
if errorlevel 1 (
  echo    FAILED: the plugin did not build ^(build\kawaii_plugin19_build.log^); no example: tell Sandalphon>> "%STATUS%"
  set "PROBLEMS=1"
  goto :summary
)
echo    plugin 1.9 built.>> "%STATUS%"
echo 4/4 the example AnimBlueprint ^(an editor commandlet, no window: a few minutes^)...>> "%STATUS%"
type "%STATUS%"
%PY% "%~dp0stage_kdm_example\run_kdm_example.py" >> "%STATUS%" 2>&1
if errorlevel 1 (
  echo    FAILED: the example was not made ^(build\kdm_example_editor.log, Saved\KawaiiDynamicMotions\example_result.json^): tell Sandalphon>> "%STATUS%"
  set "PROBLEMS=1"
)
:summary
if defined PROBLEMS (
  echo NOT ALL DONE: see the FAILED lines above, and tell Sandalphon>> "%STATUS%"
) else (
  echo DONE. The game: wear a Bahamut skin; his tail sways and his blade wings beat slowly, even standing still ^(the log:>> "%STATUS%"
  echo   "RebirthSkelCompat 3.15.0 starting"^). The editor: Content\KawaiiDynamicMotions\Examples\BahamutFusedSephiroth\>> "%STATUS%"
  echo   ABP_BahamutFusedSephiroth_KawaiiDynamicMotions ^(the node's settings: Dynamic Motions; Import From Game is back^).>> "%STATUS%"
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
