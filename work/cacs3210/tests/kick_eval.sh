#!/bin/bash
# kick_eval.sh <tag> <entry.json> <rig.json> <body.npz> [ys]: kicks (front, round: the coat through / in the legs, kick_check.py)
# and Remake Sephiroth's walk and run (the coat in the legs, clip_check.py / ys_skirt_check.py) for one entry
TAG=$1; E=$2; R=$3; M=$4; YS=$5
SP=/tmp/scratch/kick/runs; mkdir -p $SP
T=/work/cacs3180/tests; KP=/work/kawaii_preset; A=$KP/anims/eb0021_walk_samples.json
for kind in front round; do
  $T/kick_run $R $E 60 $SP/$TAG.$kind.bin 6 0.46 $kind 95 > /dev/null
  printf "%-26s %-6s %s\n" "$TAG" "$kind" "$(python3 $T/kick_check.py $M $R $SP/$TAG.$kind.bin x | sed 's/^x *//')"
done
for c in Neutral00/N_Walk01_1 Neutral00/N_Run01_1; do
  $KP/tests/anim_run_3170 $R $E $A $c $SP/$TAG.c.bin 7 60 > /dev/null
  if [ -n "$YS" ]; then chk=$T/ys_skirt_check.py; else chk=$KP/tests/clip_check.py; fi
  printf "%-26s %-6s %s\n" "" "$(basename $c | cut -d_ -f2)" "$(python3 $chk $M $R $SP/$TAG.c.bin x | sed 's/.*inside a leg \([0-9.]*%\).*depth 95% \([0-9.]*\) cm, 99% \([0-9.]*\), max \([0-9.]*\) (frame \([0-9]*\)); frames with any > 1 cm: \([0-9]*\) of \([0-9]*\).*/in-leg \1  p99 \3  max \4 cm  frames>1cm \6\/\7/')"
done
