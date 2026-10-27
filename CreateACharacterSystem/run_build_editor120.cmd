@echo off
title Create a Character System editor 1.20 - installing and building, then the weapon Blueprint test: please leave this window open
rem Create a Character System editor 1.20 (close the End editor first; the game can stay open):
rem   1. copies the 1.20 sources into the plugin (C:\FF7R2UProj\Plugins\RebirthSkelCompat: the Weapon Blueprint Maker, and
rem      the skin build's weapon Blueprints, Blender root scale and parent shaders; 1.19.1's texture bulk data offsets)
rem      and the tools into Tools\RebirthSkelCompat (weapon: the weapon templates read from your game, their maker, the
rem      editor test; README.md). The old files go to C:\FF7R2UProj\_mod_backups\before_120_<time>\ (outside the
rem      Plugins folder);
rem   2. builds the plugin (UnrealBuildTool, only its module);
rem   3. the weapon Blueprint test in an editor commandlet: Seraph Sephiroth's weapon Blueprint made from the cut-scale
rem      Masamune's template holding the Essence Shard (the class the Seraph skins' Weapon names), cooked alone into
rem      Tools\RebirthSkelCompat\weapon\out\CACS_WeaponTemplateTest_P (NOT installed); three more templates made and
rem      compiled in /Game/RebirthSkelCompat/WeaponTemplateTest.
rem Status: Tools\RebirthSkelCompat\build\editor120_status.txt (logs: build\plugin120_build.log,
rem build\weapon_template_editor.log; the test's result: C:\FF7R2UProj\Saved\RebirthSkelCompat\WeaponTemplate\result.json)
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\editor120_status.txt"
set "PLUGIN=C:\FF7R2UProj\Plugins\RebirthSkelCompat"
set "BACKUPS=C:\FF7R2UProj\_mod_backups"
set "STAGE=%~dp0stage120"
echo Create a Character System editor 1.20, started %DATE% %TIME%> "%STATUS%"
tasklist /FI "IMAGENAME eq UE4Editor.exe" 2>nul | find /I "UE4Editor.exe" >nul
if not errorlevel 1 (
  echo REFUSED: close the End editor ^(UE4Editor.exe^) first, then run this again>> "%STATUS%"
  goto :done
)
for %%F in (install_editor120.py build_editor_module.py run_weapon_template_test.ps1) do (
  if not exist "%~dp0%%F" (
    echo FAILED: %%F is missing ^(tell Sandalphon^)>> "%STATUS%"
    goto :done
  )
)
if not exist "%STAGE%\manifest.json" (
  echo FAILED: stage120\manifest.json is missing ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
if not exist "%PLUGIN%\RebirthSkelCompat.uplugin" (
  echo FAILED: %PLUGIN%\RebirthSkelCompat.uplugin is not there ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
if not exist "%BACKUPS%" mkdir "%BACKUPS%"
call :findpython
echo 1/3 the 1.20 files into place...>> "%STATUS%"
%PY% "%~dp0install_editor120.py" "%STAGE%" "%PLUGIN%" "%~dp0." "%BACKUPS%" >> "%STATUS%" 2>&1
if errorlevel 1 (
  echo FAILED: the files did not all go in ^(above^); nothing was built: tell Sandalphon>> "%STATUS%"
  goto :done
)
echo 2/3 building the plugin ^(a few minutes^)...>> "%STATUS%"
type "%STATUS%"
%PY% "%~dp0build_editor_module.py" RebirthSkelCompatEditor "%~dp0build\plugin120_build.log" > "%~dp0build\plugin120_result.txt" 2>&1
if errorlevel 1 (
  type "%~dp0build\plugin120_result.txt" >> "%STATUS%"
  echo FAILED: the plugin did not build ^(build\plugin120_build.log^): tell Sandalphon. Its old files are in %BACKUPS%\before_120_*.>> "%STATUS%"
  goto :done
)
echo    the plugin built>> "%STATUS%"
echo 3/3 the weapon Blueprint test in an editor commandlet ^(a few minutes^)...>> "%STATUS%"
type "%STATUS%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_weapon_template_test.ps1"
if errorlevel 1 (
  echo NOT ALL OF THE TEST WENT THROUGH ^(above^): tell Sandalphon. The plugin is built.>> "%STATUS%"
  goto :done
)
echo DONE: the editor has 1.20 and the Seraph weapon Blueprint is in your project. Tell Sandalphon: it checks the test container.>> "%STATUS%"
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
