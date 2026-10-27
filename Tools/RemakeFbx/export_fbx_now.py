# Remake Sephiroth on PC0010_00 as FBX, from the open End editor (Output Log, Cmd):
#     py "C:/FF7R2UProj/Tools/RemakeFbx/export_fbx_now.py"
# Exports the 258 animations run_remake_fbx.cmd built (/Game/RebirthSkelCompat/Built/RemakeSephirothPC0010/Battle08)
# with the engine's FBX exporter to Saved/RemakeSephirothFBX/<Folder>/<Animation>.fbx and zips them into
# Saved/RemakeSephirothFBX.zip. The exporter takes the skeleton's preview mesh: set PC0010_00_Skeleton's Preview Mesh to
# PC0010_00 first (not PC0000_00: that one has no LODs). Nothing is right-clicked, opened or saved.
import json, os, time, zipfile
import unreal

SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(SAVED, 'RemakeSephirothFBX')
ZIP = os.path.join(SAVED, 'RemakeSephirothFBX.zip')
BUILT = '/Game/RebirthSkelCompat/Built/RemakeSephirothPC0010/Battle08'
FOLDERS = ('Battle00', 'Battle01', 'Neutral00', 'Reaction00')
SKELETON = '/Game/Character/Player/PC0010_00_Sephiroth_Standard/Model/PC0010_00_Skeleton.PC0010_00_Skeleton'

registry = unreal.AssetRegistryHelpers.get_asset_registry()
registry.scan_paths_synchronous([BUILT], True)
found = sorted(str(a.asset_name) for a in registry.get_assets(unreal.ARFilter(class_names=['AnimSequence'], package_paths=[BUILT])))
unreal.log('REMAKE FBX: %d animations in %s' % (len(found), BUILT))
options = unreal.FbxExportOption()
for name, value in (('ascii', False), ('export_preview_mesh', False), ('map_skeletal_motion_to_root', False)):
    try:
        options.set_editor_property(name, value)
    except Exception:
        pass
done, failed, started = [], [], time.time()
with unreal.ScopedSlowTask(len(found), 'Exporting Remake Sephiroth as FBX') as task:
    task.make_dialog(True)
    for asset in found:
        if task.should_cancel():
            break
        task.enter_progress_frame(1, asset)
        folder, name = next(((f, asset[len(f) + 1:]) for f in FOLDERS if asset.startswith(f + '_')), ('Other', asset))
        filename = os.path.join(OUT, folder, name + '.fbx')
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        anim = unreal.load_asset('%s/%s.%s' % (BUILT, asset, asset))
        t = unreal.AssetExportTask()
        t.set_editor_property('object', anim)
        t.set_editor_property('exporter', unreal.AnimSequenceExporterFBX())
        t.set_editor_property('filename', filename)
        t.set_editor_property('automated', True)
        t.set_editor_property('prompt', False)
        t.set_editor_property('replace_identical', True)
        t.set_editor_property('options', options)
        ok = anim is not None and unreal.Exporter.run_asset_export_task(t) and os.path.isfile(filename) and os.path.getsize(filename) > 0
        (done if ok else failed).append('%s/%s' % (folder, name))
        if not done and len(failed) >= 3:
            break    # (no preview mesh on the skeleton: every one would fail the same way)
if done:
    with zipfile.ZipFile(ZIP + '.tmp', 'w', zipfile.ZIP_DEFLATED) as z:
        for key in done:
            z.write(os.path.join(OUT, key + '.fbx'), key + '.fbx')
    os.replace(ZIP + '.tmp', ZIP)
summary = '%d of %d exported to %s in %.0f s%s' % (len(done), len(found), OUT, time.time() - started,
          ('; failed: ' + ', '.join(failed[:10])) if failed else '')
if not done and failed:
    summary += ' -- set PC0010_00_Skeleton\'s Preview Mesh to PC0010_00 first'
unreal.log('REMAKE FBX: ' + summary)
unreal.EditorDialog.show_message('Remake Sephiroth FBX', summary, unreal.AppMsgType.OK)
