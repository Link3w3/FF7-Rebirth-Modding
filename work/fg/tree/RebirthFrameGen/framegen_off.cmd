@echo off
rem RebirthFrameGen: turns frame generation off by moving version.dll and dlssg_to_fsr3_amd_is_better.dll out of the
rem game folder into End\Binaries\Win64\ue4ss\_mod_backups\framegen_off_DATE_TIME\ (nothing is deleted).
rem build_and_install_framegen.cmd puts them back.
setlocal EnableExtensions DisableDelayedExpansion
set "GAMEDIR=C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH\End\Binaries\Win64"
if defined REBIRTH_WIN64 set "GAMEDIR=%REBIRTH_WIN64%"
set "SYS32=%SystemRoot%\System32"

"%SYS32%\tasklist.exe" /FI "IMAGENAME eq ff7rebirth_.exe" /NH 2>nul | "%SYS32%\find.exe" /I "ff7rebirth_.exe" >nul
if not errorlevel 1 goto :running
"%SYS32%\tasklist.exe" /FI "IMAGENAME eq ff7rebirth.exe" /NH 2>nul | "%SYS32%\find.exe" /I "ff7rebirth.exe" >nul
if not errorlevel 1 goto :running
if not exist "%GAMEDIR%\ff7rebirth_.exe" goto :nogame

set "HERE=%~dp0"
if not exist "%HERE%build\" mkdir "%HERE%build"
set "STAMP="
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss" > "%HERE%build\stamp_off.txt" 2>nul
set /p STAMP=<"%HERE%build\stamp_off.txt"
if not defined STAMP set "STAMP=%RANDOM%%RANDOM%"
set "OFFDIR=%GAMEDIR%\ue4ss\_mod_backups\framegen_off_%STAMP%"
set "MOVED=0"
if not exist "%GAMEDIR%\version.dll" goto :skip_proxy
call :moveout version.dll
if errorlevel 1 goto :movefailed
:skip_proxy
if not exist "%GAMEDIR%\dlssg_to_fsr3_amd_is_better.dll" goto :skip_impl
call :moveout dlssg_to_fsr3_amd_is_better.dll
if errorlevel 1 goto :movefailed
:skip_impl
if "%MOVED%"=="0" echo Frame generation was already off: neither DLL is in the game folder.
if not "%MOVED%"=="0" echo Frame generation is off. The DLLs are in %OFFDIR%
goto :end

:running
echo FINAL FANTASY VII REBIRTH is running. Close the game and run this again. Nothing was changed.
goto :end
:nogame
echo The game was not found at %GAMEDIR% - set REBIRTH_WIN64 to the folder that holds ff7rebirth_.exe.
goto :end
:movefailed
echo Could not move a DLL into %OFFDIR% - try running this as administrator.
goto :end

:end
pause
endlocal
exit /b 0

:moveout
if not exist "%OFFDIR%\" mkdir "%OFFDIR%"
if not exist "%OFFDIR%\" exit /b 1
move "%GAMEDIR%\%~1" "%OFFDIR%\%~1" > nul
if errorlevel 1 exit /b 1
set "MOVED=1"
echo moved %~1
exit /b 0
