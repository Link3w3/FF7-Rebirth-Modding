@echo off
title CRISIS CORE form (moves upright) - installing it into the game, please leave this window open
rem The CRISIS CORE form, its moves made again upright (close the game first; the editor can stay open):
rem   1. puts the new build of the Fully Playable Young Sephiroth data container in (the 18 CRISIS CORE moves of Battle10
rem      made again from Crisis Core's animations with the body upright under the root: the first build's lay on their
rem      side in game). The installed container can be the first CRISIS CORE build or the one before it; the old files go
rem      into <game>\_mod_backups\Paks\;
rem   2. makes sure the forms file has the CRISIS CORE form (compat\YoungSephirothForms.json; the old one into
rem      <game>\_mod_backups\ue4ss\ when it changes).
rem Status: build\install_cc2_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\install_cc2_status.txt"
set "GAME=C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH"
set "STAGE=%~dp0stage_cc2"
echo CRISIS CORE form (moves upright) install, started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close the game ^(%%P^) first, then run this again>> "%STATUS%"
    goto :done
  )
)
for %%F in (install_data_rebase.py FullyPlayableYoungSephirothDataAssets_P.utoc FullyPlayableYoungSephirothDataAssets_P.ucas.tail YoungSephirothForms.json) do (
  if not exist "%STAGE%\%%F" (
    echo FAILED: stage_cc2\%%F is missing ^(tell Sandalphon^)>> "%STATUS%"
    goto :done
  )
)
if not exist "%~dp0stage_cc1\install_forms_json.py" (
  echo FAILED: stage_cc1\install_forms_json.py is missing ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
call :findpython
if not defined PY (
  echo FAILED: no Python found ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
echo 1/2 the data container...>> "%STATUS%"
%PY% "%STAGE%\install_data_rebase.py" "%GAME%\End\Content\Paks" "%STAGE%" FullyPlayableYoungSephirothDataAssets_P 258947216 3dd1bd18f085d31df5abb3e4429754fe 4d67898e2aeb64750ba0c4e946effb82 d7d5ec97db303d3fddbaa7aaf96c07d1 261569712 b00520be21af25203dc89380fad31904,69ac8ff02b9e710eb2db1190fee43603 >> "%STATUS%" 2>&1
if errorlevel 1 (
  echo    THE DATA CONTAINER WAS NOT UPDATED ^(above^): tell Sandalphon>> "%STATUS%"
  goto :done
)
echo 2/2 the forms file...>> "%STATUS%"
%PY% "%~dp0stage_cc1\install_forms_json.py" "%GAME%" "%STAGE%\YoungSephirothForms.json" 3b0cf255498c8cb24e27ed5661db8456 5fc8e354faabe4468d7c8cf9c22a5189 >> "%STATUS%" 2>&1
if errorlevel 1 (
  echo    THE FORMS FILE WAS NOT PUT IN ^(above^): tell Sandalphon>> "%STATUS%"
  goto :done
)
echo DONE: start the game, play Young Sephiroth and pick CRISIS CORE in the forms menu: his moves stand upright now.>> "%STATUS%"
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
