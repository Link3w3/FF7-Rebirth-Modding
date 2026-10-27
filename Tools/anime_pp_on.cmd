@echo off
rem Puts the anime cel-shading post-process on the running game (needs RebirthLiveLink 1.4 and AnimeCelPostProcess_P in ~mods).
rem It stays on through level changes until anime_pp_off.cmd or the game closes.
set "LINK=C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH\End\Binaries\Win64\ue4ss\Mods\RebirthLiveLink\link"
powershell -NoProfile -Command "$s=[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds(); Set-Content -Path ($env:LINK + '\command.lua.tmp') -Value ('return { seq = ' + $s + ', op = \"pp_apply\", persist = false, materials = { { path = \"/Engine/EngineMaterials/DefaultPostProcessMaterial\", weight = 1.0 } } }') -Encoding ASCII; Move-Item -Force ($env:LINK + '\command.lua.tmp') ($env:LINK + '\command.lua')"
echo Sent.
timeout /t 3 >nul
type "%LINK%\status.json"
echo.
pause
