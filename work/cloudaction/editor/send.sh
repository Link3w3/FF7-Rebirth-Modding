#!/bin/bash
# send.sh <editor .py>  -> prints the remote shell command that runs it through the editor link and waits (<=170 s)
f="$1"; b=$(base64 -w0 "$f")
cat <<CMD
L="\$HOME/mnt/FF7R2UProj/Saved/RebirthEditorLink"; S=\$(date +%s%3N); { printf '# seq = %s\n' "\$S"; echo '$b' | base64 -d; } > "\$L/command.tmp" && mv "\$L/command.tmp" "\$L/command.py" && for i in \$(seq 1 170); do sleep 1; if grep -q "\"seq\": \$S" "\$L/status.json" 2>/dev/null; then python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print('ok' if d.get('ok') else 'FAILED', d.get('seconds')); print(d.get('result') or ''); print(d.get('output','')[-2000:])" "\$L/status.json"; exit 0; fi; done; echo "still running after 170 s (seq \$S)"
CMD
