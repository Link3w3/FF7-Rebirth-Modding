@echo off
title Remake Importer - building ooz.dll
rem Builds ooz.dll, the Oodle (Kraken) decompressor FINAL FANTASY VII REMAKE's paks need (Remake ships no Oodle DLL),
rem from the ooz source in ooz\ with Visual Studio 2022's C++ compiler (x64). Run it once: the Remake Importer
rem (Rebirth FX > Import FF7 Remake Character...) loads ooz.dll from this folder. Takes about a minute.
rem   build_ooz.cmd            build, check, wait for a key
rem   build_ooz.cmd nopause    the same, no waiting (what the importer's "Build ooz.dll" button runs)
rem Log: ooz\build\build.log
setlocal
cd /d "%~dp0"
set "VCVARS="
set "VSDIR="
if not exist "ooz\build" mkdir "ooz\build"
set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
if not exist "%VSWHERE%" goto :novswhere
"%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath > "ooz\build\vswhere.txt" 2>nul
set /p VSDIR=<"ooz\build\vswhere.txt"
if defined VSDIR if exist "%VSDIR%\VC\Auxiliary\Build\vcvars64.bat" set "VCVARS=%VSDIR%\VC\Auxiliary\Build\vcvars64.bat"
:novswhere
if not defined VCVARS for %%e in (Community Professional Enterprise BuildTools) do (
  if exist "%ProgramFiles%\Microsoft Visual Studio\2022\%%e\VC\Auxiliary\Build\vcvars64.bat" set "VCVARS=%ProgramFiles%\Microsoft Visual Studio\2022\%%e\VC\Auxiliary\Build\vcvars64.bat"
)
if not defined VCVARS (
  echo No Visual Studio C++ compiler was found ^(vcvars64.bat^).
  echo Install "Desktop development with C++" in the Visual Studio Installer, then run this again.
  goto :fail
)
echo Compiler: %VCVARS%
call "%VCVARS%" >nul
where cl >nul 2>nul
if errorlevel 1 (
  echo vcvars64.bat did not set up cl.exe.
  goto :fail
)
if not exist "ooz\build" mkdir "ooz\build"
echo Building ooz.dll ...
cl /nologo /O2 /MT /EHsc /LD /W0 /DNDEBUG /DOOZ_DYNAMIC /DOOZ_BUILD_DLL /I.\ooz /Fo.\ooz\build\ /Fe.\ooz\build\ooz.dll .\ooz\kraken.cpp .\ooz\lzna.cpp .\ooz\bitknit.cpp /link /NOLOGO > "ooz\build\build.log" 2>&1
if errorlevel 1 (
  type "ooz\build\build.log"
  echo.
  echo The build FAILED ^(ooz\build\build.log^).
  goto :fail
)
copy /y "ooz\build\ooz.dll" "ooz.dll" >nul
if errorlevel 1 (
  echo ooz.dll was built in ooz\build but could not be copied here ^(is the importer open? close it and run this again^).
  goto :fail
)
echo ooz.dll is built: %~dp0ooz.dll
call :findpython
if defined PY (
  echo Checking it with %PY% ...
  %PY% "%~dp0remake_importer.py" --check
)
echo.
echo Done.
if /i not "%~1"=="nopause" pause
exit /b 0

:fail
if /i not "%~1"=="nopause" pause
exit /b 1

:findpython
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
exit /b
