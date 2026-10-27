@echo off
title Vincent: guns that hurt, and his Dirge of Cerberus walk and run - installing, please leave this window open
rem Installs (close the game first; takes a few seconds):
rem   1. FullyPlayableVincentAssets_P into Paks\~mods\FullyPlayableVincentPaks: the one installed now with
rem      - the game's damage table with three rows of Vincent's own, PC0011_Dirge_Cerberus, _Hydra and _Griffon: a player's
rem        bullets (as Barret's are) from the Quicksilver's muzzle. The guns fired Elena's bullets before, rows the game made
rem        for her attacks on your party, and they hurt nothing of the enemy's;
rem      - the 43 walk, run and strafe moves built in the editor and his four strafing blend spaces playing them (what
rem        run_dirge_walk_install.cmd installs; it does not need to run as well),
rem   2. VincentDirge.json (the guns fire the new rows) and Vincent_Moves.json (the walk and run moves) into the compat folder.
rem Everything it replaces is copied to Tools\_backup\dirgegun1017 first; every file is checked (md5); if anything does not
rem check out, all of it is put back as it was.
rem Status: build\install_dirgegun_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\install_dirgegun_status.txt"
set "STAGE=C:\FF7R2UProj\Tools\_stage\dirgegun1017"
set "GAME=C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH"
set "VPAKS=%GAME%\End\Content\Paks\~mods\FullyPlayableVincentPaks"
set "COMPAT=%GAME%\End\Binaries\Win64\ue4ss\Mods\RebirthSkelCompat\compat"
set "BACKUP=C:\FF7R2UProj\Tools\_backup\dirgegun1017"
rem what may be installed now: the prologue install's, the walk install's (run_dirge_walk_install.cmd), or this one's
set "UTOCS=c73040ee65a4e5e4e8b1ac9bfd7ce1ec af4e5db703ced17174c3d6cb5121620b 9e30808b0db92ea6f94c8f4a188e13da"
set "DIRGES=bac80681a0e1171fb919573102482ec1 c61d6f3529c45ad9ac53a0aa9524bbd7 9365d20e49513eeb395e1f5a5c2d4495"
set "MOVES=58790cb53dfd62419c783b7a337c6c58 6f8a502f12218bd3b6d62734d9f5ca03"
echo Vincent guns and walk install started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close %%P first ^(the game^), then run this again>> "%STATUS%"
    goto :done
  )
)
if not exist "%COMPAT%\Vincent_Moves.json" goto :nocompat
if not exist "%COMPAT%\VincentDirge.json" goto :nocompat
if not exist "%VPAKS%\FullyPlayableVincentAssets_P.utoc" goto :novincent

echo checking the files to install...>> "%STATUS%"
call :md5 "%STAGE%\paks\FullyPlayableVincentAssets_P.pak" 978275e5395574cf363603d330e50a28 || goto :badstage
call :md5 "%STAGE%\paks\FullyPlayableVincentAssets_P.ucas" 9eb542a5af6abbbb240dacc1493e9b6c || goto :badstage
call :md5 "%STAGE%\paks\FullyPlayableVincentAssets_P.utoc" 9e30808b0db92ea6f94c8f4a188e13da || goto :badstage
call :md5 "%STAGE%\compat\VincentDirge.json" 9365d20e49513eeb395e1f5a5c2d4495 || goto :badstage
call :md5 "%STAGE%\compat\Vincent_Moves.json" 6f8a502f12218bd3b6d62734d9f5ca03 || goto :badstage
echo    all 5 as made>> "%STATUS%"

echo checking what is installed now...>> "%STATUS%"
call :oneof "%VPAKS%\FullyPlayableVincentAssets_P.utoc" %UTOCS% || goto :notbase
call :oneof "%COMPAT%\VincentDirge.json" %DIRGES% || goto :notbase
call :oneof "%COMPAT%\Vincent_Moves.json" %MOVES% || goto :notbase
echo    one this was made for>> "%STATUS%"

echo copying what this replaces to Tools\_backup\dirgegun1017...>> "%STATUS%"
if not exist "%BACKUP%\paks" mkdir "%BACKUP%\paks"
if not exist "%BACKUP%\compat" mkdir "%BACKUP%\compat"
for %%F in (pak ucas utoc) do if not exist "%BACKUP%\paks\FullyPlayableVincentAssets_P.%%F" copy /y "%VPAKS%\FullyPlayableVincentAssets_P.%%F" "%BACKUP%\paks\FullyPlayableVincentAssets_P.%%F" >nul
for %%J in (VincentDirge.json Vincent_Moves.json) do if not exist "%BACKUP%\compat\%%J" copy /y "%COMPAT%\%%J" "%BACKUP%\compat\%%J" >nul
rem (a backup is one of the installs this was made for; once made it is kept, so a second run keeps the first one's)
call :oneof "%BACKUP%\paks\FullyPlayableVincentAssets_P.utoc" %UTOCS% || goto :nobackup
call :oneof "%BACKUP%\compat\VincentDirge.json" %DIRGES% || goto :nobackup
call :oneof "%BACKUP%\compat\Vincent_Moves.json" %MOVES% || goto :nobackup
for %%F in (pak ucas) do if not exist "%BACKUP%\paks\FullyPlayableVincentAssets_P.%%F" goto :nobackup
echo    done>> "%STATUS%"

rem ---- 1. the container
echo 1/2 FullyPlayableVincentAssets_P ^(his guns' bullets, his walk and run^) into Paks\~mods\FullyPlayableVincentPaks...>> "%STATUS%"
for %%F in (pak ucas utoc) do copy /y "%STAGE%\paks\FullyPlayableVincentAssets_P.%%F" "%VPAKS%\FullyPlayableVincentAssets_P.%%F" >nul
call :md5 "%VPAKS%\FullyPlayableVincentAssets_P.pak" 978275e5395574cf363603d330e50a28 || goto :failed
call :md5 "%VPAKS%\FullyPlayableVincentAssets_P.ucas" 9eb542a5af6abbbb240dacc1493e9b6c || goto :failed
call :md5 "%VPAKS%\FullyPlayableVincentAssets_P.utoc" 9e30808b0db92ea6f94c8f4a188e13da || goto :failed
echo    installed and checked>> "%STATUS%"

rem ---- 2. the settings
echo 2/2 VincentDirge.json and Vincent_Moves.json into the compat folder...>> "%STATUS%"
copy /y "%STAGE%\compat\VincentDirge.json" "%COMPAT%\VincentDirge.json" >nul
copy /y "%STAGE%\compat\Vincent_Moves.json" "%COMPAT%\Vincent_Moves.json" >nul
call :md5 "%COMPAT%\VincentDirge.json" 9365d20e49513eeb395e1f5a5c2d4495 || goto :failed
call :md5 "%COMPAT%\Vincent_Moves.json" 6f8a502f12218bd3b6d62734d9f5ca03 || goto :failed
echo    installed and checked>> "%STATUS%"
echo ALL DONE: start the game. His shots should hurt now, and he walks and runs as in Dirge of Cerberus. After a fight send Sandalphon ue4ss\Mods\RebirthSkelCompat\RebirthSkelCompat.log>> "%STATUS%"
goto :done

:nocompat
echo STOPPED: the Create a Character System's compat folder ^(with VincentDirge.json and Vincent_Moves.json^) is not there; nothing was changed>> "%STATUS%"
goto :done

:novincent
echo STOPPED: Paks\~mods\FullyPlayableVincentPaks\FullyPlayableVincentAssets_P is not there; nothing was changed>> "%STATUS%"
goto :done

:badstage
echo STOPPED: a staged file in Tools\_stage\dirgegun1017 is not the one made for this ^(see above^); nothing was changed: tell Sandalphon>> "%STATUS%"
goto :done

:notbase
echo STOPPED: what is installed is not one this was made for ^(see above^); nothing was changed: tell Sandalphon>> "%STATUS%"
goto :done

:nobackup
echo STOPPED: Tools\_backup\dirgegun1017 does not have a copy of what is installed ^(see above^); nothing was changed: tell Sandalphon>> "%STATUS%"
goto :done

:failed
echo FAILED: putting everything back as it was from Tools\_backup\dirgegun1017...>> "%STATUS%"
for %%F in (pak ucas utoc) do copy /y "%BACKUP%\paks\FullyPlayableVincentAssets_P.%%F" "%VPAKS%\FullyPlayableVincentAssets_P.%%F" >nul
for %%J in (VincentDirge.json Vincent_Moves.json) do copy /y "%BACKUP%\compat\%%J" "%COMPAT%\%%J" >nul
for %%F in (pak ucas utoc) do fc /b "%BACKUP%\paks\FullyPlayableVincentAssets_P.%%F" "%VPAKS%\FullyPlayableVincentAssets_P.%%F" >nul || goto :stuck
for %%J in (VincentDirge.json Vincent_Moves.json) do fc /b "%BACKUP%\compat\%%J" "%COMPAT%\%%J" >nul || goto :stuck
echo    put back and checked: the game is as it was before this; tell Sandalphon>> "%STATUS%"
goto :done

:stuck
echo    NOT all of it could be put back: do not start the game; tell Sandalphon>> "%STATUS%"
goto :done

:done
echo FINISHED %DATE% %TIME%>> "%STATUS%"
type "%STATUS%"
pause
exit /b

:oneof
rem :oneof <file> <md5> [<md5> ...]: the file is one of them
set "ONEOF_FILE=%~1"
shift
set "ONEOF_FIND="
:oneof_more
if "%~1"=="" goto :oneof_check
set "ONEOF_FIND=%ONEOF_FIND% /c:%~1"
shift
goto :oneof_more
:oneof_check
certutil -hashfile "%ONEOF_FILE%" MD5 2>nul | findstr /i %ONEOF_FIND% >nul
if not errorlevel 1 exit /b 0
for %%N in ("%ONEOF_FILE%") do echo    %%~nxN is not one this was made for>> "%STATUS%"
exit /b 1

:md5
certutil -hashfile "%~1" MD5 2>nul | findstr /i /c:"%~2" >nul
if not errorlevel 1 exit /b 0
echo    %~nx1 is not the expected file ^(md5 should be %~2^)>> "%STATUS%"
exit /b 1
