# Sora's KH2 moves, step 1b: the other 45 key animations onto his skeleton (new assets in
# /Game/RebirthSkelCompat/Imported/KH2Sora), and the root of KH2_1301 read back.
import unreal, json, os
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
FOLDER = os.path.join(SAVED, 'ModExtract', 'sorakh2', 'keys_b')
SKEL = '/Game/Character/Player/PC0000_00_Sora_KH2/Model/PC0000_00_S_Skeleton.PC0000_00_S_Skeleton'
DEST = '/Game/RebirthSkelCompat/Imported/KH2Sora'
out = {}
AL = unreal.AnimationLibrary
a = unreal.EditorAssetLibrary.load_asset(DEST + '/KH2_1301')
pos = AL.get_raw_track_position_data(a, 'kh_sk')
rot = AL.get_raw_track_rotation_data(a, 'kh_sk')
out['1301_root'] = dict(npos=len(pos), nrot=len(rot), p0=[pos[0].x, pos[0].y, pos[0].z], p_last=[pos[-1].x, pos[-1].y, pos[-1].z],
                        q0=[rot[0].x, rot[0].y, rot[0].z, rot[0].w])
r = unreal.EndSkeletonCompatDataObject.import_key_animations(FOLDER, SKEL, DEST)
out['import'] = (r if isinstance(r, str) else ' | '.join(str(x) for x in (r if isinstance(r, tuple) else [r])))[-6000:]
reg = unreal.AssetRegistryHelpers.get_asset_registry()
out['count'] = len(reg.get_assets_by_path(DEST, recursive=False))
result = json.dumps(out, indent=1)
