@echo off
title Create a Character System 3.6.8 (the game mod build, second try) - running, please leave this window open
rem Create a Character System 3.6.8, second try at the game mod (close the game first; takes a minute or two).
rem The first try (run_fix368.cmd) installed the data pak (no T-pose in burning Nibelheim) but the game mod did not
rem build: it called a part of UE4SS that UE4SS.dll does not export. The source in Tools\RebirthSkelCompat\src is fixed;
rem this only
rem   1. builds the game mod 3.6.8 (main.dll) and installs it into the game: no more hitches in the forms' entrances,
rem   2. packs CreateACharacterSystem-Setup-3.6.8.exe into Tools\Share again.
rem The data pak is left as it is (it was installed and checked by run_fix368.cmd).
rem Status: build\fix368b_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\fix368b_status.txt"
set "SC=C:\FF7R2UProj\Tools\RebirthSkelCompat"
set "GAME=C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH"
set "PAK=FullyPlayableSephirothDataAssets_P"
echo Create a Character System 3.6.8 (second try) started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close %%P first ^(the game^), then run this again>> "%STATUS%"
    goto :done
  )
)
echo checking the source...>> "%STATUS%"
call :md5 "%SC%\src\RebirthSkelCompat.cpp" 8f9b700f2d125d37c916a1a281b61e5c || goto :badsource
call :md5 "%SC%\src\SkelCompatCore.hpp" b5e15379b2de390393711ddd27ea1c28 || goto :badsource
echo    the fixed 3.6.8 source>> "%STATUS%"
call :checkpak
call :findpython

echo 1/2 building the Create a Character System game mod 3.6.8 ^(main.dll, installed into the game^)...>> "%STATUS%"
%PY% "%SC%\build_dll.py" --install > "%~dp0build\fix368b_dll.log" 2>&1
if errorlevel 1 goto :badbuild
echo    game mod built and installed>> "%STATUS%"

echo 2/2 packing the Create a Character System Setup into Tools\Share...>> "%STATUS%"
set "LATEST="
if exist "%SC%\build\latest.txt" set /p LATEST=<"%SC%\build\latest.txt"
%PY% "C:\FF7R2UProj\Tools\CreateACharacterSystemSetup\make_setup.py" --stub "C:\FF7R2UProj\Tools\CreateACharacterSystemSetup\Setup.stub.exe" --main-dll "%LATEST%\main.dll" --readme "%SC%\mod\README.txt" --example "%SC%\mod\compat\example.json.txt" --source "%SC%\src\RebirthSkelCompat.cpp" --plugin "C:\FF7R2UProj\Plugins\RebirthSkelCompat" --out-dir "C:\FF7R2UProj\Tools\Share" > "%~dp0build\fix368b_setup.log" 2>&1
if errorlevel 1 (
  echo    the Setup was not packed ^(build\fix368b_setup.log^); the game mod is installed all the same>> "%STATUS%"
) else (
  echo    Setup packed ^(Tools\Share\CreateACharacterSystem-Setup-3.6.8.exe^)>> "%STATUS%"
)
echo ALL DONE: start the game, play chapter 1's burning Nibelheim, and switch Sephiroth to SAFER from the forms menu>> "%STATUS%"
goto :done

:badsource
echo STOPPED: Tools\RebirthSkelCompat\src is not the fixed 3.6.8 source ^(see above^); nothing was changed>> "%STATUS%"
goto :done

:badbuild
echo FAILED: the game mod did not build ^(build\fix368b_dll.log^); 3.6.7 stays installed>> "%STATUS%"
goto :done

:done
echo 3.6.8 (second try) FINISHED %DATE% %TIME%>> "%STATUS%"
type "%STATUS%"
pause
exit /b

:checkpak
set "PAKOK=1"
certutil -hashfile "%GAME%\End\Content\Paks\~mods\%PAK%.utoc" MD5 2>nul | findstr /i /c:"14db7f558237e469e58dba41a8cdd314" >nul || set "PAKOK="
certutil -hashfile "%GAME%\End\Content\Paks\~mods\%PAK%.ucas" MD5 2>nul | findstr /i /c:"9cca86dda1c233c1fd186528804a92e9" >nul || set "PAKOK="
if defined PAKOK echo    the data pak in ~mods is the T-pose fix>> "%STATUS%"
if not defined PAKOK echo    NOTE: the data pak in ~mods is not the T-pose fix; run run_fix368.cmd again for it>> "%STATUS%"
exit /b 0

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
