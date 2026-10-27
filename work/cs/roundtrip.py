import sys, struct
from zen import Zen
from mmimg import MMAsset
import frozen
def name_at_from(m, names):
    at = {}
    for (ni, num), offs in m.minimal_names:
        for o in offs: at[o] = (names[ni], num)
    return at
def check(data, verbose=False, cross=False):
    z = Zen(data)
    e = z.export_data(0)
    p = 0
    while True:
        frag = struct.unpack_from('<H', e, p)[0]; p += 2
        if frag & 0x100: break
    m = MMAsset(e, z.names, p + 4)
    at = name_at_from(m, z.names)
    d = frozen.decode(m.content, at)
    keys = [k[0] for k in d.keys]
    assert all(k[1] == i for i, k in enumerate(d.keys))
    content, names = frozen.encode(keys, d.fields, d.rows, cross_type_merge=cross)
    orig_names = {}
    for (ni, num), offs in m.minimal_names:
        orig_names[(z.names[ni], num)] = sorted(offs)
    ok_c = content == m.content
    ok_n = {k: sorted(v) for k, v in names.items()} == orig_names
    if verbose and not ok_c:
        n = min(len(content), len(m.content))
        first = next((i for i in range(n) if content[i] != m.content[i]), n)
        print('  len', len(content), len(m.content), 'first diff at', first)
    return ok_c, ok_n, len(d.rows)
if __name__ == '__main__':
    for fn in sys.argv[1:]:
        print(fn, check(open(fn, 'rb').read(), verbose=True))
