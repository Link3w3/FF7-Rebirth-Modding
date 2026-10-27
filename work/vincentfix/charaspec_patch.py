"""Rows of a CharaSpec zen package (the game's frozen data object), edited and written back in the same format.
Retail packages use unversioned properties (6-byte prefix); editor cooks may use tagged properties (an 8-byte "None"
terminator, then bHasGuid: 12-byte prefix). The prefix is kept as it is.
    decode(data) -> (z, e, m, d);  encode(data, z, e, m, keys, fields, rows) -> package bytes"""
import struct, sys
sys.path.insert(0, '/work/cs'); sys.path.insert(0, '/work/charaspecmod')
from zen import Zen
from mmimg import MMAsset
import frozen
from build_charaspec import build_package

def prefix_size(z, e):
    index, number = struct.unpack_from('<II', e, 0)
    if index < len(z.names) and z.names[index] == 'None' and number == 0:
        return 12   # tagged properties: "None" terminator + bHasGuid
    return 6        # unversioned header (one empty fragment) + bHasGuid

def decode(data):
    z = Zen(data)
    e = z.export_data(0)
    m = MMAsset(e, z.names, prefix_size(z, e))
    at = {}
    for (ni, num), offs in m.minimal_names:
        for o in offs:
            at[o] = (z.names[ni], num)
    d = frozen.decode(m.content, at)
    return z, e, m, d

def build_export(m, content, names, name_index):
    entries = []
    for (base, num), offs in names.items():
        if base not in name_index:
            raise KeyError('name %r is not in the package name map' % base)
        entries.append((name_index[base], num, sorted(offs)))
    entries.sort(key=lambda t: (t[0], t[1]))
    assert m.nvt == 0 and m.nsn == 0, 'vtables / script names not handled'
    out = bytearray(m.prefix)
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

def encode(data, z, e, m, keys, fields, rows):
    content, names = frozen.encode(keys, fields, rows)
    name_index = {n: i for i, n in enumerate(z.names)}
    return build_package(data, z, build_export(m, content, names, name_index))

def field_index(d):
    return {f[0][0]: i for i, f in enumerate(d.fields)}
