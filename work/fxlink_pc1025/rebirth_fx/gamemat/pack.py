"""A mod container of new packages (IoStore .utoc/.ucas + the stub .pak), as the game's own containers hold packages.

Store entries: export and bundle counts from the package itself (checked against the game package it was made from, for
copies of game packages), imported packages = the package's graph (as the game's own entries have them), load order
from the game package it was made from or given."""
import os
import shutil
import struct

from .. import iostore_write as W
from .. import matcore
from ..zen import Zen

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), 'data')
MOUNT = '../../../End/Content/'


def package_name(data):
    z = Zen(data)
    return z.mapped(z.name_mapped)


def bundle_count(z):
    total = 2 * len(z.exports)
    seen, p, n = 0, z.eb_off, 0
    while seen < total:
        first, count = struct.unpack_from('<II', z.d, p)
        p += 8
        seen += count
        n += 1
    return n


def build(items, out_dir, mod_name, retail):
    """items: [dict(data=zen bytes, bulk=bytes or None, like=game package name or None, load_order=int or None)];
    retail: {package id: store entry} of the game's containers (for `like`, and to refuse replacing game packages).
    Writes <out_dir>/<mod_name>.utoc/.ucas/.pak; returns (paths, entries)."""
    if not mod_name.endswith('_P'):
        raise ValueError('a mod container needs the _P suffix')
    chunks, entries = [None], []
    seen = set()
    for it in items:
        data = it['data']
        z = Zen(data)
        name = package_name(data)
        if not name.startswith('/Game/'):
            raise ValueError(name + ': only /Game packages')
        pid = W.package_id(name)
        if pid in seen:
            raise ValueError(name + ' is in the mod twice')
        seen.add(pid)
        if pid in retail and not it.get('replace'):
            raise ValueError(name + ' is a game package: this mod adds new packages only')
        bundles = bundle_count(z)
        load_order = it.get('load_order')
        if it.get('like'):
            e = retail.get(W.package_id(it['like']))
            if e is None:
                raise KeyError(it['like'] + ' is not among the game packages read')
            if e['export_count'] != len(z.exports) or e['export_bundle_count'] != bundles:
                raise ValueError('%s: %d exports / %d bundles, %s has %d / %d' % (name, len(z.exports), bundles, it['like'],
                                                                                 e['export_count'], e['export_bundle_count']))
            if load_order is None:
                load_order = e['load_order']
        imports = [g for g, arcs in matcore.graph_packages(data)]
        rel = name[len('/Game/'):]
        chunks.append(dict(id64=pid, type=2, data=data, path=rel + '.uasset'))
        if it.get('bulk'):
            chunks.append(dict(id64=pid, type=3, data=it['bulk'], path=rel + '.ubulk'))
        entries.append(dict(id=pid, name=name, size=len(data), export_count=len(z.exports), export_bundle_count=bundles,
                            load_order=load_order or 0, imports=imports))
    cid = W.container_id_from_name(mod_name)
    chunks[0] = dict(id64=cid, type=10, data=W.container_header(cid, entries), path=None)
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    base = os.path.join(out_dir, mod_name)
    W.write_container(base, mod_name, chunks, mount=MOUNT)
    shutil.copy(os.path.join(DATA, 'empty_P.pak'), base + '.pak')
    return [base + '.utoc', base + '.ucas', base + '.pak'], entries


def read_back(utoc):
    """{(chunk id64, type): bytes} of a container this module wrote (uncompressed blocks)."""
    with open(utoc, 'rb') as f:
        data = f.read()
    with open(utoc[:-5] + '.ucas', 'rb') as f:
        ucas = f.read()
    hdr_size, n, nblocks, entry_size, ncm, cmlen, block_size, dir_size, parts = struct.unpack_from('<IIIIIIIII', data, 20)
    p = hdr_size
    ids = []
    for _ in range(n):
        cid, idx, pad, typ = struct.unpack_from('<QHBB', data, p)
        ids.append((cid, typ))
        p += 12
    offlen = []
    for _ in range(n):
        b = data[p:p + 10]
        p += 10
        offlen.append((int.from_bytes(b[0:5], 'big'), int.from_bytes(b[5:10], 'big')))
    blocks = []
    for _ in range(nblocks):
        b = data[p:p + 12]
        p += 12
        blocks.append((int.from_bytes(b[0:5], 'little'), int.from_bytes(b[5:8], 'little'), int.from_bytes(b[8:11], 'little'), b[11]))
    out = {}
    for (cid, typ), (off, ln) in zip(ids, offlen):
        bi = off // block_size
        chunk = bytearray()
        while len(chunk) < ln:
            pos, cs, us, method = blocks[bi]
            if method != 0 or cs != us:
                raise ValueError('a compressed block: this reader takes the uncompressed containers it writes')
            chunk += ucas[pos:pos + cs]
            bi += 1
        out[(cid, typ)] = bytes(chunk[:ln])
    return out
