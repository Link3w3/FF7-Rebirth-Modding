@echo off
title Put the game's cooked RM_Surface back
rem Undoes run_build_rebuilt_surface.cmd: the rebuilt RM_Surface goes to C:\FF7R2UProj\_mod_backups\RM_Surface_rebuilt_<time>
rem and the game's cooked RM_Surface (from the backup that script made) comes back. Close the End editor first.
setlocal
cd /d "%~dp0"
tasklist /FI "IMAGENAME eq UE4Editor.exe" 2>nul | find /I "UE4Editor.exe" >nul
if not errorlevel 1 (
  echo Close the End editor first, then run this again.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop'; $mat='C:\FF7R2UProj\Content\Renderer\Material';" ^
  "$from=(Get-Content -Raw '%~dp0build\cooked_backup.txt').Trim();" ^
  "if (-not (Test-Path (Join-Path $from 'RM_Surface.uexp'))) { throw ('no cooked RM_Surface in ' + $from) }" ^
  "if (Test-Path (Join-Path $mat 'RM_Surface.uexp')) { throw 'RM_Surface is already the cooked one' }" ^
  "$keep='C:\FF7R2UProj\_mod_backups\RM_Surface_rebuilt_' + (Get-Date -Format 'yyyyMMdd_HHmmss'); New-Item -ItemType Directory -Force $keep | Out-Null;" ^
  "if (Test-Path (Join-Path $mat 'RM_Surface.uasset')) { Move-Item (Join-Path $mat 'RM_Surface.uasset') $keep };" ^
  "Move-Item (Join-Path $from 'RM_Surface.uasset') $mat; Move-Item (Join-Path $from 'RM_Surface.uexp') $mat;" ^
  "Write-Host ('The cooked RM_Surface is back; the rebuilt one is in ' + $keep)"
pause
