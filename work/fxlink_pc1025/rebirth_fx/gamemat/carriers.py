"""Surface carriers: one of the game's RMI_Surface_* material instances (a cooked package), its frozen shader map (the
shaders it has: type, vertex factory, resource index) and the order of its shaders in the game's shader library."""
import gzip
import json
import os
import struct

from .. import matcore
from .custom_mi import find_frozen, parse_shader_map_tail
from .frozen import material_shaders

HERE = os.path.dirname(os.path.abspath(__file__))
_NAMES = None


def nm(h):
    """The name of an FHashedName (shader types, vertex factories) as the game's executable has it."""
    global _NAMES
    if _NAMES is None:
        with gzip.open(os.path.join(HERE, 'names.json.gz'), 'rt', encoding='utf-8') as f:
            _NAMES = json.load(f)
    return _NAMES.get('%016x' % h, '%016x' % h)


class Carrier(object):
    def __init__(self, data, library=None, label='carrier'):
        self.data = data
        self.mi = matcore.MaterialInstance(self.data, label)
        s0, z0 = self.mi.z.bundle_positions()[self.mi.index]
        self.ex = self.data[s0:s0 + z0]
        q = find_frozen(self.ex, self.mi.v.at + self.mi.v.size)
        self.tail = t = parse_shader_map_tail(self.ex, q)
        self.fz = self.ex[t['frozen_at']:t['frozen_at'] + t['frozen_size']]
        tab = [struct.unpack_from('<Q', self.ex, t['types_at'] + 8 * k)[0] for k in range(t['ntypes'] + t['nvfs'])]
        self.types_tab, self.vfs_tab = tab[:t['ntypes']], tab[t['ntypes']:]
        self.shaders = [dict(vf=nm(vf), type=nm(ty), perm=perm, freq=freq, platform=plat, res=res, at=s)
                        for vf, ty, perm, freq, plat, res, s in material_shaders(self.fz, self.types_tab, self.vfs_tab)]
        self.resource_hash = t['resource_hash']
        self.order = library.order(self.resource_hash) if library is not None else None

    def base_pass_ps(self):
        return sorted(set((s['res']) for s in self.shaders if 'BasePassPS' in s['type'] or s['type'] == 'fa99734846c7227e'))


def _name_list(ex, at):
    """The shader map's name table at `at` (after the property block): u32 0, u32 resources, u32 count, then per name an
    FString and a u32 hash. Returns (names, end)."""
    a, nres, n = struct.unpack_from('<III', ex, at)
    p = at + 12
    names = []
    for _ in range(n):
        ln = struct.unpack_from('<i', ex, p)[0]
        p += 4
        names.append(ex[p:p + ln - 1].decode('latin1'))
        p += ln
        p += 4
    return names, p


def texture_parameters(c):
    """[(k, name or None, texture index)]: the Material_Texture2D_k of the carrier's shader map (its uniform expression
    set's standard 2D texture parameters, frozen at +176 of the image) with their names."""
    ex, t = c.ex, c.tail
    names, _ = _name_list(ex, c.mi.v.at + c.mi.v.size)
    # the script name patch table: (name index, number, count, offsets)
    p = t['frozen_at'] + t['frozen_size']
    nv, ns, nm_ = struct.unpack_from('<iii', ex, p)
    p += 12
    for _ in range(nv):
        h, n = struct.unpack_from('<QI', ex, p)
        p += 12 + 8 * n
    at_name = {}
    for _ in range(ns):
        idx, num, n = struct.unpack_from('<III', ex, p)
        for off in struct.unpack_from('<%dI' % n, ex, p + 12):
            at_name[off] = names[idx]
        p += 12 + 4 * n
    fz = c.fz
    v, n, m = struct.unpack_from('<qii', fz, 176)
    if not (v & 1 and n == m):
        raise ValueError('the texture parameter array is not at +176 of the shader map')
    base = 176 + (v >> 1)
    out = []
    for k in range(n):
        e = base + 28 * k
        idx, assoc, tex = struct.unpack_from('<iii', fz, e + 12)
        out.append((k, at_name.get(e), tex))
    return out
