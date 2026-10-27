#!/bin/bash
# coat_eval.sh <rig.json> <entry.json> <body.npz> <tag>: the coat standing (flare, coat_flare.py) and in the legs on a
# forward walk, a slow walk and a run (clip_check.py), with the 3.14.8 solver (preset_run_3148)
R=$1; K=$2; M=$3; TAG=$4
S=/tmp/scratch/coat; mkdir -p $S
P=/work/kawaii_preset/tests/preset_run_3148
T=/work/kawaii_preset/tests
$P $R $K 60 $S/$TAG.idle.bin 0 6 0 0 0 0 > /dev/null
printf "%-14s %s\n" "$TAG" "$(python3 $T/coat_flare.py $R $S/$TAG.idle.bin)"
for sc in "walk 35 6 250 0 0" "slowwalk 25 6 150 0 0" "run 55 6 450 0 0"; do
  set -- $sc
  $P $R $K 60 $S/$TAG.$1.bin $2 $3 $4 $5 $6 2.5 > /dev/null
  c=$(python3 $T/clip_check.py $M $R $S/$TAG.$1.bin x | sed 's/.*inside a leg \([0-9.]*%\).*depth 95% \([0-9.]*\) cm, 99% \([0-9.]*\), max \([0-9.]*\) (frame \([0-9]*\)); frames with any > 1 cm: \([0-9]*\) of \([0-9]*\).*/in-leg \1  p95 \2  p99 \3  max \4 cm  frames>1cm \6\/\7/')
  printf "%-14s %-9s %s\n" "" "$1" "$c"
done
