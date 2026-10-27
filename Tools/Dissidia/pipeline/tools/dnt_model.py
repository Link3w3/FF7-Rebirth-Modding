"""Dissidia NT character model (base g1m + model g1m [+ part g1ms]) -> one npz: the combined skeleton and every LOD 0
mesh of mesh group 0 (the drawn meshes; group 1 is the shadow pass), in the game's model space (cm, Y up, the character
facing +Z, +X his left).

    dnt_model.py <base.g1m> <model.g1m> <out.npz> [part.g1m ...]

Per vertex: position, normal, tangent (xyz + sign), UV 0, colour, up to 8 bone weights on the combined skeleton.
Skinning: BLENDINDICES are joint palette indices x 3; a palette entry names its joint by local id, in the base
skeleton when bit 31 is set, else in the model's own G1MS (its "external" layer, whose roots hang under base joints).
Cloth meshes of type 2 (mesh entries with cloth 2: front hair strands, belt flaps...) store positions, normals and
tangents in the frame of the palette's physics joint (its low 16 bits: a base joint's local id); they are moved into
model space by that joint's bind transform here, as gust_stuff's render_cloth_submesh_2 does.
Materials: per triangle the submesh's material index; the npz also lists, per material, its textures (G1T index, type),
the shader (mesh entry) name and the shader parameter block of its first submesh.
"""
import json
import sys

import numpy as np

sys.path.insert(0, __file__.rsplit('/', 1)[0])
import g1m


def load(base_path, model_path, part_paths=()):
    b = open(base_path, 'rb').read()
    base = g1m.Skeleton(g1m.chunk(b, 'G1MS')[0])
    models = []
    layers = []
    for tag, path in [('d', model_path)] + [('p%d' % i, p) for i, p in enumerate(part_paths)]:
        data = open(path, 'rb').read()
        ms = g1m.chunk(data, 'G1MS')[0]
        sk = g1m.Skeleton(ms) if ms else None
        if sk is not None and sk.count and sk.external:
            layers.append((tag, sk))
        models.append((tag, path, data, sk))
    rig = g1m.Rig(base, layers)
    return base, rig, models


def joint_index(rig, base, tag, sk, raw):
    if raw & 0x80000000:
        return int(raw & 0x7FFFFFFF)                  # base local id == combined index
    if tag not in rig.layer_start:
        raise ValueError('model joint %d without a layer' % raw)
    return rig.layer_start[tag] + int(raw)


def build(base_path, model_path, out_path, part_paths=()):
    base, rig, models = load(base_path, model_path, part_paths)
    P, N, T, TS, UV, COL, WB, WW, TRI, TMAT = [], [], [], [], [], [], [], [], [], []
    mats = []
    sub_info = []
    vbase = 0
    for tag, path, data, sk in models:
        g = g1m.Geometry(g1m.chunk(data, 'G1MG')[0])
        entry_of = {}
        for l in g.lods:
            if l['lod'] != 0 or l['group'] != 0:
                continue
            for me in l['meshes']:
                for s in me['submeshes']:
                    entry_of.setdefault(s, me)
        mat_base = len(mats)
        for mi, m in enumerate(g.materials):
            mats.append(dict(model=tag, index=mi, textures=m['textures'], shader_names=[], params=None))
        for si in sorted(entry_of):
            me = entry_of[si]
            sm = g.submeshes[si]
            a, tris = g.submesh_arrays(si)
            pal = g.palettes[sm['palette']]
            pos = a['POSITION'][:, :3].astype(np.float64)
            nrm = a.get('NORMAL', np.zeros((len(pos), 4)))[:, :3].astype(np.float64)
            tan = a.get('TANGENT', np.zeros((len(pos), 4))).astype(np.float64)
            if me['cloth'] == 2:
                phys = pal[0]['physics'] & 0xFFFF
                assert all((e['physics'] & 0xFFFF) == phys for e in pal), 'mixed physics joints'
                q, t = rig.wquat[phys], rig.wpos[phys]
                M = g1m.quat_matrix(q)
                pos = pos @ M.T + t
                nrm = nrm @ M.T
                tan[:, :3] = tan[:, :3] @ M.T
            elif me['cloth'] != 0:
                raise ValueError('cloth type %d not handled (submesh %d)' % (me['cloth'], si))
            # weights: up to two layers of 4
            idx = [a[k] for k in ('BLENDINDICES', 'BLENDINDICES1') if k in a]
            wts = [a[k] for k in ('BLENDWEIGHT', 'BLENDWEIGHT1') if k in a]
            I = np.concatenate(idx, axis=1)
            if len(wts) == 1 and wts[0].shape[1] < I.shape[1] and len(idx) == 1:
                w = wts[0]
                if w.shape[1] == 2:      # half x2: two weights given, the rest makes it up to 1
                    rest = np.clip(1.0 - w.sum(1, keepdims=True), 0, 1)
                    W = np.concatenate([w, rest, np.zeros((len(w), 1))], axis=1)
                else:
                    W = np.concatenate([w, np.clip(1.0 - w.sum(1, keepdims=True), 0, 1)], axis=1)[:, :I.shape[1]]
            else:
                W = np.concatenate(wts, axis=1)[:, :I.shape[1]]
            W = W.astype(np.float64)
            W[W < 0] = 0
            pal_j = np.array([joint_index(rig, base, tag, sk, e['joint']) for e in pal])
            B = pal_j[np.clip(I // 3, 0, len(pal_j) - 1)]
            s = W.sum(1, keepdims=True)
            W = np.where(s > 1e-8, W / np.maximum(s, 1e-8), 0)
            if (s < 1e-8).any():
                W[s[:, 0] < 1e-8, 0] = 1.0
            nb = 8
            Bp = np.zeros((len(pos), nb), np.int64); Wp = np.zeros((len(pos), nb))
            Bp[:, :B.shape[1]] = B; Wp[:, :W.shape[1]] = W
            P.append(pos); N.append(nrm); T.append(tan[:, :3]); TS.append(np.sign(tan[:, 3] + 1e-12))
            UV.append(a.get('TEXCOORD', np.zeros((len(pos), 2)))[:, :2])
            COL.append(a.get('COLOR', np.ones((len(pos), 4))))
            WB.append(Bp); WW.append(Wp)
            TRI.append(tris + vbase)
            TMAT.append(np.full(len(tris), mat_base + sm['material']))
            mats[mat_base + sm['material']]['shader_names'].append(me['name'])
            if mats[mat_base + sm['material']]['params'] is None:
                mats[mat_base + sm['material']]['params'] = g.shaders[sm['shader']]
            sub_info.append(dict(model=tag, submesh=si, name=me['name'], cloth=me['cloth'], nun=me['nunid'],
                                 material=mat_base + sm['material'], shader=sm['shader'], vstart=vbase,
                                 vcount=len(pos), tris=len(tris)))
            vbase += len(pos)
    out = dict(pos=np.concatenate(P), nrm=np.concatenate(N), tan=np.concatenate(T), tsign=np.concatenate(TS),
               uv=np.concatenate(UV), col=np.concatenate(COL), wbone=np.concatenate(WB), wweight=np.concatenate(WW),
               tri=np.concatenate(TRI), tmat=np.concatenate(TMAT),
               bone_names=np.array(rig.names), bone_parents=np.array(rig.parents),
               bone_lq=np.array(rig.lquat), bone_lt=np.array(rig.lpos), bone_ls=np.array(rig.lscale),
               bone_wq=rig.wquat, bone_wt=rig.wpos,
               materials=np.array([json.dumps(m) for m in mats]), submeshes=np.array([json.dumps(s) for s in sub_info]))
    np.savez_compressed(out_path, **out)
    print('%d bones, %d vertices, %d triangles, %d materials, %d submeshes' % (len(rig.names), len(out['pos']),
                                                                           len(out['tri']), len(mats), len(sub_info)))
    return out


if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:])
