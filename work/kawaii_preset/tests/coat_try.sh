#!/bin/bash
# coat_try.sh <tag> <model: winged|older|remake> [ENV=value ...]: makes that entry with the settings given, then the coat
# standing (coat_flare.py on a still run) and in the legs on Remake Sephiroth's walk, battle walk and run (anim_run)
TAG=$1; MODEL=$2; shift 2
S=/tmp/scratch/coat/$TAG; mkdir -p $S
K=/work/kawaii_preset; T=$K/tests; A=$K/anims/eb0021_walk_samples.json
case $MODEL in
  winged) R=$K/rigs/PC0010_10.json; M=$K/meshes/PC0010_10.npz; ARGS="--rig $R --mesh $M --model /Game/x/PC0010_10.PC0010_10";;
  older)  R=$K/rigs/PC0010_00.json; M=$K/meshes/PC0010_00.npz; ARGS="--rig $R --mesh $M --model /Game/x/PC0010_15.PC0010_15 --bonamik PC0010_00_BNM";;
  remake) R=$K/rigs/EB0021_00.json; M=$K/meshes/PC0010_10.npz; ARGS="--rig $R --radii-from $K/out/e_pc0010_10.radii.json --model /Game/x/EB0021_00.EB0021_00";;
esac
env "$@" python3 $K/tools/make_kawaii_preset.py $ARGS --name t --out $S/e.json > $S/gen.txt || { cat $S/gen.txt; exit 1; }
$T/preset_run_3148 $R $S/e.json 60 $S/idle.bin 0 6 0 0 0 0 > /dev/null
printf "%-22s %s\n" "$TAG" "$(python3 $T/coat_flare.py $R $S/idle.bin)"
for c in Neutral00/N_Walk01_1 Battle00/B_Walk01_1 Neutral00/N_Run01_1; do
  $T/anim_run $R $S/e.json $A $c $S/c.bin 7 60 > /dev/null
  printf "%-22s %-10s %s\n" "" "$(basename $c | cut -d_ -f2)" "$(python3 $T/clip_check.py $M $R $S/c.bin x | sed 's/.*inside a leg \([0-9.]*%\).*depth 95% \([0-9.]*\) cm, 99% \([0-9.]*\), max \([0-9.]*\) (frame \([0-9]*\)); frames with any > 1 cm: \([0-9]*\) of \([0-9]*\).*/in-leg \1  p99 \3  max \4 cm  frames>1cm \6\/\7/')"
done
