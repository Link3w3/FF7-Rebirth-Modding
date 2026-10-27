#!/bin/bash
# run_variant.sh <name> '<changes json>': the entry, its three offline runs and their mantle measures
set -e
cd /work/bfs17
N=$1; C=$2
D=tune/$N
mkdir -p $D
python3 tune_mantle.py hair/rerig_hair6_uv1.npz /Game/Character/Player/PC0010_17_Bahumunt_Fused_Sephiroth/Model/PC0010_17_Compat.PC0010_17_Compat $D "$C" > $D/report.json
rm -f $D/body.npz          # (the same for every variant: kawaii_h's)
python3 -c "import json,sys; e=json.load(open(sys.argv[1])); json.dump({'schema': 'RebirthSkelCompat/1', 'note': 'offline run', 'kawaii': e['kawaii']}, open(sys.argv[2], 'w'), indent=1)" $D/entry.json $D/test_compat.json
for clip in Neutral00/N_Walk01_1 Neutral00/N_Run01_1 Battle00/B_Walk01_1 Battle00/B_Walk01_1@0; do
  b=$(basename $clip); speed=1; case $clip in *@0) clip=${clip%@0}; b=Stand; speed=0;; esac
  ${RUNNER:-/work/kawaii_preset/tests/anim_run} $D/rig.json $D/test_compat.json kawaii/samples_scaled.json $clip $D/$b.bin 7 60 $speed > $D/$b.log 2>&1 || { echo "run failed: $D/$b.log"; cat $D/$b.log | tail -5; exit 1; }
  python3 mantle_metrics.py $D/rig.json $D/$b.bin "$N $b"
done
