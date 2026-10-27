@echo off
title Editor fix: models open with the game lighting - building, please leave this window open
rem Builds the RebirthMaterialPreview editor plugin with its own post process material row (RebirthBlendableCustomization).
rem This engine's FWeightedBlendable::Weight has no details row, so the engine's own row stopped the editor on
rem check(IsValid()) whenever a details panel showed a post process material: the model editors' Preview Scene Settings
rem with the "Rebirth Menu Day" profile (the game's tonemapper is one) crashed as soon as a model opened.
rem Close the End editor first. A failed build leaves the plugin as it was and takes the tonemapper out of the profile
rem instead, so models open (with the game's lights and sky, without its tonemap).
rem Output: build\run_blendable_fix.log here.
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "LOG=%~dp0build\run_blendable_fix.log"
call :findpython
echo Editor post process material row fix with %PY% (%DATE% %TIME%)> "%LOG%"
tasklist /FI "IMAGENAME eq UE4Editor.exe" /NH | find /I "UE4Editor.exe" >nul && (
  echo REFUSED: the End editor is still open: close it, then run this again.>> "%LOG%"
  echo The End editor is still open: close it, then run this again.
  pause
  exit /b 1
)
echo Building the RebirthMaterialPreview editor plugin, this takes a few minutes...
%PY% "%~dp0build_editor_plugins.py" RebirthMaterialPreview >> "%LOG%" 2>&1
set "RC=%ERRORLEVEL%"
echo BUILD exit=%RC%>> "%LOG%"
if not "%RC%"=="0" (
  echo The build failed: taking the game tonemapper out of the preview profile so models open.>> "%LOG%"
  %PY% "%~dp0drop_preview_blendable.py" >> "%LOG%" 2>&1
)
echo RUN COMPLETE exit=%RC%>> "%LOG%"
findstr /C:"BUILD exit" /C:"RUN COMPLETE" /C:"taken out" "%LOG%"
echo Done. You can open the editor again.
pause
exit /b

:findpython
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python399\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python399\python.exe"
if not defined PY set "PY=python"
exit /b
