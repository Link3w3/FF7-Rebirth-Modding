"""A custom material for FINAL FANTASY VII REBIRTH: a copy of one of the game's material instances (a 'carrier': its
static switches give a compiled shader map) under a new name, whose shader map carries its own shader code inline
(bShareCode = false) instead of pointing at the game's shader library, with some of those shaders replaced."""
import hashlib
import struct

from .. import matcore
from ..zen import Zen


def export_path(z, i, package):
    """'/Game/Pkg.Object:Sub.Sub2' of export i."""
    chain = []
    j = i
    for _ in range(64):
        e = z.exports[j]
        chain.append(e['name'])
        o = e['outer']
        if o == 0xFFFFFFFFFFFFFFFF or (o >> 62) != 0 or o >= len(z.exports):
            break
        j = o
    chain.reverse()
    return package + '.' + chain[0] + ''.join((':' if k == 0 else '.') + c for k, c in enumerate(chain[1:]))


def rename_package(data, new_package, rename_main=True):
    """The package under a new name: its package name (and, rename_main, its main export's name) and every public export's
    global import index (the hash of its path) to match."""
    z = Zen(data)
    old_package = z.mapped(z.name_mapped)
    old_short = old_package.rsplit('/', 1)[-1]
    new_short = new_package.rsplit('/', 1)[-1]
    names = [new_package if n == old_package else (new_short if (rename_main and n == old_short) else n) for n in z.names]
    out = matcore.rebuild(data, names=names)
    z2 = Zen(out)
    exports = bytearray(out[z2.exp_off:z2.eb_off])
    for i, e in enumerate(z2.exports):
        if e['global_import'] != 0xFFFFFFFFFFFFFFFF:
            struct.pack_into('<Q', exports, i * 72 + 56, matcore.import_hash(export_path(z2, i, new_package)))
    return out[:z2.exp_off] + bytes(exports) + out[z2.eb_off:]


def replace_import(data, old_object_path, new_object_path):
    """Every reference to old_object_path (an import) now to new_object_path: the import map entry, the graph data's
    package, and the names."""
    from ..iostore_write import package_id
    z = Zen(data)
    oh, nh = matcore.import_hash(old_object_path), matcore.import_hash(new_object_path)
    if oh not in z.imports:
        raise KeyError(old_object_path + ' is not imported')
    imports = [nh if x == oh else x for x in z.imports]
    old_pkg, new_pkg = old_object_path.split('.')[0], new_object_path.split('.')[0]
    graph = matcore.graph_packages(data)
    still = any(v for v in (matcore.resolve_imports(z) or {}).values() if v and v.split('.')[0] == old_pkg and v != old_object_path)
    graph2 = []
    for pid, arcs in graph:
        if pid == package_id(old_pkg) and not still:
            continue
        graph2.append((pid, arcs))
    if package_id(new_pkg) not in [g[0] for g in graph2]:
        graph2.append((package_id(new_pkg), [(0, 0)]))
    graph2.sort(key=lambda g: g[0])
    names = list(z.names)
    for nm in (new_pkg, new_object_path.rsplit('.', 1)[-1]):
        if nm not in names:
            names.append(nm)
    return matcore.rebuild(data, names=names, imports=imports, graph=graph2)


def shader_map_tail(export_bytes):
    """(position of bShareCode, resource hash) of a single-resource inline shader map at the end of the export."""
    p = len(export_bytes) - 24
    share = struct.unpack_from('<I', export_bytes, p)[0]
    if share != 1:
        raise ValueError('the shader map does not end with a library reference (bShareCode %d)' % share)
    return p, export_bytes[p + 4:]


def inline_code(shaders):
    """FShaderMapResourceCode: shaders = [dict(hash=20 bytes, code=bytes (maybe compressed), usize=int, freq=int)]."""
    h = hashlib.sha1()
    for s in shaders:
        h.update(s['hash'])
    out = bytearray(h.digest())
    out += struct.pack('<i', len(shaders)) + b''.join(s['hash'] for s in shaders)
    out += struct.pack('<i', len(shaders))
    for s in shaders:
        out += struct.pack('<i', len(s['code'])) + s['code'] + struct.pack('<iB', s['usize'], s['freq'])
    return bytes(out)


def with_inline_shaders(data, shaders):
    """The material instance package with its shader map's code inline (replacing the library reference)."""
    mi = matcore.MaterialInstance(data, 'carrier')
    z = mi.z
    start, size = z.bundle_positions()[mi.index]
    ex = data[start:start + size]
    p, _ = shader_map_tail(ex)
    new_ex = ex[:p] + struct.pack('<I', 0) + inline_code(shaders)
    return matcore.rebuild(data, export_index=mi.index, new_export=new_ex)


def parse_shader_map_tail(ex, q):
    """From the frozen image's size field at q to the end of the export: the image, its vtable / script name / minimal
    name patch tables, the pointer table (shader and vertex factory types, layout dependencies) and the code reference.
    Returns a dict, or None when the bytes do not fit that structure exactly."""
    L = len(ex)
    try:
        F = struct.unpack_from('<I', ex, q)[0]
        p = q + 4 + F
        nv, ns, nm = struct.unpack_from('<iii', ex, p); p += 12
        if min(nv, ns, nm) < 0 or max(nv, ns, nm) > 100000:
            return None
        for _ in range(nv):
            h, n = struct.unpack_from('<QI', ex, p); p += 12 + 8 * n
        for _ in range(ns + nm):
            n = struct.unpack_from('<I', ex, p + 8)[0]; p += 12 + 4 * n
        nt, nvf = struct.unpack_from('<ii', ex, p); p += 8
        if not (0 <= nt < 4096 and 0 <= nvf < 512):
            return None
        types_at = p; p += 8 * (nt + nvf)
        nd = struct.unpack_from('<i', ex, p)[0]; p += 4
        if not 0 <= nd < 4096:
            return None
        deps_at = p; p += 32 * nd
        share = struct.unpack_from('<I', ex, p)[0]
        if share == 1 and p + 24 == L:
            return dict(frozen_at=q + 4, frozen_size=F, types_at=types_at, ntypes=nt, nvfs=nvf, deps_at=deps_at, ndeps=nd,
                        share_at=p, resource_hash=ex[p + 4:p + 24], id_hash_at=q - 28)
    except struct.error:
        return None
    return None


def find_frozen(export_bytes, start=0):
    """Position of the frozen shader map's size field (the one whose following tables run exactly to the end)."""
    for q in range(start, len(export_bytes) - 16):
        if parse_shader_map_tail(export_bytes, q):
            return q
    raise ValueError('no frozen shader map found')


def unique_shader_map_id(data, seed):
    """The material's cooked shader map id hash (20 bytes before the frozen image's layout parameters) changed to a hash
    of `seed`, so its shader map never takes the place of the game's material's in the engine's registry."""
    mi = matcore.MaterialInstance(data, 'x')
    start, size = mi.z.bundle_positions()[mi.index]
    ex = bytearray(data[start:start + size])
    q = find_frozen(bytes(ex), mi.v.at + mi.v.size)
    at = q - 28
    ex[at:at + 20] = hashlib.sha1(seed.encode()).digest()
    return matcore.rebuild(data, export_index=mi.index, new_export=bytes(ex)), at


def wrap_shader(game_blob, dxbc):
    """A game shader blob (resource table + DXBC + optional data) with its DXBC container replaced."""
    from .dxbc import container
    at = game_blob.find(b'DXBC')
    c = container(game_blob, at)
    return game_blob[:at] + dxbc + game_blob[at + c['total']:]
