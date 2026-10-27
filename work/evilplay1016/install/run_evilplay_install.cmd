@echo off
title Evil Cloud plays like Cloud, Bizarro's camera, Create a Character System 3.6.16 - installing, please leave this window open
rem Installs (close the game first; takes a minute or two, most of it the mod's build):
rem   1. the new Fully Playable Sephiroth data pak into ~mods: everything it had, plus the playable Evil Cloud (Sephiroth's
rem      slot, chapter 1) with a motion folder of his own (PC0000_EvilCloud: copies of all 71 of Cloud's animation sets, so
rem      Sephiroth's are not touched), Cloud's packs (his AI, effects, sounds, battle camera), Cloud's commands, combos,
rem      Punisher mode and limit breaks (pt_Sephiroth), and no more left-hand sword override (Evil Cloud's six rows),
rem   2. PlayableSephiroth_Swap.json (Evil Cloud's sets come from his folder; Focused Thrust for the Masamune's ability; the
rem      sword in his left hand in cutscenes), EvilCloudBoss.json (the boss holds it in his left hand in cutscenes too) and
rem      SephirothForms.json (BIZARRO's camera further back, much further while he calls a summon) into the compat folder,
rem   3. builds the Create a Character System game mod 3.6.16 (main.dll, installed into the game): cutscene_weapon_socket and
rem      the forms' cameras, and packs CreateACharacterSystem-Setup-3.6.16.exe into Tools\Share.
rem Everything it replaces is copied to Tools\_backup\evilplay1016 first; every file is checked (md5).
rem Status: build\install_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\install_status.txt"
set "STAGE=C:\FF7R2UProj\Tools\_stage\evilplay1016"
set "GAME=C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH"
set "MODS=%GAME%\End\Content\Paks\~mods"
set "COMPAT=%GAME%\End\Binaries\Win64\ue4ss\Mods\RebirthSkelCompat\compat"
set "SC=C:\FF7R2UProj\Tools\RebirthSkelCompat"
set "BACKUP=C:\FF7R2UProj\Tools\_backup\evilplay1016"
set "PAK=FullyPlayableSephirothDataAssets_P"
echo Evil Cloud / Bizarro camera / Create a Character System 3.6.16 install started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close %%P first ^(the game^), then run this again>> "%STATUS%"
    goto :done
  )
)
if not exist "%MODS%\%PAK%.utoc" goto :nomods
if not exist "%COMPAT%" goto :nocompat
if not exist "%SC%\build_dll.py" goto :nosource
echo checking the files to install...>> "%STATUS%"
call :md5 "%STAGE%\%PAK%.ucas" be70cd6c584ed51be995503cf19d58cf || goto :badstage
call :md5 "%STAGE%\%PAK%.utoc" 0d4b3eb8c384548061e059ac40bda8ec || goto :badstage
call :md5 "%STAGE%\%PAK%.pak" 797a546e664c558fd47fb30b4be7bad5 || goto :badstage
call :md5 "%STAGE%\PlayableSephiroth_Swap.json" ebfbec6b96e3d3d4280215a0d5ccf306 || goto :badstage
call :md5 "%STAGE%\EvilCloudBoss.json" 609d51c9957aace64b5bd4768172e28b || goto :badstage
call :md5 "%STAGE%\SephirothForms.json" 1d7aa43c86f14e038eaf3d9ccd357a0b || goto :badstage
call :md5 "%STAGE%\src\RebirthSkelCompat.cpp" 92de118d7ecc8c9b81e87341ebe47a62 || goto :badstage
call :md5 "%STAGE%\src\SkelCompatCore.hpp" 0335244d6c92fc7fceed96d3e94acd0f || goto :badstage
call :md5 "%STAGE%\mod\README.txt" 6ef9ba34bee93601534ab3b722c4a47f || goto :badstage
echo    all nine as made>> "%STATUS%"

rem ---- 1. the data pak (made on the one the Evil Cloud boss install put in ~mods)
set "PAKSTEP=install"
call :quietmd5 "%MODS%\%PAK%.utoc" 0d4b3eb8c384548061e059ac40bda8ec && set "PAKSTEP=done"
if "%PAKSTEP%"=="install" (
  call :md5 "%MODS%\%PAK%.utoc" 43f9257d0b9c611d9397e413477ae5a8 || goto :otherpak
  call :md5 "%MODS%\%PAK%.ucas" b77b553d2db3a72f74b8dbed6e441ead || goto :otherpak
)
if "%PAKSTEP%"=="done" (
  echo 1/3 the data pak in ~mods is the new one already>> "%STATUS%"
  goto :jsons
)
echo 1/3 installing the data pak into ~mods ^(the old one copied to Tools\_backup\evilplay1016\mods^)...>> "%STATUS%"
if not exist "%BACKUP%\mods" mkdir "%BACKUP%\mods"
for %%E in (ucas utoc pak) do (
  if not exist "%BACKUP%\mods\%PAK%.%%E" copy /y "%MODS%\%PAK%.%%E" "%BACKUP%\mods\%PAK%.%%E" >nul
)
call :md5 "%BACKUP%\mods\%PAK%.utoc" 43f9257d0b9c611d9397e413477ae5a8 || goto :badbackup
call :md5 "%BACKUP%\mods\%PAK%.ucas" b77b553d2db3a72f74b8dbed6e441ead || goto :badbackup
copy /y "%STAGE%\%PAK%.ucas" "%MODS%\%PAK%.ucas" >nul
copy /y "%STAGE%\%PAK%.utoc" "%MODS%\%PAK%.utoc" >nul
copy /y "%STAGE%\%PAK%.pak" "%MODS%\%PAK%.pak" >nul
call :md5 "%MODS%\%PAK%.ucas" be70cd6c584ed51be995503cf19d58cf || goto :badpak
call :md5 "%MODS%\%PAK%.utoc" 0d4b3eb8c384548061e059ac40bda8ec || goto :badpak
call :md5 "%MODS%\%PAK%.pak" 797a546e664c558fd47fb30b4be7bad5 || goto :badpak
echo    data pak installed and checked>> "%STATUS%"

:jsons
rem ---- 2. the compat files
echo 2/3 installing PlayableSephiroth_Swap.json, EvilCloudBoss.json and SephirothForms.json into the compat folder...>> "%STATUS%"
if not exist "%BACKUP%\compat" mkdir "%BACKUP%\compat"
for %%J in (PlayableSephiroth_Swap.json EvilCloudBoss.json SephirothForms.json) do (
  if exist "%COMPAT%\%%J" if not exist "%BACKUP%\compat\%%J" copy /y "%COMPAT%\%%J" "%BACKUP%\compat\%%J" >nul
  copy /y "%STAGE%\%%J" "%COMPAT%\%%J" >nul
)
call :md5 "%COMPAT%\PlayableSephiroth_Swap.json" ebfbec6b96e3d3d4280215a0d5ccf306 || goto :badjson
call :md5 "%COMPAT%\EvilCloudBoss.json" 609d51c9957aace64b5bd4768172e28b || goto :badjson
call :md5 "%COMPAT%\SephirothForms.json" 1d7aa43c86f14e038eaf3d9ccd357a0b || goto :badjson
echo    the three compat files installed and checked>> "%STATUS%"

rem ---- 3. the game mod 3.6.16
echo 3/3 building the Create a Character System game mod 3.6.16 ^(main.dll, installed into the game^)...>> "%STATUS%"
if not exist "%BACKUP%\src" mkdir "%BACKUP%\src"
if not exist "%BACKUP%\src\RebirthSkelCompat.cpp" copy /y "%SC%\src\RebirthSkelCompat.cpp" "%BACKUP%\src\RebirthSkelCompat.cpp" >nul
if not exist "%BACKUP%\src\SkelCompatCore.hpp" copy /y "%SC%\src\SkelCompatCore.hpp" "%BACKUP%\src\SkelCompatCore.hpp" >nul
if not exist "%BACKUP%\src\README.txt" copy /y "%SC%\mod\README.txt" "%BACKUP%\src\README.txt" >nul
copy /y "%STAGE%\src\RebirthSkelCompat.cpp" "%SC%\src\RebirthSkelCompat.cpp" >nul
copy /y "%STAGE%\src\SkelCompatCore.hpp" "%SC%\src\SkelCompatCore.hpp" >nul
copy /y "%STAGE%\mod\README.txt" "%SC%\mod\README.txt" >nul
call :md5 "%SC%\src\RebirthSkelCompat.cpp" 92de118d7ecc8c9b81e87341ebe47a62 || goto :badsource
call :md5 "%SC%\src\SkelCompatCore.hpp" 0335244d6c92fc7fceed96d3e94acd0f || goto :badsource
call :md5 "%SC%\mod\README.txt" 6ef9ba34bee93601534ab3b722c4a47f || goto :badsource
call :findpython
%PY% "%SC%\build_dll.py" --install > "%~dp0build\install_dll.log" 2>&1
if errorlevel 1 goto :badbuild
echo    game mod 3.6.16 built and installed>> "%STATUS%"
set "LATEST="
if exist "%SC%\build\latest.txt" set /p LATEST=<"%SC%\build\latest.txt"
%PY% "C:\FF7R2UProj\Tools\CreateACharacterSystemSetup\make_setup.py" --stub "C:\FF7R2UProj\Tools\CreateACharacterSystemSetup\Setup.stub.exe" --main-dll "%LATEST%\main.dll" --readme "%SC%\mod\README.txt" --example "%SC%\mod\compat\example.json.txt" --source "%SC%\src\RebirthSkelCompat.cpp" --plugin "C:\FF7R2UProj\Plugins\RebirthSkelCompat" --out-dir "C:\FF7R2UProj\Tools\Share" > "%~dp0build\install_setup.log" 2>&1
if errorlevel 1 (
  echo    the Setup was not packed ^(build\install_setup.log^); the game mod is installed all the same>> "%STATUS%"
) else (
  echo    Setup packed ^(Tools\Share\CreateACharacterSystem-Setup-3.6.16.exe^)>> "%STATUS%"
)
echo ALL DONE: start the game. Chapter 1 ^(Nibelheim^): Evil Cloud fights like Cloud, sword in his right hand, left in cutscenes. Forms: BIZARRO's camera is further back.>> "%STATUS%"
goto :done

:nomods
echo STOPPED: the game's ~mods folder has no %PAK%; nothing was changed>> "%STATUS%"
goto :done

:nocompat
echo STOPPED: the Create a Character System's compat folder is not there ^(%COMPAT%^); nothing was changed>> "%STATUS%"
goto :done

:nosource
echo STOPPED: Tools\RebirthSkelCompat has no build_dll.py; nothing was changed>> "%STATUS%"
goto :done

:badstage
echo STOPPED: a staged file in Tools\_stage\evilplay1016 is not the one made for this ^(see above^); nothing was changed>> "%STATUS%"
goto :done

:otherpak
echo STOPPED: the data pak in ~mods is not the one this was made on ^(the Evil Cloud boss install's^); nothing was changed: tell Sandalphon>> "%STATUS%"
goto :done

:badbackup
echo STOPPED: the backup of the data pak did not check out ^(Tools\_backup\evilplay1016\mods^); nothing else was changed>> "%STATUS%"
goto :done

:badpak
echo FAILED: the data pak in ~mods did not check out; putting the old one back from Tools\_backup\evilplay1016\mods>> "%STATUS%"
for %%E in (ucas utoc pak) do copy /y "%BACKUP%\mods\%PAK%.%%E" "%MODS%\%PAK%.%%E" >nul
goto :done

:badjson
echo FAILED: a compat file did not check out ^(the data pak is installed^); run this again>> "%STATUS%"
goto :done

:badsource
echo FAILED: the 3.6.16 source did not copy into Tools\RebirthSkelCompat ^(see above^); the data pak and compat files are installed, 3.6.15 stays: run this again>> "%STATUS%"
goto :done

:badbuild
echo FAILED: the game mod did not build ^(build\install_dll.log^); the data pak and compat files are installed, 3.6.15 stays: tell Sandalphon>> "%STATUS%"
goto :done

:done
echo FINISHED %DATE% %TIME%>> "%STATUS%"
type "%STATUS%"
pause
exit /b

:md5
certutil -hashfile "%~1" MD5 2>nul | findstr /i /c:"%~2" >nul
if not errorlevel 1 exit /b 0
echo    %~nx1 is not the expected file ^(md5 should be %~2^)>> "%STATUS%"
exit /b 1

:quietmd5
certutil -hashfile "%~1" MD5 2>nul | findstr /i /c:"%~2" >nul
if not errorlevel 1 exit /b 0
exit /b 1

:findpython
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python399\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python399\python.exe"
if not defined PY set "PY=python"
exit /b
