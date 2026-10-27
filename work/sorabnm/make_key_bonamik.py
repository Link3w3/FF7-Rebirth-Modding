"""The Kingdom Key's keychain Bonamik, made as a regular Bonamik (as make_sora_bonamik.py, which this uses).

The chain (chain1 on the pommel, following the blade; chain2..chain7, the links and the token, swinging) is his KH3
keychain's (w_so010_Bonamik, v2 data the game does not run): the same bodies, masses, damping and radii, cones as loose
as KH3's (70-75 degrees, no pull back to the animation: it hangs and swings). The rest of each body's values are
Cloud's pants flaps', as in Sora's own Bonamik.

Creates (or rebuilds) /Game/Character/Weapon/WE0000_00_Kingdom_Key/Model/WE0000_00_BNM, checks it and the bones,
saves it, writes Saved/SoraBonamik/key_report.json. The weapon mesh itself is not changed (the cooked mesh is pointed at
this asset when the mod is packaged, SORA_BONAMIK=1).
"""
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_sora_bonamik as S   # noqa: E402

try:
    import unreal
except ImportError:
    unreal = None

MODEL_DIR = '/Game/Character/Weapon/WE0000_00_Kingdom_Key/Model'
MESH_PATH = MODEL_DIR + '/WE0000_00'
ASSET_NAME = 'WE0000_00_BNM'
ASSET_PATH = MODEL_DIR + '/' + ASSET_NAME
CHAIN = ['chain1', 'chain2', 'chain3', 'chain4', 'chain5', 'chain6', 'chain7']
CHAIN_PARENT = 'wep'
# KH3's: (cone limit Y, Z, inner strength) per link, chain1->chain2 first
LIMITS = [(75.0, 75.0, 0.0)] + [(70.0, 70.0, 0.0)] * 5
RADII = [1.8, 1.8, 1.8, 1.8, 3.0, 3.0]          # chain2..chain7
GROUPS = ['default', 'Keychain']


def build_spec():
    bodies, cones = [], []
    names = [S.body_name(b) for b in CHAIN]
    bodies.append(S.body(names[0], CHAIN[0], 'Keychain', dict(S.CLOTH_ROOT, m_Mass=3.0, m_Damping=1.2)))
    for k, bone in enumerate(CHAIN[1:]):
        values = dict(S.CLOTH_SWING[0], m_Mass=0.8, m_Damping=1.2, mGravityScale=1.0, m_Radius=RADII[k])
        bodies.append(S.body(names[k + 1], bone, 'Keychain', values))
        limit_y, limit_z, inner = LIMITS[k]
        cones.append(dict(S.CLOTH_CONE, mA=names[k], mB=names[k + 1], mLimitY=limit_y, mLimitZ=limit_z,
                          mInnerConeStr=inner, mConeParentStr=0.5))
    groups = [dict(S.GROUP, m_GroupName=name) for name in GROUPS]
    spec = dict(m_VersionNo=S.VERSION_NO, mSceneManager=dict(S.SCENE), mGroups=groups, mBodies=bodies, mLinks=[],
                mCones=cones, mShapes=[], mCollisionCliques=[])
    check(spec)
    return spec


def check(spec):
    names = [b['mName'] for b in spec['mBodies']]
    assert len(set(names)) == len(names)
    swinging = [b['mName'] for b in spec['mBodies'] if not b['m_IsKinematic']]
    assert sorted(c['mB'] for c in spec['mCones']) == sorted(swinging)
    assert all(c['mA'] in names for c in spec['mCones'])


def main():
    saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
    out = os.path.join(saved, 'SoraBonamik')
    if not os.path.isdir(out):
        os.makedirs(out)
    report = dict(ok=False, asset=ASSET_PATH, mesh=MESH_PATH, saved=[])
    try:
        spec = build_spec()
        report['bodies'] = len(spec['mBodies'])
        report['cones'] = len(spec['mCones'])
        mesh = unreal.EditorAssetLibrary.load_asset(MESH_PATH)
        names, parents = S.mesh_bones(mesh)
        report['mesh_bones'] = names
        for parent, child in zip([CHAIN_PARENT] + CHAIN, CHAIN):
            if parents.get(child) != parent:
                raise RuntimeError('bone %s hangs under %s in WE0000_00, not under %s' % (child, parents.get(child), parent))
        # the asset (as make_sora_bonamik's, at this path)
        S.ASSET_PATH, S.ASSET_NAME, S.MODEL_DIR = ASSET_PATH, ASSET_NAME, MODEL_DIR
        asset = S.load_or_create_asset(report)
        S.fill_asset(asset, spec)
        problems = S.verify_asset(asset, spec)
        if problems:
            report['problems'] = problems[:50]
            raise RuntimeError('%d values did not come back as written, first: %s' % (len(problems), problems[0]))
        if not unreal.EditorAssetLibrary.save_loaded_asset(asset, False):
            raise RuntimeError('could not save ' + ASSET_PATH)
        report['saved'].append(ASSET_PATH)
        report['ok'] = True
    except Exception:
        report['error'] = traceback.format_exc()
        unreal.log_error('SoraBonamik (key): ' + report['error'])
    with open(os.path.join(out, 'key_report.json'), 'w') as f:
        json.dump(report, f, indent=1)
    return report
