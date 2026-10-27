# Read only: PC0010_13's slots, user data, sockets, LODs and sections; the Hair MI's parameters; whether the white
# coverage texture and a HairCore MI exist; unsaved packages.
import unreal, json
EAL = unreal.EditorAssetLibrary
BASE = '/Game/Character/Player/PC0010_13_Young_Sephiroth'
sm = unreal.load_asset(BASE + '/Model/PC0010_13')
out = {}
out['dirty'] = [str(p.get_name()) for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
out['materials'] = [[str(m.get_editor_property('material_slot_name')), str(m.get_editor_property('imported_material_slot_name')),
                     m.get_editor_property('material_interface').get_path_name().split('.')[0] if m.get_editor_property('material_interface') else None]
                    for m in sm.get_editor_property('materials')]
kbd = []
for d in (sm.get_editor_property('asset_user_data') or []):
    if d is None:
        continue
    e = {'class': d.get_class().get_name()}
    for prop in ('BonamikDataList', 'KineDriverDataList'):
        try:
            e[prop] = [x.get_path_name() if x else None for x in d.get_editor_property(prop)]
        except Exception as ex:
            e[prop] = 'n/a'
    kbd.append(e)
out['kbd'] = kbd
out['sockets'] = sm.num_sockets()
out['lods'] = sm.get_editor_property('lod_info').__len__()
mi = unreal.load_asset(BASE + '/Material/PC0010_13_Hair')
out['hair_mi'] = {
    'parent': mi.get_editor_property('parent').get_path_name(),
    'textures': [[str(tp.get_editor_property('parameter_info').get_editor_property('name')),
                  tp.get_editor_property('parameter_value').get_path_name() if tp.get_editor_property('parameter_value') else None]
                 for tp in mi.get_editor_property('texture_parameter_values')],
    'scalars': [[str(sp.get_editor_property('parameter_info').get_editor_property('name')), sp.get_editor_property('parameter_value')]
                for sp in mi.get_editor_property('scalar_parameter_values')],
}
bo = mi.get_editor_property('base_property_overrides')
out['hair_mi']['overrides'] = {k: str(bo.get_editor_property(k)) for k in ('override_blend_mode', 'blend_mode', 'override_opacity_mask_clip_value', 'opacity_mask_clip_value')}
out['white'] = EAL.does_asset_exist('/Game/Renderer/Texture/FFFFFFFF_BC4')
out['core_mi_exists'] = EAL.does_asset_exist(BASE + '/Material/PC0010_13_HairCore')
out['textures'] = sorted(a.split('.')[0].rsplit('/', 1)[1] for a in EAL.list_assets(BASE + '/Texture', recursive=False, include_folder=False))
out['models'] = sorted(a.split('.')[0].rsplit('/', 1)[1] for a in EAL.list_assets(BASE + '/Model', recursive=False, include_folder=False))
out['mats'] = sorted(a.split('.')[0].rsplit('/', 1)[1] for a in EAL.list_assets(BASE + '/Material', recursive=False, include_folder=False))
result = json.dumps(out, indent=1)
