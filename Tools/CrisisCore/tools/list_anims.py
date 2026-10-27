import unreal
ar = unreal.AssetRegistryHelpers.get_asset_registry()
out = {}
for f in ['/Game/Motion/Player/PC0010_Sephiroth/Battle00', '/Game/Motion/Player/PC0010_Sephiroth/Neutral00']:
    assets = ar.get_assets_by_path(f, recursive=False)
    out[f] = sorted(str(a.asset_name) for a in assets)[:400]
result = out
