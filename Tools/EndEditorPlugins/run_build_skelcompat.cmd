@echo off
rem Sora update: rebuilds the Create a Character System editor plugin (1.13.0: Copy Notifies Onto) and the
rem RebirthSkelCompat game mod (3.8.0: anim_blueprints_from). Close the End editor first.
rem Output: build\run_skelcompat.log here and ..\RebirthSkelCompat\build\run-dll.log
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "LOG=%~dp0build\run_skelcompat.log"
call :findpython
echo Sora update build with %PY% (%DATE% %TIME%)> "%LOG%"
tasklist /FI "IMAGENAME eq UE4Editor.exe" /NH | find /I "UE4Editor.exe" >nul && (
  echo The End editor is still open: close it, then run this again.>> "%LOG%"
  echo The End editor is still open: close it, then run this again.
  pause
  exit /b 1
)
echo [1/2] Building the Create a Character System editor plugin, this takes a few minutes...
%PY% "%~dp0build_editor_plugins.py" RebirthSkelCompatEditor >> "%LOG%" 2>&1
echo RUN COMPLETE exit=%ERRORLEVEL%>> "%LOG%"
echo [2/2] Building and installing the RebirthSkelCompat game mod...
if not exist "%~dp0..\RebirthSkelCompat\build" mkdir "%~dp0..\RebirthSkelCompat\build"
set "DLOG=%~dp0..\RebirthSkelCompat\build\run-dll.log"
echo RebirthSkelCompat DLL build with %PY% > "%DLOG%"
%PY% "%~dp0..\RebirthSkelCompat\build_dll.py" --install >> "%DLOG%" 2>&1
echo RUN COMPLETE exit=%ERRORLEVEL%>> "%DLOG%"
echo Done. You can open the editor again.
pause
exit /b

:findpython
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python399\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python399\python.exe"
if not defined PY set "PY=python"
exit /b
