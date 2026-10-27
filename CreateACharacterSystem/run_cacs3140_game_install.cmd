@echo off
title Create a Character System 3.14.0 - building the game mod and installing it, please leave this window open
rem Create a Character System 3.14.0 (close the game first; the editor can stay open):
rem   1. builds the game mod 3.14.0 (main.dll) from Tools\RebirthSkelCompat\src and installs it (build_dll.py --install:
rem      the old main.dll is kept as dlls\main.dll.bak-<time>): KawaiiPhysics (a file's "kawaii" entries run on the meshes
rem      of their models; "disable_bonamik" turns the model's BNMs off), and everything of 3.13.0 (the EFFECTS page);
rem   2. the boss's feelers on WINGED and FLYING in both Sephiroth forms files (patch_feelers_3122.py: nothing to do
rem      when they have them);
rem   3. writes the Customization screen's catalog again (make_customization_catalog.py 3.13.0: its "effects", and the
rem      wing with the boss's feelers);
rem   4. puts Young Sephiroth's KawaiiPhysics file into compat (install_kawaii_3140.py: compat\YoungSephirothKawaii.json;
rem      his hair, coat and collar, his body BNM off while his model is shown, his wing's BNM and KDI left on).
rem Status: Tools\RebirthSkelCompat\build\install3140_status.txt
rem Leave the window open until it says FINISHED (the build takes a few minutes; Ctrl+C stops it half way).
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\install3140_status.txt"
set "COMPAT=C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH\End\Binaries\Win64\ue4ss\Mods\RebirthSkelCompat\compat"
echo Create a Character System 3.14.0 game mod install, started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close the game ^(%%P^) first, then run this again>> "%STATUS%"
    goto :done
  )
)
for %%F in (build_dll.py patch_feelers_3122.py make_customization_catalog.py install_kawaii_3140.py src\RebirthSkelCompat.cpp src\SkelCompatCore.hpp src\KawaiiSolver.hpp compat_3140\YoungSephirothKawaii.json) do (
  if not exist "%~dp0%%F" (
    echo FAILED: %%F is missing ^(tell Sandalphon^)>> "%STATUS%"
    goto :done
  )
)
findstr /L /C:"= L\"3.14.0\";" "%~dp0src\RebirthSkelCompat.cpp" >nul
if errorlevel 1 (
  echo FAILED: src\RebirthSkelCompat.cpp is not 3.14.0 ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
findstr /L /C:"KawaiiSolver.hpp" "%~dp0build_dll.py" >nul
if errorlevel 1 (
  echo FAILED: build_dll.py is not the 3.14.0 one ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
call :findpython
echo 1/4 building the game mod 3.14.0 ^(main.dll^) and installing it ^(a few minutes^)...>> "%STATUS%"
type "%STATUS%"
%PY% "%~dp0build_dll.py" --install > "%~dp0build\install3140_dll.log" 2>&1
if errorlevel 1 goto :dllfailed
echo    game mod 3.14.0 installed.>> "%STATUS%"
echo 2/4 the boss's feelers on WINGED and FLYING ^(the forms files^)...>> "%STATUS%"
rem (the folder's path has parentheses in it: it is only ever used in quotes, never inside a ( ) block)
if not exist "%COMPAT%\" goto :nocompat
%PY% "%~dp0patch_feelers_3122.py" "%COMPAT%" > "%~dp0build\install3140_feelers.log" 2>&1
if errorlevel 1 goto :feelersfailed
type "%~dp0build\install3140_feelers.log">> "%STATUS%"
goto :catalog
:nocompat
echo    ^(the mod's compat folder was not found; the forms files were not changed^)>> "%STATUS%"
goto :catalog
:feelersfailed
echo    ^(a forms file was not changed: build\install3140_feelers.log^)>> "%STATUS%"
:catalog
echo 3/4 writing the Customization catalog...>> "%STATUS%"
%PY% "%~dp0make_customization_catalog.py" > "%~dp0build\install3140_catalog.log" 2>&1
if errorlevel 1 goto :catalogfailed
echo    catalog written ^(build\install3140_catalog.log^)>> "%STATUS%"
goto :kawaii
:catalogfailed
echo    ^(the catalog was not written again: build\install3140_catalog.log; the one there stays^)>> "%STATUS%"
:kawaii
echo 4/4 Young Sephiroth's KawaiiPhysics file...>> "%STATUS%"
if not exist "%COMPAT%\" goto :nokawaii
%PY% "%~dp0install_kawaii_3140.py" "%COMPAT%" > "%~dp0build\install3140_kawaii.log" 2>&1
if errorlevel 1 goto :kawaiifailed
type "%~dp0build\install3140_kawaii.log">> "%STATUS%"
goto :finish
:nokawaii
echo    ^(the mod's compat folder was not found; the file was not put in^)>> "%STATUS%"
goto :finish
:kawaiifailed
echo    ^(the file was not put in: build\install3140_kawaii.log^)>> "%STATUS%"
:finish
echo DONE: start the game. The mod's log should say "RebirthSkelCompat 3.14.0 starting" and "Kawaii: 1 entry(s) for 1 model(s): ready".>> "%STATUS%"
goto :done
:dllfailed
echo FAILED: the game mod did not build ^(build\install3140_dll.log^); nothing was changed>> "%STATUS%"
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
