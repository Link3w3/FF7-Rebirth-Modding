@echo off
title Create a Character System 3.13.0 - building the game mod and installing it, please leave this window open
rem Create a Character System 3.13.0 (close the game first; the editor can stay open):
rem   1. builds the game mod 3.13.0 (main.dll) from Tools\RebirthSkelCompat\src and installs it (build_dll.py --install:
rem      the old main.dll is kept as dlls\main.dll.bak-<time>): the Customization screen's EFFECTS page (effects kept on
rem      a character's weapon, its body or a part it wears), a part's own effects; 3.12.2's COMBO fix for skin forms and
rem      forms' "state_effects" / "watch_damage" are in it;
rem   2. the boss's feelers on WINGED and FLYING in both Sephiroth forms files (patch_feelers_3122.py: nothing to do
rem      when they have them);
rem   3. writes the Customization screen's catalog again (make_customization_catalog.py 3.13.0: its "effects", and the
rem      wing with the boss's feelers).
rem Status: Tools\RebirthSkelCompat\build\install3130_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\install3130_status.txt"
set "COMPAT=C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH\End\Binaries\Win64\ue4ss\Mods\RebirthSkelCompat\compat"
echo Create a Character System 3.13.0 game mod install, started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close the game ^(%%P^) first, then run this again>> "%STATUS%"
    goto :done
  )
)
for %%F in (build_dll.py patch_feelers_3122.py make_customization_catalog.py) do (
  if not exist "%~dp0%%F" (
    echo FAILED: %%F is missing ^(tell Sandalphon^)>> "%STATUS%"
    goto :done
  )
)
findstr /L /C:"= L\"3.13.0\";" "%~dp0src\RebirthSkelCompat.cpp" >nul
if errorlevel 1 (
  echo FAILED: src\RebirthSkelCompat.cpp is not 3.13.0 ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
call :findpython
echo 1/3 building the game mod 3.13.0 ^(main.dll^) and installing it...>> "%STATUS%"
type "%STATUS%"
%PY% "%~dp0build_dll.py" --install > "%~dp0build\install3130_dll.log" 2>&1
if errorlevel 1 goto :dllfailed
echo    game mod 3.13.0 installed.>> "%STATUS%"
echo 2/3 the boss's feelers on WINGED and FLYING ^(the forms files^)...>> "%STATUS%"
rem (the folder's path has parentheses in it: it is only ever used in quotes, never inside a ( ) block)
if not exist "%COMPAT%\" goto :nocompat
%PY% "%~dp0patch_feelers_3122.py" "%COMPAT%" > "%~dp0build\install3130_feelers.log" 2>&1
if errorlevel 1 goto :feelersfailed
type "%~dp0build\install3130_feelers.log">> "%STATUS%"
goto :catalog
:nocompat
echo    ^(the mod's compat folder was not found; the forms files were not changed^)>> "%STATUS%"
goto :catalog
:feelersfailed
echo    ^(a forms file was not changed: build\install3130_feelers.log^)>> "%STATUS%"
:catalog
echo 3/3 writing the Customization catalog...>> "%STATUS%"
%PY% "%~dp0make_customization_catalog.py" > "%~dp0build\install3130_catalog.log" 2>&1
if errorlevel 1 goto :catalogfailed
echo    catalog written ^(build\install3130_catalog.log^)>> "%STATUS%"
goto :finish
:catalogfailed
echo    ^(the catalog was not written again: build\install3130_catalog.log; the one there stays^)>> "%STATUS%"
:finish
echo DONE: start the game. The mod's log should say "RebirthSkelCompat 3.13.0 starting"; the Customization screen has an EFFECTS page.>> "%STATUS%"
goto :done
:dllfailed
echo FAILED: the game mod did not build ^(build\install3130_dll.log^); nothing was changed>> "%STATUS%"
:done
echo FINISHED %DATE% %TIME%>> "%STATUS%"
type "%STATUS%"
pause
exit /b

:findpython
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python399\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python399\python.exe"
if not defined PY set "PY=python"
exit /b
