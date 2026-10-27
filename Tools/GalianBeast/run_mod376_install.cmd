@echo off
title Create a Character System 3.7.6 - building the game mod, please leave this window open
rem Create a Character System 3.7.6 (close the game first; takes a minute or two):
rem   builds the game mod 3.7.6 (main.dll) and installs it into the game:
rem   - the Galian Beast (any form with a model of its own) stands, walks and runs: its look gets its animation sets
rem     (Battle00 with Battle07's animations, Battle01 with Battle08's, Facial00 with Facial07's),
rem   - Vincent's gun hits: the enemies are found again (the log says how many), each enemy's whole body is a big hit zone
rem     and its head a crit spot (a critical hit: two bullets, the reticle orange-red).
rem The 3.7.5 source is in Tools\_backup\mod376\src. Status: build\mod376_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\mod376_status.txt"
set "SC=C:\FF7R2UProj\Tools\RebirthSkelCompat"
set "BACKUP=C:\FF7R2UProj\Tools\_backup\mod376"
echo Create a Character System 3.7.6 started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close %%P first ^(the game^), then run this again>> "%STATUS%"
    goto :done
  )
)
echo checking the source...>> "%STATUS%"
call :md5 "%SC%\src\RebirthSkelCompat.cpp" eb915117fd8569b66a2d9894590f5660 || goto :badsource
call :md5 "%SC%\src\SkelCompatCore.hpp" a913e8e6340b125f8d9270c3ce718b98 || goto :badsource
call :md5 "%SC%\mod\README.txt" 1e35e8e52e357881c6502ae967c5621c || goto :badsource
call :md5 "%BACKUP%\src\RebirthSkelCompat.cpp" 021e381227ab087c7bb74f599488e4ee || goto :nobackup
call :md5 "%BACKUP%\src\SkelCompatCore.hpp" 80a699a21b521cb9869e3c0ed2b1a4bd || goto :nobackup
echo    the 3.7.6 source ^(3.7.5's in Tools\_backup\mod376^)>> "%STATUS%"
call :findpython
echo building the Create a Character System game mod 3.7.6 ^(main.dll, installed into the game^)...>> "%STATUS%"
%PY% "%SC%\build_dll.py" --install > "%~dp0build\mod376_dll.log" 2>&1
if errorlevel 1 goto :badbuild
echo    game mod 3.7.6 built and installed>> "%STATUS%"
echo ALL DONE: start the game; in a battle shoot an enemy ^(its head for a critical hit^) and turn into GALIAN BEAST ^(he should stand, walk and run^); then tell Sandalphon>> "%STATUS%"
goto :done

:badsource
echo STOPPED: Tools\RebirthSkelCompat is not the 3.7.6 source ^(see above^); nothing was changed: tell Sandalphon>> "%STATUS%"
goto :done

:nobackup
echo STOPPED: Tools\_backup\mod376 does not have the 3.7.5 source; nothing was changed: tell Sandalphon>> "%STATUS%"
goto :done

:badbuild
echo FAILED: the game mod did not build ^(build\mod376_dll.log^); 3.7.5 stays installed: tell Sandalphon>> "%STATUS%"
goto :done

:done
echo 3.7.6 FINISHED %DATE% %TIME%>> "%STATUS%"
type "%STATUS%"
pause
exit /b

:md5
certutil -hashfile "%~1" MD5 2>nul | findstr /i /c:"%~2" >nul
if not errorlevel 1 exit /b 0
echo    %~nx1 is not the expected file ^(md5 should be %~2^)>> "%STATUS%"
exit /b 1

:findpython
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python399\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python399\python.exe"
if not defined PY set "PY=python"
exit /b
