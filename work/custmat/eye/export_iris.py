import os
import unreal

out = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), 'ModExtract', 'eye')
os.makedirs(out, exist_ok=True)
result = {}
for p in ['/Game/Character/Player/PC0010_00_Sephiroth_Standard/Texture/PC0010_00_Eye_C']:
    t = unreal.load_asset(p)
    task = unreal.AssetExportTask()
    task.object = t
    task.filename = os.path.join(out, p.rsplit('/', 1)[-1] + '.tga')
    task.automated = True
    task.prompt = False
    task.replace_identical = True
    task.exporter = unreal.TextureExporterTGA()
    ok = unreal.Exporter.run_asset_export_task(task)
    result[p] = dict(ok=ok, file=task.filename, size=os.path.getsize(task.filename) if os.path.isfile(task.filename) else None,
                     srgb=t.get_editor_property('srgb'), compression=str(t.get_editor_property('compression_settings')),
                     w=t.blueprint_get_size_x(), h=t.blueprint_get_size_y())
