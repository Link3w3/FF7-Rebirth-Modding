@echo off
title Create a Character System editor 1.14.0 - building, please leave this window open
rem Builds the Create a Character System editor plugin 1.14.0 (Sound Banks, and every newer game mod setting in the
rem data object: a form's model the game's way, its weapon, sets, voice, cameras, entrance and shooter; a row's voice,
rem Looks From, AnimBlueprints From, cutscene weapon socket and shooter; socket stand-ins' placement; pairs' proportion
rem bones). Close the End editor first. A failed build leaves the editor as it was.
rem Output: build\run_editor_114.log here.
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "LOG=%~dp0build\run_editor_114.log"
call :findpython
echo Create a Character System editor 1.14.0 build with %PY% (%DATE% %TIME%)> "%LOG%"
tasklist /FI "IMAGENAME eq UE4Editor.exe" /NH | find /I "UE4Editor.exe" >nul && (
  echo REFUSED: the End editor is still open: close it, then run this again.>> "%LOG%"
  echo The End editor is still open: close it, then run this again.
  pause
  exit /b 1
)
echo Building the Create a Character System editor plugin 1.14.0, this takes a few minutes...
%PY% "%~dp0build_editor_plugins.py" RebirthSkelCompatEditor >> "%LOG%" 2>&1
echo RUN COMPLETE exit=%ERRORLEVEL%>> "%LOG%"
findstr /C:"RUN COMPLETE" "%LOG%"
echo Done. You can open the editor again.
pause
exit /b

:findpython
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python399\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python399\python.exe"
if not defined PY set "PY=python"
exit /b
