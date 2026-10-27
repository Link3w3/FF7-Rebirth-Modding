"""Rebuild the game's DataObject/Resident/CharaSpec zen package in the retail format with edited rows."""
import struct, sys, hashlib
sys.path.insert(0, '/work/cs')
from zen import Zen
from mmimg import MMAsset
import frozen

RETAIL = '/work/cs/raw/retail_CharaSpec.uasset'

def load_retail():
    data = open(RETAIL, 'rb').read()
    z = Zen(data)
    e = z.export_data(0)
    m = MMAsset(e, z.names, 6)
    at = {}
    for (ni, num), offs in m.minimal_names:
        for o in offs:
            at[o] = (z.names[ni], num)
    d = frozen.decode(m.content, at)
    return data, z, e, m, d

def build_export(e_template, m, content, names, name_index):
    entries = []
    for (base, num), offs in names.items():
        if base not in name_index:
            raise KeyError('name %r is not in the retail name map' % base)
        entries.append((name_index[base], num, sorted(offs)))
    entries.sort(key=lambda t: (t[0], t[1]))
    out = bytearray(e_template[:6])                       # empty unversioned header + bHasGuid=0
    out += struct.pack('<IIHH', len(content), m.size, m.idk, m.padding)
    out += m.pad_bytes
    assert len(out) == m.content_off
    out += content
    out += struct.pack('<III', 0, 0, len(entries))
    for ni, num, offs in entries:
        out += struct.pack('<iiI', ni, num, len(offs))
        out += struct.pack('<%dI' % len(offs), *offs)
    out += m.trailer
    return bytes(out)

def build_package(data, z, export):
    header = bytearray(data[:z.header_end])
    struct.pack_into('<Q', header, z.exp_off + 8, len(export))   # export serial size
    return bytes(header) + export

def rebuild(rows_fn=None):
    data, z, e, m, d = load_retail()
    keys = [k[0] for k in d.keys]
    rows = [list(r) for r in d.rows]
    if rows_fn:
        rows_fn(keys, d.fields, rows)
    content, names = frozen.encode(keys, d.fields, rows)
    name_index = {n: i for i, n in enumerate(z.names)}
    export = build_export(e, m, content, names, name_index)
    return build_package(data, z, export), (data, e)

if __name__ == '__main__':
    pkg, (data, e) = rebuild()
    print('unmodified rebuild identical to retail:', pkg == data, len(pkg), len(data))
