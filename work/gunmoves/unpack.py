import sys, json, os
sys.path.insert(0, '/work/iostore')
from iostore import Toc, oodle
plan = json.load(open('plan.json')); reads = json.load(open('reads.json'))
blobs = {c: open(c + '.blocks', 'rb').read() for c in reads}
pos = {}
for c, rs in reads.items():
    p = 0
    for off, size in rs:
        pos[(c, off)] = p; p += size
tocs = {c: Toc(c + '-WindowsNoEditor.utoc') for c in reads}
os.makedirs('pkgs', exist_ok=True)
for e in plan:
    c = e['chunk']; t = tocs[c]
    out = bytearray()
    for boff, csz, usz, m in e['blocks']:
        p = pos[(c, boff)]
        raw = blobs[c][p:p + csz]
        out += raw[:usz] if m == 0 else oodle(raw, usz)
    start = e['offset'] - e['first_block'] * t.blocksz
    data = bytes(out[start:start + e['length']])
    name = e['path'].split('/Content/', 1)[1].replace('/', '__')
    open(os.path.join('pkgs', name), 'wb').write(data)
print(len(os.listdir('pkgs')))
