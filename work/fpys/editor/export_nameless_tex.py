# Nameless's textures (the user's tex_we049_001_*) exported as TGA to Saved/ModExtract/ys13/nameless_tex/, plus the
# scalar/vector parameters of his WE1021_49_Mat00 (M_UnityToon) and the textures' settings. Read only.
import unreal, json, os
HERE = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), 'ModExtract', 'ys13', 'nameless_tex')
os.makedirs(HERE, exist_ok=True)
EAL = unreal.EditorAssetLibrary
F = '/Game/Character/Weapon/WE1021_49_Nameless'
out = {'textures': {}, 'files': []}
for a in EAL.list_assets(F + '/Texture', recursive=False, include_folder=False):
    pkg = a.split('.')[0]
    t = unreal.load_asset(pkg)
    name = pkg.rsplit('/', 1)[-1]
    info = dict(size=[t.blueprint_get_size_x(), t.blueprint_get_size_y()], srgb=t.get_editor_property('srgb'),
                compression=str(t.get_editor_property('compression_settings')).split('.')[-1].split(':')[0],
                flip_green=t.get_editor_property('flip_green_channel'))
    task = unreal.AssetExportTask()
    task.set_editor_property('object', t)
    task.set_editor_property('filename', os.path.join(HERE, name + '.tga'))
    task.set_editor_property('automated', True)
    task.set_editor_property('prompt', False)
    task.set_editor_property('replace_identical', True)
    ok = unreal.Exporter.run_asset_export_task(task)
    info['exported'] = bool(ok)
    out['textures'][name] = info
m = unreal.load_asset(F + '/Material/WE1021_49_Mat00')
out['scalars'] = {str(p.get_editor_property('parameter_info').get_editor_property('name')): p.get_editor_property('parameter_value')
                  for p in m.get_editor_property('scalar_parameter_values')}
out['vectors'] = {str(p.get_editor_property('parameter_info').get_editor_property('name')):
                  [round(p.get_editor_property('parameter_value').r, 4), round(p.get_editor_property('parameter_value').g, 4),
                   round(p.get_editor_property('parameter_value').b, 4), round(p.get_editor_property('parameter_value').a, 4)]
                  for p in m.get_editor_property('vector_parameter_values')}
out['tex_params'] = {str(p.get_editor_property('parameter_info').get_editor_property('name')):
                     (p.get_editor_property('parameter_value').get_name() if p.get_editor_property('parameter_value') else None)
                     for p in m.get_editor_property('texture_parameter_values')}
out['files'] = sorted(os.listdir(HERE))
# the Masamune's MI for reference (its parameters)
mm = unreal.load_asset('/Game/Character/Weapon/WE1021_00_SephirothIllusion_Masamune/Material/WE1021_00_Body')
out['masamune'] = dict(scalars={str(p.get_editor_property('parameter_info').get_editor_property('name')): p.get_editor_property('parameter_value')
                                for p in mm.get_editor_property('scalar_parameter_values')},
                       vectors={str(p.get_editor_property('parameter_info').get_editor_property('name')): str(p.get_editor_property('parameter_value'))
                                for p in mm.get_editor_property('vector_parameter_values')},
                       switches=str(mm.get_editor_property('static_parameters')) if hasattr(mm, 'static_parameters') else None)
result = json.dumps(out, indent=1)
