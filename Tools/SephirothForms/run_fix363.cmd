@echo off
title Create a Character System 3.6.3 - running, please leave this window open
rem Create a Character System 3.6.3 (close the game and the End editor first; takes a few minutes):
rem   1. builds the game mod 3.6.3 (main.dll) and installs it into the game: no more crash half a minute into the game
rem      (3.6.2 loaded voice banks itself and the game's loading thread crashed in one; the mod loads none now), and
rem      3.6.2's fixes: moves play after a form's model change, no crash a while after Bizarro's model comes off,
rem   2. packs CreateACharacterSystem-Setup-3.6.3.exe into Tools\Share (game mod 3.6.3, editor plugin 1.11.1).
rem Status: build\fix363_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\fix363_status.txt"
echo Create a Character System 3.6.3 started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe UE4Editor.exe UE4Editor-Cmd.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close %%P first ^(the game or the End editor^), then run this again>> "%STATUS%"
    goto :done
  )
)
call :findpython
echo 1/2 building the Create a Character System game mod 3.6.3 ^(main.dll, installed into the game^)...>> "%STATUS%"
%PY% "C:\FF7R2UProj\Tools\RebirthSkelCompat\build_dll.py" --install > "%~dp0build\fix363_dll.log" 2>&1
if errorlevel 1 (
  echo FAILED: the game mod did not build ^(build\fix363_dll.log, Tools\RebirthSkelCompat\build\latest.txt^)>> "%STATUS%"
  goto :done
)
echo    game mod built and installed>> "%STATUS%"
echo 2/2 packing the Create a Character System Setup into Tools\Share...>> "%STATUS%"
set "SC=C:\FF7R2UProj\Tools\RebirthSkelCompat"
set "LATEST="
if exist "%SC%\build\latest.txt" set /p LATEST=<"%SC%\build\latest.txt"
%PY% "C:\FF7R2UProj\Tools\CreateACharacterSystemSetup\make_setup.py" --stub "C:\FF7R2UProj\Tools\CreateACharacterSystemSetup\Setup.stub.exe" --main-dll "%LATEST%\main.dll" --readme "%SC%\mod\README.txt" --example "%SC%\mod\compat\example.json.txt" --source "%SC%\src\RebirthSkelCompat.cpp" --plugin "C:\FF7R2UProj\Plugins\RebirthSkelCompat" --out-dir "C:\FF7R2UProj\Tools\Share" > "%~dp0build\fix363_setup.log" 2>&1
if errorlevel 1 (
  echo    the Setup was not packed ^(build\fix363_setup.log^); the game mod is installed all the same>> "%STATUS%"
) else (
  echo    Setup packed ^(Tools\Share\CreateACharacterSystem-Setup-3.6.3.exe^)>> "%STATUS%"
)
:done
echo 3.6.3 COMPLETE %DATE% %TIME%>> "%STATUS%"
type "%STATUS%"
pause
exit /b

:findpython
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python399\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python399\python.exe"
if not defined PY set "PY=python"
exit /b
