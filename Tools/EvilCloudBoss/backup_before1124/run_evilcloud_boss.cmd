@echo off
title Evil Cloud boss fights - building his moves, please leave this window open
rem Evil Cloud's boss fights, step 2 (close the End editor and the game first; the packaging at the end is the long part):
rem   1. builds Evil Cloud's 115 moves for the boss Sephiroth fights (the final battle and the VR battle): each of the
rem      boss's animations made of one of Cloud's, with the boss's own damage, AI, timing and phases
rem      (evilcloud_boss_moves.json; Saved\RebirthSkelCompat\EvilCloudBoss\ says how it went),
rem   2. packages the project (E:\FVIIREBIRTH\Pakage): the moves in pakchunk52.
rem Status: build\boss_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\boss_status.txt"
echo Evil Cloud boss moves, started %DATE% %TIME%> "%STATUS%"
for %%P in (UE4Editor.exe UE4Editor-Cmd.exe ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close %%P first ^(the End editor or the game^), then run this again>> "%STATUS%"
    goto :done
  )
)
for %%F in (evilcloud_boss_moves.json build_evilcloud_boss.py run_evilcloud_boss.ps1) do (
  if not exist "%~dp0%%F" (
    echo FAILED: %%F is missing>> "%STATUS%"
    goto :done
  )
)
echo 1/2 building Evil Cloud's moves in the editor ^(a while^)...>> "%STATUS%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_evilcloud_boss.ps1"
if errorlevel 1 (
  echo FAILED: the editor step ^(build\boss_editor.log, Saved\RebirthSkelCompat\EvilCloudBoss\build_result.json and build_moves.txt^)>> "%STATUS%"
  goto :done
)
echo 2/2 packaging the project ^(this is the long part^)...>> "%STATUS%"
call "C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Build\BatchFiles\RunUAT.bat" -ScriptsForProject=C:/FF7R2UProj/End.uproject BuildCookRun -nocompileeditor -installed -nop4 -project=C:/FF7R2UProj/End.uproject -cook -stage -archive -archivedirectory=E:/FVIIREBIRTH/Pakage -package -ue4exe=C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Binaries\Win64\UE4Editor-Cmd.exe -compressed -ddc=InstalledDerivedDataBackendGraph -iostore -pak -iostore -prereqs -manifests -targetplatform=Win64 -build -target=End -clientconfig=Shipping -utf8output > "%~dp0build\boss_package.log" 2>&1
>> "%STATUS%" echo    package exit=%ERRORLEVEL%
if exist "E:\FVIIREBIRTH\Pakage\WindowsNoEditor\End\Content\Paks\pakchunk52-WindowsNoEditor.utoc" (
  echo    pakchunk52 is there: tell Sandalphon, who puts the moves into the mod>> "%STATUS%"
) else (
  echo    pakchunk52 is NOT there ^(build\boss_package.log^)>> "%STATUS%"
)
:done
echo BOSS MOVES COMPLETE %DATE% %TIME%>> "%STATUS%"
type "%STATUS%"
pause
exit /b
