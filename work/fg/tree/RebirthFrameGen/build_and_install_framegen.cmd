@echo off
rem RebirthFrameGen: builds dlssg-to-fsr3 v0.130 (D3D12 only, from source) and installs it into FINAL FANTASY VII REBIRTH.
rem   1. checks that the game is closed, finds Visual Studio 2022 (vswhere) and CMake; installs nothing
rem   2. builds the FidelityFX SDK libraries (DX12 backend, frame interpolation, optical flow) - first run only
rem   3. builds version.dll and dlssg_to_fsr3_amd_is_better.dll (Release, x64, static CRT)
rem   4. moves any existing version.dll / dlssg_to_fsr3_amd_is_better.dll in End\Binaries\Win64 into
rem      End\Binaries\Win64\ue4ss\_mod_backups\framegen_DATE_TIME\ and copies the new ones in
rem Result: build\framegen_status.txt, step logs: build\logs\.   Options: rebuild-sdk (build the FidelityFX SDK again)
setlocal EnableExtensions DisableDelayedExpansion

set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
set "BUILD=%ROOT%\build"
set "LOGS=%BUILD%\logs"
set "STATUS=%BUILD%\framegen_status.txt"
set "FFXSDK=%ROOT%\ffx\sdk"
set "FFXLIB=%FFXSDK%\bin\ffx_sdk"
set "GAMEDIR=C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH\End\Binaries\Win64"
if defined REBIRTH_WIN64 set "GAMEDIR=%REBIRTH_WIN64%"
set "FAILMSG="
set "FAILLOG="
set "SYS32=%SystemRoot%\System32"
set "PWSH=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"

if not exist "%BUILD%\" mkdir "%BUILD%"
if not exist "%LOGS%\" mkdir "%LOGS%"
> "%STATUS%" echo RebirthFrameGen build and install - %DATE% %TIME%
call :log "folder: %ROOT%"

rem ---------------------------------------------------------------------------------------------------------------
rem the game must be closed (its DLLs are replaced)
rem ---------------------------------------------------------------------------------------------------------------
"%SYS32%\tasklist.exe" /FI "IMAGENAME eq ff7rebirth_.exe" /NH 2>nul | "%SYS32%\find.exe" /I "ff7rebirth_.exe" >nul
if not errorlevel 1 goto :game_running
"%SYS32%\tasklist.exe" /FI "IMAGENAME eq ff7rebirth.exe" /NH 2>nul | "%SYS32%\find.exe" /I "ff7rebirth.exe" >nul
if not errorlevel 1 goto :game_running
call :log "[ok] the game is not running"

if not exist "%GAMEDIR%\ff7rebirth_.exe" goto :no_game
call :log "[ok] game folder: %GAMEDIR%"

rem a time stamp for the backup folder
set "STAMP="
"%PWSH%" -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss" > "%BUILD%\stamp.txt" 2>nul
set /p STAMP=<"%BUILD%\stamp.txt"
if not defined STAMP set "STAMP=%RANDOM%%RANDOM%"

rem ---------------------------------------------------------------------------------------------------------------
rem Visual Studio (C++ x64 tools) and CMake
rem ---------------------------------------------------------------------------------------------------------------
set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
if not exist "%VSWHERE%" goto :no_vswhere
set "VSPATH="
set "VSVER="
"%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath > "%BUILD%\vs_path.txt" 2>nul
"%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationVersion > "%BUILD%\vs_version.txt" 2>nul
set /p VSPATH=<"%BUILD%\vs_path.txt"
set /p VSVER=<"%BUILD%\vs_version.txt"
if not defined VSPATH goto :no_vs
if not exist "%VSPATH%\Common7\Tools\VsDevCmd.bat" goto :no_vs
set "VSMAJOR="
for /f "tokens=1 delims=." %%a in ("%VSVER%") do set "VSMAJOR=%%a"
set "GEN="
if "%VSMAJOR%"=="17" set "GEN=Visual Studio 17 2022"
if "%VSMAJOR%"=="18" set "GEN=Visual Studio 18 2026"
if not defined GEN goto :old_vs
call :log "[ok] Visual Studio %VSVER%: %VSPATH%"

call "%VSPATH%\Common7\Tools\VsDevCmd.bat" -arch=amd64 -host_arch=amd64 -no_logo > "%LOGS%\0_vsdevcmd.log" 2>&1
"%SYS32%\where.exe" cl.exe > nul 2>&1
if errorlevel 1 goto :no_cl
call :log "[ok] the x64 C++ compiler is set up (log: build\logs\0_vsdevcmd.log)"

"%SYS32%\where.exe" cmake.exe > nul 2>&1
if not errorlevel 1 goto :have_cmake
if not exist "%ProgramFiles%\CMake\bin\cmake.exe" goto :no_cmake
set "PATH=%ProgramFiles%\CMake\bin;%PATH%"
:have_cmake
set "CMAKELINE="
cmake --version > "%BUILD%\cmake_version.txt" 2>&1
set /p CMAKELINE=<"%BUILD%\cmake_version.txt"
set "CMAKEVER="
for /f "tokens=3" %%v in ("%CMAKELINE%") do set "CMAKEVER=%%v"
if not defined CMAKEVER goto :no_cmake
set "CMV_MAJ=0"
set "CMV_MIN=0"
for /f "tokens=1,2 delims=.-" %%a in ("%CMAKEVER%") do set "CMV_MAJ=%%a" & set "CMV_MIN=%%b"
if %CMV_MAJ% LSS 3 goto :old_cmake
if %CMV_MAJ% EQU 3 if %CMV_MIN% LSS 23 goto :old_cmake
call :log "[ok] CMake %CMAKEVER%, generator: %GEN%"

rem ---------------------------------------------------------------------------------------------------------------
rem FidelityFX SDK (DX12 backend, frame interpolation, optical flow). The same configure options and build switches
rem as the SDK's BuildFidelityFXSDK.bat, Release only, in build\ffx_sdk_vsNN; the libraries land in ffx\sdk\bin\ffx_sdk.
rem ---------------------------------------------------------------------------------------------------------------
set "SDKBUILD=%BUILD%\ffx_sdk_vs%VSMAJOR%"
set "SDKMARK=%BUILD%\ffx_sdk_built_vs%VSMAJOR%.txt"
if /i "%~1"=="rebuild-sdk" goto :sdk_build
if not exist "%SDKMARK%" goto :sdk_build
if not exist "%FFXLIB%\ffx_backend_dx12_x64.lib" goto :sdk_build
if not exist "%FFXLIB%\ffx_frameinterpolation_x64.lib" goto :sdk_build
if not exist "%FFXLIB%\ffx_opticalflow_x64.lib" goto :sdk_build
call :log "[ok] FidelityFX SDK libraries already built (run with rebuild-sdk to build them again)"
goto :sdk_done
:sdk_build
call :log "[..] building the FidelityFX SDK (shader compilation included; the first time takes several minutes)"
set "FAILLOG=%LOGS%\1_ffx_sdk_configure.log"
cmake -S "%FFXSDK%" -B "%SDKBUILD%" -G "%GEN%" -A x64 -DFFX_API_BACKEND=DX12_X64 -DFFX_FI=ON -DFFX_OF=ON -DFFX_AUTO_COMPILE_SHADERS=1 > "%FAILLOG%" 2>&1
if errorlevel 1 goto :sdk_failed
set "FAILLOG=%LOGS%\2_ffx_sdk_build.log"
rem the SDK's DX12 backend compiles with /W4 /WX: a warning that a newer compiler adds must not stop the build
set "_CL_=/WX-"
cmake --build "%SDKBUILD%" --config Release --parallel 4 -- /p:CL_MPcount=16 /p:VcpkgEnabled=false > "%FAILLOG%" 2>&1
set "SDKBUILDERR=%ERRORLEVEL%"
set "_CL_="
if not "%SDKBUILDERR%"=="0" goto :sdk_failed
if not exist "%FFXLIB%\ffx_backend_dx12_x64.lib" goto :sdk_failed
if not exist "%FFXLIB%\ffx_frameinterpolation_x64.lib" goto :sdk_failed
if not exist "%FFXLIB%\ffx_opticalflow_x64.lib" goto :sdk_failed
> "%SDKMARK%" echo FidelityFX SDK built with %GEN% on %DATE% %TIME%
call :log "[ok] FidelityFX SDK libraries built (logs: build\logs\1_ffx_sdk_configure.log, 2_ffx_sdk_build.log)"
:sdk_done

rem ---------------------------------------------------------------------------------------------------------------
rem dlssg-to-fsr3: version.dll and dlssg_to_fsr3_amd_is_better.dll
rem ---------------------------------------------------------------------------------------------------------------
set "DLSSGBUILD=%BUILD%\dlssg_vs%VSMAJOR%"
set "OUT=%DLSSGBUILD%\Release"
call :log "[..] building dlssg-to-fsr3"
set "FAILLOG=%LOGS%\3_dlssg_configure.log"
cmake -S "%ROOT%\dlssg" -B "%DLSSGBUILD%" -G "%GEN%" -A x64 > "%FAILLOG%" 2>&1
if errorlevel 1 goto :dlssg_failed
set "FAILLOG=%LOGS%\4_dlssg_build.log"
cmake --build "%DLSSGBUILD%" --config Release --parallel -- /p:VcpkgEnabled=false > "%FAILLOG%" 2>&1
if errorlevel 1 goto :dlssg_failed
if not exist "%OUT%\version.dll" goto :dlssg_failed
if not exist "%OUT%\dlssg_to_fsr3_amd_is_better.dll" goto :dlssg_failed
call :log "[ok] built %OUT%\version.dll and dlssg_to_fsr3_amd_is_better.dll (logs: build\logs\3_dlssg_configure.log, 4_dlssg_build.log)"
set "FAILLOG="

rem ---------------------------------------------------------------------------------------------------------------
rem install: back up what is there under the same names, then copy
rem ---------------------------------------------------------------------------------------------------------------
"%SYS32%\tasklist.exe" /FI "IMAGENAME eq ff7rebirth_.exe" /NH 2>nul | "%SYS32%\find.exe" /I "ff7rebirth_.exe" >nul
if not errorlevel 1 goto :game_running

set "BACKUP=%GAMEDIR%\ue4ss\_mod_backups\framegen_%STAMP%"
set "MOVED=0"
if not exist "%GAMEDIR%\version.dll" goto :backup_impl
"%SYS32%\fc.exe" /b "%OUT%\version.dll" "%GAMEDIR%\version.dll" > nul 2>&1
if errorlevel 1 call :log "[warn] there already is a version.dll in the game folder that is not this build. It is moved to the backup folder below. If it belonged to another mod, that mod is off until you put it back."
call :backup version.dll
if errorlevel 1 goto :backup_failed
:backup_impl
if not exist "%GAMEDIR%\dlssg_to_fsr3_amd_is_better.dll" goto :backup_done
call :backup dlssg_to_fsr3_amd_is_better.dll
if errorlevel 1 goto :backup_failed
:backup_done
if "%MOVED%"=="0" call :log "[ok] no version.dll or dlssg_to_fsr3_amd_is_better.dll in the game folder before: nothing to back up"

copy /Y "%OUT%\version.dll" "%GAMEDIR%\version.dll" > nul
if errorlevel 1 goto :copy_failed
copy /Y "%OUT%\dlssg_to_fsr3_amd_is_better.dll" "%GAMEDIR%\dlssg_to_fsr3_amd_is_better.dll" > nul
if errorlevel 1 goto :copy_failed
"%SYS32%\fc.exe" /b "%OUT%\version.dll" "%GAMEDIR%\version.dll" > nul 2>&1
if errorlevel 1 goto :copy_failed
"%SYS32%\fc.exe" /b "%OUT%\dlssg_to_fsr3_amd_is_better.dll" "%GAMEDIR%\dlssg_to_fsr3_amd_is_better.dll" > nul 2>&1
if errorlevel 1 goto :copy_failed
call :log "[ok] installed version.dll and dlssg_to_fsr3_amd_is_better.dll into the game folder"

if exist "%GAMEDIR%\dlssg_to_fsr3.ini" goto :ini_kept
copy /Y "%ROOT%\dlssg\resources\dlssg_to_fsr3.ini" "%GAMEDIR%\dlssg_to_fsr3.ini" > nul
if errorlevel 1 goto :copy_failed
call :log "[ok] copied dlssg_to_fsr3.ini (all debug options off)"
goto :ini_done
:ini_kept
call :log "[ok] kept the dlssg_to_fsr3.ini that was already there"
:ini_done

rem other frame-generation wrappers would load a second copy
for %%f in (winhttp.dll dbghelp.dll nvngx.dll dlssg_to_fsr3.asi dlssg_to_fsr3.dll) do if exist "%GAMEDIR%\%%f" call :log "[warn] %%f is in the game folder: if it is another dlssg-to-fsr3 copy, move it out"

rem ---------------------------------------------------------------------------------------------------------------
rem information only (read, never changed)
rem ---------------------------------------------------------------------------------------------------------------
set "SLDIR=%GAMEDIR%\..\..\..\Engine\Plugins\StreamlineSubset\Binaries\ThirdParty\Win64"
set "SLMSG=[warn] Engine\Plugins\StreamlineSubset\Binaries\ThirdParty\Win64\sl.dlss_g.dll not found: the DLSS Frame Generation option may not exist in this game version"
if exist "%SLDIR%\sl.dlss_g.dll" set "SLMSG=[ok] the game's Streamline frame-generation plugin is present"
call :log "%SLMSG%"
set "HAGS="
"%SYS32%\reg.exe" query "HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers" /v HwSchMode > "%BUILD%\hags.txt" 2>&1
"%SYS32%\find.exe" /I "0x2" "%BUILD%\hags.txt" > nul && set "HAGS=on"
if not defined HAGS "%SYS32%\find.exe" /I "0x1" "%BUILD%\hags.txt" > nul && set "HAGS=off"
if "%HAGS%"=="on" call :log "[ok] Hardware-accelerated GPU scheduling is on"
if "%HAGS%"=="off" call :log "[todo] Hardware-accelerated GPU scheduling is OFF: Settings, System, Display, Graphics, Hardware-accelerated GPU scheduling ON, then restart Windows"
if not defined HAGS call :log "[todo] could not read the Hardware-accelerated GPU scheduling setting: check Settings, System, Display, Graphics (it must be ON, then restart Windows)"

call :log ""
call :log "RESULT: SUCCESS"
call :log "In the game: DLSS on (Balanced or Performance), DLSS Frame Generation on, NVIDIA Reflex on, VSync off."
call :log "After the first start with frame generation, dlssg_to_fsr3.log appears next to ff7rebirth_.exe."
call :log "To turn it off: framegen_off.cmd, or move version.dll and dlssg_to_fsr3_amd_is_better.dll out of the game folder."
if not "%MOVED%"=="0" call :log "Backup of the replaced files: %BACKUP%"
goto :end

rem ---------------------------------------------------------------------------------------------------------------
rem failures
rem ---------------------------------------------------------------------------------------------------------------
:game_running
set "FAILMSG=FINAL FANTASY VII REBIRTH is running. Close the game and run this again. Nothing was changed."
goto :failed
:no_game
set "FAILMSG=The game was not found at %GAMEDIR% - set REBIRTH_WIN64 to the folder that holds ff7rebirth_.exe and run this again. Nothing was changed."
goto :failed
:no_vswhere
set "FAILMSG=Visual Studio Installer not found (no vswhere.exe). Install Visual Studio 2022 with Desktop development with C++. Nothing was installed or changed."
goto :failed
:no_vs
set "FAILMSG=No Visual Studio with the x64 C++ tools was found. In Visual Studio Installer: Modify, Desktop development with C++. Nothing was installed or changed."
goto :failed
:old_vs
set "FAILMSG=Visual Studio %VSVER% is too old: this build needs Visual Studio 2022 or newer. Nothing was installed or changed."
goto :failed
:no_cl
set "FAILLOG=%LOGS%\0_vsdevcmd.log"
set "FAILMSG=The Visual Studio developer environment did not set up the x64 compiler (cl.exe). See the log. Nothing was installed or changed."
goto :failed
:no_cmake
set "FAILMSG=CMake not found. In Visual Studio Installer: Modify, Individual components, C++ CMake tools for Windows (or install CMake from cmake.org). Nothing was installed or changed."
goto :failed
:old_cmake
set "FAILMSG=CMake %CMAKEVER% is too old (3.23 or newer is needed). Update Visual Studio 2022 or install a newer CMake. Nothing was installed or changed."
goto :failed
:sdk_failed
set "FAILMSG=The FidelityFX SDK build failed. See the log. Nothing in the game folder was changed."
goto :failed
:dlssg_failed
set "FAILMSG=The dlssg-to-fsr3 build failed. See the log. Nothing in the game folder was changed."
goto :failed
:backup_failed
set "FAILMSG=Could not move the existing file into %BACKUP% - nothing was replaced. Is the folder writable (try running this as administrator)?"
goto :failed
:copy_failed
set "FAILMSG=Copying into the game folder failed (try running this as administrator). Backups, if any, are in %BACKUP%"
goto :failed

:failed
call :log ""
call :log "RESULT: FAILED"
call :log "%FAILMSG%"
if not defined FAILLOG goto :end
call :log "log: %FAILLOG% - its last lines:"
"%PWSH%" -NoProfile -Command "Get-Content -LiteralPath $env:FAILLOG -Tail 30" >> "%STATUS%" 2>nul
"%PWSH%" -NoProfile -Command "Get-Content -LiteralPath $env:FAILLOG -Tail 30" 2>nul

:end
echo.
echo Status written to %STATUS%
pause
endlocal
exit /b 0

rem ---------------------------------------------------------------------------------------------------------------
rem helpers
rem ---------------------------------------------------------------------------------------------------------------
:log
>> "%STATUS%" echo(%~1
echo(%~1
exit /b 0

:backup
if not exist "%BACKUP%\" mkdir "%BACKUP%"
if not exist "%BACKUP%\" exit /b 1
move "%GAMEDIR%\%~1" "%BACKUP%\%~1" > nul
if errorlevel 1 exit /b 1
set "MOVED=1"
call :log "[ok] moved the existing %~1 to %BACKUP%"
exit /b 0
