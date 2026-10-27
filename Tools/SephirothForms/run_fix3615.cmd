@echo off
title Create a Character System 3.6.15 (the forms) - running, please leave this window open
rem Create a Character System 3.6.15 (close the game first; takes a minute or two):
rem   1. builds the game mod 3.6.15 (main.dll) and installs it into the game: 3.6.14 took a form's moves (its animation
rem      pack) for an empty level set and put the level set that loaded last in their place (the forms stopped about
rem      10 s after every switch, and Bizarro's and Safer's entrances froze); only the game's level set entries are
rem      filled now,
rem   2. packs CreateACharacterSystem-Setup-3.6.15.exe into Tools\Share.
rem Status: build\fix3615_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\fix3615_status.txt"
set "SC=C:\FF7R2UProj\Tools\RebirthSkelCompat"
echo Create a Character System 3.6.15 started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close %%P first ^(the game^), then run this again>> "%STATUS%"
    goto :done
  )
)
echo checking the source...>> "%STATUS%"
call :md5 "%SC%\src\RebirthSkelCompat.cpp" 7a534f4f9a428bb8b1fb26ccca6fdda3 || goto :badsource
call :md5 "%SC%\src\SkelCompatCore.hpp" b5e15379b2de390393711ddd27ea1c28 || goto :badsource
call :md5 "%SC%\mod\README.txt" 6d9edbef0a5d171fa7fd8a6251a60054 || goto :badsource
echo    the 3.6.15 source>> "%STATUS%"
call :findpython

echo 1/2 building the Create a Character System game mod 3.6.15 ^(main.dll, installed into the game^)...>> "%STATUS%"
%PY% "%SC%\build_dll.py" --install > "%~dp0build\fix3615_dll.log" 2>&1
if errorlevel 1 goto :badbuild
echo    game mod built and installed>> "%STATUS%"

echo 2/2 packing the Create a Character System Setup into Tools\Share...>> "%STATUS%"
set "LATEST="
if exist "%SC%\build\latest.txt" set /p LATEST=<"%SC%\build\latest.txt"
%PY% "C:\FF7R2UProj\Tools\CreateACharacterSystemSetup\make_setup.py" --stub "C:\FF7R2UProj\Tools\CreateACharacterSystemSetup\Setup.stub.exe" --main-dll "%LATEST%\main.dll" --readme "%SC%\mod\README.txt" --example "%SC%\mod\compat\example.json.txt" --source "%SC%\src\RebirthSkelCompat.cpp" --plugin "C:\FF7R2UProj\Plugins\RebirthSkelCompat" --out-dir "C:\FF7R2UProj\Tools\Share" > "%~dp0build\fix3615_setup.log" 2>&1
if errorlevel 1 (
  echo    the Setup was not packed ^(build\fix3615_setup.log^); the game mod is installed all the same>> "%STATUS%"
) else (
  echo    Setup packed ^(Tools\Share\CreateACharacterSystem-Setup-3.6.15.exe^)>> "%STATUS%"
)
echo ALL DONE: start the game and switch forms in a battle; each form should keep its moves>> "%STATUS%"
goto :done

:badsource
echo STOPPED: Tools\RebirthSkelCompat is not the 3.6.15 source ^(see above^); nothing was changed>> "%STATUS%"
goto :done

:badbuild
echo FAILED: the game mod did not build ^(build\fix3615_dll.log^); 3.6.14 stays installed>> "%STATUS%"
goto :done

:done
echo 3.6.15 FINISHED %DATE% %TIME%>> "%STATUS%"
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
