@echo off
title Create a Character System 3.6.7 (Bizarro's cutscene entrance, proportions in cutscenes) - running, please leave this window open
rem Create a Character System 3.6.7 (close the game first; takes a minute or two):
rem   1. builds the game mod 3.6.7 (main.dll) and installs it into the game: an entrance can be a cutscene's own shots
rem      (BIZARRO's is the end of his transformation cutscene), and "proportions" now also works in cutscenes,
rem   2. packs CreateACharacterSystem-Setup-3.6.7.exe into Tools\Share again,
rem   3. installs the new Fully Playable Sephiroth data pak into ~mods (it loads "Alone at last. Shall we?" with him),
rem   4. installs the new SephirothForms.json (BIZARRO's entrance) into the mod's compat folder.
rem Every file it replaces is copied to Tools\_backup\fix367 first; every file it installs is checked (md5).
rem Status: build\fix367_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\fix367_status.txt"
set "STAGE=C:\FF7R2UProj\Tools\_stage\fix367a"
set "GAME=C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH"
set "MODS=%GAME%\End\Content\Paks\~mods"
set "COMPAT=%GAME%\End\Binaries\Win64\ue4ss\Mods\RebirthSkelCompat\compat"
set "BACKUP=C:\FF7R2UProj\Tools\_backup\fix367"
set "PAK=FullyPlayableSephirothDataAssets_P"
echo Create a Character System 3.6.7 started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close %%P first ^(the game^), then run this again>> "%STATUS%"
    goto :done
  )
)
if not exist "%MODS%\%PAK%.utoc" goto :nomods
if not exist "%COMPAT%\SephirothForms.json" goto :nocompat
echo checking the files to install...>> "%STATUS%"
call :md5 "%STAGE%\%PAK%.ucas" 1233f546adff58b764e8f818cd4b09ff || goto :badstage
call :md5 "%STAGE%\%PAK%.utoc" 90ce77bbfaa39781d7fbeb4ea74e8d8b || goto :badstage
call :md5 "%STAGE%\%PAK%.pak" 797a546e664c558fd47fb30b4be7bad5 || goto :badstage
call :md5 "%STAGE%\SephirothForms.json" 45599496eab1baa0f8d7da001846c608 || goto :badstage
echo    all four as made>> "%STATUS%"
call :findpython

echo 1/4 building the Create a Character System game mod 3.6.7 ^(main.dll, installed into the game^)...>> "%STATUS%"
%PY% "C:\FF7R2UProj\Tools\RebirthSkelCompat\build_dll.py" --install > "%~dp0build\fix367_dll.log" 2>&1
if errorlevel 1 (
  echo FAILED: the game mod did not build ^(build\fix367_dll.log, Tools\RebirthSkelCompat\build\latest.txt^); the pak and SephirothForms.json were left as they were>> "%STATUS%"
  goto :done
)
echo    game mod built and installed>> "%STATUS%"

echo 2/4 packing the Create a Character System Setup into Tools\Share...>> "%STATUS%"
set "SC=C:\FF7R2UProj\Tools\RebirthSkelCompat"
set "LATEST="
if exist "%SC%\build\latest.txt" set /p LATEST=<"%SC%\build\latest.txt"
%PY% "C:\FF7R2UProj\Tools\CreateACharacterSystemSetup\make_setup.py" --stub "C:\FF7R2UProj\Tools\CreateACharacterSystemSetup\Setup.stub.exe" --main-dll "%LATEST%\main.dll" --readme "%SC%\mod\README.txt" --example "%SC%\mod\compat\example.json.txt" --source "%SC%\src\RebirthSkelCompat.cpp" --plugin "C:\FF7R2UProj\Plugins\RebirthSkelCompat" --out-dir "C:\FF7R2UProj\Tools\Share" > "%~dp0build\fix367_setup.log" 2>&1
if errorlevel 1 (
  echo    the Setup was not packed ^(build\fix367_setup.log^); the game mod is installed all the same>> "%STATUS%"
) else (
  echo    Setup packed ^(Tools\Share\CreateACharacterSystem-Setup-3.6.7.exe^)>> "%STATUS%"
)

echo 3/4 installing the Fully Playable Sephiroth data pak into ~mods ^(the old one copied to Tools\_backup\fix367\mods^)...>> "%STATUS%"
if not exist "%BACKUP%\mods" mkdir "%BACKUP%\mods"
for %%E in (ucas utoc pak) do (
  if not exist "%BACKUP%\mods\%PAK%.%%E" copy /y "%MODS%\%PAK%.%%E" "%BACKUP%\mods\%PAK%.%%E" >nul
)
copy /y "%STAGE%\%PAK%.ucas" "%MODS%\%PAK%.ucas" >nul
copy /y "%STAGE%\%PAK%.utoc" "%MODS%\%PAK%.utoc" >nul
copy /y "%STAGE%\%PAK%.pak" "%MODS%\%PAK%.pak" >nul
call :md5 "%MODS%\%PAK%.ucas" 1233f546adff58b764e8f818cd4b09ff || goto :badpak
call :md5 "%MODS%\%PAK%.utoc" 90ce77bbfaa39781d7fbeb4ea74e8d8b || goto :badpak
call :md5 "%MODS%\%PAK%.pak" 797a546e664c558fd47fb30b4be7bad5 || goto :badpak
echo    data pak installed and checked>> "%STATUS%"

echo 4/4 installing SephirothForms.json ^(the old one copied to Tools\_backup\fix367\compat^)...>> "%STATUS%"
if not exist "%BACKUP%\compat" mkdir "%BACKUP%\compat"
if not exist "%BACKUP%\compat\SephirothForms.json" copy /y "%COMPAT%\SephirothForms.json" "%BACKUP%\compat\SephirothForms.json" >nul
copy /y "%STAGE%\SephirothForms.json" "%COMPAT%\SephirothForms.json" >nul
call :md5 "%COMPAT%\SephirothForms.json" 45599496eab1baa0f8d7da001846c608 || goto :badcompat
echo    SephirothForms.json installed and checked>> "%STATUS%"
echo ALL DONE: start the game, switch Sephiroth to BIZARRO from the forms menu, and play a cutscene>> "%STATUS%"
goto :done

:nomods
echo STOPPED: the game's ~mods folder has no %PAK% ^(looked in %MODS%^); nothing was changed>> "%STATUS%"
goto :done

:nocompat
echo STOPPED: the mod's compat folder has no SephirothForms.json ^(looked in %COMPAT%^); nothing was changed>> "%STATUS%"
goto :done

:badstage
echo STOPPED: a staged file in %STAGE% is not the one made for this ^(see above^); nothing was changed>> "%STATUS%"
goto :done

:badpak
echo FAILED: the data pak in ~mods did not check out; putting the old one back from Tools\_backup\fix367\mods>> "%STATUS%"
for %%E in (ucas utoc pak) do copy /y "%BACKUP%\mods\%PAK%.%%E" "%MODS%\%PAK%.%%E" >nul
goto :done

:badcompat
echo FAILED: SephirothForms.json did not check out; putting the old one back from Tools\_backup\fix367\compat>> "%STATUS%"
copy /y "%BACKUP%\compat\SephirothForms.json" "%COMPAT%\SephirothForms.json" >nul
goto :done

:done
echo 3.6.7 FINISHED %DATE% %TIME%>> "%STATUS%"
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
