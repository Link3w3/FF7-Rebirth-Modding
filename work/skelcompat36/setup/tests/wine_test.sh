#!/bin/bash
# Runs Setup.exe under wine against a fake game / Steam library / engine / End project and checks what it does.
#   tests/wine_test.sh <Setup.exe> <stage dir with game/ and plugin/>
set -u
SETUP=$(readlink -f "$1")
STAGE=$(readlink -f "$2")
export WINEPREFIX=${WINEPREFIX:-/tmp/wpfx} WINEDEBUG=-all
W=/usr/lib/wine/wine64
T=/tmp/t
FAILS=0
ok() { echo "  ok   $*"; }
bad() { echo "  FAIL $*"; FAILS=$((FAILS + 1)); }
check() { if eval "$1"; then ok "$2"; else bad "$2"; fi; }

GAME="$T/SteamLib/steamapps/common/FINAL FANTASY VII REBIRTH"
WIN64="$GAME/End/Binaries/Win64"
MOD="$WIN64/ue4ss/Mods/RebirthSkelCompat"
PROJ="$T/Proj"
PLUG="$PROJ/Plugins/RebirthSkelCompat"
PBACK="$PROJ/CreateACharacterSystem-Backups"
TEMPLOG() { cat "$WINEPREFIX"/drive_c/users/*/Temp/CreateACharacterSystem-Setup.log 2>/dev/null | tr -d '\r'; }

setup_env() {
  rm -rf "$T"
  mkdir -p "$WIN64/ue4ss/Mods" "$T/Steam/steamapps" "$T/Engine/Engine/Binaries/Win64" "$T/Engine/Engine/Plugins/Runtime" "$PROJ"
  printf 'MZ fake game' > "$WIN64/ff7rebirth_.exe"
  python3 -c "open('$WIN64/ue4ss/UE4SS.dll','wb').write(b'MZ'+b'\0'*3000000+b'UE4SS - v3.0.1 Beta #0 - Git SHA #c0a8d4c'+b'\0'*100)"
  printf 'BPModLoaderMod : 1\n' > "$WIN64/ue4ss/Mods/mods.txt"
  printf '"libraryfolders"\n{\n\t"0"\n\t{\n\t\t"path"\t\t"Z:\\\\tmp\\\\t\\\\Steam"\n\t}\n\t"1"\n\t{\n\t\t"path"\t\t"Z:\\\\tmp\\\\t\\\\SteamLib"\n\t}\n}\n' > "$T/Steam/steamapps/libraryfolders.vdf"
  printf '"AppState"\n{\n\t"appid"\t\t"2909400"\n\t"installdir"\t\t"FINAL FANTASY VII REBIRTH"\n}\n' > "$T/SteamLib/steamapps/appmanifest_2909400.acf"
  printf '{\n\t"BuildId": "17c11882-043f-4330-9e21-2efa519533c5",\n\t"Modules":\n\t{\n\t}\n}\n' > "$T/Engine/Engine/Binaries/Win64/UE4Editor.modules"
  printf '{\n\t"FileVersion": 3,\n\t"EngineAssociation": "{B27A4B37-4B47-29AB-F685-658A01DA370E}",\n\t"Modules": [ { "Name": "EndGame", "Type": "Runtime" } ]\n}\n' > "$PROJ/End.uproject"
  $W reg add 'HKCU\Software\Valve\Steam' /v SteamPath /t REG_SZ /d 'z:/tmp/t/steam' /f >/dev/null 2>&1
  $W reg add 'HKCU\SOFTWARE\Epic Games\Unreal Engine\Builds' /v '{B27A4B37-4B47-29AB-F685-658A01DA370E}' /t REG_SZ /d 'Z:/tmp/t/Engine' /f >/dev/null 2>&1
  cp "$SETUP" "$T/Setup.exe"
  rm -f "$WINEPREFIX"/drive_c/users/*/Temp/CreateACharacterSystem-Setup.log
}

run() { (cd "$T" && timeout 180 $W Setup.exe "$@"); }
P='/project:Z:\tmp\t\Proj\End.uproject'

same_tree() { # <installed dir> <stage dir>: every staged file is installed byte for byte
  local missing=0
  while IFS= read -r -d '' f; do
    rel=${f#$2/}
    cmp -s "$f" "$1/$rel" || { echo "    differs: $rel"; missing=1; }
  done < <(find "$2" -type f -print0)
  return $missing
}

echo "== 1. fresh install: game found through Steam, project given"
setup_env
run /S "$P"; rc=$?
check "[ $rc -eq 0 ]" "exit code 0 (got $rc)"
check "same_tree '$MOD' '$STAGE/game'" "game files installed byte for byte"
check "same_tree '$PLUG' '$STAGE/plugin'" "plugin files installed byte for byte"
check "[ -f '$PLUG/README.txt' ] && [ -f '$PLUG/CreateACharacterSystem.install.txt' ] && [ -f '$MOD/CreateACharacterSystem.install.txt' ]" "README and install records"
check "TEMPLOG | grep -q 'Engine build matches'" "engine build found through the registry"
check "TEMPLOG | grep -q 'UE4SS 3.0.1 (c0a8d4c) found'" "UE4SS build recognised"
check "[ ! -e '$MOD/Backups' ] && [ ! -e '$PBACK' ]" "nothing backed up on a fresh install"
check "[ \"\$(cat '$WIN64/ue4ss/Mods/mods.txt')\" = 'BPModLoaderMod : 1' ]" "mods.txt untouched"

echo "== 2. run again: nothing changes, log not duplicated"
run /S "$P"; rc=$?
check "[ $rc -eq 0 ]" "exit code 0"
check "grep -q '0 installed, 3 already up to date, 1 kept' '$MOD/CreateACharacterSystem-Setup.log'" "game part reported up to date"
check "grep -q '0 installed, 13 already up to date' '$MOD/CreateACharacterSystem-Setup.log'" "plugin part reported up to date"
check "[ ! -e '$MOD/Backups' ] && [ ! -e '$PBACK' ]" "no backups when nothing changed"
check "[ \$(grep -c 'Installing Create a Character System' '$MOD/CreateACharacterSystem-Setup.log') -eq 2 ]" "one log block per run"

echo "== 3. changed main.dll, stale source, user files, read-only README, enabled.txt with content"
printf 'old dll' > "$MOD/dlls/main.dll"
printf 'my pair' > "$MOD/compat/MyCharacter.json"
printf 'x' > "$MOD/enabled.txt"
chmod u+w "$MOD/README.txt"; printf 'old readme' > "$MOD/README.txt"; chmod a-w "$MOD/README.txt"
printf '// gone in this version' > "$PLUG/Source/RebirthSkelCompatEditor/Private/Removed.cpp"
printf 'hot reload' > "$PLUG/Binaries/Win64/UE4Editor-RebirthSkelCompatEditor-0001.dll"
printf 'symbols' > "$PLUG/Binaries/Win64/UE4Editor-RebirthSkelCompatEditor.pdb"
run /S "$P"; rc=$?
check "[ $rc -eq 0 ]" "exit code 0"
check "cmp -s '$MOD/dlls/main.dll' '$STAGE/game/dlls/main.dll'" "main.dll replaced"
check "[ \"\$(cat \"\$(find '$MOD/Backups' -path '*dlls/main.dll' | head -1)\")\" = 'old dll' ]" "old main.dll in Backups/<stamp>/dlls"
check "[ \"\$(cat '$MOD/compat/MyCharacter.json')\" = 'my pair' ]" "user compat file untouched"
check "[ \"\$(cat '$MOD/enabled.txt')\" = 'x' ]" "existing enabled.txt kept"
check "cmp -s '$MOD/README.txt' '$STAGE/game/README.txt'" "read-only README replaced"
check "[ ! -e '$PLUG/Source/RebirthSkelCompatEditor/Private/Removed.cpp' ] && find '$PBACK' -name Removed.cpp | grep -q ." "stale source moved to <project>\\CreateACharacterSystem-Backups"
check "[ ! -e '$PLUG/Binaries/Win64/UE4Editor-RebirthSkelCompatEditor-0001.dll' ]" "hot-reload DLL moved away"
check "[ -e '$PLUG/Binaries/Win64/UE4Editor-RebirthSkelCompatEditor.pdb' ]" ".pdb left in place"
check "! find '$PROJ/Plugins' -name '*.uplugin' | grep -v '^$PLUG/RebirthSkelCompat.uplugin$' | grep -q ." "no second .uplugin under Plugins"

echo "== 4. silent uninstall without paths touches nothing"
run /S /uninstall; rc=$?
check "[ -f '$MOD/dlls/main.dll' ] && [ -f '$PLUG/RebirthSkelCompat.uplugin' ]" "nothing removed"
check "[ $rc -eq 2 ]" "exit code 2, nothing to do (got $rc)"

echo "== 5. uninstall: edited and own files are kept or backed up"
printf '\n// my change\n' >> "$PLUG/Source/RebirthSkelCompatEditor/Private/EndMoveMaker.cpp"
mkdir -p "$PLUG/Source/RebirthSkelCompatEditor/Private/MyWork"; printf '// mine' > "$PLUG/Source/RebirthSkelCompatEditor/Private/MyWork/MyNewClass.cpp"
printf 'notes' > "$PLUG/Source/NOTES.txt"
run /S /uninstall "$P" '/game:Z:\tmp\t\SteamLib\steamapps\common\FINAL FANTASY VII REBIRTH'; rc=$?
check "[ $rc -eq 0 ]" "exit code 0 (got $rc)"
check "[ ! -e '$MOD/dlls/main.dll' ] && [ ! -e '$MOD/README.txt' ] && [ ! -e '$MOD/enabled.txt' ] && [ ! -e '$MOD/CreateACharacterSystem.install.txt' ]" "game files removed"
check "[ \"\$(cat '$MOD/compat/MyCharacter.json')\" = 'my pair' ]" "user compat file kept"
check "[ ! -e '$PLUG/RebirthSkelCompat.uplugin' ] && [ ! -e '$PLUG/Source/RebirthSkelCompatEditor/Private/SkelCompatCore.hpp' ]" "unchanged plugin files removed"
check "[ ! -e '$PLUG/Source/RebirthSkelCompatEditor/Private/EndMoveMaker.cpp' ] && grep -q 'my change' \"\$(find '$PBACK' -name EndMoveMaker.cpp | head -1)\"" "edited EndMoveMaker.cpp moved to the backup folder"
check "[ -f '$PLUG/Source/RebirthSkelCompatEditor/Private/MyWork/MyNewClass.cpp' ] && [ -f '$PLUG/Source/NOTES.txt' ]" "own sources stay in place"
check "[ -e '$PLUG/Binaries/Win64/UE4Editor-RebirthSkelCompatEditor.pdb' ]" ".pdb (not Setup's) left"

echo "== 6. uninstall of a copy Setup didn't install does nothing"
setup_env
mkdir -p "$PLUG/Source"; printf '{ "VersionName": "dev" }' > "$PLUG/RebirthSkelCompat.uplugin"; printf '// wip' > "$PLUG/Source/WorkInProgress.cpp"
run /S /uninstall "$P"; rc=$?
check "[ -f '$PLUG/RebirthSkelCompat.uplugin' ] && [ -f '$PLUG/Source/WorkInProgress.cpp' ]" "developer copy untouched"
check "[ $rc -eq 2 ]" "exit code 2 (got $rc)"

echo "== 7. project found by the scan (C:\\FF7R2UProj), game given by a subfolder"
setup_env
mkdir -p "$WINEPREFIX/drive_c/FF7R2UProj"
cp "$PROJ/End.uproject" "$WINEPREFIX/drive_c/FF7R2UProj/End.uproject"
run /S '/game:Z:\tmp\t\SteamLib\steamapps\common\FINAL FANTASY VII REBIRTH\End\Binaries\Win64\ue4ss'; rc=$?
check "[ $rc -eq 0 ]" "exit code 0"
check "[ -f '$WINEPREFIX/drive_c/FF7R2UProj/Plugins/RebirthSkelCompat/RebirthSkelCompat.uplugin' ]" "plugin went to C:\\FF7R2UProj"
check "[ -f '$MOD/dlls/main.dll' ]" "game root found from a subfolder"
rm -rf "$WINEPREFIX/drive_c/FF7R2UProj"

echo "== 8. no UE4SS, engine of another build"
setup_env
rm -f "$WIN64/ue4ss/UE4SS.dll"
printf '{ "BuildId": "00000000-0000-0000-0000-000000000000" }' > "$T/Engine/Engine/Binaries/Win64/UE4Editor.modules"
run /S "$P"; rc=$?
check "[ $rc -eq 0 ]" "exit code 0"
check "TEMPLOG | grep -q \"UE4SS isn't installed\"" "warns UE4SS is missing"
check "TEMPLOG | grep -q 'build differs'" "warns the engine build differs"
check "[ -f '$MOD/dlls/main.dll' ]" "still installs into ue4ss\\Mods"

echo "== 9. another copy of the plugin in the project or the engine"
setup_env
mkdir -p "$PROJ/Plugins/Old/RebirthSkelCompat-1.8"; printf '{}' > "$PROJ/Plugins/Old/RebirthSkelCompat-1.8/RebirthSkelCompat.uplugin"
run /S "$P"; rc=$?
check "[ $rc -eq 1 ]" "exit code 1 (got $rc)"
check "[ ! -e '$PLUG' ]" "plugin not installed next to the other copy"
check "TEMPLOG | grep -q 'Another copy of the plugin'" "says why"
check "[ -f '$MOD/dlls/main.dll' ]" "game part still installed"
setup_env
mkdir -p "$T/Engine/Engine/Plugins/Runtime/RebirthSkelCompat"; printf '{}' > "$T/Engine/Engine/Plugins/Runtime/RebirthSkelCompat/RebirthSkelCompat.uplugin"
run /S /nogame "$P"; rc=$?
check "[ $rc -eq 1 ] && [ ! -e '$PLUG' ]" "engine copy blocks it too (exit $rc)"

echo "== 10. a given path that isn't usable"
setup_env
run /S '/game:Z:\no\such\game' "$P"; rc=$?
check "[ $rc -eq 1 ]" "exit code 1 (got $rc)"
check "TEMPLOG | grep -q 'No FINAL FANTASY VII REBIRTH here'" "logged"
check "[ -f '$PLUG/RebirthSkelCompat.uplugin' ]" "the usable part still installed"

echo "== 11. damaged Setup (cut short)"
head -c 1000000 "$SETUP" > "$T/Setup.exe"
run /S; rc=$?
check "[ $rc -eq 3 ]" "refuses with exit code 3 (got $rc)"
check "TEMPLOG | grep -q 'damaged'" "logged"

echo
if [ $FAILS -eq 0 ]; then echo "ALL WINE TESTS PASSED"; else echo "$FAILS FAILED"; exit 1; fi
