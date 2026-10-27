@echo off
title Remake Importer
rem The Remake Importer without the editor: its window (or, without tkinter, the same questions here) makes a
rem character's job; then, in the End editor (Output Log, Cmd), the line it prints imports it.
rem The editor's Rebirth FX > Import FF7 Remake Character... does both at once.
rem   run_remake_importer.cmd             the window
rem   run_remake_importer.cmd --console   in this console
rem   run_remake_importer.cmd --check     what your Python has for it (numpy, AES, ooz.dll)
setlocal
cd /d "%~dp0"
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY (
  echo Python 3 was not found: install it from python.org ^(with the py launcher^), then run this again.
  pause
  exit /b 1
)
%PY% "%~dp0remake_importer.py" %*
if errorlevel 1 pause
