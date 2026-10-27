"""Every RMI_Surface_*: static switches, texture parameters, base property overrides, and its base pass pixel shaders."""
import sys, struct, json, glob, os, collections
sys.path[:0] = ['/work/custmat', '/work/iostore', '/work/cs', '/work/fx1018/editor/Python']
from rebirth_fx import matcore
from custom_mi import find_frozen, parse_shader_map_tail
from frozen import material_shaders
from shlib import Library
NAMES = json.load(open('/work/custmat/exe_hashed_names.json'))
def nm(h): return NAMES.get('%016x' % h, '%016x' % h)
L = Library('/data/uploads/FF7R2UProj/Saved/ModExtract/shlib/End_header.bin', 'End')
BASEPASS_PS = 'fa99734846c7227e'
out = []
for path in sorted(glob.glob('/work/rmsurf/rmi/p*/pkgs/Renderer__MaterialInstance__Surface__*.uasset')):
    data = open(path, 'rb').read()
    name = path.rsplit('__', 1)[1][:-7]
    try:
        mi = matcore.MaterialInstance(data, name)
    except Exception as e:
        print('!!', name, e); continue
    s0, n0 = mi.z.bundle_positions()[mi.index]
    ex = data[s0:s0 + n0]
    rec = dict(name=name, parent=mi.parent, switches={s['name']: s['value'] for s in mi.static_switches},
               params=[(p['kind'], p['name'], p['value']) for p in mi.params], permutation=mi.has_static_permutation)
    props = mi.v.value
    bpo = props.get('BasePropertyOverrides')
    if bpo is not None:
        rec['overrides'] = {k: (v.value if not hasattr(v.value, 'items') else '?') for k, v in bpo.value.items()}
    try:
        q = find_frozen(ex, mi.v.at + mi.v.size)
        t = parse_shader_map_tail(ex, q)
        fz = ex[t['frozen_at']:t['frozen_at'] + t['frozen_size']]
        tab = [struct.unpack_from('<Q', ex, t['types_at'] + 8 * k)[0] for k in range(t['ntypes'] + t['nvfs'])]
        types_tab, vfs_tab = tab[:t['ntypes']], tab[t['ntypes']:]
        shaders = material_shaders(fz, types_tab, vfs_tab)
        i = L.map_index[t['resource_hash']]
        off, num, _, _ = L.map_entries[i]
        order = [L.indices[off + k] for k in range(num)]
        bp = {}
        for vf, ty, perm, freq, plat, res, s in shaders:
            if nm(ty) == BASEPASS_PS:
                si = order[res]
                o, size, usize, fq = L.shader_entries[si]
                bp[nm(vf)] = dict(lib=si, offset=L.file_offset(dict(offset=o)), size=size, usize=usize, freq=fq, hash=L.shader_hashes[si].hex())
        rec['shaders'] = len(shaders)
        rec['vfs'] = [nm(v) for v in vfs_tab]
        rec['basepass'] = bp
    except Exception as e:
        rec['error'] = str(e)[:200]
    out.append(rec)
json.dump(out, open('rmi_surface.json', 'w'), indent=1)
sw = collections.Counter()
for r in out:
    for k, v in r['switches'].items():
        if v: sw[k] += 1
print(len(out), 'RMI_Surface;', sum(1 for r in out if r.get('basepass')), 'with base pass shaders')
print('switches on (count):', sw.most_common())
allsw = sorted({k for r in out for k in r['switches']})
print(len(allsw), 'switch names:', allsw)
libs = {v['lib'] for r in out for v in (r.get('basepass') or {}).values()}
print('unique base pass PS:', len(libs))
