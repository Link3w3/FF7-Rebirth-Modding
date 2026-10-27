#!/bin/bash
# scenarios.sh <rig.json> <kawaii.json> <body.npz or -> <tag>: clipping and rest offsets over the standard motions
R=$1; K=$2; M=$3; TAG=$4
S=/tmp/scratch/scn; mkdir -p $S
P=/work/kawaii_preset/tests/preset_run
for sc in "idle 0 6 0 0 0 0" "walk 35 6 250 0 0" "run 55 6 450 0 0" "runturn 55 6 450 20 0" "sprint 70 6 700 0 0" "runstop 55 6 450 0 3.5" "spin 0 6 0 90 3.5 0"; do
  set -- $sc
  $P $R $K 60 $S/$TAG.$1.bin $2 $3 $4 $5 $6 ${7:-2.5} > /dev/null
  if [ "$M" != "-" ]; then c=$(python3 /work/kawaii_preset/tests/clip_check.py $M $R $S/$TAG.$1.bin x | sed 's/.*inside a leg \([0-9.]*%\).*depth 95% \([0-9.]*\) cm, 99% \([0-9.]*\), max \([0-9.]*\).*/in-leg \1 p99 \3 max \4/'); else c=""; fi
  ro=$(python3 /work/kawaii_preset/tests/rest_offsets.py $R $S/$TAG.$1.bin | awk '{printf "%s %s/%s ", $1, $7, $10}' | tr -d ',')
  printf "%-8s %-36s end offsets (median/max cm): %s\n" $1 "$c" "$ro"
done
