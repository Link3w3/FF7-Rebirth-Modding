@echo off
setlocal
rem Step 1 of the Dissidia NT extraction: Cethleann reads the game's file table (no game files are changed).
cd /d "C:\FF7R2UProj\Tools\Dissidia"
set "GAME=C:\Program Files (x86)\Steam\steamapps\common\DISSIDIA FINAL FANTASY NT Free Edition"
echo Reading Dissidia NT's file table with Cethleann...
"Cethleann\Cethleann.DataExporter.exe" --yshtola --game DissidiaNT --yshtola-manifest-only "C:\FF7R2UProj\Tools\Dissidia\manifest" "%GAME%" > "tables_log.txt" 2>&1
type "tables_log.txt"
echo.
echo Done. Tell Sandalphon it finished.
pause
