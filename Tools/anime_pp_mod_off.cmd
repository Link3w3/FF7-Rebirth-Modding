@echo off
rem Takes the AnimeCelPostProcess_P mod out of the game (close the game first): moves its three files out of the
rem Paks folder into C:\FF7R2UProj\Tools\_disabled_mods (the game loads every pak under Paks, subfolders too).
set "MODS=C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH\End\Content\Paks\~mods"
set "PARK=C:\FF7R2UProj\Tools\_disabled_mods"
if not exist "%PARK%" mkdir "%PARK%"
for %%F in (pak ucas utoc) do if exist "%MODS%\AnimeCelPostProcess_P.%%F" move /Y "%MODS%\AnimeCelPostProcess_P.%%F" "%PARK%\" >nul
echo AnimeCelPostProcess is out of the game (its files are in %PARK%).
pause
