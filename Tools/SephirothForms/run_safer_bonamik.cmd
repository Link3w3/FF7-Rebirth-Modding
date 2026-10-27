@echo off
title Safer Bonamik - running, please leave this window open
rem Safer Sephiroth's regular Bonamik (close the End editor and the game first):
rem   1. makes PC0010_999_BNM_Regular (make_safer_bonamik.py: his hair, his feathers, his body's collisions) and
rem      puts it on the PC0010_999 mesh in place of the v2 PC0010_999_BNM,
rem   2. packages the project (E:\FVIIREBIRTH\Pakage): his model folder in pakchunk49, the moves in pakchunk47.
rem Status: build\bonamik_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\bonamik_status.txt"
echo Safer Bonamik, started %DATE% %TIME%> "%STATUS%"
for %%P in (UE4Editor.exe UE4Editor-Cmd.exe ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close %%P first ^(the End editor or the game^), then run this again>> "%STATUS%"
    goto :done
  )
)
for %%F in (make_safer_bonamik.py run_safer_bonamik.ps1) do (
  if not exist "%~dp0%%F" (
    echo FAILED: %%F is missing>> "%STATUS%"
    goto :done
  )
)
echo 1/2 making his Bonamik...>> "%STATUS%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_safer_bonamik.ps1"
if errorlevel 1 (
  echo FAILED: the editor step ^(build\bonamik_editor.log, Saved\SaferBonamik\report.json^)>> "%STATUS%"
  goto :done
)
echo 2/2 packaging the project ^(this is the long part^)...>> "%STATUS%"
call "C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Build\BatchFiles\RunUAT.bat" -ScriptsForProject=C:/FF7R2UProj/End.uproject BuildCookRun -nocompileeditor -installed -nop4 -project=C:/FF7R2UProj/End.uproject -cook -stage -archive -archivedirectory=E:/FVIIREBIRTH/Pakage -package -ue4exe=C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Binaries\Win64\UE4Editor-Cmd.exe -compressed -ddc=InstalledDerivedDataBackendGraph -iostore -pak -iostore -prereqs -manifests -targetplatform=Win64 -build -target=End -clientconfig=Shipping -utf8output > "%~dp0build\bonamik_package.log" 2>&1
>> "%STATUS%" echo    package exit=%ERRORLEVEL%
:done
echo BONAMIK COMPLETE %DATE% %TIME%>> "%STATUS%"
type "%STATUS%"
pause
exit /b
