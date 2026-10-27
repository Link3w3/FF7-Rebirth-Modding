@echo off
title Sephiroth Bizarro form - running, please leave this window open
rem Builds Create a Character System 3.6 and your playable Sephiroth's Bizarro form (close the End editor and the game
rem first; it takes a while):
rem   1. the Create a Character System game mod 3.6.0 (main.dll, installed into the game: the forms menu, super armor,
rem      time limits and cooldowns),
rem   2. the Create a Character System editor plugin 1.11.0 (forms; clips and speed of built moves),
rem   3. packs CreateACharacterSystem-Setup-3.6.0.exe into Tools\Share from those two builds,
rem   4. his forms in the SephirothForms data object and the Bizarro form's moves (Battle05), built from Bizarro
rem      Sephiroth's animations,
rem   5. packages the project (E:\FVIIREBIRTH\Pakage), so the moves are in pakchunk47.
rem Status: build\bizarro_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\bizarro_status.txt"
echo Sephiroth Bizarro form started %DATE% %TIME%> "%STATUS%"
for %%P in (UE4Editor.exe UE4Editor-Cmd.exe ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close %%P first ^(the End editor or the game^), then run this again>> "%STATUS%"
    goto :done
  )
)
if not exist "%~dp0bizarro\bizarro_moves.json" (
  echo FAILED: bizarro\bizarro_moves.json is missing>> "%STATUS%"
  goto :done
)
call :findpython
echo 1/5 building the Create a Character System game mod 3.6.0 ^(main.dll, installed into the game^)...>> "%STATUS%"
%PY% "C:\FF7R2UProj\Tools\RebirthSkelCompat\build_dll.py" --install > "%~dp0build\bizarro_dll.log" 2>&1
if errorlevel 1 (
  echo FAILED: the game mod did not build ^(build\bizarro_dll.log, Tools\RebirthSkelCompat\build\latest.txt^)>> "%STATUS%"
  goto :done
)
echo    game mod built and installed>> "%STATUS%"
echo 2/5 building the Create a Character System editor plugin 1.11.0...>> "%STATUS%"
%PY% "C:\FF7R2UProj\Tools\EndEditorPlugins\build_editor_plugins.py" RebirthSkelCompatEditor > "%~dp0build\bizarro_plugin.log" 2>&1
if errorlevel 1 (
  echo FAILED: the plugin did not build ^(build\bizarro_plugin.log, Tools\EndEditorPlugins\build\latest.json^)>> "%STATUS%"
  goto :done
)
echo    plugin built>> "%STATUS%"
echo 3/5 packing the Create a Character System Setup into Tools\Share...>> "%STATUS%"
set "SC=C:\FF7R2UProj\Tools\RebirthSkelCompat"
set "LATEST="
if exist "%SC%\build\latest.txt" set /p LATEST=<"%SC%\build\latest.txt"
%PY% "C:\FF7R2UProj\Tools\CreateACharacterSystemSetup\make_setup.py" --stub "C:\FF7R2UProj\Tools\CreateACharacterSystemSetup\Setup.stub.exe" --main-dll "%LATEST%\main.dll" --readme "%SC%\mod\README.txt" --example "%SC%\mod\compat\example.json.txt" --source "%SC%\src\RebirthSkelCompat.cpp" --plugin "C:\FF7R2UProj\Plugins\RebirthSkelCompat" --out-dir "C:\FF7R2UProj\Tools\Share" > "%~dp0build\bizarro_setup.log" 2>&1
if errorlevel 1 (
  echo    the Setup was not packed ^(build\bizarro_setup.log^); going on>> "%STATUS%"
) else (
  echo    Setup packed ^(Tools\Share^)>> "%STATUS%"
)
echo 4/5 his forms and the Bizarro form's moves...>> "%STATUS%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_bizarro_form.ps1"
if errorlevel 1 (
  echo FAILED: the editor step ^(build\bizarro_editor.log, Saved\RebirthSkelCompat\SephirothForms\bizarro_result.json^)>> "%STATUS%"
  goto :done
)
echo 5/5 packaging the project ^(this is the long part^)...>> "%STATUS%"
call "C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Build\BatchFiles\RunUAT.bat" -ScriptsForProject=C:/FF7R2UProj/End.uproject BuildCookRun -nocompileeditor -installed -nop4 -project=C:/FF7R2UProj/End.uproject -cook -stage -archive -archivedirectory=E:/FVIIREBIRTH/Pakage -package -ue4exe=C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Binaries\Win64\UE4Editor-Cmd.exe -compressed -ddc=InstalledDerivedDataBackendGraph -iostore -pak -iostore -prereqs -manifests -targetplatform=Win64 -build -target=End -clientconfig=Shipping -utf8output > "%~dp0build\bizarro_package.log" 2>&1
>> "%STATUS%" echo    package exit=%ERRORLEVEL%
:done
echo BIZARRO FORM COMPLETE %DATE% %TIME%>> "%STATUS%"
type "%STATUS%"
pause
exit /b

:findpython
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python399\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python399\python.exe"
if not defined PY set "PY=python"
exit /b
