import unreal, json
out = {}
for path in ('/Game/Character/Player/PC0010_13_Young_Sephiroth/Model/PC0010_13', '/Game/Character/Weapon/WE1021_49_Nameless/Model/WE1021_49'):
    sm = unreal.load_asset(path)
    out[path] = [(str(m.get_editor_property('material_slot_name')), m.get_editor_property('material_interface').get_path_name() if m.get_editor_property('material_interface') else None)
                 for m in sm.get_editor_property('materials')]
mi = unreal.load_asset('/Game/Character/Weapon/WE1021_49_Nameless/Material/WE1021_49_Body')
out['WE1021_49_Body'] = {str(p.get_editor_property('parameter_info').get_editor_property('name')):
                         (p.get_editor_property('parameter_value').get_name() if p.get_editor_property('parameter_value') else None)
                         for p in mi.get_editor_property('texture_parameter_values')}
mm = unreal.load_asset('/Game/Character/Player/PC0010_13_Young_Sephiroth/Material/PC0010_13_Body')
out['PC0010_13_Body'] = {str(p.get_editor_property('parameter_info').get_editor_property('name')):
                         (p.get_editor_property('parameter_value').get_name() if p.get_editor_property('parameter_value') else None)
                         for p in mm.get_editor_property('texture_parameter_values')}
result = json.dumps(out, indent=1)
