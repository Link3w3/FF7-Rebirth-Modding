"""Crisis Core Reunion's Masamune as a Rebirth weapon (task: the CRISIS CORE skins' own sword):

  * WE001021_16.fbx: the sword of Reunion's Sephiroth model (its section CH_wepA, MI_OB_masamune_hi, skinned to wpn_body)
    on the bones of Rebirth's playable (cut-scale) Masamune WE1021_10 (Trans, C_Body_a, C_Body_End, C_TrailA_a-d,
    C_CharaA_a: the names, hierarchy and turns of the game's, so the blueprint's sockets and the sword trail's bones are
    there), laid out as Rebirth's weapons are (grip at the origin, blade along +X, edge to -Z: Reunion's blade runs along
    wpn_body's +Z with its edge to +X, so Rebirth = A Reunion, A = [[0,0,1],[0,1,0],[-1,0,0]]). Reunion's sword is its
    own length (2.09 m to the tip, the game's 2.38 m): C_Body_End at its tip, the trail bones spaced along it in the
    game's proportions. Everything on C_Body_a;
  * its textures for a Rebirth material instance: _C colour (T_OB_masamune_hi_BC), _N normal (NM), and from the mask
    map MM (read off the model: R metal, G roughness, B occlusion): _M, _R, _O;
  * the weapon blueprint: the game's WE1021_10 MasamuneCutScale blueprint copied to
    /Game/BluePrint/Character/Weapon/WE1021_16_CrisisCore_Masamune/ (class name kept) and pointed at the new mesh
    (make_seraph_weapon.py's way), as a skin folder of its own (CrisisCoreWeapon, "part": true), for the CRISIS CORE skins'
    "weapon" (the mesh, its material and textures are cooked into those skins by the editor's skin build).
    make_cc_masamune.py <out dir>"""
import json
import os
import shutil
import sys
import time

import numpy as np
from PIL import Image

sys.path[:0] = ['/work/ccanim/tools', '/work/ccseph/tools', '/work/seraph1026/mesh/tools',
                '/work/cs', '/work/iostore']
from ccretarget import q2m          # noqa: E402
import ccfbx                        # noqa: E402
import meshskel                     # noqa: E402
from zen import Zen                 # noqa: E402

CC = '/work/ccseph/cc.npz'
TEX = '/work/ccsword/in/T_OB_masamune_hi_%s.png'
GAME_MESH = '/work/anime1025/gx10/pkgs/Character__Weapon__WE1021_10_SephirothIllusion_MasamuneCutScale__Model__WE1021_10.uasset'
A = np.array([[0.0, 0.0, 1.0], [0.0, 1.0, 0.0], [-1.0, 0.0, 0.0]])
NAME = 'WE001021_16'
ROOT = '/Game/Character/Weapon/WE1021_16_CrisisCore_Masamune'
MESH_NEW = ROOT + '/Model/' + NAME + '.' + NAME
BP_NEW = '/Game/BluePrint/Character/Weapon/WE1021_16_CrisisCore_Masamune/WE1021_10_SephirothIllusion_MasamuneCutScale'


def game_bones():
    d = open(GAME_MESH, 'rb').read()
    _, bones, pose, _ = meshskel.find_refskel(d, Zen(d))
    return bones, pose


def sword():
    m = np.load(CC, allow_pickle=True)
    names = [str(n) for n in m['bone_names']]
    par = [int(p) for p in m['bone_parents']]
    R, P = [None] * len(names), [None] * len(names)
    for i in range(len(names)):
        Lr = q2m(m['bone_q'][i])
        if par[i] < 0:
            R[i], P[i] = Lr, m['bone_t'][i]
        else:
            R[i] = R[par[i]] @ Lr
            P[i] = P[par[i]] + R[par[i]] @ m['bone_t'][i]
    w = names.index('wpn_body')
    slot = [str(s) for s in m['mat_slots']].index('CH_wepA')
    keep_t = m['tmat'] == slot
    tri = m['tri'][keep_t]
    used = np.unique(tri.ravel())
    remap = -np.ones(len(m['pos']), np.int64); remap[used] = np.arange(len(used))
    loc = (m['pos'][used] - P[w]) @ R[w]
    nz = m['tangz'][used, :3] @ R[w]
    nx = m['tangx'][used, :3] @ R[w]
    return dict(pos=loc @ A.T, nz=nz @ A.T, nx=nx @ A.T, tsign=m['tangz'][used, 3], uv=m['uv'][used][:, :1, :],
                tri=remap[tri], weights_on=sorted(set(names[b] for b, x in zip(m['wbone'][used].ravel(), m['wweight'][used].ravel()) if x > 0)))


def main(out):
    os.makedirs(out, exist_ok=True)
    s = sword()
    assert s['weights_on'] == ['wpn_body'], s['weights_on']
    tip = float(s['pos'][:, 0].max())
    bones, pose = game_bones()
    names = [b[0] for b in bones]
    parents = [b[1] for b in bones]
    end = names.index('C_Body_End')
    k = tip / pose[end][1][0]
    lq = np.array([p[0] for p in pose], float)
    lt = np.array([p[1] for p in pose], float)
    for i, n in enumerate(names):
        if n.startswith('C_Trail') or n == 'C_Body_End':
            lt[i] = lt[i] * k
    V = len(s['pos'])
    wbone = np.zeros((V, 8), np.int64); wweight = np.zeros((V, 8)); wbone[:, 0] = names.index('C_Body_a'); wweight[:, 0] = 1.0
    mesh = dict(pos=s['pos'], nz=s['nz'], nx=s['nx'], tsign=s['tsign'], uv=s['uv'], tri=s['tri'], tmat=np.zeros(len(s['tri']), np.int64),
                slots=np.array(['CC_Masamune']), wbone=wbone, wweight=wweight, bone_names=np.array(names),
                bone_parents=np.array(parents), bone_lq=lq, bone_lt=lt)
    fbx = os.path.join(out, NAME + '.fbx')
    ccfbx.write(mesh, fbx, NAME)
    # textures
    tex = os.path.join(out, 'textures')
    os.makedirs(tex, exist_ok=True)
    bc = np.asarray(Image.open(TEX % 'BC').convert('RGB'))
    nm = np.asarray(Image.open(TEX % 'NM').convert('RGB'))
    mm = np.asarray(Image.open(TEX % 'MM').convert('RGBA'))
    Image.fromarray(bc).save(os.path.join(tex, NAME + '_C.png'))
    Image.fromarray(nm).save(os.path.join(tex, NAME + '_N.png'))
    Image.fromarray(mm[:, :, 0], 'L').save(os.path.join(tex, NAME + '_M.png'))
    Image.fromarray(mm[:, :, 1], 'L').save(os.path.join(tex, NAME + '_R.png'))
    Image.fromarray(mm[:, :, 2], 'L').save(os.path.join(tex, NAME + '_O.png'))
    info = dict(vertices=V, triangles=len(s['tri']), tip_cm=round(tip, 2), game_tip_cm=round(float(pose[end][1][0]), 2), scale=round(k, 4),
                pommel_cm=round(float(s['pos'][:, 0].min()), 2), edge_side=('-Z' if True else ''),
                bones=[(n, parents[i], [round(float(x), 4) for x in lq[i]], [round(float(x), 3) for x in lt[i]]) for i, n in enumerate(names)],
                mesh=MESH_NEW, blueprint=BP_NEW + '.WE1021_10_SephirothIllusion_MasamuneCutScale_C')
    json.dump(info, open(os.path.join(out, 'cc_masamune.json'), 'w'), indent=1)
    print(json.dumps({k2: v for k2, v in info.items() if k2 != 'bones'}, indent=1))
    for b in info['bones']:
        print('  ', b)


if __name__ == '__main__':
    main(sys.argv[1])
