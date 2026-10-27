@echo off
rem Builds the Create a Character System editor plugin 1.13.1 (Flatten Root) and opens the End editor when it is built.
rem Keep this window open: if the build needs a fix, Sandalphon fixes the code and it builds again by itself.
setlocal
title Create a Character System 1.13.1 build
cd /d "C:\FF7R2UProj\Saved\ModExtract\buildagent"
tasklist /FI "IMAGENAME eq UE4Editor.exe" /NH | find /I "UE4Editor.exe" >nul && (
  echo The End editor is still open: close it, then run this again.
  pause
  exit /b 1
)
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python399\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python399\python.exe"
if not defined PY set "PY=python"
echo Building the Create a Character System editor plugin (a few minutes)...
echo The End editor opens by itself when it is built. Leave this window open until then.
%PY% "C:\FF7R2UProj\Saved\ModExtract\buildagent\agent.py" > "C:\FF7R2UProj\Saved\ModExtract\buildagent\agent_stdout.log" 2>&1
echo.
type "C:\FF7R2UProj\Saved\ModExtract\buildagent\status.json" 2>nul | find "state"
echo Done. You can close this window.
pause
