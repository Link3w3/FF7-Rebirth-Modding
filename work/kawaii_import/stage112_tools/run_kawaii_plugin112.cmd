@echo off
title Kawaii Dynamic Motions 1.12 for the End editor - installing and building the plugin, please leave this window open
rem Kawaii Dynamic Motions 1.12 (with Create a Character System 3.20.0): the motions of animation sets (EndAnimSet) in the
rem node ("pose_animset": the set's motion of what the character plays, KH3-style in step with it with Sync), played by the
rem editor's preview, and planes as solid floors ("one_sided"). Close the End editor first (the game can stay open).
rem   1. the plugin's files into C:\FF7R2UProj\Plugins\KawaiiPhysics (install_kawaii_plugin.py from stage_kawaii_plugin112,
rem      checked against its manifest; the plugin there goes to _mod_backups\KawaiiPhysics_<time>\ first);
rem   2. its build (build_kawaii_plugin.py: UnrealBuildTool, only its modules KawaiiPhysics and KawaiiPhysicsEd); when it
rem      does not build, the plugin from before is put back (restore_kawaii_plugin.py) so the editor opens as it was.
rem   run_kawaii_plugin112.cmd wait reopen   waits up to 6 minutes for the editor to close first, and opens it again after.
rem Status: Tools\RebirthSkelCompat\build\kawaii_plugin112_status.txt (the build's log: build\kawaii_plugin112_build.log)
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\kawaii_plugin112_status.txt"
set "WAIT=%~1"
set "REOPEN=%~2"
echo Kawaii Dynamic Motions 1.12 plugin install and build, started %DATE% %TIME%> "%STATUS%"
if /I not "%WAIT%"=="wait" goto :check
echo waiting for the End editor to close...>> "%STATUS%"
for /L %%i in (1,1,180) do (
  tasklist /FI "IMAGENAME eq UE4Editor.exe" 2>nul | find /I "UE4Editor.exe" >nul
  if errorlevel 1 goto :check
  ping -n 3 127.0.0.1 >nul
)
:check
tasklist /FI "IMAGENAME eq UE4Editor.exe" 2>nul | find /I "UE4Editor.exe" >nul
if not errorlevel 1 (
  echo REFUSED: close the End editor ^(UE4Editor.exe^) first, then run this again>> "%STATUS%"
  goto :done
)
for %%F in (install_kawaii_plugin.py build_kawaii_plugin.py restore_kawaii_plugin.py stage_kawaii_plugin112\manifest.json) do (
  if not exist "%~dp0%%F" (
    echo FAILED: %%F is missing ^(tell Sandalphon^)>> "%STATUS%"
    goto :done
  )
)
findstr /L /C:"1.12.0-cacs3.20" "%~dp0stage_kawaii_plugin112\manifest.json" >nul
if errorlevel 1 (
  echo FAILED: stage_kawaii_plugin112 is not Kawaii Dynamic Motions 1.12 ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
call :findpython
echo 1/2 the plugin's files into Plugins\KawaiiPhysics...>> "%STATUS%"
%PY% "%~dp0install_kawaii_plugin.py" "%~dp0stage_kawaii_plugin112" "C:\FF7R2UProj\Plugins" "%~dp0_mod_backups" >> "%STATUS%" 2>&1
if errorlevel 1 (
  echo FAILED: the files did not all go in ^(above^); the plugin was NOT built: tell Sandalphon>> "%STATUS%"
  goto :done
)
echo 2/2 building the plugin ^(a few minutes^)...>> "%STATUS%"
%PY% "%~dp0build_kawaii_plugin.py" > "%~dp0build\kawaii_plugin112_build.log" 2>&1
if errorlevel 1 (
  echo FAILED: the plugin did not build ^(build\kawaii_plugin112_build.log^): tell Sandalphon. Putting the plugin from before back...>> "%STATUS%"
  %PY% "%~dp0restore_kawaii_plugin.py" "C:\FF7R2UProj\Plugins" "%~dp0_mod_backups" >> "%STATUS%" 2>&1
  goto :done
)
echo DONE: Kawaii Dynamic Motions 1.12 built.>> "%STATUS%"
:done
echo FINISHED %DATE% %TIME%>> "%STATUS%"
if /I not "%REOPEN%"=="reopen" goto :show
tasklist /FI "IMAGENAME eq UE4Editor.exe" 2>nul | find /I "UE4Editor.exe" >nul
if not errorlevel 1 exit /b
echo opening the End editor again>> "%STATUS%"
start "" "C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Binaries\Win64\UE4Editor.exe" "C:\FF7R2UProj\End.uproject"
exit /b
:show
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
