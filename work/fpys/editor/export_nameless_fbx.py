# WE1021_49 (the Nameless) exported as FBX to Saved/ModExtract/ys13/nameless_fbx/WE1021_49.fbx (to read its string's
# vertices for its Bonamik). Read only.
import unreal, json, os
HERE = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), 'ModExtract', 'ys13', 'nameless_fbx')
os.makedirs(HERE, exist_ok=True)
sm = unreal.load_asset('/Game/Character/Weapon/WE1021_49_Nameless/Model/WE1021_49')
t = unreal.AssetExportTask()
t.set_editor_property('object', sm)
t.set_editor_property('filename', os.path.join(HERE, 'WE1021_49.fbx'))
t.set_editor_property('automated', True)
t.set_editor_property('prompt', False)
t.set_editor_property('replace_identical', True)
opt = unreal.FbxExportOption()
opt.set_editor_property('ascii', False)
opt.set_editor_property('collision', False)
opt.set_editor_property('level_of_detail', False)
t.set_editor_property('options', opt)
ok = unreal.Exporter.run_asset_export_task(t)
result = json.dumps({'ok': bool(ok), 'files': os.listdir(HERE), 'size': os.path.getsize(os.path.join(HERE, 'WE1021_49.fbx')) if ok else 0})
