@echo off
set "LINK=C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH\End\Binaries\Win64\ue4ss\Mods\RebirthLiveLink\link"
powershell -NoProfile -Command "$s=[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds(); Set-Content -Path ($env:LINK + '\command.lua.tmp') -Value ('return { seq = ' + $s + ', op = \"stop\" }') -Encoding ASCII; Move-Item -Force ($env:LINK + '\command.lua.tmp') ($env:LINK + '\command.lua')"
echo Stopped.
timeout /t 2 >nul
