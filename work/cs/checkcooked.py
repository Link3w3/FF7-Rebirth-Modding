import sys, struct
from legacy import Legacy
from mmimg import MMAsset
from zen import Zen
import frozen

def load_legacy(path_uasset, path_uexp=None):
    a = open(path_uasset, 'rb').read()
    x = open(path_uexp, 'rb').read() if path_uexp else b''
    return Legacy(a, x)

def frozen_of_legacy(L):
    e = L.export_data(0)
    # property block: unversioned header fragments or tagged "None"
    if L.flags & 0x2000:
        p = 0
        while True:
            frag = struct.unpack_from('<H', e, p)[0]; p += 2
            assert (frag >> 9) == 0, 'property values present'
            if frag & 0x100: break
    else:
        p = 8
    has_guid = struct.unpack_from('<I', e, p)[0]; p += 4
    if has_guid: p += 16
    m = MMAsset(e, L.names, p)
    names = {}
    for (ni, num), offs in m.minimal_names:
        names[(L.names[ni], num)] = sorted(offs)
    return e, m, names

def retail():
    z = Zen(open('raw/retail_CharaSpec.uasset', 'rb').read())
    m = MMAsset(z.export_data(0), z.names, 6)
    names = {}
    for (ni, num), offs in m.minimal_names:
        names[(z.names[ni], num)] = sorted(offs)
    return m, names

if __name__ == '__main__':
    L = load_legacy(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print('flags', hex(L.flags), 'memmapped', bool(L.flags & 0x00800000), 'unversioned', bool(L.flags & 0x2000), 'names', len(L.names), 'exports', [(e['name'], e['size']) for e in L.exports])
    print('imports', L.imports)
    e, m, names = frozen_of_legacy(L)
    print('export', len(e), 'frozen', m.frozen_size, 'hdr', m.size, m.idk, 'pad', m.padding, 'content_off', m.content_off, 'end', m.end, 'trailer', len(m.trailer), 'export%16', len(e) % 16)
    rm, rnames = retail()
    print('content == retail:', m.content == rm.content, '| names == retail:', names == rnames)
