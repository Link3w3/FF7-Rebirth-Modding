"""RM_Surface's shader map: every shader (vertex factory, type, permutation, frequency, library resource)."""
import sys, struct, json, collections
sys.path[:0] = ['/work/custmat', '/work/iostore', '/work/cs']
from zen import Zen
from custom_mi import find_frozen, parse_shader_map_tail
from frozen import material_shaders
from shlib import Library
NAMES = json.load(open('/work/custmat/exe_hashed_names.json'))
def nm(h): return NAMES.get('%016x' % h, '%016x' % h)
path = sys.argv[1]
data = open(path, 'rb').read()
z = Zen(data)
pos = z.bundle_positions()
print('exports:', [(k, e['name']) for k, e in enumerate(z.exports)][:8], len(z.exports))
mat = [k for k, e in enumerate(z.exports) if e['name'] == sys.argv[2]][0]
s0, n0 = pos[mat]
ex = data[s0:s0 + n0]
q = find_frozen(ex, 0)
t = parse_shader_map_tail(ex, q)
fz = ex[t['frozen_at']:t['frozen_at'] + t['frozen_size']]
tab = [struct.unpack_from('<Q', ex, t['types_at'] + 8 * k)[0] for k in range(t['ntypes'] + t['nvfs'])]
types_tab, vfs_tab = tab[:t['ntypes']], tab[t['ntypes']:]
shaders = material_shaders(fz, types_tab, vfs_tab)
L = Library('/data/uploads/FF7R2UProj/Saved/ModExtract/shlib/End_header.bin', 'End')
i = L.map_index[t['resource_hash']]
off, num, _, _ = L.map_entries[i]
order = [L.indices[off + k] for k in range(num)]
print('frozen image', t['frozen_size'], 'bytes; types', len(types_tab), 'vfs', len(vfs_tab), 'shaders', len(shaders), 'library resources', len(order))
c = collections.Counter((nm(ty), freq) for vf, ty, perm, freq, plat, res, s in shaders)
for (ty, freq), n in sorted(c.items(), key=lambda kv: -kv[1]):
    print('  %4d x %-60s freq %d' % (n, ty, freq))
print('vertex factories:', [nm(v) for v in vfs_tab])
rows = []
for vf, ty, perm, freq, plat, res, s in shaders:
    si = order[res]
    o, size, usize, fq = L.shader_entries[si]
    rows.append(dict(vf=nm(vf), type=nm(ty), perm=perm, freq=freq, res=res, lib=si, offset=L.file_offset(dict(offset=o)), size=size, usize=usize, hash=L.shader_hashes[si].hex()))
json.dump(rows, open(sys.argv[3], 'w'), indent=0)
print('written', sys.argv[3], len(rows))
