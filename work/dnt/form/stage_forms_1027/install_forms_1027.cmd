@echo off
title DISSIDIA NT form and the CRISIS CORE field set - installing them into the game, please leave this window open
rem The DISSIDIA NT form (pack Battle12) and the CRISIS CORE skins' field set (Neutral10), for Fully Playable Young
rem Sephiroth (close the game first; the editor can stay open):
rem   1. puts the new build of the Fully Playable Young Sephiroth data container in (the 18 DISSIDIA NT moves and the 4
rem      Crisis Core field moves added, Battle12 on Sephiroth's CharaSpec rows): the installed .ucas with new blocks after
rem      it, the old files into <game>\_mod_backups\Paks\;
rem   2. puts the forms file in (compat\YoungSephirothForms.json with the DISSIDIA NT form and the field set; the old one
rem      into <game>\_mod_backups\ue4ss\).
rem Status: build\install_forms_1027_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\install_forms_1027_status.txt"
set "GAME=C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH"
set "STAGE=%~dp0stage_forms_1027"
echo DISSIDIA NT form install, started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close the game ^(%%P^) first, then run this again>> "%STATUS%"
    goto :done
  )
)
for %%F in (install_data_rebase.py install_forms_json.py FullyPlayableYoungSephirothDataAssets_P.utoc FullyPlayableYoungSephirothDataAssets_P.ucas.tail YoungSephirothForms.json) do (
  if not exist "%STAGE%\%%F" (
    echo FAILED: stage_forms_1027\%%F is missing ^(tell Sandalphon^)>> "%STATUS%"
    goto :done
  )
)
call :findpython
if not defined PY (
  echo FAILED: no Python found ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
echo 1/2 the data container...>> "%STATUS%"
%PY% "%STAGE%\install_data_rebase.py" "%GAME%\End\Content\Paks" "%STAGE%" FullyPlayableYoungSephirothDataAssets_P 267039472 70f560cbabd6637b9ce829a756cbc129 5487bb622f8d354781588922436fcd8c b02caf18548d3a1241f2ad1049a3b337 269729056 72533e6420ae98b00a13762a6b7cb6c6 >> "%STATUS%" 2>&1
if errorlevel 1 (
  echo    THE DATA CONTAINER WAS NOT UPDATED ^(above^): tell Sandalphon>> "%STATUS%"
  goto :done
)
echo 2/2 the forms file...>> "%STATUS%"
%PY% "%STAGE%\install_forms_json.py" "%GAME%" "%STAGE%\YoungSephirothForms.json" de29a4b763ed4d5e084a115966b2f8ea dfeef99a1a9f3b434bba5bda86aee702 >> "%STATUS%" 2>&1
if errorlevel 1 (
  echo    THE FORMS FILE WAS NOT PUT IN ^(above^): tell Sandalphon>> "%STATUS%"
  goto :done
)
echo DONE: start the game, play Young Sephiroth and pick DISSIDIA NT in the forms menu.>> "%STATUS%"
:done
type "%STATUS%"
echo.
pause
exit /b 0

:findpython
set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY (
  where python >nul 2>&1 && set "PY=python"
)
exit /b 0
