@echo off
title Create a Character System 3.16.1 - installing, please leave this window open
rem Create a Character System 3.16.1 (close the game first; the editor can stay open):
rem   1. checks CLOUD's files (CreateACharacterCloud_P, the CLOUD moveset's moves, his rows in the Fully Playable Young
rem      Sephiroth data container, CloudCharacter.json, the forms files' CLOUD moveset, the Cloud skins' socket): each
rem      the one made, in place or not yet (a container moved to another folder under ~mods counts as in place),
rem   2. builds the game mod 3.16.1 (main.dll) from Tools\RebirthSkelCompat\src and installs it (build_dll.py --install:
rem      the old main.dll is kept as dlls\main.dll.bak-<time>, the mod's README.txt updated),
rem   3. puts in any of CLOUD's files not in place yet (after the 3.16.0 install: the forms files, whose CLOUD moveset now
rem      puts the Buster Sword in Cloud's right hand in battle; the files there before go to the game's _mod_backups first).
rem 3.16.1: a CHARACTER page character waits at the start for every table it reads; one it can do without that the game
rem had not loaded yet goes in at the next map load once it is there; a data object not found is looked for again a
rem second later at the soonest; a compat row's "refresh_abilities": false holds for a place's recalculation too; a
rem moveset's "weapon_socket" (CLOUD's: the sword in his right hand in battle); a skin's field socket 4 times a second.
rem Status: Tools\CloudCharacter\build\install3161_status.txt
rem Leave the window open until it says FINISHED (the build takes a few minutes; Ctrl+C stops it half way).
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\install3161_status.txt"
set "CACS=C:\FF7R2UProj\Tools\RebirthSkelCompat"
echo Create a Character System 3.16.1 install, started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close the game ^(%%P^) first, then run this again>> "%STATUS%"
    goto :done
  )
)
for %%F in (install_cloud_character.py install_data_rebase.py manifest.json CloudCharacter.json CreateACharacterCloud_P.utoc CreateACharacterCloud_P.ucas CreateACharacterCloud_P.pak CloudMovesetMoves_P.utoc CloudMovesetMoves_P.ucas CloudMovesetMoves_P.pak) do (
  if not exist "%~dp0%%F" (
    echo FAILED: %%F is missing ^(tell Sandalphon^)>> "%STATUS%"
    goto :done
  )
)
for %%F in (moveset\compat\YoungSephirothForms.json moveset\compat\SephirothForms.json moveset\skins\RebirthCloud\skin.json moveset\skins\RemakeCloud\skin.json) do (
  if not exist "%~dp0%%F" (
    echo FAILED: %%F is missing ^(tell Sandalphon^)>> "%STATUS%"
    goto :done
  )
)
for %%F in (build_dll.py src\RebirthSkelCompat.cpp src\SkelCompatCore.hpp src\KawaiiSolver.hpp mod\README.txt) do (
  if not exist "%CACS%\%%F" (
    echo FAILED: Tools\RebirthSkelCompat\%%F is missing ^(tell Sandalphon^)>> "%STATUS%"
    goto :done
  )
)
findstr /L /C:"= L\"3.16.1\";" "%CACS%\src\RebirthSkelCompat.cpp" >nul
if errorlevel 1 (
  echo FAILED: Tools\RebirthSkelCompat\src\RebirthSkelCompat.cpp is not 3.16.1 ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
findstr /L /C:"CharacterTableOptional" "%CACS%\src\SkelCompatCore.hpp" >nul
if errorlevel 1 (
  echo FAILED: Tools\RebirthSkelCompat\src\SkelCompatCore.hpp is not 3.16's ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
findstr /L /C:"Create a Character System 3.16.1" "%CACS%\mod\README.txt" >nul
if errorlevel 1 (
  echo FAILED: Tools\RebirthSkelCompat\mod\README.txt is not 3.16.1's ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
call :findpython
echo 1/4 checking CLOUD's files, the installed Fully Playable Young Sephiroth data container and the files the changes are for...>> "%STATUS%"
%PY% "%~dp0install_cloud_character.py" --check >> "%STATUS%" 2>&1
if errorlevel 1 (
  echo FAILED: nothing was changed ^(see above^)>> "%STATUS%"
  goto :done
)
echo 2/4 building the game mod 3.16.1 ^(main.dll^) and installing it ^(a few minutes^)...>> "%STATUS%"
type "%STATUS%"
%PY% "%CACS%\build_dll.py" --install > "%~dp0build\install3161_dll.log" 2>&1
if errorlevel 1 (
  echo FAILED: the game mod did not build ^(Tools\CloudCharacter\build\install3161_dll.log^); nothing was changed: tell Sandalphon>> "%STATUS%"
  goto :done
)
echo    game mod 3.16.1 installed.>> "%STATUS%"
echo 3/4 CLOUD's files not in place yet ^(after the 3.16.0 install: the forms files, the CLOUD moveset with the sword in his right hand^)...>> "%STATUS%"
%PY% "%~dp0install_cloud_character.py" --install >> "%STATUS%" 2>&1
if errorlevel 1 (
  echo FAILED: see above ^(the game mod 3.16.1 is in; the files above the failure are in, the ones after it are not^): tell Sandalphon>> "%STATUS%"
  goto :done
)
echo 4/4 done.>> "%STATUS%"
echo DONE: start the game. The log should say "RebirthSkelCompat 3.16.1 starting".>> "%STATUS%"
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
