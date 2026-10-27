#!/bin/bash
# run_step.sh <step> "<python value of K>" [seconds]   run editor/ca_<step>.py (after ca_common.py) with K set
D="$HOME/mnt/FF7R2UProj/Saved/ModExtract/cloudaction"
W="$D/editor/_wrap_$1.py"
cat > "$W" <<PY
K = $2
import unreal, os
_d = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), 'ModExtract', 'cloudaction', 'editor')
exec(open(os.path.join(_d, 'ca_common.py')).read())
exec(open(os.path.join(_d, 'ca_$1.py')).read())
PY
bash "$D/run_editor.sh" "$W" "${3:-170}"
