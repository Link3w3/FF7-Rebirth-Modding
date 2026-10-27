# Cloud's area actions now in Content/Motion/Action (legacy cooked, as the project has his other motion folders): scan and load
import unreal, json
ar = unreal.AssetRegistryHelpers.get_asset_registry()
ar.scan_paths_synchronous(['/Game/Motion/Action'], True)
out = {}
f = unreal.ARFilter(package_paths=['/Game/Motion/Action'], recursive_paths=True)
found = ar.get_assets(f)
out['registry'] = len(found)
a = unreal.load_asset('/Game/Motion/Action/0000-COMON/PC0000_Cloud/L_CMN_PC0000_00_Payment.L_CMN_PC0000_00_Payment')
out['payment'] = None if a is None else dict(cls=a.get_class().get_name(), skel=a.get_editor_property('skeleton').get_path_name(),
                                            len=a.get_editor_property('sequence_length'), blend=a.get_editor_property('override_behavior_action_blend_time'))
d = unreal.EndSkeletonCompatDataObject.describe_animations(['/Game/Motion/Action/0000-COMON/PC0000_Cloud/L_CMN_PC0000_00_Payment.L_CMN_PC0000_00_Payment'])
out['describe'] = d[:3000]
result = json.dumps(out, indent=1)
