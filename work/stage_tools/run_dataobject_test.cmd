@echo off
title Rebirth data object test - running, please leave this window open
rem Self-test of the CharaSpec / data object tools (close the End editor first). Status: build\dataobject_test_status.txt
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_dataobject_test.ps1"
