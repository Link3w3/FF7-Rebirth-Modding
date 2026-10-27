#!/bin/bash
# prints a device command that runs the given python file through the editor link and waits up to $2 seconds
F="$1"; W="${2:-20}"
B=$(base64 -w0 "$F")
cat <<CMD
P="\$HOME/mnt/FF7R2UProj/Saved/RebirthEditorLink"; SEQ=\$(date +%s%3N); { echo "# seq = \$SEQ"; echo '$B' | base64 -d; } > "\$P/command.py.tmp" && mv -f "\$P/command.py.tmp" "\$P/command.py"; for i in \$(seq 1 $W); do sleep 1; if grep -q "\"seq\": \$SEQ" "\$P/status.json" 2>/dev/null; then cat "\$P/status.json"; exit 0; fi; done; echo "no answer yet for \$SEQ"
CMD
