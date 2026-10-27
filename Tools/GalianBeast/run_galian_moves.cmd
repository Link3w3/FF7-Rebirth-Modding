@echo off
title Vincent's Galian Beast - building its moves, please leave this window open
rem Vincent's Galian Beast form, step 2 (close the End editor and the game first; the packaging at the end is the long part):
rem   1. builds the Galian Beast's 385 moves in the End editor (Create a Character System editor plugin 1.12.4's Build
rem      Moves, one at a time: a move that stops the editor is left out and the editor goes on with the others), each of
rem      them made of the Galian boss's own animations: its attacks with Cloud's combo and cancel timing, its dodges,
rem      reactions, walks and runs, and ten of the boss's attacks for its commands; then takes Cloud's voice lines out of
rem      them (the beast does not talk) and lets the beast's trails and smoke play for its own abilities
rem      (galian_moves.json; Saved\RebirthSkelCompat\VincentGalian\ says how it went),
rem   2. packages the project (E:\FVIIREBIRTH\Pakage): the moves in pakchunk55.
rem Nothing in the game is changed by this; Sandalphon makes the install from what it builds.
rem Status: build\galian_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\galian_status.txt"
echo Galian Beast moves, started %DATE% %TIME%> "%STATUS%"
for %%P in (UE4Editor.exe UE4Editor-Cmd.exe ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close %%P first ^(the End editor or the game^), then run this again>> "%STATUS%"
    goto :done
  )
)
echo checking the files...>> "%STATUS%"
call :md5 "%~dp0build_galian_moves.py" 6b836f85100ac861ca41d6e73267d16b || goto :badfile
call :md5 "%~dp0galian_moves.json" cf8cde7108956aed6a7ab96f349a9a41 || goto :badfile
call :md5 "%~dp0galian_forms_import.json" ed06a242756a48fb95d14ff82f0b96c9 || goto :badfile
call :md5 "%~dp0run_galian_moves.ps1" dba9c92edaef7e6649552d1e15065b72 || goto :badfile
echo    all 4 as made>> "%STATUS%"
findstr /L /C:"1.12.4" "C:\FF7R2UProj\Plugins\RebirthSkelCompat\RebirthSkelCompat.uplugin" >nul
if errorlevel 1 (
  echo FAILED: the plugin in C:\FF7R2UProj\Plugins\RebirthSkelCompat is not 1.12.4 ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
echo 1/2 building the Galian Beast's moves in the editor ^(a while^)...>> "%STATUS%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_galian_moves.ps1"
if errorlevel 1 (
  echo FAILED: the editor step ^(build\galian_editor.log, Saved\RebirthSkelCompat\VincentGalian\build_result.json, progress.json and build_moves.txt^): tell Sandalphon>> "%STATUS%"
  goto :done
)
echo 2/2 packaging the project ^(this is the long part^)...>> "%STATUS%"
set "T0="
for /f %%T in ('powershell -NoProfile -Command "[DateTime]::UtcNow.Ticks"') do set "T0=%%T"
call "C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Build\BatchFiles\RunUAT.bat" -ScriptsForProject=C:/FF7R2UProj/End.uproject BuildCookRun -nocompileeditor -installed -nop4 -project=C:/FF7R2UProj/End.uproject -cook -stage -archive -archivedirectory=E:/FVIIREBIRTH/Pakage -package -ue4exe=C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Binaries\Win64\UE4Editor-Cmd.exe -compressed -ddc=InstalledDerivedDataBackendGraph -iostore -pak -iostore -prereqs -manifests -targetplatform=Win64 -build -target=End -clientconfig=Shipping -utf8output > "%~dp0build\galian_package.log" 2>&1
set "PKEXIT=%ERRORLEVEL%"
>> "%STATUS%" echo    package exit=%PKEXIT%
set "P55=E:\FVIIREBIRTH\Pakage\WindowsNoEditor\End\Content\Paks\pakchunk55-WindowsNoEditor.utoc"
if not exist "%P55%" (
  echo FAILED: pakchunk55 is NOT there ^(build\galian_package.log^): tell Sandalphon>> "%STATUS%"
  goto :done
)
rem (pakchunk55 has to be this packaging's, not one left from before)
powershell -NoProfile -Command "if ((Get-Item -LiteralPath '%P55%').LastWriteTimeUtc.Ticks -gt [long]'%T0%') { exit 0 } else { exit 1 }"
if errorlevel 1 (
  echo FAILED: pakchunk55 is an old one: the packaging did not make a new one ^(build\galian_package.log^): tell Sandalphon>> "%STATUS%"
  goto :done
)
if not "%PKEXIT%"=="0" (
  echo DONE, BUT the packaging ended with exit %PKEXIT% ^(pakchunk55 was made all the same^): tell Sandalphon>> "%STATUS%"
  goto :done
)
echo ALL DONE: pakchunk55 is there: tell Sandalphon, who makes the install from it>> "%STATUS%"
goto :done

:badfile
echo STOPPED: a file next to this is not the one made for it ^(see above^); nothing was changed: tell Sandalphon>> "%STATUS%"
goto :done

:done
echo GALIAN MOVES COMPLETE %DATE% %TIME%>> "%STATUS%"
type "%STATUS%"
pause
exit /b

:md5
certutil -hashfile "%~1" MD5 2>nul | findstr /i /c:"%~2" >nul
if not errorlevel 1 exit /b 0
echo    %~nx1 is not the expected file ^(md5 should be %~2^)>> "%STATUS%"
exit /b 1
