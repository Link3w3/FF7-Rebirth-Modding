@echo off
rem Rebirth FX: builds and installs, in this order (about 3 minutes):
rem   1. Create a Character System 3.7.9 (the RebirthSkelCompat game mod DLL): its frame pump also drives the
rem      RebirthLiveLink mod (the editor's live link to the game). Needs the game closed.
rem   2. The End editor plugin RebirthMaterialPreview with the Rebirth FX helpers (game effects read from the game,
rem      a search list). Needs the End editor closed.
rem Close the game and the End editor first. Output: build\rebirthfx_build.log ("ALL DONE" at the end).
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "LOG=%~dp0build\rebirthfx_build.log"
echo Rebirth FX build, started %DATE% %TIME% > "%LOG%"
echo Building Create a Character System 3.7.9 and the Rebirth FX editor helpers; this takes a few minutes...
call :findpython
echo.>> "%LOG%"
echo === 1/2 Create a Character System 3.7.9 (game mod DLL) with %PY%>> "%LOG%"
%PY% "%~dp0RebirthSkelCompat\build_dll.py" --install --pack-headers >> "%LOG%" 2>&1
set "RC1=%ERRORLEVEL%"
echo    DLL exit=%RC1% >> "%LOG%"
echo.>> "%LOG%"
echo === 2/2 RebirthMaterialPreview (End editor plugin)>> "%LOG%"
%PY% "%~dp0EndEditorPlugins\build_editor_plugins.py" RebirthMaterialPreview >> "%LOG%" 2>&1
set "RC2=%ERRORLEVEL%"
echo    PLUGIN exit=%RC2% >> "%LOG%"
if not "%RC1%"=="0" goto :fail
if not "%RC2%"=="0" goto :fail
echo ALL DONE %DATE% %TIME% >> "%LOG%"
echo.
echo Done: both are built and installed. (build\rebirthfx_build.log has the details.)
pause
exit /b 0

:fail
echo FAILED: DLL exit %RC1%, plugin exit %RC2% (is the game or the editor running?): tell Sandalphon >> "%LOG%"
echo.
echo FAILED: see build\rebirthfx_build.log
pause
exit /b 1

:findpython
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python399\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python399\python.exe"
if not defined PY set "PY=python"
exit /b
