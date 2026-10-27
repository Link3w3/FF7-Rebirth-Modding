"""Surface carriers: the game's RMI_Surface_* shader maps (frozen content, shader list, library entries)."""
import sys, struct, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from custom_mi import find_frozen, parse_shader_map_tail
from frozen import material_shaders
from shlib import Library
sys.path.insert(0, '/work/fx1018/editor/Python')
from rebirth_fx import matcore

NAMES = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exe_hashed_names.json')))
LIB = None
PKGS = '/work/anime/pkgs/'


def nm(h):
    return NAMES.get('%016x' % h, '%016x' % h)


def lib():
    global LIB
    if LIB is None:
        LIB = Library('/data/uploads/FF7R2UProj/Saved/ModExtract/shlib/End_header.bin', 'End')
    return LIB


class Carrier:
    def __init__(self, path):
        self.path = path
        self.data = open(path, 'rb').read()
        self.mi = matcore.MaterialInstance(self.data, 'carrier')
        s0, z0 = self.mi.z.bundle_positions()[self.mi.index]
        self.ex = self.data[s0:s0 + z0]
        q = find_frozen(self.ex, self.mi.v.at + self.mi.v.size)
        self.tail = t = parse_shader_map_tail(self.ex, q)
        self.fz = self.ex[t['frozen_at']:t['frozen_at'] + t['frozen_size']]
        tab = [struct.unpack_from('<Q', self.ex, t['types_at'] + 8 * k)[0] for k in range(t['ntypes'] + t['nvfs'])]
        self.types_tab, self.vfs_tab = tab[:t['ntypes']], tab[t['ntypes']:]
        self.shaders = [dict(vf=nm(vf), type=nm(ty), perm=perm, freq=freq, platform=plat, res=res, at=s)
                        for vf, ty, perm, freq, plat, res, s in material_shaders(self.fz, self.types_tab, self.vfs_tab)]
        L = lib()
        i = L.map_index[t['resource_hash']]
        off, num, _, _ = L.map_entries[i]
        self.order = [L.indices[off + k] for k in range(num)]     # resource index -> library shader index

    def library_plan(self):
        """[[file offset, size, usize, freq, library index, hash hex]] of every shader of the map."""
        L = lib()
        out = []
        for si in self.order:
            o, size, usize, freq = L.shader_entries[si]
            out.append([L.file_offset(dict(offset=o)), size, usize, freq, si, L.shader_hashes[si].hex()])
        return out

    def base_pass_ps(self):
        return sorted(set((s['res']) for s in self.shaders if 'BasePassPS' in s['type'] or s['type'] == 'fa99734846c7227e'))


if __name__ == '__main__':
    for name in sys.argv[1:]:
        c = Carrier(PKGS + 'Renderer__MaterialInstance__Surface__%s.uasset' % name)
        print(name, 'resources', len(c.order), 'mesh shaders', len(c.shaders), 'vfs', len(c.vfs_tab))
        bp = {}
        for s in c.shaders:
            if 'BasePass' in s['type'] or s['type'] in ('fa99734846c7227e', 'a75b6d5330585563', 'ba003999e9f87ebb'):
                bp.setdefault((s['type'], s['res']), []).append(s['vf'])
        for k, v in sorted(bp.items(), key=lambda kv: kv[0][1]):
            print('   res %3d %-50s %s' % (k[1], k[0], ','.join(x.replace('VertexFactory', 'VF') for x in v)))
        plan = c.library_plan()
        print('   code bytes (compressed)', sum(p[1] for p in plan), 'uncompressed', sum(p[2] for p in plan))


def _name_list(ex, at):
    """The shader map's name table at `at` (after the property block): u32 0, u32 resources, u32 count, then per name an
    FString and a u32 hash. Returns (names, end)."""
    a, nres, n = struct.unpack_from('<III', ex, at)
    p = at + 12
    names = []
    for _ in range(n):
        ln = struct.unpack_from('<i', ex, p)[0]; p += 4
        names.append(ex[p:p + ln - 1].decode('latin1')); p += ln
        p += 4
    return names, p


def texture_parameters(c):
    """[(k, name or None, texture index)]: the Material_Texture2D_k of the carrier's shader map (its uniform expression
    set's standard 2D texture parameters, frozen at +176 of the image) with their names."""
    ex, t = c.ex, c.tail
    names, _ = _name_list(ex, c.mi.v.at + c.mi.v.size)
    # the script name patch table: (name index, number, count, offsets)
    p = t['frozen_at'] + t['frozen_size']
    nv, ns, nm_ = struct.unpack_from('<iii', ex, p); p += 12
    for _ in range(nv):
        h, n = struct.unpack_from('<QI', ex, p); p += 12 + 8 * n
    at_name = {}
    for _ in range(ns):
        idx, num, n = struct.unpack_from('<III', ex, p)
        for off in struct.unpack_from('<%dI' % n, ex, p + 12):
            at_name[off] = names[idx]
        p += 12 + 4 * n
    fz = c.fz
    v, n, m = struct.unpack_from('<qii', fz, 176)
    assert v & 1 and n == m, 'texture parameter array not at +176'
    base = 176 + (v >> 1)
    out = []
    for k in range(n):
        e = base + 28 * k
        idx, assoc, tex = struct.unpack_from('<iii', fz, e + 12)
        out.append((k, at_name.get(e), tex))
    return out
