"""One Dissidia NT Sephiroth outfit, from its face-rigged npz (dnt_face.py), to what the End editor imports:

  * <Model>.fbx         the skeletal mesh on Rebirth's bones (ccseph/tools/ccfbx.py: FBX 7.3 ASCII, the import's mirror
                        undone), its material slots by part: DNT_<Part><n> (Cloth, Hair, Lash, Face, Skin, Eye, Mouth);
                        the eyes' glass and highlight shells are left out (Rebirth's eye material has its own);
  * <Model>_rig.json, <Model>_mesh.npz   the rig (component space) and mesh (sparse weights, slot names) for the
                        KawaiiPhysics preset (kawaii_preset/tools/make_kawaii_preset.py);
  * <Model>_mats.json   each slot's material instance: its Rebirth parent (Sephiroth's PC0010_00 material instances:
                        BodyA cloth, BodyB cloth with cut-outs, Hair, Head, Skin, Eye), and its textures by parameter,
                        made by dnt_tex.py from the outfit's G1T (Color, Normal, Roughness, Metallic, WideOcclusion,
                        Coverage);
  * <Model>_tex.json    the job for dnt_tex.py.

Dissidia NT's texture types (worked out from the files: Sephiroth's coat, skin, hair, eyes): 1 albedo (+ alpha: the
cut-outs of hair and lashes), 2 R gloss / G specular reflectance (F0) / B metal, 3 normal, 5 R occlusion (G 1), 21 a
second normal (the face's wrinkle blend), 37 the hair's flow / shift map. Roughness = 1 - gloss.

    dnt_build.py <face npz> <model name e.g. PC0010_18_DNT_1p1c> <out dir> <texture dir name on the PC>"""
import gzip
import json
import os
import sys

import numpy as np

sys.path.insert(0, '/work/ccseph/tools')
import ccfbx   # noqa: E402

PARENTS = {
    'Cloth': '/Game/Character/Player/PC0010_00_Sephiroth_Standard/Material/PC0010_00_BodyA',
    'ClothCut': '/Game/Character/Player/PC0010_00_Sephiroth_Standard/Material/PC0010_00_BodyB',
    'Hair': '/Game/Character/Player/PC0010_00_Sephiroth_Standard/Material/PC0010_00_Hair',
    'Lash': '/Game/Character/Player/PC0010_00_Sephiroth_Standard/Material/PC0010_00_Hair',
    'Face': '/Game/Character/Player/PC0010_00_Sephiroth_Standard/Material/PC0010_00_Head',
    'Mouth': '/Game/Character/Player/PC0010_00_Sephiroth_Standard/Material/PC0010_00_Head',
    'Skin': '/Game/Character/Player/PC0010_00_Sephiroth_Standard/Material/PC0010_00_Skin',
    'Eye': '/Game/Character/Player/PC0010_00_Sephiroth_Standard/Material/PC0010_00_Eye',
}


def role_of(name, centre):
    if name == 'PBB-ArIriNbSssWt':
        return 'Face'
    if name == 'PBB-ArIriNSssWt':
        return 'Skin'
    if name == 'PBB-ArGfPmSssWt':
        return 'Eye'
    if name in ('PBB-ArGfNWt', 'PBB-ArNWt') and 185 < centre[2] < 191 and abs(centre[1]) < 6:
        return None                       # the eyes' glass / highlight shells
    if name == 'PBB-ArNSssWt':
        return 'Mouth'
    if name.startswith('PBS-ArHha'):
        return 'Lash' if (name.endswith('Zc') or name.endswith('Zd')) else 'Hair'
    return 'Cloth'


def main(face_path, model, out_dir, pc_tex_dir):
    m = dict(np.load(face_path))
    mats = [json.loads(s) for s in m['materials']]
    subs = [json.loads(s) for s in m['submeshes']]
    P = m['pos']
    tri, tmat = m['tri'], m['tmat']
    # triangle -> submesh (the triangles were written in submesh order)
    tri_sub = np.zeros(len(tri), int)
    k = 0
    for i, s in enumerate(subs):
        tri_sub[k:k + s['tris']] = i
        k += s['tris']
    assert k == len(tri)
    slot_of_key = {}
    slots = []
    slot_info = []
    tslot = np.full(len(tri), -1)
    for i, s in enumerate(subs):
        centre = P[s['vstart']:s['vstart'] + s['vcount']].mean(0)
        role = role_of(s['name'], centre)
        if role is None:
            continue
        key = (s['material'], role)
        if key not in slot_of_key:
            n = sum(1 for kk in slot_of_key if kk[1] == role)
            slot_of_key[key] = len(slots)
            slots.append('DNT_%s%d' % (role, n))
            slot_info.append(dict(slot=slots[-1], role=role, material=s['material'],
                                  shader=s['name'], textures=mats[s['material']]['textures'],
                                  params=mats[s['material']]['params']))
        tslot[tri_sub == i] = slot_of_key[key]
    keep_t = tslot >= 0
    used_v = np.unique(tri[keep_t].ravel())
    remap = -np.ones(len(P), np.int64); remap[used_v] = np.arange(len(used_v))
    out = dict(pos=P[used_v], nz=m['nz'][used_v], nx=m['nx'][used_v], tsign=m['tsign'][used_v],
               uv=m['uv'][used_v][:, None, :], tri=remap[tri[keep_t]], tmat=tslot[keep_t], slots=np.array(slots),
               wbone=m['wbone'][used_v], wweight=m['wweight'][used_v], bone_names=m['bone_names'],
               bone_parents=m['bone_parents'], bone_lq=m['bone_lq'], bone_lt=m['bone_lt'])
    os.makedirs(out_dir, exist_ok=True)
    fbx = os.path.join(out_dir, model + '.fbx')
    ccfbx.write(out, fbx, model)
    with open(fbx, 'rb') as f, gzip.open(fbx + '.gz', 'wb', compresslevel=6) as g:
        g.write(f.read())
    os.remove(fbx)
    # rig + mesh for the Kawaii preset
    names = [str(n) for n in m['bone_names']]
    par = m['bone_parents']
    bones = [dict(name=n, parent=(names[par[i]] if par[i] >= 0 else None), q=m['bone_cq'][i].tolist(),
                  t=m['bone_ct'][i].tolist(), local_q=m['bone_lq'][i].tolist(), local_t=m['bone_lt'][i].tolist(),
                  scale=[1.0, 1.0, 1.0]) for i, n in enumerate(names)]
    json.dump(dict(source=face_path, bones=bones), open(os.path.join(out_dir, model + '_rig.json'), 'w'), indent=0)
    wb, ww = out['wbone'], out['wweight']
    v, kk = np.nonzero(ww > 0)
    vslot = np.zeros(len(out['pos']), np.int32); vslot[out['tri'].ravel()] = np.repeat(out['tmat'], 3)
    np.savez(os.path.join(out_dir, model + '_mesh.npz'), pos=out['pos'], w_bone=wb[v, kk], w_vert=v,
             w_weight=ww[v, kk], bones=np.array(names), vmat=vslot, mats=np.array(slots))
    # materials and the texture job
    job = {'model': model, 'materials': {}}
    spec = {'model': model, 'texture_dir': pc_tex_dir, 'slots': []}
    for info in slot_info:
        tex = {}
        for t in info['textures']:
            tex.setdefault(t['type'], t['index'])
        mi = info['material']
        stem = '%s_M%02d' % (model, mi)
        need = job['materials'].setdefault(str(mi), {'stem': stem, 'textures': {str(k): v for k, v in tex.items()},
                                                     'maps': []})
        role = info['role']
        maps = {'Color': '_C', 'Normal': '_N', 'Roughness': '_R', 'Metallic': '_M', 'WideOcclusion': '_O'}
        if role in ('Hair', 'Lash'):
            maps['Coverage'] = '_A'
            maps['WideBentNormal'] = '_N'
        if role == 'Eye':
            maps = {'Color': '_C', 'Normal': '_N', 'WideOcclusion': '_O'}
        for suffix in set(maps.values()):
            if suffix not in need['maps']:
                need['maps'].append(suffix)
        parent_key = role
        if role == 'Cloth':
            parent_key = 'ClothCut'        # the alpha decides at texture time: dnt_tex.py drops Coverage when opaque
            maps['Coverage'] = '_A'
            if '_A' not in need['maps']:
                need['maps'].append('_A')
        spec['slots'].append(dict(slot=info['slot'], role=role, parent=PARENTS[parent_key],
                                  parent_opaque=PARENTS['Cloth'] if role == 'Cloth' else None,
                                  material=mi, shader=info['shader'],
                                  textures={p: stem + s for p, s in maps.items()}, dnt_params=info['params']))
    json.dump(job, open(os.path.join(out_dir, model + '_tex.json'), 'w'), indent=1)
    json.dump(spec, open(os.path.join(out_dir, model + '_mats.json'), 'w'), indent=1)
    print('%s: %d vertices, %d triangles, %d bones, slots %s' % (model, len(out['pos']), len(out['tri']), len(names),
                                                                ', '.join(slots)))


if __name__ == '__main__':
    main(*sys.argv[1:5])
