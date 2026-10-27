import sys, json, os
sys.path.insert(0, '/work/iostore')
from iostore import oodle
plan = json.load(open('plan.json')); ranges = [tuple(r) for r in json.load(open('ranges.json'))]
blob = open(sys.argv[1], 'rb').read()
pos = {}; p = 0
for r in ranges:
    pos[r] = (p, r[2]); p += r[2]
os.makedirs('pkgs', exist_ok=True)
for e in plan:
    out = bytearray()
    for b in e['blocks']:
        off, csz, usz, m = b
        q, n = pos[(e['container'], off, csz)]
        raw = blob[q:q + n]
        out += raw[:usz] if m == 0 else oodle(raw, usz)
    start = e['off'] - e['first'] * e['blocksz']
    data = bytes(out[start:start + e['len']])
    fn = 'pkgs/%s.type%d.bin' % (e['name'], e['type'])
    open(fn, 'wb').write(data)
    print(fn, len(data))
