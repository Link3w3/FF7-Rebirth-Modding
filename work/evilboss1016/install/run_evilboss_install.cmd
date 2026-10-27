@echo off
title Evil Cloud boss fights - installing, please leave this window open
rem Installs Evil Cloud's boss fights (close the game first; takes a few seconds):
rem   1. the new Fully Playable Sephiroth data pak into ~mods: everything it had, plus Evil Cloud's 115 boss moves (each of
rem      the boss's animations made of one of Cloud's, with the boss's own damage, AI and timing) and the boss's feeler
rem      attacks made Cloud's (Blade Burst's wave, a beam of his, Finishing Touch's whirlwind and burst; no feelers),
rem   2. EvilCloudBoss.json into the Create a Character System's compat folder: the boss fights (the final battle and the VR
rem      battle) play those moves, with Cloud's effects and sounds.
rem The data pak it replaces is copied to Tools\_backup\evilboss1124\mods first; every file is checked (md5).
rem Status: build\install_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\install_status.txt"
set "STAGE=C:\FF7R2UProj\Tools\_stage\evilboss1124"
set "GAME=C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH"
set "MODS=%GAME%\End\Content\Paks\~mods"
set "COMPAT=%GAME%\End\Binaries\Win64\ue4ss\Mods\RebirthSkelCompat\compat"
set "BACKUP=C:\FF7R2UProj\Tools\_backup\evilboss1124"
set "PAK=FullyPlayableSephirothDataAssets_P"
echo Evil Cloud boss fights install started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close %%P first ^(the game^), then run this again>> "%STATUS%"
    goto :done
  )
)
if not exist "%MODS%\%PAK%.utoc" goto :nomods
if not exist "%COMPAT%" goto :nocompat
echo checking the files to install...>> "%STATUS%"
call :md5 "%STAGE%\%PAK%.ucas" b77b553d2db3a72f74b8dbed6e441ead || goto :badstage
call :md5 "%STAGE%\%PAK%.utoc" 43f9257d0b9c611d9397e413477ae5a8 || goto :badstage
call :md5 "%STAGE%\%PAK%.pak" 797a546e664c558fd47fb30b4be7bad5 || goto :badstage
call :md5 "%STAGE%\EvilCloudBoss.json" c7f2c9d338dc18fa9e0c82eb4a0eaaa5 || goto :badstage
echo    all four as made>> "%STATUS%"

echo installing the data pak into ~mods ^(the old one copied to Tools\_backup\evilboss1124\mods^)...>> "%STATUS%"
if not exist "%BACKUP%\mods" mkdir "%BACKUP%\mods"
for %%E in (ucas utoc pak) do (
  if not exist "%BACKUP%\mods\%PAK%.%%E" copy /y "%MODS%\%PAK%.%%E" "%BACKUP%\mods\%PAK%.%%E" >nul
)
copy /y "%STAGE%\%PAK%.ucas" "%MODS%\%PAK%.ucas" >nul
copy /y "%STAGE%\%PAK%.utoc" "%MODS%\%PAK%.utoc" >nul
copy /y "%STAGE%\%PAK%.pak" "%MODS%\%PAK%.pak" >nul
call :md5 "%MODS%\%PAK%.ucas" b77b553d2db3a72f74b8dbed6e441ead || goto :badpak
call :md5 "%MODS%\%PAK%.utoc" 43f9257d0b9c611d9397e413477ae5a8 || goto :badpak
call :md5 "%MODS%\%PAK%.pak" 797a546e664c558fd47fb30b4be7bad5 || goto :badpak
echo    data pak installed and checked>> "%STATUS%"

echo installing EvilCloudBoss.json into the compat folder...>> "%STATUS%"
if exist "%COMPAT%\EvilCloudBoss.json" if not exist "%BACKUP%\compat\EvilCloudBoss.json" (
  if not exist "%BACKUP%\compat" mkdir "%BACKUP%\compat"
  copy /y "%COMPAT%\EvilCloudBoss.json" "%BACKUP%\compat\EvilCloudBoss.json" >nul
)
copy /y "%STAGE%\EvilCloudBoss.json" "%COMPAT%\EvilCloudBoss.json" >nul
call :md5 "%COMPAT%\EvilCloudBoss.json" c7f2c9d338dc18fa9e0c82eb4a0eaaa5 || goto :badjson
echo    EvilCloudBoss.json installed and checked>> "%STATUS%"
echo ALL DONE: start the game and play the VR battle with Sephiroth first, then the final battle>> "%STATUS%"
goto :done

:nomods
echo STOPPED: the game's ~mods folder has no %PAK%; nothing was changed>> "%STATUS%"
goto :done

:nocompat
echo STOPPED: the Create a Character System's compat folder is not there ^(%COMPAT%^); nothing was changed>> "%STATUS%"
goto :done

:badstage
echo STOPPED: a staged file in Tools\_stage\evilboss1124 is not the one made for this ^(see above^); nothing was changed>> "%STATUS%"
goto :done

:badpak
echo FAILED: the data pak in ~mods did not check out; putting the old one back from Tools\_backup\evilboss1124\mods>> "%STATUS%"
for %%E in (ucas utoc pak) do copy /y "%BACKUP%\mods\%PAK%.%%E" "%MODS%\%PAK%.%%E" >nul
goto :done

:badjson
echo FAILED: EvilCloudBoss.json in the compat folder did not check out ^(the data pak is installed^); run this again>> "%STATUS%"
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
