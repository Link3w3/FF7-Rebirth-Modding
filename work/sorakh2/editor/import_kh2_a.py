# Sora's KH2 moves, step 1a: two key animations (KH2_1301, KH2_1015) onto his skeleton with Create a Character System's
# Import Key Animations (new assets in /Game/RebirthSkelCompat/Imported/KH2Sora, the game's ACL settings), then checked.
import unreal, json, os
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
FOLDER = os.path.join(SAVED, 'ModExtract', 'sorakh2', 'keys_a')
SKEL = '/Game/Character/Player/PC0000_00_Sora_KH2/Model/PC0000_00_S_Skeleton.PC0000_00_S_Skeleton'
DEST = '/Game/RebirthSkelCompat/Imported/KH2Sora'
out = {}
r = unreal.EndSkeletonCompatDataObject.import_key_animations(FOLDER, SKEL, DEST)
ok, report = (r[0], r[1]) if isinstance(r, tuple) else (r, '')
out['ok'] = ok
out['report'] = report[-3000:]
AL = unreal.AnimationLibrary
for n in ('KH2_1301', 'KH2_1015'):
    a = unreal.EditorAssetLibrary.load_asset(DEST + '/' + n)
    if a is None:
        out[n] = 'missing'; continue
    out[n] = dict(frames=AL.get_num_frames(a), length=a.get_editor_property('sequence_length'),
                  bone=str(a.get_editor_property('bone_compression_settings').get_path_name()),
                  curve=str(a.get_editor_property('curve_compression_settings').get_path_name()),
                  tracks=len(AL.get_animation_track_names(a)))
result = json.dumps(out, indent=1)
