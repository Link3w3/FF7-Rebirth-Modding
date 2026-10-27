# Read only: which SQEX_KBD_AssetUserData subobjects PC0010_13 has, and which one its Asset User Data uses.
import unreal, json
MESH = '/Game/Character/Player/PC0010_13_Young_Sephiroth/Model/PC0010_13'
sm = unreal.load_asset(MESH)
used = [d.get_path_name() for d in (sm.get_editor_property('asset_user_data') or []) if d is not None]
found = {}
for n in ('SQEX_KBD_AssetUserData_0', 'SQEX_KBD_AssetUserData_1', 'SQEX_KBD_AssetUserData_2', 'SQEX_KBD_AssetUserData_3'):
    o = unreal.find_object(None, MESH + '.PC0010_13:' + n)
    if o is None:
        o = unreal.find_object(None, MESH + '.' + n)
    if o is not None:
        found[n] = dict(path=o.get_path_name(), outer=o.get_outer().get_name(),
                        bnm=[x.get_name() for x in o.get_editor_property('BonamikDataList')],
                        kdi=[x.get_name() for x in o.get_editor_property('KineDriverDataList')])
result = json.dumps(dict(used=used, found=found, has_rename=hasattr(unreal.Object, 'rename')), indent=1)
