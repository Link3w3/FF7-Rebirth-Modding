@echo off
title CLOUD voice fix - installing, please leave this window open
rem CLOUD's voice fix (close the game first; the editor can stay open):
rem   CreateACharacterCloud_P again: its CharaSpec packs listed the English, French and German copies of Cloud's voice
rem   and lip sync as packages to load, besides the ones the game's own packs list. The game then loaded every language
rem   of his voice into the one voice package it plays: his voice in another language, and the crashes (his first voice
rem   line after the CHARACTER page swap; loading a save with CLOUD chosen). The packages are the same; only the
rem   container's header is new. The old files go to the game's _mod_backups\Paks first. Nothing else changes.
rem Status: Tools\CloudCharacter\build\voicefix_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\voicefix_status.txt"
echo CLOUD voice fix, started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close the game ^(%%P^) first, then run this again>> "%STATUS%"
    goto :done
  )
)
for %%F in (install_cloud_voicefix.py CreateACharacterCloud_P.utoc CreateACharacterCloud_P.ucas CreateACharacterCloud_P.pak) do (
  if not exist "%~dp0voicefix\%%F" (
    echo FAILED: voicefix\%%F is missing ^(tell Sandalphon^)>> "%STATUS%"
    goto :done
  )
)
if not exist "%~dp0manifest.json" (
  echo FAILED: manifest.json is missing ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
call :findpython
echo 1/2 checking the fixed files and the installed CreateACharacterCloud_P...>> "%STATUS%"
%PY% "%~dp0voicefix\install_cloud_voicefix.py" --check >> "%STATUS%" 2>&1
if errorlevel 1 (
  echo FAILED: nothing was changed ^(see above^)>> "%STATUS%"
  goto :done
)
echo 2/2 putting the fixed CreateACharacterCloud_P in...>> "%STATUS%"
%PY% "%~dp0voicefix\install_cloud_voicefix.py" --install >> "%STATUS%" 2>&1
if errorlevel 1 (
  echo FAILED: see above ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
echo DONE: start the game, load a save, then Customization, CHARACTER, CLOUD ^(Cross^).>> "%STATUS%"
echo CLOUD should speak in your voice language now, and swinging or talking right after the swap should not crash.>> "%STATUS%"
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
