"""Targeted reads of the game's IoStore packages.
plan  <name> <utoc>:<path-substring> ...   -> writes plan.json and prints the device python
unpack <name> <blocks-dir>                 -> rebuilds the packages from <chunk>.blocks into pkgs/
"""
import sys, os, json, struct
sys.path.insert(0, '/work/iostore')
from iostore import Toc, oodle
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def plan(name, specs):
    items = []; reads = {}
    for spec in specs:
        utoc, sub = spec.split(':', 1)
        t = Toc(utoc)
        chunk = os.path.basename(utoc).split('-')[0]
        hits = [(i, p) for i, p in t.files.items() if sub in p]
        if not hits:
            print('NOT FOUND', spec); continue
        for i, p in hits:
            off, ln = t.offlen[i]
            first = off // t.blocksz; last = (off + ln - 1) // t.blocksz
            blocks = []
            for bi in range(first, last + 1):
                boff, csz, usz, m = t.blocks[bi]
                blocks.append([boff, (csz + 15) & ~15, csz, usz, m])
            items.append({'chunk': chunk, 'utoc': utoc, 'path': p, 'index': i, 'offset': off, 'length': ln,
                          'first_block': first, 'blocksz': t.blocksz, 'blocks': blocks, 'methods': t.methods})
            rs = reads.setdefault(chunk, [])
            for b in blocks:
                if [b[0], b[1]] not in rs: rs.append([b[0], b[1]])
    for chunk in reads: reads[chunk].sort()
    os.makedirs(os.path.join(HERE, 'plans'), exist_ok=True)
    json.dump({'name': name, 'items': items, 'reads': reads}, open(os.path.join(HERE, 'plans', name + '.json'), 'w'))
    dev = f'''import os
reads = {json.dumps(reads)}
base = os.path.expanduser("~/mnt/FINAL FANTASY VII REBIRTH/End/Content/Paks")
out = os.path.expanduser("~/mnt/FF7R2UProj/Saved/ModExtract/{name}")
os.makedirs(out, exist_ok=True)
for chunk, ranges in reads.items():
    with open(os.path.join(base, chunk + "-WindowsNoEditor.ucas"), "rb") as f, open(os.path.join(out, chunk + ".blocks"), "wb") as o:
        n = 0
        for off, size in ranges:
            f.seek(off); d = f.read(size); assert len(d) == size, (chunk, off, size, len(d)); o.write(d); n += size
    print(chunk, len(ranges), n)
'''
    open(os.path.join(HERE, 'plans', name + '_device.py'), 'w').write(dev)
    for it in items: print(it['chunk'], it['index'], it['path'], it['length'])

def unpack(name, blocksdir):
    p = json.load(open(os.path.join(HERE, 'plans', name + '.json')))
    data = {}
    for chunk, ranges in p['reads'].items():
        raw = open(os.path.join(blocksdir, chunk + '.blocks'), 'rb').read()
        pos = 0; at = {}
        for off, size in ranges:
            at[off] = raw[pos:pos + size]; pos += size
        data[chunk] = at
    os.makedirs(os.path.join(HERE, 'pkgs'), exist_ok=True)
    for it in p['items']:
        out = bytearray()
        for boff, rsz, csz, usz, m in it['blocks']:
            raw = data[it['chunk']][boff][:csz]
            if m == 0: out += raw[:usz]
            else: out += oodle(raw, usz)
        start = it['offset'] - it['first_block'] * it['blocksz']
        pkg = bytes(out[start:start + it['length']])
        fn = it['path'].replace('../../../End/Content/', '').replace('/', '__')
        open(os.path.join(HERE, 'pkgs', fn), 'wb').write(pkg)
        print('wrote', fn, len(pkg))

if __name__ == '__main__':
    if sys.argv[1] == 'plan': plan(sys.argv[2], sys.argv[3:])
    else: unpack(sys.argv[2], sys.argv[3])
