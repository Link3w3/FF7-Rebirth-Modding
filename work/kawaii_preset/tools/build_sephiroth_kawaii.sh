#!/bin/bash
# Makes compat/SephirothKawaii.json (out/SephirothKawaii.json) from the rigs and meshes: the four Sephiroth entries
# (tools/make_kawaii_preset.py), merged (tools/merge_kawaii.py) with the note in tools/sephiroth_kawaii_note.txt, and the
# models that share an entry added (tools/add_kawaii_model.py: Anime Sephiroth's PC0010_01 on the winged entry); Seraph
# Sephiroth's entry (tools/make_seraph_kawaii.py) the fifth.
#   tools/build_sephiroth_kawaii.sh [out folder = out]
set -e
cd "$(dirname "$0")/.."
O=${1:-out}
mkdir -p "$O"
T=tools
python3 $T/make_kawaii_preset.py --rig rigs/PC0010_00.json --mesh meshes/PC0010_00.npz \
  --model /Game/Character/Player/PC0010_15_Sephiroth_Older/Model/PC0010_15.PC0010_15 --requires YoungSephiroth_P \
  --bonamik PC0010_00_BNM --name "Sephiroth (Rebirth, PC0010_15): hair, coat, belts, collar" --out $O/e_pc0010_15.json
python3 $T/make_kawaii_preset.py --rig rigs/PC0010_10.json --mesh meshes/PC0010_10.npz \
  --model /Game/Character/Player/PC0010_10_Sephiroth_Transform/Model/PC0010_10.PC0010_10 \
  --name "Sephiroth (Rebirth, winged, PC0010_10): hair, coat, belts, collar, wing" --out $O/e_pc0010_10.json
# (the Remake models: no mesh; the chains' radii measured on the winged model, whose chains they share)
python3 $T/make_kawaii_preset.py --rig rigs/EB0021_00.json --radii-from $O/e_pc0010_10.radii.json \
  --model /Game/GameContents/Character/Enemy/EB0021_00_Sephiroth_Standard/Model/EB0021_00.EB0021_00 \
  --name "Remake Sephiroth (EB0021_00): hair, coat, belts, collar" --out $O/e_eb0021_00.json
python3 $T/make_kawaii_preset.py --rig rigs/EB0021_01_Body.json --radii-from $O/e_pc0010_10.radii.json \
  --model /Game/GameContents/Character/Enemy/EB0021_01_Sephiroth_Transform/Model/EB0021_01_Body.EB0021_01_Body \
  --name "Remake Sephiroth (winged, EB0021_01): hair, coat, belts, collar, wing" --out $O/e_eb0021_01.json
# (2026-10-26) Seraph Sephiroth (the Seraph Sephiroth skins' model): the winged entry's coat, belts, collar and wing nodes,
# and his own hair's from the preset on his rig and mesh (rigs/meshes PC0010_15_Seraph: tools/mesh_bones.py and
# tools/cooked_mesh_inline.py on the skin's cooked model)
python3 $T/make_seraph_kawaii.py --rig rigs/PC0010_15_Seraph.json --mesh meshes/PC0010_15_Seraph.npz --winged-rig rigs/PC0010_10.json \
  --winged $O/e_pc0010_10.json --model /Game/Character/Player/PC0010_15_Seraph_Sephiroth_Transformed/Model/PC0010_15.PC0010_15 \
  --out $O/e_pc0010_15_seraph.json
python3 $T/merge_kawaii.py $O/SephirothKawaii.json "$(cat $T/sephiroth_kawaii_note.txt)" \
  $O/e_pc0010_15.json $O/e_pc0010_10.json $O/e_eb0021_00.json $O/e_eb0021_01.json $O/e_pc0010_15_seraph.json
python3 $T/add_kawaii_model.py $O/SephirothKawaii.json /Game/Character/Player/PC0010_10_Sephiroth_Transform/Model/PC0010_10.PC0010_10 \
  /Game/Character/Player/PC0010_00_Sephiroth_Standard/Model/PC0010_10/PC0010_01.PC0010_01 \
  --name "Sephiroth (Rebirth, winged, PC0010_10; also Anime Sephiroth, PC0010_01): hair, coat, belts, collar, wing" \
  --note "Anime Sephiroth (2026-10-26): the Anime Sephiroth skin's model (PC0010_01, the winged model brought back from an FBX: the same bones in the same reference pose, the same body, the same Bonamik and KineDriver) is on the winged Sephiroth's entry."
md5sum $O/SephirothKawaii.json
