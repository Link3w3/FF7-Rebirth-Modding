@echo off
rem Turns the AnimeShader-on-Cloud test mod back on (close the game first).
set "MODS=C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH\End\Content\Paks\~mods"
set "PARK=C:\FF7R2UProj\Tools\_disabled_mods"
for %%F in (pak ucas utoc) do if exist "%PARK%\AnimeShaderCloud_P.%%F" move /Y "%PARK%\AnimeShaderCloud_P.%%F" "%MODS%\" >nul
echo AnimeShader on Cloud is on.
pause
