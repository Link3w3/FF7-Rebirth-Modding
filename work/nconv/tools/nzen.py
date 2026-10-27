"""Write a cooked zen package (UE 4.26 IoStore, as Rebirth ships them) from export data: summary, name map + hashes,
import map, export map, one export bundle, graph data, then the export data in bundle (serialize) order.

Export serial offsets count from CookedHeaderSize in export-map order, as the game's packages do; the export data is laid
out in the order the bundle serializes the exports."""
import struct, sys
sys.path[:0] = ['/work/fx1018/editor/Python']
from rebirth_fx.matcore import import_hash, _encode_name, _name_hash
from rebirth_fx.iostore_write import package_id

NULL = 0xFFFFFFFFFFFFFFFF
HASH_VERSION = 0xC1640000


def mapped(names, s):
    """FMappedName (u64) of s, adding the base name to `names` (a uwrite.Names) when needed"""
    raw = names.encode(s)
    idx, num = struct.unpack('<II', raw)
    return idx | (num << 32)


def build(package, names, imports, exports, order, flags=0x80002200, cooked_header_size=None):
    """package: '/Game/...'; names: uwrite.Names whose index 0 is the package name; imports: [u64 FPackageObjectIndex];
    exports: [dict(name, outer (0-based export index or None), cls (u64), template (u64), public (bool), oflags,
    filter, data (bytes))]; order: [(export index, 0 create | 1 serialize)] (each export twice).
    -> (package bytes, store entry dict)"""
    assert names.names[0] == package, 'name 0 must be the package name'
    n = len(exports)
    assert sorted(order) == sorted([(i, 0) for i in range(n)] + [(i, 1) for i in range(n)]), 'bundle order'
    emap = bytearray()
    sizes = [len(e['data']) for e in exports]
    for e in exports:
        mapped(names, e['name'])
    # name map first (sizes of what follows depend on it)
    nb = bytearray()
    for s in names.names:
        h, b, wide = _encode_name(s)
        nb += h
        if wide and (64 + len(nb)) & 1:
            nb.append(0)
        nb += b
    nm_off, nm_size = 64, len(nb)
    p = nm_off + nm_size
    pad = (8 - p % 8) % 8
    nh_off = p + pad
    hashes = struct.pack('<Q', HASH_VERSION) + b''.join(struct.pack('<Q', _name_hash(s)) for s in names.names)
    imp = b''.join(struct.pack('<Q', x) for x in imports)
    imp_off = nh_off + len(hashes)
    exp_off = imp_off + len(imp)
    eb_off = exp_off + 72 * n
    bundles = struct.pack('<II', 0, 2 * n) + b''.join(struct.pack('<II', i, c) for i, c in order)
    # graph: every imported package (package imports), each bundle 0 -> 0
    pkgs = sorted({imp_pkg for imp_pkg in (e.get('_pkg') for e in []) if imp_pkg})
    graph_off = eb_off + len(bundles)
    return nb, pad, hashes, imp, bundles, (nm_off, nm_size, nh_off, imp_off, exp_off, eb_off, graph_off), sizes


def write(package, names, imports, imported_packages, exports, order, flags=0x80002200):
    """the zen package bytes and its package store entry (for the container header)"""
    nb, pad, hashes, imp, bundles, offs, sizes = build(package, names, imports, exports, order, flags)
    nm_off, nm_size, nh_off, imp_off, exp_off, eb_off, graph_off = offs
    pids = sorted(set(p if isinstance(p, int) else package_id(p) for p in imported_packages))   # paths or package ids
    gr = bytearray(struct.pack('<i', len(pids)))
    for pid in pids:
        gr += struct.pack('<Qi', pid, 1) + struct.pack('<ii', 0, 0)
    header_end = graph_off + len(gr)
    cooked_header_size = header_end
    # serial offsets in export-map order
    offsets = []
    at = cooked_header_size
    for s in sizes:
        offsets.append(at); at += s
    emap = bytearray()
    for i, e in enumerate(exports):
        outer = NULL if e['outer'] is None else e['outer']
        gimp = import_hash(e['path']) if e.get('public') else NULL
        emap += struct.pack('<QQQQQQQQIB3x', offsets[i], sizes[i], mapped(names, e['name']), outer, e['cls'], NULL,
                            e['template'], gimp, e['oflags'], e['filter'])
    assert len(emap) == 72 * len(exports)
    summary = struct.pack('<QQIIiiiiiiiiii', 0, 0, flags, cooked_header_size, nm_off, nm_size, nh_off, len(hashes),
                          imp_off, exp_off, eb_off, graph_off, len(gr), 0)
    out = bytearray(summary) + nb + b'\0' * pad + hashes + imp + emap + bundles + gr
    assert len(out) == header_end, (len(out), header_end)
    for i, c in order:
        if c == 1:
            out += exports[i]['data']
    entry = dict(id=package_id(package), size=len(out), export_count=len(exports), export_bundle_count=1,
                 imports=pids, load_order=0)
    return bytes(out), entry
