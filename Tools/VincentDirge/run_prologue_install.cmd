@echo off
title Vincent in the prologue, battle walking and running, voice fix - installing, please leave this window open
rem Installs (close the game first; takes a few seconds):
rem   1. VincentVoice_P v2 into Paks\~mods: Vincent's battle voice, without v1's crash at start-up ("audio data was not
rem      cooked into SQEXSEADSound ... VO_PC0000_00_Cloud": v1 left one of the bank's three size fields at its old size),
rem   2. FullyPlayableVincentAssets_P into Paks\~mods\FullyPlayableVincentPaks: Cloud in his SOLDIER uniform (the prologue's
rem      five CharaSpec rows: ZackCostume, Dirty, Age21, DirtyAge21, Wet) is Vincent too, as Cloud's own slot is (his model,
rem      his blueprint, his action sounds, Vincent in the field as well),
rem   3. VincentDirge.json and Vincent_Moves.json into the compat folder: he walks and runs in battle again (only his Dirge
rem      of Cerberus stance stays a "move": the Dirge of Cerberus walk and run clips stand in place, so they left him
rem      walking on the spot), and the shooter, his anim sets and his melee moves cover the prologue's rows too.
rem Everything it replaces is copied to Tools\_backup\prologue1016 first; every file is checked (md5).
rem Status: build\install_prologue_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\install_prologue_status.txt"
set "STAGE=C:\FF7R2UProj\Tools\_stage\prologue1016"
set "GAME=C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH"
set "MODS=%GAME%\End\Content\Paks\~mods"
set "VPAKS=%MODS%\FullyPlayableVincentPaks"
set "COMPAT=%GAME%\End\Binaries\Win64\ue4ss\Mods\RebirthSkelCompat\compat"
set "VOICEDOC=C:\FF7R2UProj\Tools\VincentVoice"
set "BACKUP=C:\FF7R2UProj\Tools\_backup\prologue1016"
echo Vincent prologue / battle movement / voice v2 install started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close %%P first ^(the game^), then run this again>> "%STATUS%"
    goto :done
  )
)
if not exist "%COMPAT%" goto :nocompat
if not exist "%VPAKS%\FullyPlayableVincentAssets_P.utoc" goto :novincent

echo checking the files to install...>> "%STATUS%"
call :md5 "%STAGE%\paks\FullyPlayableVincentAssets_P.pak" 978275e5395574cf363603d330e50a28 || goto :badstage
call :md5 "%STAGE%\paks\FullyPlayableVincentAssets_P.ucas" bf6acd8b1f52713e6674187465d64b5b || goto :badstage
call :md5 "%STAGE%\paks\FullyPlayableVincentAssets_P.utoc" c73040ee65a4e5e4e8b1ac9bfd7ce1ec || goto :badstage
call :md5 "%STAGE%\paks\VincentVoice_P.pak" 602a1b0aee4bf950ec7a27d6bacae32e || goto :badstage
call :md5 "%STAGE%\paks\VincentVoice_P.ucas" 5884eb2d0b6eaa318b4b329c15b8fe83 || goto :badstage
call :md5 "%STAGE%\paks\VincentVoice_P.utoc" f84e042aea3885a8a7c7bff749b74f59 || goto :badstage
call :md5 "%STAGE%\compat\VincentDirge.json" bac80681a0e1171fb919573102482ec1 || goto :badstage
call :md5 "%STAGE%\compat\Vincent_Moves.json" 58790cb53dfd62419c783b7a337c6c58 || goto :badstage
echo    all 8 as made>> "%STATUS%"

echo copying what this replaces to Tools\_backup\prologue1016...>> "%STATUS%"
if not exist "%BACKUP%\paks" mkdir "%BACKUP%\paks"
if not exist "%BACKUP%\compat" mkdir "%BACKUP%\compat"
for %%F in (pak ucas utoc) do (
  if exist "%VPAKS%\FullyPlayableVincentAssets_P.%%F" if not exist "%BACKUP%\paks\FullyPlayableVincentAssets_P.%%F" copy /y "%VPAKS%\FullyPlayableVincentAssets_P.%%F" "%BACKUP%\paks\FullyPlayableVincentAssets_P.%%F" >nul
  if exist "%MODS%\VincentVoice_P.%%F" if not exist "%BACKUP%\paks\VincentVoice_P.%%F" copy /y "%MODS%\VincentVoice_P.%%F" "%BACKUP%\paks\VincentVoice_P.%%F" >nul
)
for %%J in (VincentDirge.json Vincent_Moves.json) do (
  if exist "%COMPAT%\%%J" if not exist "%BACKUP%\compat\%%J" copy /y "%COMPAT%\%%J" "%BACKUP%\compat\%%J" >nul
)
call :md5 "%BACKUP%\paks\FullyPlayableVincentAssets_P.utoc" 55fa8e60a7e9fb159523c572a76fd68e || goto :nobackup
call :md5 "%BACKUP%\paks\FullyPlayableVincentAssets_P.ucas" e8e19b57f1a7b019e7353d0676b6bd41 || goto :nobackup
echo    done>> "%STATUS%"

rem ---- 1. the voice
echo 1/3 VincentVoice_P v2 into Paks\~mods...>> "%STATUS%"
for %%F in (pak ucas utoc) do copy /y "%STAGE%\paks\VincentVoice_P.%%F" "%MODS%\VincentVoice_P.%%F" >nul
call :md5 "%MODS%\VincentVoice_P.pak" 602a1b0aee4bf950ec7a27d6bacae32e || goto :badvoice
call :md5 "%MODS%\VincentVoice_P.ucas" 5884eb2d0b6eaa318b4b329c15b8fe83 || goto :badvoice
call :md5 "%MODS%\VincentVoice_P.utoc" f84e042aea3885a8a7c7bff749b74f59 || goto :badvoice
if exist "%VOICEDOC%\VincentVoice_README.txt" if not exist "%BACKUP%\VincentVoice_README.txt" copy /y "%VOICEDOC%\VincentVoice_README.txt" "%BACKUP%\VincentVoice_README.txt" >nul
if exist "%VOICEDOC%" copy /y "%STAGE%\voice\VincentVoice_README.txt" "%VOICEDOC%\VincentVoice_README.txt" >nul
echo    installed and checked>> "%STATUS%"

rem ---- 2. the prologue
:assets
echo 2/3 FullyPlayableVincentAssets_P ^(the prologue's Cloud is Vincent^) into Paks\~mods\FullyPlayableVincentPaks...>> "%STATUS%"
for %%F in (pak ucas utoc) do copy /y "%STAGE%\paks\FullyPlayableVincentAssets_P.%%F" "%VPAKS%\FullyPlayableVincentAssets_P.%%F" >nul
call :md5 "%VPAKS%\FullyPlayableVincentAssets_P.pak" 978275e5395574cf363603d330e50a28 || goto :badassets
call :md5 "%VPAKS%\FullyPlayableVincentAssets_P.ucas" bf6acd8b1f52713e6674187465d64b5b || goto :badassets
call :md5 "%VPAKS%\FullyPlayableVincentAssets_P.utoc" c73040ee65a4e5e4e8b1ac9bfd7ce1ec || goto :badassets
echo    installed and checked>> "%STATUS%"

rem ---- 3. the settings
:settings
echo 3/3 VincentDirge.json and Vincent_Moves.json into the compat folder...>> "%STATUS%"
copy /y "%STAGE%\compat\VincentDirge.json" "%COMPAT%\VincentDirge.json" >nul
copy /y "%STAGE%\compat\Vincent_Moves.json" "%COMPAT%\Vincent_Moves.json" >nul
call :md5 "%COMPAT%\VincentDirge.json" bac80681a0e1171fb919573102482ec1 || goto :badjson
call :md5 "%COMPAT%\Vincent_Moves.json" 58790cb53dfd62419c783b7a337c6c58 || goto :badjson
echo    installed and checked>> "%STATUS%"
echo ALL DONE: start the game. He walks and runs in battle again, the prologue's Cloud is Vincent, and his voice is back without the crash. If anything is off send Sandalphon ue4ss\Mods\RebirthSkelCompat\RebirthSkelCompat.log>> "%STATUS%"
goto :done

:nocompat
echo STOPPED: the Create a Character System's compat folder is not there; nothing was changed>> "%STATUS%"
goto :done

:novincent
echo STOPPED: Paks\~mods\FullyPlayableVincentPaks\FullyPlayableVincentAssets_P is not there; nothing was changed>> "%STATUS%"
goto :done

:badstage
echo STOPPED: a staged file in Tools\_stage\prologue1016 is not the one made for this ^(see above^); nothing was changed: tell Sandalphon>> "%STATUS%"
goto :done

:nobackup
echo STOPPED: the installed FullyPlayableVincentAssets_P is not the one this was made from ^(or did not copy to Tools\_backup\prologue1016^); nothing was changed: tell Sandalphon>> "%STATUS%"
goto :done

:badvoice
echo FAILED: VincentVoice_P did not check out; moving it out of Paks\~mods ^(to Tools\_backup\prologue1016\failed^) so the game starts; going on with the rest>> "%STATUS%"
if not exist "%BACKUP%\failed" mkdir "%BACKUP%\failed"
for %%F in (pak ucas utoc) do if exist "%MODS%\VincentVoice_P.%%F" move /y "%MODS%\VincentVoice_P.%%F" "%BACKUP%\failed\VincentVoice_P.%%F" >nul
goto :assets

:badassets
echo FAILED: FullyPlayableVincentAssets_P did not check out; putting the old one back from Tools\_backup\prologue1016\paks; going on with the settings>> "%STATUS%"
for %%F in (pak ucas utoc) do if exist "%BACKUP%\paks\FullyPlayableVincentAssets_P.%%F" copy /y "%BACKUP%\paks\FullyPlayableVincentAssets_P.%%F" "%VPAKS%\FullyPlayableVincentAssets_P.%%F" >nul
goto :settings

:badjson
echo FAILED: the settings did not check out; putting the old ones back from Tools\_backup\prologue1016\compat>> "%STATUS%"
for %%J in (VincentDirge.json Vincent_Moves.json) do if exist "%BACKUP%\compat\%%J" copy /y "%BACKUP%\compat\%%J" "%COMPAT%\%%J" >nul
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
