"""kh3bonamik.py's editor half against the strict mock `unreal` module, in the situations the menu meets."""
import importlib, json, os, shutil, sys
sys.path.insert(0, '/work/kh3bnm/tools/mock_unreal')
sys.path.insert(0, '/work/kh3bnm/src')
TEST = '/work/kh3bnm/test/p_ex011_Bonamik.uasset'
OUT = '/tmp/scratch/kh3mock'
MESH = '/Game/Character/KH3/p_ex011/p_ex011'

def fresh(name):
    for m in ('unreal', 'rebirth_fx.kh3bonamik', 'rebirth_fx'):
        sys.modules.pop(m, None)
    import unreal
    unreal.OUTDIR = os.path.join(OUT, name)
    shutil.rmtree(unreal.OUTDIR, ignore_errors=True)
    os.makedirs(unreal.OUTDIR)
    import rebirth_fx.kh3bonamik as k
    return unreal, k

def kh3_bones(k):
    """A bone list like the KH3 mesh: Trans root, every body bone, parents from the parent-child links."""
    _, spec, _, _, _ = k.load_file(TEST)
    bodies = spec['m_Bodies']
    parent = {}
    for l in spec['m_Links']:
        if l['m_LinkType'].value == 1:
            a, c = bodies[l['m_ParentId']]['m_JointName'], bodies[l['m_ChildId']]['m_JointName']
            if a != c and c not in parent:
                parent[c] = a
    names = ['Trans'] + k.bones_used(spec)
    index = dict((n, i) for i, n in enumerate(names))
    return [(n, index.get(parent.get(n, 'Trans'), 0) if n != 'Trans' else -1) for n in names]

ok = True
def expect(cond, what):
    global ok
    print('   %s %s' % ('ok  ' if cond else 'FAIL', what))
    ok &= bool(cond)

print('1) mesh with every bone')
u, k = fresh('full'); bones = kh3_bones(k)
mesh = u.setup_mesh(MESH, bones)
r = k.convert_file(TEST, mesh=MESH)
print(k.report_text(r))
expect(r['ok'], 'converted')
expect(r['asset'] == '/Game/Character/KH3/p_ex011/p_ex011_Bonamik' and r['asset_action'] == 'created', 'asset next to the mesh, created')
expect(r['saved'] == [r['asset'], MESH], 'saved asset and mesh')
asset = u.REGISTRY[r['asset']]
v2 = asset.get_editor_property('v2')
expect(v2 is not None and v2.get_outer() is asset and v2.get_name() == 'SQEX_BonamikAsset_v2_0', 'v2 object inside, named like the game\'s')
expect(asset.get_editor_property('m_VersionNo') == 2401 and v2.get_editor_property('m_VersionNo') == 2401, 'version 2401 on both')
expect(len(v2.get_editor_property('m_Bodies')) == 214 and len(v2.get_editor_property('m_Links')) == 239 and len(v2.get_editor_property('m_Planes')) == 15, 'counts')
sm = v2.get_editor_property('m_SceneManager')
expect(list(sm.get_editor_property('m_TotalLinksInBatch'))[:7] == [120, 13, 7, 8, 7, 4, 0] and sm.get_editor_property('m_RootName') == 'Trans', 'scene batches and root')
expect(sm.get_editor_property('m_FastMotionHandlingMode').name.endswith('LOCAL_FORCE'), 'enum in scene')
b0 = v2.get_editor_property('m_Bodies')[0]
expect(b0.get_editor_property('m_ColShape').value == 6 and b0.get_editor_property('m_CollisionBatchNo') == 0x440000, 'body 0 plane shape, batch bits')
ud = mesh.get_editor_property('asset_user_data')
expect(len(ud) == 1 and [d.get_path_name() for d in ud[0].get_editor_property('BonamikDataList')] == [asset.get_path_name()], 'mesh lists it')
expect(os.path.isfile(r['report_file']) and os.path.isfile(os.path.join(os.path.dirname(r['report_file']), 'p_ex011_Bonamik.v2.json')), 'report + data json written')

print('   again (asset and user data exist)')
u.SAVED[:] = []
r = k.convert_file(TEST, mesh=MESH)
expect(r['ok'] and r['asset_action'] == 'replaced' and r['mesh_action'] == 'already listed' and r['saved'] == [r['asset']], 'replaced, mesh untouched')
expect(len([o for o in u.NEW_OBJECTS if isinstance(o, u.SQEX_BonamikAsset_v2)]) == 1, 'one v2 object')

print('2) mesh without hood1 and with KUBI for kubi')
u, k = fresh('missing')
bones = [(n if n != 'kubi' else 'KUBI', p) for n, p in kh3_bones(k) if n != 'hood1']
u.setup_mesh(MESH, bones)
r = k.convert_file(TEST, mesh=MESH)
print(k.report_text(r))
expect(not r['ok'] and 'missing 1 of the 105 bones' in r['error'] and 'hood1' in r['error'] and 'kubi' not in r['error'] and r['saved'] == [] and not u.REGISTRY.get('/Game/Character/KH3/p_ex011/p_ex011_Bonamik'), 'refused for hood1 only, nothing made')
print('   2b) same mesh with hood1 back: KUBI is fine (Unreal names match without case), root trans for Trans')
u, k = fresh('case')
bones = [({'kubi': 'KUBI', 'Trans': 'trans'}.get(n, n), p) for n, p in kh3_bones(k)]
u.setup_mesh(MESH, bones)
r = k.convert_file(TEST, mesh=MESH)
print(k.report_text(r))
v2 = u.REGISTRY[r['asset']].get_editor_property('v2')
expect(r['ok'] and any('kubi/KUBI' in n for n in r['notes']) and v2.get_editor_property('m_SceneManager').get_editor_property('m_RootName') == 'Trans' and not any('root' in w for w in r['warnings']), 'accepted, noted, root name kept')

print('3) no mesh')
u, k = fresh('nomesh')
r = k.convert_file(TEST)
expect(r['ok'] and r['asset'] == '/Game/KH3Bonamik/p_ex011_Bonamik' and r['saved'] == [r['asset']] and any('no mesh' in w for w in r['warnings']), 'default folder, warned')

print('4) existing asset with Bonamik data of its own')
u, k = fresh('legacy')
u.setup_mesh(MESH, kh3_bones(k))
pkg = u.Package(None, '/Game/Character/KH3/p_ex011/p_ex011_Bonamik')
other = u.SQEX_BonamikAsset(pkg, 'p_ex011_Bonamik'); other._v['mBodies'] = ['x']
u.REGISTRY['/Game/Character/KH3/p_ex011/p_ex011_Bonamik'] = other
r = k.convert_file(TEST, mesh=MESH)
expect(not r['ok'] and 'Bonamik data of its own' in r['error'] and r['saved'] == [], 'left alone')

print('5) mesh root is not Trans; mesh lists another Bonamik')
u, k = fresh('root')
bones = [(n if n != 'Trans' else 'Root', p) for n, p in kh3_bones(k)]
mesh = u.setup_mesh(MESH, bones)
oth = u.SQEX_BonamikAsset(u.Package(None, '/Game/Other/Other_BNM'), 'Other_BNM')
kbd = u.new_object(u.SQEX_KBD_AssetUserData, mesh); kbd._v['BonamikDataList'] = [oth]; mesh._v['asset_user_data'] = [kbd]
r = k.convert_file(TEST, mesh=MESH)
v2 = u.REGISTRY[r['asset']].get_editor_property('v2')
expect(r['ok'] and v2.get_editor_property('m_SceneManager').get_editor_property('m_RootName') == 'Root' and any('Root' in w for w in r['warnings']), 'root swapped, warned')
expect(r['mesh_bonamiks'] == ['Other_BNM', 'p_ex011_Bonamik'] and any('2 Bonamiks' in w for w in r['warnings']), 'appended, two-Bonamik note')

print('5b) mesh re-exported with Y-down bones (Blender style)')
u, k = fresh('axes')
bones = kh3_bones(k)
mesh = u.setup_mesh(MESH, bones)
mesh.__dict__['_offsets'] = dict((n, (0.3, 6.0, 0.2)) for n, p in bones)
r = k.convert_file(TEST, mesh=MESH)
expect(r['ok'] and any('X axis' in w for w in r['warnings']) and r['bones_along_x'].startswith('0 of'), 'converted with the bone-axis warning (%s)' % r.get('bones_along_x'))
u, k = fresh('axes_ok')
mesh = u.setup_mesh(MESH, kh3_bones(k))
r = k.convert_file(TEST, mesh=MESH)
expect(r['ok'] and not any('X axis' in w for w in r['warnings']) and r['bones_along_x'].split(' of ')[0] == r['bones_along_x'].split(' of ')[1], 'X-down bones: no warning (%s)' % r.get('bones_along_x'))

print('6) menu: one mesh selected, file picked, asset exists -> asked; answered No then Yes')
u, k = fresh('menu')
mesh = u.setup_mesh(MESH, kh3_bones(k)); u.SELECTED[:] = [mesh]
k._pick_files = lambda title, start=None: [TEST]
reports = k.menu()
expect(reports and reports[0]['ok'] and u.DIALOGS[-1][2] == 'OK' and 'test the cloth' in u.DIALOGS[-1][1] and u.SYNCED, 'first run: converted, summary shown, browser synced')
u.ANSWERS[:] = [u.AppReturnType.NO]
n = len(u.DIALOGS)
reports = k.menu()
expect(reports is None and u.DIALOGS[n][2] == 'YES_NO' and 'already exists' in u.DIALOGS[n][1], 'asked about replacing; No stops')
u.ANSWERS[:] = [u.AppReturnType.YES]
reports = k.menu()
expect(reports and reports[0]['asset_action'] == 'replaced', 'Yes replaces')

print('7) menu: nothing selected -> asked; No stops, nothing picked')
u, k = fresh('menu2')
picked = []
k._pick_files = lambda title, start=None: picked.append(1) or [TEST]
u.ANSWERS[:] = [u.AppReturnType.NO]
expect(k.menu() is None and not picked, 'stopped before the file dialog')
u.SELECTED[:] = [u.setup_mesh(MESH, kh3_bones(k)), u.setup_mesh(MESH + '_2', kh3_bones(k))]
expect(k.menu() is None and '2 skeletal meshes' in u.DIALOGS[-1][1], 'two meshes: asks to select one')

print('8) bad files')
u, k = fresh('bad')
d = os.path.join(OUT, 'bad'); open(os.path.join(d, 'junk.uasset'), 'wb').write(os.urandom(4000))
r = k.convert_file(os.path.join(d, 'junk.uasset'))
expect(not r['ok'] and 'not a UE4 .uasset' in r['error'], 'junk: ' + r['error'][:80])
shutil.copy(TEST, os.path.join(d, 'lonely_Bonamik.uasset'))
r = k.convert_file(os.path.join(d, 'lonely_Bonamik.uasset'))
expect(not r['ok'] and '.uexp' in r['error'], 'no uexp: ' + r['error'][:90])
shutil.copy(TEST, os.path.join(d, 'cut_Bonamik.uasset'))
open(os.path.join(d, 'cut_Bonamik.uexp'), 'wb').write(open(TEST[:-7] + '.uexp', 'rb').read()[:300000])
r = k.convert_file(os.path.join(d, 'cut_Bonamik.uasset'))
expect(not r['ok'] and 'uexp' in r['error'], 'cut uexp: ' + r['error'][:90])
r = k.convert_file(os.path.join(d, 'none.txt'))
expect(not r['ok'] and '.uasset' in r['error'], 'not a uasset: ' + r['error'][:90])
print('ALL MOCK RUNS AS EXPECTED' if ok else 'MOCK RUN PROBLEM')
sys.exit(0 if ok else 1)
