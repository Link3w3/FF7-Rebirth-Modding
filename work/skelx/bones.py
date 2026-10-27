import sys, struct, os, json
sys.path.insert(0, '/work/cs')
from zen import Zen

def scan(data, names, min_bones=20):
    found = []
    for off in range(0, len(data) - 4, 4) if False else range(0, len(data) - 4):
        n = struct.unpack_from('<i', data, off)[0]
        if n < min_bones or n > 4000 or off + 4 + 12 * n > len(data):
            continue
        ok = True
        bones = []
        for i in range(n):
            ni, num, parent = struct.unpack_from('<IIi', data, off + 4 + 12 * i)
            idx = ni & 0x3FFFFFFF
            if idx >= len(names) or (i == 0 and parent != -1) or (i > 0 and not (0 <= parent < i)):
                ok = False
                break
            nm = names[idx] + ('_%d' % (num - 1) if num else '')
            bones.append((nm, parent))
        if ok:
            found.append((off, bones))
    return found

def load(path):
    data = open(path, 'rb').read()
    z = Zen(data)
    out = {}
    for ei, e in enumerate(z.exports):
        ed = z.export_data(ei)
        res = scan(ed, z.names)
        if res:
            out[(ei, e['name'])] = res
    return z, out

if __name__ == '__main__':
    result = {}
    for fn in sys.argv[1:]:
        z, out = load(fn)
        for (ei, en), res in out.items():
            for off, bones in res:
                print(os.path.basename(fn), ei, en, 'offset', off, 'bones', len(bones), bones[:3])
        best = max((b for res in out.values() for _, b in res), key=len, default=None)
        result[os.path.basename(fn)] = best
    json.dump(result, open('bones.json', 'w'), indent=0)
