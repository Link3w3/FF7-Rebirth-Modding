#!/bin/sh
# the opaque (GBuffer) permutations
python3 -c "
import json, re
for r in json.load(open('gen/index.json')):
    n = r['name'][12:]
    if not re.search(r'Glass|Crystal|Water|Ocean|Unlit', n): print(n)
"
