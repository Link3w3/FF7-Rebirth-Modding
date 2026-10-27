@echo off
title Create a Character System 3.6.8 (no T-pose in burning Nibelheim, no hitches in the entrances) - running, please leave this window open
rem Create a Character System 3.6.8 (close the game first; takes a minute or two):
rem   1. installs the new Fully Playable Sephiroth data pak into ~mods: Sephiroth in Cloud's slot gets Cloud's level,
rem      field-action and riding animation sets (the burning Nibelheim walk of chapter 1, crawl spaces, carts, ropes,
rem      chocobos...) instead of T-posing,
rem   2. builds the game mod 3.6.8 (main.dll) and installs it into the game: no more hitches in the forms' entrances,
rem   3. packs CreateACharacterSystem-Setup-3.6.8.exe into Tools\Share again.
rem Every file it replaces is copied to Tools\_backup\fix368 first; every file it installs is checked (md5).
rem Status: build\fix368_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\fix368_status.txt"
set "STAGE=C:\FF7R2UProj\Tools\_stage\fix368a"
set "GAME=C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH"
set "MODS=%GAME%\End\Content\Paks\~mods"
set "BACKUP=C:\FF7R2UProj\Tools\_backup\fix368"
set "PAK=FullyPlayableSephirothDataAssets_P"
echo Create a Character System 3.6.8 started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close %%P first ^(the game^), then run this again>> "%STATUS%"
    goto :done
  )
)
if not exist "%MODS%\%PAK%.utoc" goto :nomods
echo checking the files to install...>> "%STATUS%"
call :md5 "%STAGE%\%PAK%.ucas" 9cca86dda1c233c1fd186528804a92e9 || goto :badstage
call :md5 "%STAGE%\%PAK%.utoc" 14db7f558237e469e58dba41a8cdd314 || goto :badstage
call :md5 "%STAGE%\%PAK%.pak" 797a546e664c558fd47fb30b4be7bad5 || goto :badstage
echo    all three as made>> "%STATUS%"

echo 1/3 installing the Fully Playable Sephiroth data pak into ~mods ^(the old one copied to Tools\_backup\fix368\mods^)...>> "%STATUS%"
if not exist "%BACKUP%\mods" mkdir "%BACKUP%\mods"
for %%E in (ucas utoc pak) do (
  if not exist "%BACKUP%\mods\%PAK%.%%E" copy /y "%MODS%\%PAK%.%%E" "%BACKUP%\mods\%PAK%.%%E" >nul
)
copy /y "%STAGE%\%PAK%.ucas" "%MODS%\%PAK%.ucas" >nul
copy /y "%STAGE%\%PAK%.utoc" "%MODS%\%PAK%.utoc" >nul
copy /y "%STAGE%\%PAK%.pak" "%MODS%\%PAK%.pak" >nul
call :md5 "%MODS%\%PAK%.ucas" 9cca86dda1c233c1fd186528804a92e9 || goto :badpak
call :md5 "%MODS%\%PAK%.utoc" 14db7f558237e469e58dba41a8cdd314 || goto :badpak
call :md5 "%MODS%\%PAK%.pak" 797a546e664c558fd47fb30b4be7bad5 || goto :badpak
echo    data pak installed and checked>> "%STATUS%"
call :findpython

echo 2/3 building the Create a Character System game mod 3.6.8 ^(main.dll, installed into the game^)...>> "%STATUS%"
%PY% "C:\FF7R2UProj\Tools\RebirthSkelCompat\build_dll.py" --install > "%~dp0build\fix368_dll.log" 2>&1
if errorlevel 1 (
  echo FAILED: the game mod did not build ^(build\fix368_dll.log^); 3.6.7 stays installed, the data pak is installed all the same>> "%STATUS%"
  goto :done
)
echo    game mod built and installed>> "%STATUS%"

echo 3/3 packing the Create a Character System Setup into Tools\Share...>> "%STATUS%"
set "SC=C:\FF7R2UProj\Tools\RebirthSkelCompat"
set "LATEST="
if exist "%SC%\build\latest.txt" set /p LATEST=<"%SC%\build\latest.txt"
%PY% "C:\FF7R2UProj\Tools\CreateACharacterSystemSetup\make_setup.py" --stub "C:\FF7R2UProj\Tools\CreateACharacterSystemSetup\Setup.stub.exe" --main-dll "%LATEST%\main.dll" --readme "%SC%\mod\README.txt" --example "%SC%\mod\compat\example.json.txt" --source "%SC%\src\RebirthSkelCompat.cpp" --plugin "C:\FF7R2UProj\Plugins\RebirthSkelCompat" --out-dir "C:\FF7R2UProj\Tools\Share" > "%~dp0build\fix368_setup.log" 2>&1
if errorlevel 1 (
  echo    the Setup was not packed ^(build\fix368_setup.log^); the game mod is installed all the same>> "%STATUS%"
) else (
  echo    Setup packed ^(Tools\Share\CreateACharacterSystem-Setup-3.6.8.exe^)>> "%STATUS%"
)
echo ALL DONE: start the game and play chapter 1's burning Nibelheim; the forms' entrances should play smoothly>> "%STATUS%"
goto :done

:nomods
echo STOPPED: the game's ~mods folder has no %PAK% ^(looked in %MODS%^); nothing was changed>> "%STATUS%"
goto :done

:badstage
echo STOPPED: a staged file in %STAGE% is not the one made for this ^(see above^); nothing was changed>> "%STATUS%"
goto :done

:badpak
echo FAILED: the data pak in ~mods did not check out; putting the old one back from Tools\_backup\fix368\mods>> "%STATUS%"
for %%E in (ucas utoc pak) do copy /y "%BACKUP%\mods\%PAK%.%%E" "%MODS%\%PAK%.%%E" >nul
goto :done

:done
echo 3.6.8 FINISHED %DATE% %TIME%>> "%STATUS%"
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
