"""Dissidia NT's five Masamunes (item/w_sev200_00*) as Rebirth weapons (task #610, made ready before the mapping is
agreed: the models and textures only; which of Cloud's weapons each one stands in for is decided with the user):

  * <NAME>.fbx: the sword (LOD 0, its own materials as slots) on the bones of Rebirth's playable (cut-scale) Masamune
    WE1021_10 (Trans, C_Body_a, C_Body_End, C_TrailA_a-d, C_CharaA_a: the game's names, hierarchy and turns, so the
    blueprint's sockets and the sword trail's bones are there), laid out as Rebirth's weapons are: grip at the origin,
    blade along +X, edge to -Z. Dissidia NT's sword lies along +X of its own root (b22's frame in his hand) with the edge
    to +Z, and Dissidia NT is right-handed: u = diag(1, 1, -1) v (a reflection, as the animations' weapon frame:
    dnt_anim.D_EDGE), so the triangles keep their order (Unreal's winding then) and the tangent signs flip (as
    dnt_rerig2.py's body). Its own length (Dissidia NT's Masamune is 3.5 m to the tip, Rebirth's 2.38 m; SCALE below
    makes it any other): C_Body_End at its tip, the trail bones spaced along it in the game's proportions. Everything
    on C_Body_a;
  * its textures for Rebirth material instances (dnt_tex.py's way, per material): _C albedo, _N normal, _R roughness
    (1 - gloss), _M metal, _O occlusion; an emissive material (PBB-EmN: the 2p1c sword's lit panel) also gets _E (its
    type 19 map).
    make_dnt_masamunes.py <item dir> <out dir> [scale: 1 = Dissidia NT's own length, or "rebirth" = the game's 2.38 m]"""
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, '..', 'tools'), '/work/ccseph/tools', '/work/ccsword',
                '/work/ccanim/tools', '/work/seraph1026/mesh/tools', '/work/cs',
                '/work/iostore']
import g1m                      # noqa: E402
import dnt_tex                  # noqa: E402
import ccfbx                    # noqa: E402
import make_cc_masamune as ccm  # noqa: E402  (game_bones: WE1021_10's reference skeleton)

SWORDS = [('w_sev200_00', '00'), ('w_sev200_00_2p1c', '02'), ('w_sev200_00_3p1c', '03'), ('w_sev200_00_4p1c', '04'),
          ('w_sev200_00_5p1c', '05')]
ROOT = '/Game/Character/Weapon/WE1021_19_DissidiaNT_Masamune'
D = np.diag([1.0, 1.0, -1.0])           # Dissidia NT weapon space -> Rebirth weapon space (a reflection)
TYPES = {1: 'albedo', 2: 'gloss/F0/metal', 3: 'normal', 5: 'occlusion', 19: 'emission'}


def name_of(code):
    return 'WE001021_19_' + code


def load(item, w):
    b = open(os.path.join(item, w, w + '.g1m'), 'rb').read()
    tb = open(os.path.join(item, w, w + '.g1t'), 'rb').read()
    G = g1m.Geometry(g1m.chunk(b, 'G1MG')[0])
    entry_of = {}
    for lod in G.lods:
        if lod['lod'] != 0 or lod['group'] != 0:
            continue
        for me in lod['meshes']:
            for s in me['submeshes']:
                entry_of.setdefault(s, me)
    P, N, T, TS, UV, TRI, TMAT = [], [], [], [], [], [], []
    shader_of = {}
    vbase = 0
    for si in sorted(entry_of):
        me = entry_of[si]
        assert me['cloth'] == 0, (w, si, 'cloth')
        sm = G.submeshes[si]
        a, tris = G.submesh_arrays(si)
        pos = a['POSITION'][:, :3].astype(np.float64)
        nrm = a['NORMAL'][:, :3].astype(np.float64)
        tan = a['TANGENT'].astype(np.float64)
        P.append(pos @ D.T)
        N.append(nrm @ D.T)
        T.append(tan[:, :3] @ D.T)
        TS.append(-np.sign(tan[:, 3] + 1e-12))           # (the reflection flips the tangent sign)
        UV.append(a['TEXCOORD'][:, :2].astype(np.float64))
        TRI.append(np.asarray(tris, np.int64) + vbase)    # (the triangles keep their order: see the docstring)
        TMAT.append(np.full(len(tris), sm['material']))
        shader_of.setdefault(sm['material'], me['name'])
        vbase += len(pos)
    mats = [dict(index=i, textures={int(t['type']): int(t['index']) for t in m['textures']}, shader=shader_of.get(i, ''))
            for i, m in enumerate(G.materials)]
    return dict(pos=np.concatenate(P), nz=np.concatenate(N), nx=np.concatenate(T), tsign=np.concatenate(TS),
                uv=np.concatenate(UV), tri=np.concatenate(TRI), tmat=np.concatenate(TMAT)), mats, tb


def textures(tb, mats, name, out):
    es = dnt_tex.entries(tb)
    cache = {}

    def tex(i):
        if i not in cache:
            cache[i] = dnt_tex.decode(tb, es[i])
        return cache[i]
    written = {}
    for m in mats:
        stem = '%s_M%02d' % (name, m['index'])
        t = m['textures']
        files = {}

        def rgb(a, suffix):
            p = os.path.join(out, stem + suffix + '.png')
            Image.fromarray(np.ascontiguousarray(a[:, :, :3])).save(p, compress_level=6)
            files[suffix] = os.path.basename(p)

        def grey(a, suffix):
            p = os.path.join(out, stem + suffix + '.png')
            Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'L').save(p, compress_level=6)
            files[suffix] = os.path.basename(p)
        # (10-27: dnt_tex.py's conversions for Unreal, as the outfits': the metal's colour, the normal map in the imported
        #  model's tangent frame (the reflection keeps the body's: (n.y, -n.x, n.z)), roughness from Dissidia NT's gloss,
        #  metal 0 or 1)
        spec = tex(t[2]) if 2 in t else None
        if 1 in t:
            rgb(dnt_tex.albedo_for_unreal(tex(t[1]), spec), '_C')
            alpha = tex(t[1])[:, :, 3]
            if (alpha < 26).mean() >= 0.002:
                grey(alpha, '_A')
        if 3 in t:
            rgb(dnt_tex.normal_for_unreal(tex(t[3])), '_N')
        if spec is not None:
            grey(dnt_tex.roughness_for_unreal(spec[:, :, 0]), '_R')
            grey(np.where(spec[:, :, 2] >= 128, 255, 0), '_M')
        if 5 in t:
            grey(tex(t[5])[:, :, 0], '_O')
        elif 1 in t:
            grey(np.full(tex(t[1]).shape[:2], 255), '_O')
        if 19 in t:
            rgb(tex(t[19]), '_E')
        written[m['index']] = dict(stem=stem, shader=m['shader'], files=files,
                                   unused=sorted(TYPES.get(k, 'type %d' % k) for k in t if k not in (1, 2, 3, 5, 19)))
    return written


def bones_for(tip):
    bones, pose = ccm.game_bones()
    names = [b[0] for b in bones]
    parents = [b[1] for b in bones]
    end = names.index('C_Body_End')
    k = tip / pose[end][1][0]
    lq = np.array([p[0] for p in pose], float)
    lt = np.array([p[1] for p in pose], float)
    for i, n in enumerate(names):
        if n.startswith('C_Trail') or n == 'C_Body_End':
            lt[i] = lt[i] * k
    return names, parents, lq, lt, k, float(pose[end][1][0])


def main(item, out_root, scale='1'):
    os.makedirs(out_root, exist_ok=True)
    summary = []
    for w, code in SWORDS:
        name = name_of(code)
        out = os.path.join(out_root, name)
        os.makedirs(os.path.join(out, 'textures'), exist_ok=True)
        mesh, mats, tb = load(item, w)
        own_tip = float(mesh['pos'][:, 0].max())
        names, parents, lq, lt, _, game_tip = bones_for(own_tip)
        f = (game_tip / own_tip) if scale == 'rebirth' else float(scale)
        if f != 1.0:
            mesh['pos'] = mesh['pos'] * f
            names, parents, lq, lt, _, game_tip = bones_for(own_tip * f)
        tip = float(mesh['pos'][:, 0].max())
        V = len(mesh['pos'])
        wbone = np.zeros((V, 8), np.int64)
        wweight = np.zeros((V, 8))
        wbone[:, 0] = names.index('C_Body_a')
        wweight[:, 0] = 1.0
        used = sorted(set(int(x) for x in mesh['tmat']))
        slot_of = {mi: k for k, mi in enumerate(used)}
        slots = ['DNT_Masamune%d' % mi for mi in used]
        m = dict(pos=mesh['pos'], nz=mesh['nz'], nx=mesh['nx'], tsign=mesh['tsign'], uv=mesh['uv'][:, None, :],
                 tri=mesh['tri'], tmat=np.array([slot_of[int(x)] for x in mesh['tmat']]), slots=np.array(slots),
                 wbone=wbone, wweight=wweight, bone_names=np.array(names), bone_parents=np.array(parents),
                 bone_lq=lq, bone_lt=lt)
        ccfbx.write(m, os.path.join(out, name + '.fbx'), name)
        tex = textures(tb, mats, name, os.path.join(out, 'textures'))
        info = dict(source=w, name=name, mesh='%s/Model/%s.%s' % (ROOT, name, name), vertices=V, triangles=int(len(mesh['tri'])),
                    tip_cm=round(tip, 2), game_tip_cm=round(game_tip, 2), scale=round(f, 4),
                    pommel_cm=round(float(mesh['pos'][:, 0].min()), 2),
                    curve_at_tip_cm=round(float(mesh['pos'][np.argmax(mesh['pos'][:, 0]), 2]), 2),
                    width_cm=[round(float(mesh['pos'][:, 1].min()), 2), round(float(mesh['pos'][:, 1].max()), 2)],
                    height_cm=[round(float(mesh['pos'][:, 2].min()), 2), round(float(mesh['pos'][:, 2].max()), 2)],
                    slots=[dict(slot=slots[slot_of[mi]], material=mi, shader=tex[mi]['shader'], textures=tex[mi]['files'],
                                unused=tex[mi]['unused']) for mi in used],
                    bones=[(n, parents[i], [round(float(x), 4) for x in lq[i]], [round(float(x), 3) for x in lt[i]])
                           for i, n in enumerate(names)])
        json.dump(info, open(os.path.join(out, name + '.json'), 'w'), indent=1)
        summary.append({k: v for k, v in info.items() if k != 'bones'})
        print('%s (%s): %d vertices, %d triangles, tip %.1f cm (the game\'s %.1f), slots %s' % (
            name, w, V, len(mesh['tri']), tip, game_tip, ', '.join('%s %s %s' % (s['slot'], s['shader'], sorted(s['textures']))
                                                                  for s in info['slots'])))
    json.dump(summary, open(os.path.join(out_root, 'dnt_masamunes.json'), 'w'), indent=1)


if __name__ == '__main__':
    main(*sys.argv[1:4])
