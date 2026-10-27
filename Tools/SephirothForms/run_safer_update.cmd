@echo off
title Safer update - running, please leave this window open
rem Safer Sephiroth's update (close the End editor and the game first; the packaging at the end is the long part):
rem   1. the Create a Character System editor plugin 1.12.3 (moves made of part of another character: the little
rem      Sephiroth on Bizarro's head moving Safer's upper body; only an animation's sounds; notifies from composites),
rem   2. the game mod 3.6.6 (main.dll, installed into the game): a form's entrance (a flash, its animation, a descent
rem      from the sky, a cinematic camera),
rem   3. packs CreateACharacterSystem-Setup into Tools\Share again, with both,
rem   4. builds Safer's 27 new moves: Bizarro's twelve abilities on Safer, and his entrance (safer\safer_atb_moves.json),
rem   5. packages the project (E:\FVIIREBIRTH\Pakage): the moves in pakchunk47, his model folder in pakchunk49.
rem His regular Bonamik (run_safer_bonamik.cmd) is in the project already: it is packaged with the rest.
rem Status: build\update_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\update_status.txt"
echo Safer update, started %DATE% %TIME%> "%STATUS%"
for %%P in (UE4Editor.exe UE4Editor-Cmd.exe ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close %%P first ^(the End editor or the game^), then run this again>> "%STATUS%"
    goto :done
  )
)
for %%F in (safer\forms_import.json safer\safer_moves.json safer\safer_atb_moves.json bizarro\bizarro_moves.json build_safer_update.py run_safer_update.ps1) do (
  if not exist "%~dp0%%F" (
    echo FAILED: %%F is missing>> "%STATUS%"
    goto :done
  )
)
call :findpython
echo 1/5 building the Create a Character System editor plugin 1.12.3...>> "%STATUS%"
%PY% "C:\FF7R2UProj\Tools\EndEditorPlugins\build_editor_plugins.py" RebirthSkelCompatEditor > "%~dp0build\update_plugin.log" 2>&1
if errorlevel 1 (
  echo FAILED: the plugin did not build ^(build\update_plugin.log, Tools\EndEditorPlugins\build\latest.json^)>> "%STATUS%"
  goto :done
)
echo    plugin built>> "%STATUS%"
echo 2/5 building the Create a Character System game mod 3.6.6 ^(main.dll, installed into the game^)...>> "%STATUS%"
%PY% "C:\FF7R2UProj\Tools\RebirthSkelCompat\build_dll.py" --install > "%~dp0build\update_dll.log" 2>&1
if errorlevel 1 (
  echo FAILED: the game mod did not build ^(build\update_dll.log, Tools\RebirthSkelCompat\build\latest.txt^)>> "%STATUS%"
  goto :done
)
echo    game mod built and installed>> "%STATUS%"
echo 3/5 packing the Create a Character System Setup into Tools\Share...>> "%STATUS%"
set "SC=C:\FF7R2UProj\Tools\RebirthSkelCompat"
set "LATEST="
if exist "%SC%\build\latest.txt" set /p LATEST=<"%SC%\build\latest.txt"
%PY% "C:\FF7R2UProj\Tools\CreateACharacterSystemSetup\make_setup.py" --stub "C:\FF7R2UProj\Tools\CreateACharacterSystemSetup\Setup.stub.exe" --main-dll "%LATEST%\main.dll" --readme "%SC%\mod\README.txt" --example "%SC%\mod\compat\example.json.txt" --source "%SC%\src\RebirthSkelCompat.cpp" --plugin "C:\FF7R2UProj\Plugins\RebirthSkelCompat" --out-dir "C:\FF7R2UProj\Tools\Share" > "%~dp0build\update_setup.log" 2>&1
if errorlevel 1 (
  echo    the Setup was not packed ^(build\update_setup.log^); going on>> "%STATUS%"
) else (
  echo    Setup packed ^(Tools\Share^)>> "%STATUS%"
)
echo 4/5 Safer's new moves...>> "%STATUS%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_safer_update.ps1"
if errorlevel 1 (
  echo FAILED: the editor step ^(build\update_editor.log, Saved\RebirthSkelCompat\SephirothForms\safer_update_result.json and safer_update_build.txt^)>> "%STATUS%"
  goto :done
)
echo 5/5 packaging the project ^(this is the long part^)...>> "%STATUS%"
call "C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Build\BatchFiles\RunUAT.bat" -ScriptsForProject=C:/FF7R2UProj/End.uproject BuildCookRun -nocompileeditor -installed -nop4 -project=C:/FF7R2UProj/End.uproject -cook -stage -archive -archivedirectory=E:/FVIIREBIRTH/Pakage -package -ue4exe=C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Binaries\Win64\UE4Editor-Cmd.exe -compressed -ddc=InstalledDerivedDataBackendGraph -iostore -pak -iostore -prereqs -manifests -targetplatform=Win64 -build -target=End -clientconfig=Shipping -utf8output > "%~dp0build\update_package.log" 2>&1
>> "%STATUS%" echo    package exit=%ERRORLEVEL%
:done
echo UPDATE COMPLETE %DATE% %TIME%>> "%STATUS%"
type "%STATUS%"
pause
exit /b

:findpython
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python399\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python399\python.exe"
if not defined PY set "PY=python"
exit /b
