@echo off
title Create a Character System 3.16.0, CLOUD and the CLOUD moveset - installing, please leave this window open
rem Create a Character System 3.16.0 with CLOUD and the CLOUD moveset (close the game first; the editor can stay open):
rem   1. builds the game mod 3.16.0 (main.dll) from Tools\RebirthSkelCompat\src and installs it (build_dll.py --install:
rem      the old main.dll is kept as dlls\main.dll.bak-<time>, the mod's README.txt updated):
rem        - the Customization screen's CHARACTER page: who plays in Cloud's place, Sephiroth or CLOUD (the game's own
rem          Cloud as a character of his own), one at a time, from the next map load,
rem        - the MOVESET page (it takes the COMBO page's place): a form plays another form's whole moveset, or CLOUD's,
rem        - Cloud skins' Buster Sword on his back outside battle,
rem   2. puts CLOUD's container CreateACharacterCloud_P (his own CharaSpec packs, blueprints and AnimBlueprint) in
rem      ~mods\CreateACharacterCloud and the CLOUD moveset's moves (CloudMovesetMoves_P) in
rem      ~mods\FullyPlayableSephirothPaks\CloudMoveset,
rem   3. updates the Fully Playable Young Sephiroth data container with CLOUD's rows (his CharaSpec rows, pt_Cloud and
rem      Cloud's abilities as the game has them; the old files go to the game's _mod_backups\Paks first),
rem   4. puts CloudCharacter.json in the mod's compat folder, the CLOUD moveset in YoungSephirothForms.json and
rem      SephirothForms.json, and "weapon_field_socket" in the skins RebirthCloud and RemakeCloud (the files there before go
rem      to the game's _mod_backups\ue4ss first).
rem Status: Tools\CloudCharacter\build\install3160_status.txt
rem Leave the window open until it says FINISHED (the build takes a few minutes; Ctrl+C stops it half way).
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\install3160_status.txt"
set "CACS=C:\FF7R2UProj\Tools\RebirthSkelCompat"
echo Create a Character System 3.16.0, CLOUD and the CLOUD moveset install, started %DATE% %TIME%> "%STATUS%"
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
findstr /L /C:"= L\"3.16.0\";" "%CACS%\src\RebirthSkelCompat.cpp" >nul
if errorlevel 1 (
  echo FAILED: Tools\RebirthSkelCompat\src\RebirthSkelCompat.cpp is not 3.16.0 ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
findstr /L /C:"ParseCharacters" "%CACS%\src\SkelCompatCore.hpp" >nul
if errorlevel 1 (
  echo FAILED: Tools\RebirthSkelCompat\src\SkelCompatCore.hpp is not 3.16.0's ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
findstr /L /C:"Create a Character System 3.16.0" "%CACS%\mod\README.txt" >nul
if errorlevel 1 (
  echo FAILED: Tools\RebirthSkelCompat\mod\README.txt is not 3.16.0's ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
call :findpython
echo 1/4 checking the files, the installed Fully Playable Young Sephiroth data container and the files the changes are for...>> "%STATUS%"
%PY% "%~dp0install_cloud_character.py" --check >> "%STATUS%" 2>&1
if errorlevel 1 (
  echo FAILED: nothing was changed ^(see above^)>> "%STATUS%"
  goto :done
)
echo 2/4 building the game mod 3.16.0 ^(main.dll^) and installing it ^(a few minutes^)...>> "%STATUS%"
type "%STATUS%"
%PY% "%CACS%\build_dll.py" --install > "%~dp0build\install3160_dll.log" 2>&1
if errorlevel 1 (
  echo FAILED: the game mod did not build ^(Tools\CloudCharacter\build\install3160_dll.log^); nothing was changed: tell Sandalphon>> "%STATUS%"
  goto :done
)
echo    game mod 3.16.0 installed.>> "%STATUS%"
echo 3/4 CLOUD's container and the CLOUD moveset's moves, CLOUD's rows in the data container, the compat files and skins...>> "%STATUS%"
%PY% "%~dp0install_cloud_character.py" --install >> "%STATUS%" 2>&1
if errorlevel 1 (
  echo FAILED: see above ^(the game mod 3.16.0 is in; the files above the failure are in, the ones after it are not^): tell Sandalphon>> "%STATUS%"
  goto :done
)
echo 4/4 done.>> "%STATUS%"
echo DONE: start the game. The log should say "RebirthSkelCompat 3.16.0 starting". In the field: the main menu, Customization:>> "%STATUS%"
echo   - the MOVESET page: CLOUD is on the list ^(Sephiroth fights with Cloud's motions from his next move^),>> "%STATUS%"
echo   - a Cloud skin ^(SKINS page^): the Buster Sword on his back in the field, in his hand in battle,>> "%STATUS%"
echo   - the CHARACTER page ^(the last page: L1 once^): Sephiroth is "Playing"; Cross on CLOUD says "Next load". Save, load that>> "%STATUS%"
echo     save: Cloud is back in his place ^(Sephiroth again: Square on the page, then the next load^).>> "%STATUS%"
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
