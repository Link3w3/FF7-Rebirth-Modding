@echo off
title Vincent - building his Dirge of Cerberus walk and run, please leave this window open
rem Vincent's Dirge of Cerberus walk and run in battle that move him (close the End editor and the game first; the
rem packaging at the end is the long part):
rem   1. in the editor (build_dirge_locomotion.py, plan dirge_locomotion_plan.json): 43 moves built in Vincent_Moves, his
rem      battle walk, run and strafe animations, each his Dirge of Cerberus motion with the root motion of Cloud's
rem      animation of that name (the game moves a character by its walk's and run's root motion; the Dirge of Cerberus
rem      motions alone stand in place), one at a time: a move that stops the editor is left out and the others go on
rem      (Saved\RebirthSkelCompat\DirgeLocomotion\ says how it went),
rem   2. packages the project (E:\FVIIREBIRTH\Pakage): the moves in pakchunk46 with his melee combo.
rem Nothing is installed in the game: tell Sandalphon when it is done.
rem Status: build\loco_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\loco_status.txt"
echo Vincent Dirge of Cerberus walk and run, started %DATE% %TIME%> "%STATUS%"
for %%P in (UE4Editor.exe UE4Editor-Cmd.exe ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close %%P first ^(the End editor or the game^), then run this again>> "%STATUS%"
    goto :done
  )
)
for %%F in (dirge_locomotion_plan.json build_dirge_locomotion.py run_dirge_locomotion.ps1) do (
  if not exist "%~dp0%%F" (
    echo FAILED: %%F is missing>> "%STATUS%"
    goto :done
  )
)
findstr /L /C:"1.12.4" "C:\FF7R2UProj\Plugins\RebirthSkelCompat\RebirthSkelCompat.uplugin" >nul
if errorlevel 1 (
  echo FAILED: the plugin in C:\FF7R2UProj\Plugins\RebirthSkelCompat is not 1.12.4 ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
echo 1/2 building his walk and run in the editor ^(a while^)...>> "%STATUS%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_dirge_locomotion.ps1"
if errorlevel 1 (
  echo FAILED: the editor step ^(build\loco_editor.log, Saved\RebirthSkelCompat\DirgeLocomotion\build_result.json, progress.json and build_moves.txt^)>> "%STATUS%"
  goto :done
)
echo 2/2 packaging the project ^(this is the long part^)...>> "%STATUS%"
call "C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Build\BatchFiles\RunUAT.bat" -ScriptsForProject=C:/FF7R2UProj/End.uproject BuildCookRun -nocompileeditor -installed -nop4 -project=C:/FF7R2UProj/End.uproject -cook -stage -archive -archivedirectory=E:/FVIIREBIRTH/Pakage -package -ue4exe=C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Binaries\Win64\UE4Editor-Cmd.exe -compressed -ddc=InstalledDerivedDataBackendGraph -iostore -pak -iostore -prereqs -manifests -targetplatform=Win64 -build -target=End -clientconfig=Shipping -utf8output > "%~dp0build\loco_package.log" 2>&1
>> "%STATUS%" echo    package exit=%ERRORLEVEL%
if exist "E:\FVIIREBIRTH\Pakage\WindowsNoEditor\End\Content\Paks\pakchunk46-WindowsNoEditor.utoc" (
  echo    pakchunk46 is there: tell Sandalphon, who puts the moves into the mod>> "%STATUS%"
) else (
  echo    pakchunk46 is NOT there ^(build\loco_package.log^)>> "%STATUS%"
)
:done
echo DIRGE WALK AND RUN COMPLETE %DATE% %TIME%>> "%STATUS%"
type "%STATUS%"
pause
exit /b
