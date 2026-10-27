@echo off
rem Puts the AnimeCelPostProcess_P mod back into the game (close the game first).
set "MODS=C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH\End\Content\Paks\~mods"
set "PARK=C:\FF7R2UProj\Tools\_disabled_mods"
for %%F in (pak ucas utoc) do if exist "%PARK%\AnimeCelPostProcess_P.%%F" move /Y "%PARK%\AnimeCelPostProcess_P.%%F" "%MODS%\" >nul
echo AnimeCelPostProcess is back in the game.
pause
