#!/bin/sh
# Builds owners_sim (the DLL's ability-row choice, RebirthSkelCompat.cpp from TakenPlayers to AbilityRowFor, as it is)
# and runs it on a compat folder, a skins folder and a list of installed paks:
#   tests/owners_sim.sh <compat dir> <skins dir> <paks file>
set -e
T=$(dirname "$0")
OUT=${TMPDIR:-/tmp}/owners_sim.$$
mkdir -p "$OUT"
python3 - "$T/../src/RebirthSkelCompat.cpp" "$OUT/owners_body.inc" <<'PY'
import sys
s = open(sys.argv[1], encoding='utf-8').read()
a = s.index('std::vector<std::pair<std::wstring, std::wstring>> TakenPlayers;')
b = s.index('std::wstring ApplyAbilities(const SkelCompat::AnimSetRow& row')
open(sys.argv[2], 'w').write(s[a:b])
PY
g++ -std=c++20 -O1 -I"$T/../src" -I"$OUT" -o "$OUT/owners_sim" "$T/owners_sim.cpp"
"$OUT/owners_sim" "$@"
