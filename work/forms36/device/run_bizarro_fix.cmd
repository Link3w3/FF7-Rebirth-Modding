@echo off
title Sephiroth Bizarro form, part 2 - running, please leave this window open
rem The rest of your playable Sephiroth's Bizarro form (close the End editor and the game first):
rem   1. the Create a Character System editor plugin 1.11.1 (ACL's safety fallback off: Bizarro Sephiroth's 54 m skeleton
rem      tripped it on 19 of his moves, and what it left is not something the game can read),
rem   2. packs CreateACharacterSystem-Setup-3.6.0.exe into Tools\Share again, with that plugin,
rem   3. builds those 19 moves again (bizarro\only.json; the other Bizarro moves are built already),
rem   4. packages the project (E:\FVIIREBIRTH\Pakage), so the moves are in pakchunk47.
rem The game mod 3.6.0 is installed already (run_bizarro_form.cmd). Status: build\bizarro_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\bizarro_status.txt"
echo Sephiroth Bizarro form, part 2, started %DATE% %TIME%> "%STATUS%"
for %%P in (UE4Editor.exe UE4Editor-Cmd.exe ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close %%P first ^(the End editor or the game^), then run this again>> "%STATUS%"
    goto :done
  )
)
if not exist "%~dp0bizarro\only.json" (
  echo FAILED: bizarro\only.json is missing>> "%STATUS%"
  goto :done
)
call :findpython
echo 1/4 building the Create a Character System editor plugin 1.11.1...>> "%STATUS%"
%PY% "C:\FF7R2UProj\Tools\EndEditorPlugins\build_editor_plugins.py" RebirthSkelCompatEditor > "%~dp0build\bizarro_plugin.log" 2>&1
if errorlevel 1 (
  echo FAILED: the plugin did not build ^(build\bizarro_plugin.log, Tools\EndEditorPlugins\build\latest.json^)>> "%STATUS%"
  goto :done
)
echo    plugin built>> "%STATUS%"
echo 2/4 packing the Create a Character System Setup into Tools\Share...>> "%STATUS%"
set "SC=C:\FF7R2UProj\Tools\RebirthSkelCompat"
set "LATEST="
if exist "%SC%\build\latest.txt" set /p LATEST=<"%SC%\build\latest.txt"
%PY% "C:\FF7R2UProj\Tools\CreateACharacterSystemSetup\make_setup.py" --stub "C:\FF7R2UProj\Tools\CreateACharacterSystemSetup\Setup.stub.exe" --main-dll "%LATEST%\main.dll" --readme "%SC%\mod\README.txt" --example "%SC%\mod\compat\example.json.txt" --source "%SC%\src\RebirthSkelCompat.cpp" --plugin "C:\FF7R2UProj\Plugins\RebirthSkelCompat" --out-dir "C:\FF7R2UProj\Tools\Share" > "%~dp0build\bizarro_setup.log" 2>&1
if errorlevel 1 (
  echo    the Setup was not packed ^(build\bizarro_setup.log^); going on>> "%STATUS%"
) else (
  echo    Setup packed ^(Tools\Share^)>> "%STATUS%"
)
echo 3/4 the 19 Bizarro moves again...>> "%STATUS%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_bizarro_form.ps1"
if errorlevel 1 (
  echo FAILED: the editor step ^(build\bizarro_editor.log, Saved\RebirthSkelCompat\SephirothForms\bizarro_result.json^)>> "%STATUS%"
  goto :done
)
echo 4/4 packaging the project ^(this is the long part^)...>> "%STATUS%"
call "C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Build\BatchFiles\RunUAT.bat" -ScriptsForProject=C:/FF7R2UProj/End.uproject BuildCookRun -nocompileeditor -installed -nop4 -project=C:/FF7R2UProj/End.uproject -cook -stage -archive -archivedirectory=E:/FVIIREBIRTH/Pakage -package -ue4exe=C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Binaries\Win64\UE4Editor-Cmd.exe -compressed -ddc=InstalledDerivedDataBackendGraph -iostore -pak -iostore -prereqs -manifests -targetplatform=Win64 -build -target=End -clientconfig=Shipping -utf8output > "%~dp0build\bizarro_package.log" 2>&1
>> "%STATUS%" echo    package exit=%ERRORLEVEL%
:done
echo BIZARRO FORM PART 2 COMPLETE %DATE% %TIME%>> "%STATUS%"
type "%STATUS%"
pause
exit /b

:findpython
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python399\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python399\python.exe"
if not defined PY set "PY=python"
exit /b
