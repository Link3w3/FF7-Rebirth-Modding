@echo off
title Create a Character System editor 1.20.1 - installing and building: please leave this window open
rem Create a Character System editor 1.20.1 (close the End editor first; the game can stay open):
rem   1. copies the 1.20.1 sources into the plugin (C:\FF7R2UProj\Plugins\RebirthSkelCompat: the skin build's weapon
rem      package walk leaves out the cooked textures a material instance keeps of its parent, so a skin whose weapon
rem      wears a material instance of the project builds) and README.md into Tools\RebirthSkelCompat. The old files go
rem      to C:\FF7R2UProj\_mod_backups\before_1201_<time>\ (outside the Plugins folder);
rem   2. builds the plugin (UnrealBuildTool, only its module).
rem Status: Tools\RebirthSkelCompat\build\editor1201_status.txt (log: build\plugin1201_build.log)
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\editor1201_status.txt"
set "PLUGIN=C:\FF7R2UProj\Plugins\RebirthSkelCompat"
set "BACKUPS=C:\FF7R2UProj\_mod_backups"
set "STAGE=%~dp0stage1201"
echo Create a Character System editor 1.20.1, started %DATE% %TIME%> "%STATUS%"
tasklist /FI "IMAGENAME eq UE4Editor.exe" 2>nul | find /I "UE4Editor.exe" >nul
if not errorlevel 1 (
  echo REFUSED: close the End editor ^(UE4Editor.exe^) first, then run this again>> "%STATUS%"
  goto :done
)
for %%F in (install_editor1201.py build_editor_module.py) do (
  if not exist "%~dp0%%F" (
    echo FAILED: %%F is missing ^(tell Sandalphon^)>> "%STATUS%"
    goto :done
  )
)
if not exist "%STAGE%\manifest.json" (
  echo FAILED: stage1201\manifest.json is missing ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
if not exist "%PLUGIN%\RebirthSkelCompat.uplugin" (
  echo FAILED: %PLUGIN%\RebirthSkelCompat.uplugin is not there ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
if not exist "%BACKUPS%" mkdir "%BACKUPS%"
call :findpython
echo 1/2 the 1.20.1 files into place...>> "%STATUS%"
%PY% "%~dp0install_editor1201.py" "%STAGE%" "%PLUGIN%" "%~dp0." "%BACKUPS%" >> "%STATUS%" 2>&1
if errorlevel 1 (
  echo FAILED: the files did not all go in ^(above^); nothing was built: tell Sandalphon>> "%STATUS%"
  goto :done
)
echo 2/2 building the plugin ^(a few minutes^)...>> "%STATUS%"
type "%STATUS%"
%PY% "%~dp0build_editor_module.py" RebirthSkelCompatEditor "%~dp0build\plugin1201_build.log" > "%~dp0build\plugin1201_result.txt" 2>&1
if errorlevel 1 (
  type "%~dp0build\plugin1201_result.txt" >> "%STATUS%"
  echo FAILED: the plugin did not build ^(build\plugin1201_build.log^): tell Sandalphon. Its old files are in %BACKUPS%\before_1201_*.>> "%STATUS%"
  goto :done
)
echo    the plugin built>> "%STATUS%"
echo DONE: the editor has 1.20.1. Open the editor again and tell Sandalphon: it builds the two Bahamut skins with the Sword of Light ^(keep the game closed^).>> "%STATUS%"
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
