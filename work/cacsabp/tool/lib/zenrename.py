"""Rename names in a UE4.26 zen package (name map + hashes) and rebuild its header offsets."""
import struct, sys
sys.path.insert(0, '/work/cs')
from zen import Zen
from cityhash import CityHash64

def encode_name(s):
    try:
        b = s.encode('ascii'); wide = False
    except UnicodeEncodeError:
        b = s.encode('utf-16-le'); wide = True
    n = len(s)
    h = struct.pack('>H', (0x8000 if wide else 0) | n)
    return h, b, wide

def name_hash(s):
    try:
        return CityHash64(s.lower().encode('ascii'))
    except UnicodeEncodeError:
        return CityHash64(s.lower().encode('utf-16-le'))

def rebuild(data, renames, export_global_imports=None):
    z = Zen(data)
    names = [renames.get(n, n) for n in z.names]
    # name batch
    nb = bytearray()
    for s in names:
        h, b, wide = encode_name(s)
        nb += h
        if wide and (64 + len(nb)) & 1:
            nb.append(0)
        nb += b
    nm_off = 64
    nm_size = len(nb)
    p = nm_off + nm_size
    pad = (8 - p % 8) % 8
    nh_off = p + pad
    hashes = struct.pack('<Q', z.hash_version) + b''.join(struct.pack('<Q', name_hash(s)) for s in names)
    nh_size = len(hashes)
    old = data
    imports = old[z.imp_off:z.exp_off]
    exports = bytearray(old[z.exp_off:z.eb_off])
    bundles = old[z.eb_off:z.graph_off]
    graph = old[z.graph_off:z.graph_off + z.graph_size]
    if export_global_imports:
        for i, gi in export_global_imports.items():
            struct.pack_into('<Q', exports, i * 72 + 56, gi)
    imp_off = nh_off + nh_size
    exp_off = imp_off + len(imports)
    eb_off = exp_off + len(exports)
    graph_off = eb_off + len(bundles)
    header_end = graph_off + len(graph)
    summary = struct.pack('<QQIIiiiiiiiiii', z.name_mapped, z.srcname_mapped, z.flags, z.cooked_header_size, nm_off, nm_size, nh_off, nh_size,
                          imp_off, exp_off, eb_off, graph_off, len(graph), z.pad)
    out = bytearray(summary)
    out += nb
    out += b'\0' * pad
    out += hashes + imports + exports + bundles + graph
    assert len(out) == header_end
    out += old[z.header_end:]
    return bytes(out)

def graph_imports(data):
    z = Zen(data)
    g = data[z.graph_off:z.graph_off + z.graph_size]
    n = struct.unpack_from('<i', g, 0)[0]; o = 4; ids = []
    for _ in range(n):
        pid, arcs = struct.unpack_from('<Qi', g, o); o += 12 + arcs * 8
        ids.append(pid)
    return ids
