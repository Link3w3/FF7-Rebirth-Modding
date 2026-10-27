# Can the editor load Cloud's game animations of an area action (for Copy Notifies Onto), and is Sora's folder free?
import unreal, json
out = {}
for p in ['/Game/Motion/Action/0000-COMON/PC0000_Cloud/L_CMN_PC0000_00_Payment.L_CMN_PC0000_00_Payment',
          '/Game/Motion/Player/PC0000_Cloud/Event00/NT_01_Enter02.NT_01_Enter02']:
    a = unreal.load_asset(p)
    out[p] = None if a is None else dict(cls=a.get_class().get_name(), skel=a.get_editor_property('skeleton').get_path_name(),
                                         len=a.get_editor_property('sequence_length'),
                                         pose=a.get_editor_property('pose_animation'),
                                         blend=a.get_editor_property('override_behavior_action_blend_time'))
out['sora_action_folder_exists'] = unreal.EditorAssetLibrary.does_directory_exist('/Game/Motion/Action/0000-COMON/PC0000_00_Sora_KH2')
out['sora_event_folder_exists'] = unreal.EditorAssetLibrary.does_directory_exist('/Game/Motion/Player/PC0000_00_Sora_KH2/Event00')
sk = unreal.load_asset('/Game/Character/Player/PC0000_00_Sora_KH2/Model/PC0000_00_S_Skeleton')
out['flat_old_root'] = unreal.EditorAssetLibrary.get_metadata_tag(sk, 'CaC.FlattenRoot.OldRoot')
a = unreal.load_asset('/Game/Motion/FieldAction/Hub00/PC0000_00_Sora_KH2/N_LifeSpot01_0')
out['sora_fa_flat_done'] = unreal.EditorAssetLibrary.get_metadata_tag(a, 'CaC.FlattenRoot.Done') if a else None
d = unreal.EndSkeletonCompatDataObject.describe_animations(['/Game/Motion/Action/0000-COMON/PC0000_Cloud/L_CMN_PC0000_00_Payment.L_CMN_PC0000_00_Payment'])
out['describe'] = d[:2500]
result = json.dumps(out, indent=1)
