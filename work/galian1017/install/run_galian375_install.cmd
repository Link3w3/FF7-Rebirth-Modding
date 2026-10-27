@echo off
title Vincent's Galian Beast - Create a Character System 3.7.5 - installing, please leave this window open
rem Installs (close the game first; takes a minute or two, most of it the mod's build):
rem   1. VincentGalian_P into Paks\~mods\FullyPlayableVincentPaks (new): the Galian Beast's moves (made of the Galian
rem      boss's animations), its anim blueprint and blend spaces,
rem   2. FullyPlayableVincentAssets_P into Paks\~mods\FullyPlayableVincentPaks: the beast's damage, its abilities and
rem      limit breaks, his CharaSpec rows listing its animation sets, effects and sounds (the gun rows as they are),
rem   3. zzVincentGunShop_P where it is now (Paks\~mods\FullyPlayableVincentPaks with his others, or Paks\~mods): the
rem      shop as it is, with the beast's ability names and help texts,
rem   4. VincentGalian.json into the compat folder: the GALIAN BEAST form on the forms menu (hold Triangle),
rem   5. builds the Create a Character System game mod 3.7.5 (main.dll, installed into the game): a form's "sets" (the
rem      beast keeps its own animations in Punisher mode and its own face). Then packs
rem      CreateACharacterSystem-Setup-3.7.5.exe into Tools\Share.
rem Everything it replaces is copied to Tools\_backup\galian375 first; every file is checked (md5).
rem Status: build\install375_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\install375_status.txt"
set "STAGE=C:\FF7R2UProj\Tools\_stage\galian375"
set "GAME=C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH"
set "MODS=%GAME%\End\Content\Paks\~mods"
set "VPAKS=%MODS%\FullyPlayableVincentPaks"
set "COMPAT=%GAME%\End\Binaries\Win64\ue4ss\Mods\RebirthSkelCompat\compat"
set "SC=C:\FF7R2UProj\Tools\RebirthSkelCompat"
set "SETUPTOOL=C:\FF7R2UProj\Tools\CreateACharacterSystemSetup"
set "BACKUP=C:\FF7R2UProj\Tools\_backup\galian375"
rem what may be installed now: the gun shop's (3.7.4), or this one's
set "ASSETS_UTOCS=b0b4a3bf3a1abe28cf4f8200dfd480ac 1b2fec320fa47daab913705d7993cc86"
set "SHOP_UTOCS=3c30ffa6e1989149d782fa6ed41a3f6c faa14a5357086a7e3c957e700bcfd62f"
set "CPPS=a4b759c2241577a2bffec737a86c5abd 021e381227ab087c7bb74f599488e4ee"
set "HPPS=4b70ac89f7dc8c6ea5ad709267110678 80a699a21b521cb9869e3c0ed2b1a4bd"
set "READMES=e16a2e0939383fb6351c5656c84bff3c 15f0ea170b9eed372af7a3442708a7d3"
echo Vincent's Galian Beast / Create a Character System 3.7.5 install started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close %%P first ^(the game^), then run this again>> "%STATUS%"
    goto :done
  )
)
if not exist "%COMPAT%\VincentDirge.json" goto :nocompat
if not exist "%VPAKS%\FullyPlayableVincentAssets_P.utoc" goto :novincent
rem the gun shop: where it is (its install put it in ~mods; it may since have gone in with his other containers)
set "SHOPDIR="
if exist "%MODS%\zzVincentGunShop_P.utoc" set "SHOPDIR=%MODS%"
if exist "%VPAKS%\zzVincentGunShop_P.utoc" (
  if defined SHOPDIR goto :twoshops
  set "SHOPDIR=%VPAKS%"
)
if not defined SHOPDIR goto :noshop
if not exist "%SC%\build_dll.py" goto :nosource
call :md5 "%SC%\build_dll.py" e3ff1c3bfce270d88e47239076c1fce2 || goto :oldbuild

echo checking the files to install...>> "%STATUS%"
call :md5 "%STAGE%\paks\VincentGalian_P.pak" 978275e5395574cf363603d330e50a28 || goto :badstage
call :md5 "%STAGE%\paks\VincentGalian_P.ucas" dd4b8f53de75ffe0a2eca223978225bb || goto :badstage
call :md5 "%STAGE%\paks\VincentGalian_P.utoc" dce384df37f1ab4e4eef5fecfcf34559 || goto :badstage
call :md5 "%STAGE%\paks\FullyPlayableVincentAssets_P.pak" 978275e5395574cf363603d330e50a28 || goto :badstage
call :md5 "%STAGE%\paks\FullyPlayableVincentAssets_P.ucas" da8576d559e8c23344273ceee444d192 || goto :badstage
call :md5 "%STAGE%\paks\FullyPlayableVincentAssets_P.utoc" 1b2fec320fa47daab913705d7993cc86 || goto :badstage
call :md5 "%STAGE%\paks\zzVincentGunShop_P.pak" 978275e5395574cf363603d330e50a28 || goto :badstage
call :md5 "%STAGE%\paks\zzVincentGunShop_P.ucas" 17287f84db84f76a7d14c3b30013b0fc || goto :badstage
call :md5 "%STAGE%\paks\zzVincentGunShop_P.utoc" faa14a5357086a7e3c957e700bcfd62f || goto :badstage
call :md5 "%STAGE%\compat\VincentGalian.json" 4b346e3225172f8ce46c14073c1e4f71 || goto :badstage
call :md5 "%STAGE%\src\RebirthSkelCompat.cpp" 021e381227ab087c7bb74f599488e4ee || goto :badstage
call :md5 "%STAGE%\src\SkelCompatCore.hpp" 80a699a21b521cb9869e3c0ed2b1a4bd || goto :badstage
call :md5 "%STAGE%\mod\README.txt" 15f0ea170b9eed372af7a3442708a7d3 || goto :badstage
echo    all 13 as made>> "%STATUS%"

echo checking what is installed now...>> "%STATUS%"
call :oneof "%VPAKS%\FullyPlayableVincentAssets_P.utoc" %ASSETS_UTOCS% || goto :notbase
call :oneof "%SHOPDIR%\zzVincentGunShop_P.utoc" %SHOP_UTOCS% || goto :notbase
call :oneof "%SC%\src\RebirthSkelCompat.cpp" %CPPS% || goto :notbase
call :oneof "%SC%\src\SkelCompatCore.hpp" %HPPS% || goto :notbase
call :oneof "%SC%\mod\README.txt" %READMES% || goto :notbase
if exist "%VPAKS%\VincentGalian_P.utoc" call :md5 "%VPAKS%\VincentGalian_P.utoc" dce384df37f1ab4e4eef5fecfcf34559 || goto :notbase
if exist "%COMPAT%\VincentGalian.json" call :md5 "%COMPAT%\VincentGalian.json" 4b346e3225172f8ce46c14073c1e4f71 || goto :notbase
echo    one this was made for>> "%STATUS%"

echo copying what this replaces to Tools\_backup\galian375...>> "%STATUS%"
for %%D in (paks src) do if not exist "%BACKUP%\%%D" mkdir "%BACKUP%\%%D"
for %%F in (pak ucas utoc) do if not exist "%BACKUP%\paks\FullyPlayableVincentAssets_P.%%F" copy /y "%VPAKS%\FullyPlayableVincentAssets_P.%%F" "%BACKUP%\paks\FullyPlayableVincentAssets_P.%%F" >nul
for %%F in (pak ucas utoc) do if not exist "%BACKUP%\paks\zzVincentGunShop_P.%%F" copy /y "%SHOPDIR%\zzVincentGunShop_P.%%F" "%BACKUP%\paks\zzVincentGunShop_P.%%F" >nul
for %%S in (RebirthSkelCompat.cpp SkelCompatCore.hpp) do if not exist "%BACKUP%\src\%%S" copy /y "%SC%\src\%%S" "%BACKUP%\src\%%S" >nul
if not exist "%BACKUP%\src\README.txt" copy /y "%SC%\mod\README.txt" "%BACKUP%\src\README.txt" >nul
rem (a backup is one of the installs this was made for; once made it is kept, so a second run keeps the first one's)
call :oneof "%BACKUP%\paks\FullyPlayableVincentAssets_P.utoc" %ASSETS_UTOCS% || goto :nobackup
call :oneof "%BACKUP%\paks\zzVincentGunShop_P.utoc" %SHOP_UTOCS% || goto :nobackup
call :oneof "%BACKUP%\src\RebirthSkelCompat.cpp" %CPPS% || goto :nobackup
call :oneof "%BACKUP%\src\SkelCompatCore.hpp" %HPPS% || goto :nobackup
call :oneof "%BACKUP%\src\README.txt" %READMES% || goto :nobackup
for %%F in (pak ucas) do if not exist "%BACKUP%\paks\FullyPlayableVincentAssets_P.%%F" goto :nobackup
for %%F in (pak ucas) do if not exist "%BACKUP%\paks\zzVincentGunShop_P.%%F" goto :nobackup
echo    done>> "%STATUS%"

rem ---- 1. the Galian Beast's moves
echo 1/5 VincentGalian_P ^(the Galian Beast's moves, anim blueprint and blend spaces^) into Paks\~mods\FullyPlayableVincentPaks...>> "%STATUS%"
for %%F in (pak ucas utoc) do copy /y "%STAGE%\paks\VincentGalian_P.%%F" "%VPAKS%\VincentGalian_P.%%F" >nul
call :md5 "%VPAKS%\VincentGalian_P.pak" 978275e5395574cf363603d330e50a28 || goto :failed
call :md5 "%VPAKS%\VincentGalian_P.ucas" dd4b8f53de75ffe0a2eca223978225bb || goto :failed
call :md5 "%VPAKS%\VincentGalian_P.utoc" dce384df37f1ab4e4eef5fecfcf34559 || goto :failed
echo    installed and checked>> "%STATUS%"

rem ---- 2. its data
echo 2/5 FullyPlayableVincentAssets_P ^(the beast's damage, abilities and limit breaks; his sets, effects and sounds^) into Paks\~mods\FullyPlayableVincentPaks...>> "%STATUS%"
for %%F in (pak ucas utoc) do copy /y "%STAGE%\paks\FullyPlayableVincentAssets_P.%%F" "%VPAKS%\FullyPlayableVincentAssets_P.%%F" >nul
call :md5 "%VPAKS%\FullyPlayableVincentAssets_P.pak" 978275e5395574cf363603d330e50a28 || goto :failed
call :md5 "%VPAKS%\FullyPlayableVincentAssets_P.ucas" da8576d559e8c23344273ceee444d192 || goto :failed
call :md5 "%VPAKS%\FullyPlayableVincentAssets_P.utoc" 1b2fec320fa47daab913705d7993cc86 || goto :failed
echo    installed and checked>> "%STATUS%"

rem ---- 3. its text
echo 3/5 zzVincentGunShop_P ^(the beast's ability names and help texts^) where it is ^(%SHOPDIR%^)...>> "%STATUS%"
for %%F in (pak ucas utoc) do copy /y "%STAGE%\paks\zzVincentGunShop_P.%%F" "%SHOPDIR%\zzVincentGunShop_P.%%F" >nul
call :md5 "%SHOPDIR%\zzVincentGunShop_P.pak" 978275e5395574cf363603d330e50a28 || goto :failed
call :md5 "%SHOPDIR%\zzVincentGunShop_P.ucas" 17287f84db84f76a7d14c3b30013b0fc || goto :failed
call :md5 "%SHOPDIR%\zzVincentGunShop_P.utoc" faa14a5357086a7e3c957e700bcfd62f || goto :failed
echo    installed and checked>> "%STATUS%"

rem ---- 4. the form
echo 4/5 VincentGalian.json ^(the GALIAN BEAST form^) into the compat folder...>> "%STATUS%"
copy /y "%STAGE%\compat\VincentGalian.json" "%COMPAT%\VincentGalian.json" >nul
call :md5 "%COMPAT%\VincentGalian.json" 4b346e3225172f8ce46c14073c1e4f71 || goto :failed
echo    installed and checked>> "%STATUS%"

rem ---- 5. the game mod 3.7.5
echo 5/5 building the Create a Character System game mod 3.7.5 ^(main.dll, installed into the game^)...>> "%STATUS%"
copy /y "%STAGE%\src\RebirthSkelCompat.cpp" "%SC%\src\RebirthSkelCompat.cpp" >nul
copy /y "%STAGE%\src\SkelCompatCore.hpp" "%SC%\src\SkelCompatCore.hpp" >nul
copy /y "%STAGE%\mod\README.txt" "%SC%\mod\README.txt" >nul
call :md5 "%SC%\src\RebirthSkelCompat.cpp" 021e381227ab087c7bb74f599488e4ee || goto :badsource
call :md5 "%SC%\src\SkelCompatCore.hpp" 80a699a21b521cb9869e3c0ed2b1a4bd || goto :badsource
call :md5 "%SC%\mod\README.txt" 15f0ea170b9eed372af7a3442708a7d3 || goto :badsource
call :findpython
%PY% "%SC%\build_dll.py" --install > "%~dp0build\install375_dll.log" 2>&1
if errorlevel 1 goto :badbuild
echo    game mod 3.7.5 built and installed>> "%STATUS%"
set "LATEST="
if exist "%SC%\build\latest.txt" set /p LATEST=<"%SC%\build\latest.txt"
%PY% "%SETUPTOOL%\make_setup.py" --stub "%SETUPTOOL%\Setup.stub.exe" --main-dll "%LATEST%\main.dll" --readme "%SC%\mod\README.txt" --example "%SC%\mod\compat\example.json.txt" --source "%SC%\src\RebirthSkelCompat.cpp" --plugin "C:\FF7R2UProj\Plugins\RebirthSkelCompat" --out-dir "C:\FF7R2UProj\Tools\Share" --version 3.7.5 > "%~dp0build\install375_setup.log" 2>&1
if errorlevel 1 (
  echo    the Setup was not packed ^(build\install375_setup.log^); the game mod is installed all the same>> "%STATUS%"
) else (
  echo    Setup packed ^(Tools\Share\CreateACharacterSystem-Setup-3.7.5.exe^)>> "%STATUS%"
)
echo ALL DONE: start the game and, in a battle, hold Triangle with Vincent: GALIAN BEAST is on the forms menu. After a fight send Sandalphon ue4ss\Mods\RebirthSkelCompat\RebirthSkelCompat.log>> "%STATUS%"
goto :done

:nocompat
echo STOPPED: the Create a Character System's compat folder ^(with VincentDirge.json^) is not there; nothing was changed>> "%STATUS%"
goto :done

:novincent
echo STOPPED: Paks\~mods\FullyPlayableVincentPaks\FullyPlayableVincentAssets_P is not there; nothing was changed>> "%STATUS%"
goto :done

:nosource
echo STOPPED: Tools\RebirthSkelCompat has no build_dll.py; nothing was changed>> "%STATUS%"
goto :done

:noshop
echo STOPPED: zzVincentGunShop_P ^(the gun shop^) is in neither Paks\~mods nor Paks\~mods\FullyPlayableVincentPaks; nothing was changed: tell Sandalphon>> "%STATUS%"
goto :done

:twoshops
echo STOPPED: zzVincentGunShop_P is in both Paks\~mods and Paks\~mods\FullyPlayableVincentPaks: keep one ^(move the other out of ~mods^), then run this again; nothing was changed>> "%STATUS%"
goto :done

:oldbuild
echo STOPPED: Tools\RebirthSkelCompat\build_dll.py is not the one this was made for; nothing was changed: tell Sandalphon>> "%STATUS%"
goto :done

:badstage
echo STOPPED: a staged file in Tools\_stage\galian375 is not the one made for this ^(see above^); nothing was changed: tell Sandalphon>> "%STATUS%"
goto :done

:notbase
echo STOPPED: what is installed is not one this was made for ^(see above^); nothing was changed: tell Sandalphon>> "%STATUS%"
goto :done

:nobackup
echo STOPPED: Tools\_backup\galian375 does not have a copy of what is installed ^(see above^); nothing was changed: tell Sandalphon>> "%STATUS%"
goto :done

:failed
echo FAILED: putting the containers and the settings back as they were...>> "%STATUS%"
if not exist "%BACKUP%\taken_out" mkdir "%BACKUP%\taken_out"
for %%F in (pak ucas utoc) do if exist "%VPAKS%\VincentGalian_P.%%F" move /y "%VPAKS%\VincentGalian_P.%%F" "%BACKUP%\taken_out\VincentGalian_P.%%F" >nul
if exist "%COMPAT%\VincentGalian.json" move /y "%COMPAT%\VincentGalian.json" "%BACKUP%\taken_out\VincentGalian.json" >nul
for %%F in (pak ucas utoc) do copy /y "%BACKUP%\paks\FullyPlayableVincentAssets_P.%%F" "%VPAKS%\FullyPlayableVincentAssets_P.%%F" >nul
for %%F in (pak ucas utoc) do copy /y "%BACKUP%\paks\zzVincentGunShop_P.%%F" "%SHOPDIR%\zzVincentGunShop_P.%%F" >nul
for %%F in (pak ucas utoc) do if exist "%VPAKS%\VincentGalian_P.%%F" goto :stuck
if exist "%COMPAT%\VincentGalian.json" goto :stuck
for %%F in (pak ucas utoc) do fc /b "%BACKUP%\paks\FullyPlayableVincentAssets_P.%%F" "%VPAKS%\FullyPlayableVincentAssets_P.%%F" >nul || goto :stuck
for %%F in (pak ucas utoc) do fc /b "%BACKUP%\paks\zzVincentGunShop_P.%%F" "%SHOPDIR%\zzVincentGunShop_P.%%F" >nul || goto :stuck
echo    put back and checked ^(the Galian Beast's files moved to Tools\_backup\galian375\taken_out^): the game is as it was before this; tell Sandalphon>> "%STATUS%"
goto :done

:stuck
echo    NOT all of it could be put back: do not start the game; tell Sandalphon>> "%STATUS%"
goto :done

:badsource
echo FAILED: the 3.7.5 source did not copy into Tools\RebirthSkelCompat ^(see above^); putting the old source back; the Galian Beast is installed, the game mod stays 3.7.4 ^(the form works, but Punisher mode and its face use Vincent's sets^): run this again>> "%STATUS%"
goto :oldsource

:badbuild
echo FAILED: the game mod did not build ^(build\install375_dll.log^); the Galian Beast is installed, the game mod stays 3.7.4 ^(the form works, but Punisher mode and its face use Vincent's sets^) and the old source goes back: tell Sandalphon>> "%STATUS%"
goto :oldsource

:oldsource
for %%S in (RebirthSkelCompat.cpp SkelCompatCore.hpp) do copy /y "%BACKUP%\src\%%S" "%SC%\src\%%S" >nul
copy /y "%BACKUP%\src\README.txt" "%SC%\mod\README.txt" >nul
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

:findpython
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python399\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python399\python.exe"
if not defined PY set "PY=python"
exit /b
