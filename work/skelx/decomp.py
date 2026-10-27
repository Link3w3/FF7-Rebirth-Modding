import json, os, sys, ctypes
sys.path.insert(0, '/work/cs')
from unblock import oodle
src = sys.argv[1]; dst = sys.argv[2]
idx = json.load(open(os.path.join(src, 'index.json')))
os.makedirs(dst, exist_ok=True)
for w, rec in idx.items():
    raw = open(os.path.join(src, os.path.basename(w) + '.blocks'), 'rb').read()
    p = 0; out = bytearray()
    for csz, usz, m in rec['blocks']:
        data = raw[p:p+csz]; p += csz
        out += data[:usz] if m == 'None' else oodle(data, usz)
    start = rec['offset'] - rec['first_block'] * rec['blocksize']
    blob = bytes(out[start:start + rec['length']])
    open(os.path.join(dst, os.path.basename(w)), 'wb').write(blob)
    print(os.path.basename(w), len(blob), rec['blocks'][0][2])
