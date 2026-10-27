@echo off
title KawaiiPhysics for the End editor - installing and building the plugin, please leave this window open
rem KawaiiPhysics for the End editor (close the End editor first; the game can stay open):
rem   1. puts the plugin's files into C:\FF7R2UProj\Plugins\KawaiiPhysics (install_kawaii_plugin.py: from
rem      stage_kawaii_plugin, checked against its manifest; a KawaiiPhysics plugin already there goes to
rem      _mod_backups\KawaiiPhysics_<time>\ first);
rem   2. builds it (build_kawaii_plugin.py: UnrealBuildTool, only its modules KawaiiPhysics and KawaiiPhysicsEd).
rem Status: Tools\RebirthSkelCompat\build\kawaii_plugin_status.txt (the build's log: build\kawaii_plugin_build.log)
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\kawaii_plugin_status.txt"
echo KawaiiPhysics plugin install and build, started %DATE% %TIME%> "%STATUS%"
tasklist /FI "IMAGENAME eq UE4Editor.exe" 2>nul | find /I "UE4Editor.exe" >nul
if not errorlevel 1 (
  echo REFUSED: close the End editor ^(UE4Editor.exe^) first, then run this again>> "%STATUS%"
  goto :done
)
for %%F in (install_kawaii_plugin.py build_kawaii_plugin.py stage_kawaii_plugin\manifest.json) do (
  if not exist "%~dp0%%F" (
    echo FAILED: %%F is missing ^(tell Sandalphon^)>> "%STATUS%"
    goto :done
  )
)
call :findpython
echo 1/2 the plugin's files into Plugins\KawaiiPhysics...>> "%STATUS%"
%PY% "%~dp0install_kawaii_plugin.py" "%~dp0stage_kawaii_plugin" "C:\FF7R2UProj\Plugins" "%~dp0_mod_backups" >> "%STATUS%" 2>&1
if errorlevel 1 (
  echo FAILED: the files did not all go in ^(above^); the plugin was NOT built: tell Sandalphon>> "%STATUS%"
  goto :done
)
echo 2/2 building the plugin ^(a few minutes^)...>> "%STATUS%"
type "%STATUS%"
%PY% "%~dp0build_kawaii_plugin.py" > "%~dp0build\kawaii_plugin_build.log" 2>&1
if errorlevel 1 (
  echo FAILED: the plugin did not build ^(build\kawaii_plugin_build.log^): tell Sandalphon>> "%STATUS%"
  goto :done
)
echo DONE: start the editor. In an AnimBlueprint's AnimGraph, right-click: Kawaii Physics. Its details have Create a Character ^> Export For Game.>> "%STATUS%"
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
