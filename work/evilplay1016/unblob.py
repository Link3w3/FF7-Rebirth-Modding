"""Packages out of a dump_many.py blob (the raw blocks of each chunk, as the game's .ucas has them, Oodle or stored).
    unblob.py <blob.bin> <out dir>"""
import json, os, sys
sys.path.insert(0, '/work/iostore')
from iostore import oodle
blob, out = sys.argv[1], sys.argv[2]
meta = json.load(open(blob + '.json'))
data = open(blob, 'rb').read()
os.makedirs(out, exist_ok=True)
pos = 0
for m in meta:
    raw = bytearray()
    for boff, csz, usz, method in m['blocks']:
        piece = data[pos:pos + csz]
        pos += csz
        raw += piece[:usz] if method == 0 else oodle(piece, usz)
    start = m['off'] - m['first'] * m['blocksz']
    pkg = bytes(raw[start:start + m['len']])
    name = m['path'].replace('../../../End/Content/', '').replace('/', '__')
    open(os.path.join(out, name), 'wb').write(pkg)
    print(name, len(pkg))
assert pos == len(data)
