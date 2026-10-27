@echo off
setlocal
rem Step 2 of the Dissidia NT extraction: Cethleann exports Sephiroth's files (his 9 outfits, motions, weapons, effects,
rem event motions, and the game's shaders and shared textures for his materials), then unbundles them into
rem models (G1M), textures (G1T) and animations. Nothing in the game folder is changed.
cd /d "C:\FF7R2UProj\Tools\Dissidia"
echo Exporting Sephiroth's files with Cethleann (a minute or two)...
"Cethleann\Cethleann.DataExporter.exe" --yshtola --game DissidiaNT "C:\FF7R2UProj\Tools\Dissidia\seph_export" "C:\FF7R2UProj\Tools\Dissidia\seph_game" > "export_log.txt" 2>&1
echo Unbundling the models, textures and animations...
"Cethleann\Cethleann.Unbundler(extracts the models, textures AND anims for dissidia nt).exe" --recursive --deep-recursive "C:\FF7R2UProj\Tools\Dissidia\seph_export" > "unbundle_log.txt" 2>&1
echo.
echo Done. Tell Sandalphon it finished.
pause
