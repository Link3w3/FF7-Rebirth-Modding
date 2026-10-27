@echo off
rem Test 2: the same, with a new shader: the lines and sparks glow pulsing magenta (the big slash itself stays as it is).
rem Plays it in front of your character in the running game (needs RebirthLiveLink, and RebirthCustomTest_P in ~mods).
set "LINK=C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH\End\Binaries\Win64\ue4ss\Mods\RebirthLiveLink\link"
powershell -NoProfile -Command "$s=[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds(); Set-Content -Path ($env:LINK + '\command.lua.tmp') -Value ('return { seq = ' + $s + ', op = \"spawn\", path = \"/Game/RebirthCustom/FX_RebirthCustom_Test/FX_RebirthCustom_Test\", loop = true, every = 3.0, forward = 300.0, up = 80.0 }') -Encoding ASCII; Move-Item -Force ($env:LINK + '\command.lua.tmp') ($env:LINK + '\command.lua')"
echo Sent. The game loads the effect the first time, so it shows on the next replay (a few seconds).
timeout /t 5 >nul
type "%LINK%\status.json"
echo.
pause
