# PC0010_13's reimport left its old SQEX_KBD_AssetUserData_1 behind as a subobject nothing uses (its Asset User Data now
# holds _0, the same lists): moved out of the package (into the transient package) so the cooked mesh carries one, as
# before. The mesh saved; its Asset User Data checked unchanged.
import unreal, json
EAL = unreal.EditorAssetLibrary
MESH = '/Game/Character/Player/PC0010_13_Young_Sephiroth/Model/PC0010_13'
sm = unreal.load_asset(MESH)
used = [d for d in (sm.get_editor_property('asset_user_data') or []) if d is not None]
used_paths = [d.get_path_name() for d in used]
assert len(used) == 1 and used_paths[0].endswith(':SQEX_KBD_AssetUserData_0'), used_paths
TRANSIENT = unreal.find_object(None, '/Engine/Transient')
assert TRANSIENT is not None, 'no transient package'
out = {'used_before': used_paths, 'moved': []}
for n in ('SQEX_KBD_AssetUserData_1', 'SQEX_KBD_AssetUserData_2', 'SQEX_KBD_AssetUserData_3'):
    o = unreal.find_object(None, MESH + '.PC0010_13:' + n)
    if o is None or o.get_path_name() in used_paths:
        continue
    ok = o.rename(None, TRANSIENT)
    out['moved'].append([n, bool(ok), o.get_path_name()])
assert out['moved'], 'nothing to move'
sm.modify()
assert EAL.save_loaded_asset(sm, False), 'could not save ' + MESH
sm = unreal.load_asset(MESH)
out['used_after'] = [d.get_path_name() for d in (sm.get_editor_property('asset_user_data') or []) if d is not None]
out['left'] = [n for n in ('SQEX_KBD_AssetUserData_0', 'SQEX_KBD_AssetUserData_1', 'SQEX_KBD_AssetUserData_2')
               if unreal.find_object(None, MESH + '.PC0010_13:' + n) is not None]
k = sm.get_editor_property('asset_user_data')[0]
out['lists'] = dict(bnm=[x.get_name() for x in k.get_editor_property('BonamikDataList')], kdi=[x.get_name() for x in k.get_editor_property('KineDriverDataList')])
out['dirty_after'] = [str(p.get_name()) for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
result = json.dumps(out, indent=1)
