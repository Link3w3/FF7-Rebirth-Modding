@echo off
title Create a Character System 3.14.5 - building the game mod and installing it, please leave this window open
rem Create a Character System 3.14.5 (close the game first; the editor can stay open):
rem   1. builds the game mod 3.14.5 (main.dll) from Tools\RebirthSkelCompat\src and installs it (build_dll.py --install:
rem      the old main.dll is kept as dlls\main.dll.bak-<time>, the mod's README.txt updated): "disable_kinedriver" takes
rem      a model's KineDriver (its KDIs) off it as it loads, like the BNMs in 3.14.4. The KineDriver writes the hair,
rem      collar and wing bones again after KawaiiPhysics, so the Sephiroth skins still showed none of it.
rem   2. puts the new compat\SephirothKawaii.json in (the KineDriver off on the four Sephiroth skins; the one there is
rem      kept in Tools\RebirthSkelCompat\backup). Only after the mod built.
rem Status: Tools\RebirthSkelCompat\build\install3145_status.txt
rem Leave the window open until it says FINISHED (the build takes a few minutes; Ctrl+C stops it half way).
setlocal
cd /d "%~dp0"
if not exist build mkdir build
set "STATUS=%~dp0build\install3145_status.txt"
set "COMPAT=C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH\End\Binaries\Win64\ue4ss\Mods\RebirthSkelCompat\compat"
set "FILE=SephirothKawaii.json"
set "MD5=bf30755650c2183272809ad87893cd9d"
echo Create a Character System 3.14.5 game mod install, started %DATE% %TIME%> "%STATUS%"
for %%P in (ff7rebirth_.exe ff7rebirth.exe) do (
  tasklist /FI "IMAGENAME eq %%P" 2>nul | find /I "%%P" >nul
  if not errorlevel 1 (
    echo REFUSED: close the game ^(%%P^) first, then run this again>> "%STATUS%"
    goto :done
  )
)
for %%F in (build_dll.py src\RebirthSkelCompat.cpp src\SkelCompatCore.hpp src\KawaiiSolver.hpp mod\README.txt compat_3145\SephirothKawaii.json) do (
  if not exist "%~dp0%%F" (
    echo FAILED: %%F is missing ^(tell Sandalphon^)>> "%STATUS%"
    goto :done
  )
)
findstr /L /C:"= L\"3.14.5\";" "%~dp0src\RebirthSkelCompat.cpp" >nul
if errorlevel 1 (
  echo FAILED: src\RebirthSkelCompat.cpp is not 3.14.5 ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
findstr /L /C:"DisableKineDriverAssets" "%~dp0src\SkelCompatCore.hpp" >nul
if errorlevel 1 (
  echo FAILED: src\SkelCompatCore.hpp is not 3.14.5's ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
findstr /L /C:"Create a Character System 3.14.5" "%~dp0mod\README.txt" >nul
if errorlevel 1 (
  echo FAILED: mod\README.txt is not 3.14.5's ^(tell Sandalphon^)>> "%STATUS%"
  goto :done
)
call :md5 "%~dp0compat_3145\%FILE%" %MD5% || goto :badfile
if not exist "%COMPAT%\" goto :nocompat
call :findpython
echo 1/2 building the game mod 3.14.5 ^(main.dll^) and installing it ^(a few minutes^)...>> "%STATUS%"
type "%STATUS%"
%PY% "%~dp0build_dll.py" --install > "%~dp0build\install3145_dll.log" 2>&1
if errorlevel 1 goto :dllfailed
echo    game mod 3.14.5 installed.>> "%STATUS%"
echo 2/2 the new SephirothKawaii.json ^(the KineDriver off on the four Sephiroth skins^)...>> "%STATUS%"
rem (the compat folder's path has parentheses in it: it is only ever used in quotes, never inside a ( ) block)
if not exist "%COMPAT%\%FILE%" goto :copy
call :same "%COMPAT%\%FILE%" %MD5% && goto :copy
if not exist "%~dp0backup" mkdir "%~dp0backup"
set /a N=1
:nextname
if exist "%~dp0backup\%FILE%.before3145_%N%" (set /a N+=1 & goto :nextname)
copy /y "%COMPAT%\%FILE%" "%~dp0backup\%FILE%.before3145_%N%" >nul
if not exist "%~dp0backup\%FILE%.before3145_%N%" goto :nobackup
echo    the one that was there is kept as Tools\RebirthSkelCompat\backup\%FILE%.before3145_%N%>> "%STATUS%"
:copy
copy /y "%~dp0compat_3145\%FILE%" "%COMPAT%\%FILE%" >nul
call :md5 "%COMPAT%\%FILE%" %MD5% || goto :badcopy
echo    SephirothKawaii.json in place and checked>> "%STATUS%"
echo DONE: start the game and put on a Sephiroth skin. The log should say "RebirthSkelCompat 3.14.5 starting", "Kawaii: PC0010_15: taken off the model as it loaded: its Bonamik PC0010_00_BNM, its KineDriver PC0010_00_KDI, PC0010_00_KDI_Extra1", and on the "Kawaii check" lines "the result still in its buffer" N of N.>> "%STATUS%"
goto :done
:nocompat
echo FAILED: the mod's compat folder was not found; nothing was changed ^(tell Sandalphon^)>> "%STATUS%"
goto :done
:badfile
echo FAILED: Tools\RebirthSkelCompat\compat_3145\%FILE% is not the one made for this; nothing was changed ^(tell Sandalphon^)>> "%STATUS%"
goto :done
:nobackup
echo FAILED: the SephirothKawaii.json there could not be kept in Tools\RebirthSkelCompat\backup; the mod is 3.14.5 but the file was not changed ^(tell Sandalphon^)>> "%STATUS%"
goto :done
:badcopy
echo FAILED: the SephirothKawaii.json in the compat folder did not check out ^(tell Sandalphon^)>> "%STATUS%"
goto :done
:dllfailed
echo FAILED: the game mod did not build ^(build\install3145_dll.log^); nothing was changed: tell Sandalphon>> "%STATUS%"
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

:md5
certutil -hashfile "%~1" MD5 2>nul | findstr /i /c:"%~2" >nul
if not errorlevel 1 exit /b 0
echo    %~nx1 is not the expected file ^(md5 should be %~2^)>> "%STATUS%"
exit /b 1

:same
certutil -hashfile "%~1" MD5 2>nul | findstr /i /c:"%~2" >nul
if not errorlevel 1 exit /b 0
exit /b 1
