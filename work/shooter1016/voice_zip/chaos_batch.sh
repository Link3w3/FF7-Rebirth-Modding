#!/bin/sh
# Apply the Chaos filter to every one of Vincent's English voice clips, keeping each file's exact name (the hex cue id +
# cue name) so AudioMog maps them back. Usage: chaos_batch.sh <filter_complex> <src dir> <out dir> [glob]
FILT="$1"; SRC="$2"; OUT="$3"; GLOB="${4:-*vn.wav}"
mkdir -p "$OUT"
n=0; fail=0
for src in "$SRC"/$GLOB; do
  [ -f "$src" ] || continue
  base=$(basename "$src")
  if ffmpeg -y -v error -i "$src" -filter_complex "$FILT" -ar 44100 -ac 1 -c:a pcm_s16le "$OUT/$base" 2>/dev/null; then
    n=$((n+1))
  else
    echo "FAILED: $base"; fail=$((fail+1))
  fi
done
echo "done: $n clips, $fail failed -> $OUT"
