@echo off
title Sephiroth title screen - removing
rem Takes the Sephiroth title screen out of ~mods (close the game first): the three SephirothTitleScreen_P files are
rem moved to Tools\SephirothTitle\removed (from ~mods or the folder in it they are in, like FullyPlayableSephirothPaks),
rem and the title screen is the game's own again (Buster Sword, green motes, Prelude).
rem Status: build\remove_status.txt
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\remove_status.txt"
set "OUT=%~dp0removed"
set "GAME=C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH"
set "MODS=%GAME%\End\Content\Paks\~mods"
set "PAK=SephirothTitleScreen_P"
echo Sephiroth title screen removal started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close %%P first ^(the game^), then run this again>> "%STATUS%"
    goto :done
  )
)
set "FOUND=0"
for /r "%MODS%" %%F in (%PAK%.utoc) do if exist "%%F" call :take "%%~dpF"
if "%FOUND%"=="0" goto :none
echo REMOVED: the files are in Tools\SephirothTitle\removed; the title screen is the game's own again>> "%STATUS%"
goto :done

:take
set /a FOUND+=1
if not exist "%OUT%" mkdir "%OUT%"
if exist "%~1%PAK%.utoc" move /y "%~1%PAK%.utoc" "%OUT%\%PAK%.utoc" >nul
if exist "%~1%PAK%.ucas" move /y "%~1%PAK%.ucas" "%OUT%\%PAK%.ucas" >nul
if exist "%~1%PAK%.pak" move /y "%~1%PAK%.pak" "%OUT%\%PAK%.pak" >nul
if exist "%~1%PAK%.utoc" echo FAILED: %PAK%.utoc could not be moved out of "%~1" ^(is the game still open?^)>> "%STATUS%"
if exist "%~1%PAK%.ucas" echo FAILED: %PAK%.ucas could not be moved out of "%~1" ^(is the game still open?^)>> "%STATUS%"
exit /b 0

:none
echo nothing to remove: SephirothTitleScreen_P is not in ~mods>> "%STATUS%"
goto :done

:done
echo FINISHED %DATE% %TIME%>> "%STATUS%"
type "%STATUS%"
pause
exit /b
