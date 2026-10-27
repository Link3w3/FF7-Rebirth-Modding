@echo off
rem Takes the anime cel-shading post-process off the running game.
set "LINK=C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH\End\Binaries\Win64\ue4ss\Mods\RebirthLiveLink\link"
powershell -NoProfile -Command "$s=[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds(); Set-Content -Path ($env:LINK + '\command.lua.tmp') -Value ('return { seq = ' + $s + ', op = \"pp_clear\" }') -Encoding ASCII; Move-Item -Force ($env:LINK + '\command.lua.tmp') ($env:LINK + '\command.lua')"
echo Sent.
timeout /t 3 >nul
type "%LINK%\status.json"
echo.
pause
