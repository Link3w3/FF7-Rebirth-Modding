import unreal, json
reg = unreal.AssetRegistryHelpers.get_asset_registry()
out = {}
for root in ('/Game/Motion/Player/PC0000_Cloud', '/Game/Motion/Player/PC0000_00_Sora_KH2'):
    assets = reg.get_assets_by_path(root, recursive=False)
    out[root] = sorted('%s:%s' % (a.asset_name, a.asset_class) for a in assets)
    out[root + ' subs'] = [str(s) for s in reg.get_sub_paths(root, False)]
d = unreal.EndSkeletonCompatDataObject.describe_animations(['/Game/Motion/Player/PC0000_Cloud/Battle00.Battle00'])
out['describe_len'] = len(d)
result = json.dumps(out, indent=0)
open(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()) + 'ModExtract/sorarig/cloud_battle00_describe.json', 'w').write(d)
