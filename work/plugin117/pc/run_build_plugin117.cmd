@echo off
title Create a Character System editor 1.17 - installing and building the editor plugin, please leave this window open
rem Create a Character System editor 1.17 (close the End editor first; the game can stay open):
rem   1. copies the plugin's 1.17 sources into C:\FF7R2UProj\Plugins\RebirthSkelCompat (the old ones into its
rem      _mod_backups\before_117_<time>\): the Skin Maker (Window > Rebirth Skin Maker, or right-click a Skeletal Mesh >
rem      Create a Character Skin...), the Parts Builder (Window > Rebirth Parts Builder, or right-click a Skeletal Mesh >
rem      Make a Customization Part...; a part's Effects), Build Skins for one skin and for a part's own assets, the
rem      game mod's 3.12.2 rules for Validate; and make_customization_catalog.py 3.13.0 into Tools\RebirthSkelCompat
rem      (the old one into its _mod_backups\before_117_<time>\);
rem   2. builds the plugin (build_plugin.py: UnrealBuildTool, only the plugin module).
rem Status: Tools\RebirthSkelCompat\build\plugin117_status.txt (the build's log: build\plugin117_build.log)
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\plugin117_status.txt"
set "PLUGIN=C:\FF7R2UProj\Plugins\RebirthSkelCompat"
set "STAGE=%~dp0stage117"
echo Create a Character System editor 1.17 plugin build, started %DATE% %TIME%> "%STATUS%"
tasklist /FI "IMAGENAME eq UE4Editor.exe" 2>nul | find /I "UE4Editor.exe" >nul
if not errorlevel 1 (
  echo REFUSED: close the End editor ^(UE4Editor.exe^) first, then run this again>> "%STATUS%"
  goto :done
)
for %%F in (build_plugin.py install_plugin117.py) do (
  if not exist "%~dp0%%F" (
    echo FAILED: %%F is missing ^(tell Sandalphon^)>> "%STATUS%"
    goto :done
  )
)
if not exist "%STAGE%\manifest.json" (
  echo FAILED: stage117\manifest.json is missing ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
call :findpython
echo 1/2 the 1.17 sources into the plugin, and the catalog maker...>> "%STATUS%"
%PY% "%~dp0install_plugin117.py" "%STAGE%" "%PLUGIN%" "%~dp0." >> "%STATUS%" 2>&1
if errorlevel 1 (
  echo FAILED: the files did not all go in ^(above^); the plugin was NOT built: tell Sandalphon>> "%STATUS%"
  goto :done
)
echo 2/2 building the plugin ^(a few minutes^)...>> "%STATUS%"
type "%STATUS%"
%PY% "%~dp0build_plugin.py" > "%~dp0build\plugin117_build.log" 2>&1
if errorlevel 1 (
  echo FAILED: the plugin did not build ^(build\plugin117_build.log^): tell Sandalphon. The editor still has the 1.16.2 plugin.>> "%STATUS%"
  goto :done
)
echo DONE: start the editor. Window has Rebirth Skin Maker and Rebirth Parts Builder; right-click a Skeletal Mesh for Create a Character Skin... and Make a Customization Part...>> "%STATUS%"
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
