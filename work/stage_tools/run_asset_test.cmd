@echo off
title Rebirth data asset test - running, please leave this window open
rem Self-test of data asset and blueprint editing (close the End editor first). Status: build\asset_test_status.txt
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_asset_test.ps1"
