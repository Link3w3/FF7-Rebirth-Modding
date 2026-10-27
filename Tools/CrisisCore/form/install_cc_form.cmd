@echo off
title CRISIS CORE form - installing it into the game, please leave this window open
rem The CRISIS CORE form (close the game first; the editor can stay open):
rem   1. updates the installed Fully Playable Young Sephiroth data container with the 18 CRISIS CORE moves (Battle10) and
rem      Cloud's rows listing Battle10 (the old files into <game>\_mod_backups\Paks\);
rem   2. puts the forms file in (compat\YoungSephirothForms.json: the CRISIS CORE form at the end of the forms menu; the
rem      old one into <game>\_mod_backups\ue4ss\).
rem Status: build\install_cc_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\install_cc_status.txt"
set "GAME=C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH"
set "STAGE=%~dp0stage_cc1"
echo CRISIS CORE form install, started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close the game ^(%%P^) first, then run this again>> "%STATUS%"
    goto :done
  )
)
for %%F in (install_data_tail.py install_forms_json.py FullyPlayableYoungSephirothDataAssets_P.utoc FullyPlayableYoungSephirothDataAssets_P.ucas.tail YoungSephirothForms.json) do (
  if not exist "%STAGE%\%%F" (
    echo FAILED: stage_cc1\%%F is missing ^(tell Sandalphon^)>> "%STATUS%"
    goto :done
  )
)
call :findpython
if not defined PY (
  echo FAILED: no Python found ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
echo 1/2 the data container...>> "%STATUS%"
%PY% "%STAGE%\install_data_tail.py" "%GAME%\End\Content\Paks" "%STAGE%" FullyPlayableYoungSephirothDataAssets_P 69ac8ff02b9e710eb2db1190fee43603 3dd1bd18f085d31df5abb3e4429754fe 258947216 b00520be21af25203dc89380fad31904 598be8199ca17670e5216a46cc6710b7 261569184 >> "%STATUS%" 2>&1
if errorlevel 1 (
  echo    THE DATA CONTAINER WAS NOT UPDATED ^(above^): tell Sandalphon; the forms file was not put in either>> "%STATUS%"
  goto :done
)
echo 2/2 the forms file...>> "%STATUS%"
%PY% "%STAGE%\install_forms_json.py" "%GAME%" "%STAGE%\YoungSephirothForms.json" 3b0cf255498c8cb24e27ed5661db8456 5fc8e354faabe4468d7c8cf9c22a5189 >> "%STATUS%" 2>&1
if errorlevel 1 (
  echo    THE FORMS FILE WAS NOT PUT IN ^(above^): tell Sandalphon>> "%STATUS%"
  goto :done
)
echo DONE: start the game, play Young Sephiroth and pick CRISIS CORE in the forms menu.>> "%STATUS%"
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
