"""Game package extraction in two steps (the .ucas files stay on the PC; only the needed compressed blocks come over).
    gx.py plan <utoc> <out dir> <regex> [<regex> ...]   -> <out dir>/plan.json + the device read command (printed)
    gx.py assemble <utoc> <out dir> <raw dir>          -> <out dir>/pkgs/<path with __>.uasset
The read command reads merged block ranges from the .ucas next to the .utoc on the PC into <scratch>/r_<offset>.bin."""
import json, os, re, struct, sys
sys.path[:0] = ['/work/iostore', '/work/cs']
from iostore import Toc
from unblock import oodle


def plan(utoc, out, pats):
    t = Toc(utoc)
    items = []
    for i, path in t.files.items():
        if not any(re.search(p, path) for p in pats):
            continue
        off, ln = t.offlen[i]
        first = off // t.blocksz
        last = (off + ln - 1) // t.blocksz
        blocks = [list(t.blocks[b]) for b in range(first, last + 1)]
        items.append(dict(path=path, index=i, offset=off, length=ln, first_block=first, blocks=blocks))
    reads = sorted({(b[0], (b[1] + 15) & ~15) for it in items for b in it['blocks']})
    merged = []
    for o, s in reads:
        if merged and merged[-1][0] + merged[-1][1] >= o:
            merged[-1][1] = max(merged[-1][1], o + s - merged[-1][0])
        else:
            merged.append([o, s])
    os.makedirs(out, exist_ok=True)
    json.dump(dict(utoc=utoc, items=items, merged=merged), open(os.path.join(out, 'plan.json'), 'w'))
    total = sum(s for _, s in merged)
    print('%d packages, %d ranges, %d bytes' % (len(items), len(merged), total))
    return merged


def read_block(raw_dir, merged, off, csize):
    for o, s in merged:
        if o <= off and off + csize <= o + s:
            with open(os.path.join(raw_dir, 'r_%d.bin' % o), 'rb') as f:
                f.seek(off - o)
                return f.read(csize)
    raise KeyError('block at %d not read' % off)


def assemble(utoc, out, raw_dir):
    p = json.load(open(os.path.join(out, 'plan.json')))
    t = Toc(utoc)
    os.makedirs(os.path.join(out, 'pkgs'), exist_ok=True)
    for it in p['items']:
        data = bytearray()
        for off, csize, usize, method in it['blocks']:
            raw = read_block(raw_dir, p['merged'], off, csize)
            data += raw[:usize] if method == 0 else oodle(raw, usize)
        start = it['offset'] - it['first_block'] * t.blocksz
        pkg = bytes(data[start:start + it['length']])
        name = it['path'].split('Content/')[1].replace('/', '__')
        open(os.path.join(out, 'pkgs', name), 'wb').write(pkg)
        print(name, len(pkg))


if __name__ == '__main__':
    if sys.argv[1] == 'plan':
        merged = plan(sys.argv[2], sys.argv[3], sys.argv[4:])
        print(json.dumps(merged))
    else:
        assemble(sys.argv[2], sys.argv[3], sys.argv[4])
