@echo off
title Sephiroth Safer form - running, please leave this window open
rem Safer Sephiroth as a form of your playable Sephiroth (close the End editor and the game first; the move build and
rem the packaging at the end are the long parts):
rem   1. the Create a Character System editor plugin 1.12.1 (a form's Model Turn and Model Lift: Safer's model, made facing
rem      +Y and floating high, turned to face the game's way and brought down to the ground in his moves),
rem   2. packs CreateACharacterSystem-Setup-3.6.5.exe into Tools\Share again, with that plugin,
rem   3. puts his forms with SAFER (animation pack Battle06) in the SephirothForms data object, labels Safer's model folder
rem      (model, skeleton, wings, materials, textures) for chunk 49 and builds his 186 moves (safer\only.json) from his own
rem      animations, with the walks, runs and turns his idle leaning into Sephiroth's flying locomotion,
rem   4. packages the project (E:\FVIIREBIRTH\Pakage): his moves in pakchunk47, his model in pakchunk49.
rem The game mod 3.6.5 is installed already. Status: build\safer_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\safer_status.txt"
echo Sephiroth Safer form, started %DATE% %TIME%> "%STATUS%"
for %%P in (UE4Editor.exe UE4Editor-Cmd.exe ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close %%P first ^(the End editor or the game^), then run this again>> "%STATUS%"
    goto :done
  )
)
for %%F in (safer\only.json safer\forms_import.json safer\safer_moves.json build_safer_form.py run_safer_form.ps1) do (
  if not exist "%~dp0%%F" (
    echo FAILED: %%F is missing ^(run make_safer_files.py^)>> "%STATUS%"
    goto :done
  )
)
call :findpython
echo 1/4 building the Create a Character System editor plugin 1.12.1...>> "%STATUS%"
%PY% "C:\FF7R2UProj\Tools\EndEditorPlugins\build_editor_plugins.py" RebirthSkelCompatEditor > "%~dp0build\safer_plugin.log" 2>&1
if errorlevel 1 (
  echo FAILED: the plugin did not build ^(build\safer_plugin.log, Tools\EndEditorPlugins\build\latest.json^)>> "%STATUS%"
  goto :done
)
echo    plugin built>> "%STATUS%"
echo 2/4 packing the Create a Character System Setup into Tools\Share...>> "%STATUS%"
set "SC=C:\FF7R2UProj\Tools\RebirthSkelCompat"
set "LATEST="
if exist "%SC%\build\latest.txt" set /p LATEST=<"%SC%\build\latest.txt"
%PY% "C:\FF7R2UProj\Tools\CreateACharacterSystemSetup\make_setup.py" --stub "C:\FF7R2UProj\Tools\CreateACharacterSystemSetup\Setup.stub.exe" --main-dll "%LATEST%\main.dll" --readme "%SC%\mod\README.txt" --example "%SC%\mod\compat\example.json.txt" --source "%SC%\src\RebirthSkelCompat.cpp" --plugin "C:\FF7R2UProj\Plugins\RebirthSkelCompat" --out-dir "C:\FF7R2UProj\Tools\Share" > "%~dp0build\safer_setup.log" 2>&1
if errorlevel 1 (
  echo    the Setup was not packed ^(build\safer_setup.log^); going on>> "%STATUS%"
) else (
  echo    Setup packed ^(Tools\Share^)>> "%STATUS%"
)
echo 3/4 his forms, his model's chunk label and his 186 moves (the long part)...>> "%STATUS%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_safer_form.ps1"
if errorlevel 1 (
  echo FAILED: the editor step ^(build\safer_editor.log, Saved\RebirthSkelCompat\SephirothForms\safer_result.json and safer_build.txt^)>> "%STATUS%"
  goto :done
)
echo 4/4 packaging the project ^(this is the long part^)...>> "%STATUS%"
call "C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Build\BatchFiles\RunUAT.bat" -ScriptsForProject=C:/FF7R2UProj/End.uproject BuildCookRun -nocompileeditor -installed -nop4 -project=C:/FF7R2UProj/End.uproject -cook -stage -archive -archivedirectory=E:/FVIIREBIRTH/Pakage -package -ue4exe=C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Binaries\Win64\UE4Editor-Cmd.exe -compressed -ddc=InstalledDerivedDataBackendGraph -iostore -pak -iostore -prereqs -manifests -targetplatform=Win64 -build -target=End -clientconfig=Shipping -utf8output > "%~dp0build\safer_package.log" 2>&1
>> "%STATUS%" echo    package exit=%ERRORLEVEL%
:done
echo SAFER FORM COMPLETE %DATE% %TIME%>> "%STATUS%"
type "%STATUS%"
pause
exit /b

:findpython
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python399\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python399\python.exe"
if not defined PY set "PY=python"
exit /b
