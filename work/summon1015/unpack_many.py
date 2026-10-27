import sys, json, os
sys.path.insert(0, '/work/iostore')
from iostore import oodle
blob = open(sys.argv[1], 'rb').read(); meta = json.load(open(sys.argv[1] + '.json')); outdir = sys.argv[2]
p = 0
for m in meta:
    out = bytearray()
    for boff, csz, usz, meth in m['blocks']:
        raw = blob[p:p + csz]; p += csz
        out += raw[:usz] if meth == 0 else oodle(raw, usz)
    start = m['off'] - m['first'] * m['blocksz']
    data = bytes(out[start:start + m['len']])
    parts = m['path'].split('/'); name = (parts[-2] + '__' + parts[-1]) if parts[-1].startswith('Battle') else parts[-1]
    open(os.path.join(outdir, name), 'wb').write(data)
    print(name, len(data))
