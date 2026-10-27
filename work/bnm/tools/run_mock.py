"""Runs make_chaos_vincent_wing_bonamik.py against the strict mock `unreal` module in three situations."""
import importlib, json, os, runpy, shutil, sys
sys.path.insert(0, '/work/bnm/tools/mock_unreal')
SCRIPT = '/work/bnm/ChaosVincentBonamik/make_chaos_vincent_wing_bonamik.py'
BONES = [(b[0], b[1]) for b in json.load(open('/work/bnm/chaos_bones.json'))['bones']]
OUT = '/tmp/scratch/mock'

def fresh(name):
    if 'unreal' in sys.modules: del sys.modules['unreal']
    import unreal
    unreal.OUTDIR = os.path.join(OUT, name)
    shutil.rmtree(unreal.OUTDIR, ignore_errors=True)
    return unreal

def run(unreal):
    runpy.run_path(SCRIPT, run_name='__main__')
    report = json.load(open(os.path.join(unreal.OUTDIR, 'Saved', 'ChaosVincentBonamik', 'report.json')))
    return report

def summary(unreal, report):
    asset = unreal.REGISTRY.get('/Game/Character/Player/PC011_10_Chaos/Model/PC0011_10_BNM')
    mesh = unreal.REGISTRY['/Game/Character/Player/PC011_10_Chaos/Model/PC0011_10']
    ud = mesh.get_editor_property('asset_user_data')
    print('  ok', report['ok'], '| asset', report.get('asset_action'), '| mesh', report.get('mesh_action'), '| saved', report['saved'], '| cooks', len(unreal.COOKS))
    if asset is not None:
        v2 = asset.get_editor_property('v2')
        print('  asset', asset.get_path_name(), 'version', asset.get_editor_property('m_VersionNo'), '| v2', v2.get_path_name() if v2 else None,
              '| bodies', len(v2.get_editor_property('m_Bodies')), 'links', len(v2.get_editor_property('m_Links')))
    print('  user data', [(d.get_path_name(), [x.get_path_name() for x in d.get_editor_property('BonamikDataList')]) for d in ud])
    if not report['ok']: print(report.get('error')); print(report.get('problems', [])[:5])
    return report['ok']

ok = True
print('1) fresh project, mesh without user data')
u = fresh('fresh'); u.setup_mesh('/Game/Character/Player/PC011_10_Chaos/Model/PC0011_10', BONES)
r = run(u); ok &= summary(u, r)
print('   run again in the same editor session (asset and user data exist)')
r = run(u); ok &= summary(u, r)
ok &= r.get('mesh_action', '').startswith('already') and r['asset_action'] == 'rebuilt' and len([o for o in u.NEW_OBJECTS if not isinstance(o, u.SkeletalMeshComponent)]) == 2

print('2) mesh with an existing KBD user data listing another Bonamik')
u = fresh('existing')
other = u.SQEX_BonamikAsset(u.Package(None, '/Game/Other/Other_BNM'), 'Other_BNM')
mesh = u.setup_mesh('/Game/Character/Player/PC011_10_Chaos/Model/PC0011_10', BONES)
kbd = u.new_object(u.SQEX_KBD_AssetUserData, mesh); kbd._v['BonamikDataList'] = [other]
mesh._v['asset_user_data'] = [kbd]
r = run(u); ok &= summary(u, r)

print('3) commandlet run (no dialog) and a mesh missing bone 3F')
u = fresh('missing'); u.COMMAND_LINE = 'End.uproject -run=pythonscript -script=x.py'
u.setup_mesh('/Game/Character/Player/PC011_10_Chaos/Model/PC0011_10', [b for b in BONES if b[0] != '3F'] if False else [(n, p) if n != '3F' else ('3F_renamed', p) for n, p in BONES])
r = run(u); summary(u, r)
ok &= (not r['ok']) and not u.DIALOGS and 'no bones named 3F' in r['error'] and r['saved'] == []
print('ALL MOCK RUNS AS EXPECTED' if ok else 'MOCK RUN PROBLEM')
