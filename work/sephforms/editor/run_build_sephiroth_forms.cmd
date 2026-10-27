@echo off
title Sephiroth forms move build - running, please leave this window open
rem Builds your playable Sephiroth's winged and flying moves with RebirthSkelCompat (close the End editor first).
rem Status: build\status.txt
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_build_sephiroth_forms.ps1"
type "%~dp0build\status.txt"
pause
