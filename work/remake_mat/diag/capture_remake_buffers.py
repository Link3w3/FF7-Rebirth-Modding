# Diagnostic: shows Remake Sephiroth (EB0021_00) in the level viewport, away from the level's own content, and saves what
# the editor renders for him: Lit, Base Color, Metallic, Roughness, Specular, World Normal, Ambient Occlusion, Opacity.
# Then puts the viewport back and removes him. Run in the open End editor (Output Log, Cmd):
#   py "C:/FF7R2UProj/Tools/RemakeMaterials/capture_remake_buffers.py"
# Images: C:\FF7R2UProj\Saved\RemakeMaterials\captures\*.png
import os
import json
import unreal

MESH = '/Game/GameContents/Character/Enemy/EB0021_00_Sephiroth_Standard/Model/EB0021_00'
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(SAVED, 'RemakeMaterials', 'captures')
os.makedirs(OUT, exist_ok=True)
LIB = unreal.RebirthMaterialDiagnosticsLibrary
AL = unreal.AutomationLibrary
ELL = unreal.EditorLevelLibrary
report = {'captures': [], 'notes': []}
ORIGIN = unreal.Vector(0.0, 0.0, 50000.0)

cam_loc, cam_rot = ELL.get_level_viewport_camera_info()
view_mode = None
try:
    view_mode = AL.get_editor_active_viewport_view_mode()
except Exception as ex:
    report['notes'].append('view mode: %s' % ex)
actors = []
try:
    sm = unreal.load_asset(MESH)
    a = ELL.spawn_actor_from_class(unreal.SkeletalMeshActor, ORIGIN, unreal.Rotator(0.0, 0.0, 0.0))
    a.skeletal_mesh_component.set_skeletal_mesh(sm)
    actors.append(a)
    # a light from the front and a sky light, so Lit shows something whatever the level has
    light = ELL.spawn_actor_from_class(unreal.DirectionalLight, ORIGIN + unreal.Vector(0, 0, 500), unreal.Rotator(-30.0, 180.0, 0.0))
    actors.append(light)
    for view, cam in (('front', (unreal.Vector(420.0, 0.0, 110.0), unreal.Rotator(0.0, 180.0, 0.0))),
                      ('face', (unreal.Vector(70.0, 0.0, 175.0), unreal.Rotator(0.0, 180.0, 0.0))),
                      ('back', (unreal.Vector(-420.0, 0.0, 110.0), unreal.Rotator(0.0, 0.0, 0.0)))):
        loc, rot = cam
        ELL.set_level_viewport_camera_info(ORIGIN + loc, rot)
        for buf in ('Lit', 'BaseColor', 'Metallic', 'Roughness', 'Specular', 'WorldNormal', 'AmbientOcclusion', 'Opacity'):
            if view != 'front' and buf not in ('Lit', 'BaseColor', 'Opacity'):
                continue
            try:
                if buf == 'Lit':
                    AL.set_editor_viewport_view_mode(unreal.ViewModeIndex.VMI_LIT)
                else:
                    AL.set_editor_viewport_view_mode(unreal.ViewModeIndex.VMI_VISUALIZE_BUFFER)
                    AL.set_editor_viewport_visualize_buffer(buf)
                fn = os.path.join(OUT, '%s_%s.png' % (view, buf))
                r = LIB.capture_editor_viewport_image(fn, False)
                r = LIB.capture_editor_viewport_image(fn, False)   # (the first draw after a change can be stale)
                report['captures'].append({'view': view, 'buffer': buf, 'file': fn, 'receipt': r[:300]})
            except Exception as ex:
                report['notes'].append('%s %s: %s' % (view, buf, ex))
finally:
    for a in actors:
        try:
            ELL.destroy_actor(a)
        except Exception:
            pass
    ELL.set_level_viewport_camera_info(cam_loc, cam_rot)
    try:
        AL.set_editor_viewport_view_mode(view_mode if view_mode is not None else unreal.ViewModeIndex.VMI_LIT)
    except Exception:
        pass
    json.dump(report, open(os.path.join(OUT, 'report.json'), 'w'), indent=1)
    unreal.log('REMAKECAPTURE %d images in %s; notes: %s' % (len(report['captures']), OUT, report['notes']))
