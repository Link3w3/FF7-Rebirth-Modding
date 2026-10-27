import sys, json, os
sys.path.insert(0, '/work/iostore')
from iostore import oodle
blob = open(sys.argv[1], 'rb').read(); meta = json.load(open(sys.argv[1] + '.json'))
p = 0
for m in meta:
    out = bytearray()
    for boff, csz, usz, meth in m['blocks']:
        raw = blob[p:p + csz]; p += csz
        out += raw[:usz] if meth == 0 else oodle(raw, usz)
    start = m['off'] - m['first'] * m['blocksz']
    data = bytes(out[start:start + m['len']])
    name = m['path'].split('/')[-1].replace('.uasset', '')
    open(os.path.join(sys.argv[2], name + '.bin'), 'wb').write(data)
print('ok', len(meta))
