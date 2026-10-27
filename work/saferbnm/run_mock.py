"""Runs make_safer_bonamik.py against the strict mock `unreal` module in three situations."""
import json, os, runpy, shutil, sys
sys.path.insert(0, '/work/saferbnm/mock_unreal')
SCRIPT = '/work/saferbnm/make_safer_bonamik.py'
SKEL = '/tmp/scratch/look365/safer_PC0010_999_Skeleton.json'
skel = json.load(open(SKEL))
BONES = [(b['name'], b['parent'] if b['parent'] is not None else -1) for b in skel]
OUT = '/tmp/scratch/mock_safer'
MESH = '/Game/Character/Player/PC0010_999_Safer_Sephiroth/Model/PC0010_999'
NEW = '/Game/Character/Player/PC0010_999_Safer_Sephiroth/Model/PC0010_999_BNM_Regular'
OLD = '/Game/Character/Player/PC0010_999_Safer_Sephiroth/Model/PC0010_999_BNM'


def fresh(name):
    if 'unreal' in sys.modules:
        del sys.modules['unreal']
    import unreal
    unreal.OUTDIR = os.path.join(OUT, name)
    shutil.rmtree(unreal.OUTDIR, ignore_errors=True)
    return unreal


def with_old(u, bones):
    """Safer's mesh as it is: its KBD user data lists the v2 PC0010_999_BNM."""
    old = u.SQEX_BonamikAsset(u.Package(None, OLD), 'PC0010_999_BNM')
    u.REGISTRY[OLD] = old
    mesh = u.setup_mesh(MESH, bones)
    kbd = u.new_object(u.SQEX_KBD_AssetUserData, mesh)
    kbd._v['BonamikDataList'] = [old]
    mesh._v['asset_user_data'] = [kbd]
    return mesh


def run(u):
    runpy.run_path(SCRIPT, run_name='__main__')
    return json.load(open(os.path.join(u.OUTDIR, 'Saved', 'SaferBonamik', 'report.json')))


def summary(u, report):
    asset = u.REGISTRY.get(NEW)
    mesh = u.REGISTRY[MESH]
    ud = mesh.get_editor_property('asset_user_data')
    print('  ok', report['ok'], '| asset', report.get('asset_action'), '| mesh', report.get('mesh_action'), '| saved', report['saved'])
    if asset is not None:
        print('  asset version', asset.get_editor_property('m_VersionNo'), '| v2', asset.get_editor_property('v2'),
              '| bodies', len(asset.get_editor_property('mBodies')), 'cones', len(asset.get_editor_property('mCones')),
              'links', len(asset.get_editor_property('mLinks')), 'shapes', len(asset.get_editor_property('mShapes')),
              'groups', len(asset.get_editor_property('mGroups')))
    print('  user data', [(d.get_path_name(), [x.get_path_name() for x in d.get_editor_property('BonamikDataList')]) for d in ud])
    if not report['ok']:
        print(report.get('error'))
        print(report.get('problems', [])[:5])
    return report['ok']


ok = True
print('1) Safer\'s mesh listing the v2 PC0010_999_BNM')
u = fresh('first')
with_old(u, BONES)
r = run(u)
ok &= summary(u, r)
lst = [x.get_path_name() for x in u.REGISTRY[MESH].get_editor_property('asset_user_data')[0].get_editor_property('BonamikDataList')]
ok &= lst == [NEW + '.PC0010_999_BNM_Regular'] and r['asset_action'] == 'created' and MESH + '.PC0010_999' in u.SAVED
print('   run again in the same editor session (asset made, mesh already switched)')
r = run(u)
ok &= summary(u, r) and r['mesh_action'].startswith('already') and r['asset_action'] == 'rebuilt'

print('2) commandlet run and a mesh missing L_HairE_c_Phy')
u = fresh('missing')
u.COMMAND_LINE = 'End.uproject -run=pythonscript -script=x.py'
with_old(u, [(n if n != 'L_HairE_c_Phy' else 'L_HairE_c_Phy_renamed', p) for n, p in BONES])
r = run(u)
summary(u, r)
ok &= (not r['ok']) and not u.DIALOGS and 'no bones named L_HairE_c_Phy' in r['error'] and r['saved'] == []

print('3) the spec values come back from the mock as written (every field)')
u = fresh('values')
with_old(u, BONES)
r = run(u)
asset = u.REGISTRY[NEW]
import importlib.util
s_ = importlib.util.spec_from_file_location('m', SCRIPT); M = importlib.util.module_from_spec(s_); s_.loader.exec_module(M)
spec = M.build_spec()
bodies = asset.get_editor_property('mBodies')
b = bodies[[x['mName'] for x in spec['mBodies']].index('Bdy_Sta_C_Head_a_0_2')]
print('  skull body', b.get_editor_property('mParentName'), b.get_editor_property('m_LocalTransform'), b.get_editor_property('m_Radius'))
ok &= r['ok'] and abs(b.get_editor_property('m_LocalTransform').x - 23.0) < 1e-6
print('ALL MOCK RUNS AS EXPECTED' if ok else 'MOCK RUN PROBLEM')
