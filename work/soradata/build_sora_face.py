"""SoraFace_P: Sora's facial set (/Game/Motion/Player/PC0000_00_Sora_KH2/Facial00: 35 face animations from his KH3 face
animations, the blend spaces F_Brow, F_Emotion01 and F_Eyelid_move01, the set itself) and his facial control rig
(/Game/Character/Player/PC0000_00_Sora_KH2/Model/PC0000_00_S_FCR), cooked by the End editor and converted by retoc,
made ready for the game as SoraAssets_P is (build_sora_assets: animations laid out as the game reads them), and:
  * each blend space's grid (GridSamples, what the game blends by) taken from Cloud's own blend space of that name
    (/Game/Motion/Player/PC0000_Cloud/Facial00/<name>): ours has the same samples at the same places in the same order
    and the same axes, so its grid is the same, and the editor (no resampling from Python) cooked a stale one.

    build_sora_face.py <retoc .utoc> <out dir>
"""
import hashlib
import os
import shutil
import struct
import sys

sys.path[:0] = ['/work/soradata', '/work/fx1018/editor/Python', '/work/iostore', '/work/cs']
import build_sora_assets as B                # noqa: E402
from build_sora_assets import A, W, Toc, Zen, hdr, Package   # noqa: E402
from rebirth_fx import matcore               # noqa: E402

CLOUD_BS = '/work/fx1018/pkgs/Motion__Player__PC0000_Cloud__Facial00__%s.uasset'
BLEND_SPACES = ('F_Brow', 'F_Emotion01', 'F_Eyelid_move01')


def bs_export(data, label):
    pkg = Package(data, label)
    hits = [(i, v) for i, (cls, v, base) in pkg.exports.items() if cls == 'BlendSpace']
    assert len(hits) == 1, (label, hits)
    return pkg, hits[0][0], hits[0][1]


def samples(pkg, v):
    imps = matcore.resolve_imports(pkg.z)
    out = []
    for s in v.value['SampleData'].value:
        sv = s.value if hasattr(s, 'value') else s
        a = sv['Animation'].value
        name = imps.get(-a - 1, '').rsplit('.', 1)[-1]
        val = sv['SampleValue'].value if 'SampleValue' in sv else 0
        val = tuple(round(float(x), 4) for x in val) if isinstance(val, (list, tuple)) else (0.0, 0.0, 0.0)
        out.append((name, val))
    return out


def axes(v):
    out = []
    for k in ('BlendParameters[0]', 'BlendParameters[1]'):
        p = v.value[k].value if k in v.value else {}
        g = lambda f, d: (p[f].value if f in p and hasattr(p[f], 'value') else p.get(f, d)) if p else d
        out.append((float(g('Min', 0.0)), float(g('Max', 100.0)), int(g('GridNum', 4))))
    return out


def grid_bytes(data, pkg, index, v):
    ex_start, ex_size = pkg.z.bundle_positions()[index]
    x = v.value['GridSamples']
    return data[ex_start + x.at:ex_start + x.at + x.size]


def patch_grid(data, name, label):
    cloud = open(CLOUD_BS % name, 'rb').read()
    cpkg, cidx, cv = bs_export(cloud, 'Cloud ' + name)
    pkg, idx, v = bs_export(data, label)
    mine, theirs = samples(pkg, v), samples(cpkg, cv)
    assert mine == theirs, (label, mine, theirs)
    assert axes(v) == axes(cv), (label, axes(v), axes(cv))
    new_grid = grid_bytes(cloud, cpkg, cidx, cv)
    ex_start, ex_size = pkg.z.bundle_positions()[idx]
    ex = data[ex_start:ex_start + ex_size]
    x = v.value['GridSamples']
    old_n = struct.unpack_from('<i', ex, x.at)[0]
    new_ex = ex[:x.at] + new_grid + ex[x.at + x.size:]
    out = matcore.replace_export(data, idx, new_ex)
    bpkg, bidx, bv = bs_export(out, label)
    assert grid_bytes(out, bpkg, bidx, bv) == new_grid and samples(bpkg, bv) == mine and axes(bv) == axes(v), label
    return out, old_n, struct.unpack_from('<i', new_grid, 0)[0]


def main(utoc, out, name='SoraFace_P'):
    chunks, store = B.read(utoc)
    ids = set(c['id64'] for c in chunks)
    entries = []
    report = dict(anims=0, blend_spaces=0, blocks=0, grids={})
    for c in chunks:
        if c['type'] != 2:
            continue
        e = B.entry(c, store[c['id64']])
        base = c['path'].rsplit('/', 1)[-1][:-len('.uasset')]
        if c['path'].startswith('Motion/Player/PC0000_00_Sora_KH2/Facial00/') and base in BLEND_SPACES:
            c['data'], was, now = patch_grid(c['data'], base, c['path'])
            e['size'] = len(c['data'])
            report['grids'][base] = '%d -> %d grid samples (Cloud\'s)' % (was, now)
        z = Zen(c['data'])
        if z.flags & A.PKG_ALIGNED_EXPORTS:
            c['data'] = A.realign(c['data'])
            blocks = B.verify_anim(c['data'], c['path'], need_block=False)
            if any(cls == 'AnimSequence' for cls, v, b in Package(c['data'], c['path']).exports.values()):
                assert blocks >= 1, (c['path'], 'no ACL block')
            if blocks:
                report['anims'] += 1
                report['blocks'] += blocks
            else:
                report['blend_spaces'] += 1
            e['size'] = len(c['data']) | (A.SHIFT << 60)
        entries.append(e)
    assert len(report['grids']) == len(BLEND_SPACES), report['grids']
    B.load_orders(chunks, entries)
    os.makedirs(out, exist_ok=True)
    cid = W.container_id_from_name(name)
    allc = [dict(id64=cid, type=10, data=W.container_header(cid, entries), path=None)] + chunks
    base = os.path.join(out, name)
    W.write_container(base, name, allc, mount=B.MOUNT)
    shutil.copy(utoc[:-5] + '.pak', base + '.pak')
    back = Toc(base + '.utoc')
    assert back.entries == len(allc)
    cid2, ents = hdr.parse_header(back.read(0))
    assert cid2 == cid and len(ents) == len(entries)
    by = {e['id']: e for e in entries}
    for i in range(1, back.entries):
        c = allc[i]
        assert back.read(i) == c['data'] and back.chunk_id64(i) == c['id64'] and back.chunk_type(i) == c['type'], c['path']
        assert back.files.get(i) == B.MOUNT + c['path'], (back.files.get(i), c['path'])
        e, b = by[c['id64']], ents[c['id64']]
        assert (b['size'], b['export_count'], b['export_bundle_count'], b['load_order'], list(b['imports'])) == \
               (e['size'], e['export_count'], e['export_bundle_count'], e['load_order'], e['imports']), c['path']
    report['packages'] = len(entries)
    report['files'] = {ext: (os.path.getsize(base + '.' + ext), hashlib.md5(open(base + '.' + ext, 'rb').read()).hexdigest())
                       for ext in ('utoc', 'ucas', 'pak')}
    return report


if __name__ == '__main__':
    print(main(*sys.argv[1:3]))
