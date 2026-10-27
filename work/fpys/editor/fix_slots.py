# The material slots of PC0010_13 and WE1021_49 set for real (the earlier loops changed copies of the slot structs):
# PC0010_13's 7 slots -> his PC0010_13_* Rebirth MIs (the import had matched the outfit folder's Unity materials by name);
# WE1021_49's slot -> WE1021_49_Body. Each slot rebuilt (name, imported name, UV data kept), read back from the asset.
import unreal, json
EAL = unreal.EditorAssetLibrary
YS = '/Game/Character/Player/PC0010_13_Young_Sephiroth/Material/PC0010_13_'
JOBS = {
    '/Game/Character/Player/PC0010_13_Young_Sephiroth/Model/PC0010_13': {
        'mat_ch049_001_body': YS + 'Body', 'mat_ch049_001_head': YS + 'Head', 'mat_ch049_001_hair': YS + 'Hair',
        'mat_ch049_001_hair_tp': YS + 'Hair', 'mat_ch049_001_eyelash': YS + 'Eyelash', 'mat_ch049_001_eye_shadow': YS + 'EyeShadow',
        'mat_ch049_001_eye': YS + 'Eye'},
    '/Game/Character/Weapon/WE1021_49_Nameless/Model/WE1021_49': {
        'mat_we049_001_body': '/Game/Character/Weapon/WE1021_49_Nameless/Material/WE1021_49_Body'},
}
out = {}
for mesh_path, want in JOBS.items():
    sm = unreal.load_asset(mesh_path)
    old = sm.get_editor_property('materials')
    for i in range(len(old)):
        m = old[i]
        slot = str(m.get_editor_property('material_slot_name'))
        key = slot if slot in want else str(m.get_editor_property('imported_material_slot_name'))
        assert key in want, (mesh_path, slot)
        m.set_editor_property('material_interface', unreal.load_asset(want[key]))
        old[i] = m                       # (the element is a copy: write it back into the array)
    sm.set_editor_property('materials', old)
    sm.modify()
    EAL.save_loaded_asset(sm, False)
    back = unreal.load_asset(mesh_path).get_editor_property('materials')
    got = {str(m.get_editor_property('material_slot_name')): m.get_editor_property('material_interface').get_path_name().split('.')[0] for m in back}
    bad = {k: v for k, v in got.items() if v != want[k]}
    assert not bad, (mesh_path, bad)
    out[mesh_path] = got
result = json.dumps(out, indent=1)
