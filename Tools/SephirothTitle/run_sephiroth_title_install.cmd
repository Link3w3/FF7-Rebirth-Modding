@echo off
title Sephiroth title screen - installing, please leave this window open
rem Installs the Sephiroth title screen (close the game first; takes a second):
rem   SephirothTitleScreen_P (.pak, .ucas, .utoc) into ~mods: on the title screen the Buster Sword is the bloody
rem   Masamune (WE1021_01 Brood, same place and angle), Sephiroth's black feathers fall (in place of the title's green
rem   motes) and the music is One-Winged Angel - Reborn (the final battle's last part) instead of the Prelude. It holds
rem   only four of the title's own packages, patched; nothing of the game itself is changed.
rem   If SephirothTitleScreen_P is already in ~mods (or a folder in it, like FullyPlayableSephirothPaks), it is
rem   replaced there; the old files go to Tools\SephirothTitle\backup first. run_sephiroth_title_remove.cmd takes it out.
rem Every file is checked (md5). Status: build\install_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\install_status.txt"
set "STAGE=%~dp0stage"
set "BACKUP=%~dp0backup"
set "GAME=C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH"
set "MODS=%GAME%\End\Content\Paks\~mods"
set "PAK=SephirothTitleScreen_P"
set "UCAS_MD5=f287795ac27e691c6097043f617a290e"
set "UTOC_MD5=a2a7973683abb6815368731059bbe2fc"
set "PAK_MD5=978275e5395574cf363603d330e50a28"
echo Sephiroth title screen install started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close %%P first ^(the game^), then run this again>> "%STATUS%"
    goto :done
  )
)
if not exist "%MODS%" goto :nomods
echo checking the files to install...>> "%STATUS%"
call :md5 "%STAGE%\%PAK%.ucas" %UCAS_MD5% || goto :badstage
call :md5 "%STAGE%\%PAK%.utoc" %UTOC_MD5% || goto :badstage
call :md5 "%STAGE%\%PAK%.pak" %PAK_MD5% || goto :badstage
echo    all three as made>> "%STATUS%"

rem where it goes: the folder it is in already (the last one found), else ~mods itself
set "DEST="
set "COPIES=0"
for /r "%MODS%" %%F in (%PAK%.utoc) do if exist "%%F" call :found "%%~dpF"
if not defined DEST set "DEST=%MODS%\"
if %COPIES% GTR 1 echo    NOTE: %COPIES% copies of %PAK% were in ~mods; only the one in "%DEST%" is replaced>> "%STATUS%"
echo installing into "%DEST%"...>> "%STATUS%"
if not exist "%DEST%%PAK%.utoc" goto :copy
if not exist "%BACKUP%" mkdir "%BACKUP%"
copy /y "%DEST%%PAK%.ucas" "%BACKUP%\%PAK%.ucas" >nul
copy /y "%DEST%%PAK%.utoc" "%BACKUP%\%PAK%.utoc" >nul
if exist "%DEST%%PAK%.pak" copy /y "%DEST%%PAK%.pak" "%BACKUP%\%PAK%.pak" >nul
echo    the old files copied to Tools\SephirothTitle\backup>> "%STATUS%"

:copy
copy /y "%STAGE%\%PAK%.ucas" "%DEST%%PAK%.ucas" >nul
copy /y "%STAGE%\%PAK%.utoc" "%DEST%%PAK%.utoc" >nul
copy /y "%STAGE%\%PAK%.pak" "%DEST%%PAK%.pak" >nul
call :md5 "%DEST%%PAK%.ucas" %UCAS_MD5% || goto :badcopy
call :md5 "%DEST%%PAK%.utoc" %UTOC_MD5% || goto :badcopy
call :md5 "%DEST%%PAK%.pak" %PAK_MD5% || goto :badcopy
echo    installed and checked>> "%STATUS%"
echo ALL DONE: start the game; the title screen has the bloody Masamune, black feathers falling and One-Winged Angel>> "%STATUS%"
goto :done

:found
set "DEST=%~1"
set /a COPIES+=1
exit /b 0

:nomods
echo STOPPED: the game's ~mods folder is not there; nothing was changed>> "%STATUS%"
goto :done

:badstage
echo STOPPED: a file in Tools\SephirothTitle\stage is not the one made for this ^(see above^); nothing was changed>> "%STATUS%"
goto :done

:badcopy
echo FAILED: a file in ~mods did not check out; run this again ^(or run_sephiroth_title_remove.cmd^)>> "%STATUS%"
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
