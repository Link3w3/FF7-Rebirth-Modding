#!/bin/bash
# run_editor.sh <editor .py> [seconds]   send a Python script to the End editor's link and wait for its answer
# run_editor.sh --wait <seq> [seconds]   wait for the answer to a command sent earlier
L="$HOME/mnt/FF7R2UProj/Saved/RebirthEditorLink"
if [ "$1" = "--wait" ]; then S="$2"; W="${3:-170}"; else
  W="${2:-170}"
  if ! grep -q "\"seq\": $(sed -n 's/^# seq = //p' "$L/command.py" | head -1)" "$L/status.json" 2>/dev/null; then
    echo "BUSY: the editor has not answered its last command yet"; exit 1
  fi
  S=$(date +%s%3N); { printf '# seq = %s\n' "$S"; cat "$1"; } > "$L/command.tmp" && mv "$L/command.tmp" "$L/command.py"
fi
for i in $(seq 1 "$W"); do
  sleep 1
  if grep -q "\"seq\": $S" "$L/status.json" 2>/dev/null; then
    python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print('ok' if d.get('ok') else 'FAILED', d.get('seconds'), 's'); print(d.get('result') or d.get('error') or ''); o=d.get('output',''); print(o[-3000:] if o else '')" "$L/status.json"
    exit 0
  fi
done
echo "still running after $W s (seq $S): run_editor.sh --wait $S"
