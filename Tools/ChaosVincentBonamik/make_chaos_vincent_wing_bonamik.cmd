@echo off
rem Builds Chaos Vincent's wing Bonamik (PC0011_10_BNM) and adds it to the PC0011_10 mesh, with the End editor closed.
rem With the editor open, use File > Execute Python Script... > make_chaos_vincent_wing_bonamik.py instead.
rem Result: C:\FF7R2UProj\Saved\ChaosVincentBonamik\report.json   Log: make_chaos_vincent_wing_bonamik.log (next to this file)
setlocal
tasklist /FI "IMAGENAME eq UE4Editor.exe" 2>nul | find /I "UE4Editor.exe" >nul
if not errorlevel 1 (
  echo The End editor is open. Close it first, or run the .py from File ^> Execute Python Script... in the editor.
  pause
  exit /b 2
)
set "UE=C:\RebirthEngine\RebirthEngineV5\Windows\Engine\Binaries\Win64\UE4Editor-Cmd.exe"
echo Building PC0011_10_BNM, this takes a minute or two...
"%UE%" "C:\FF7R2UProj\End.uproject" -run=pythonscript -script="%~dp0make_chaos_vincent_wing_bonamik.py" -unattended -nopause -nosplash -nosound -abslog="%~dp0make_chaos_vincent_wing_bonamik.log"
echo.
findstr /C:"ChaosWingBonamik:" "%~dp0make_chaos_vincent_wing_bonamik.log"
echo.
echo Report: C:\FF7R2UProj\Saved\ChaosVincentBonamik\report.json
pause
