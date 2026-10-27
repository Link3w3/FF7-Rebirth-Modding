import unreal, json
ROOT = '/Game/Motion/Player/PC0000_00_Sora_KH2/Battle00'
reg = unreal.AssetRegistryHelpers.get_asset_registry()
assets = reg.get_assets_by_path(ROOT, recursive=False)
out = {}
for ad in assets:
    n = str(ad.asset_name)
    a = ad.get_asset()
    src = ''
    try:
        aid = a.get_editor_property('asset_import_data')
        src = aid.get_first_filename() if aid else ''
    except Exception as e:
        src = 'ERR ' + str(e)[:60]
    out[n] = dict(cls=str(ad.asset_class), src=src)
subs = reg.get_sub_paths(ROOT, False)
result = json.dumps(dict(n=len(out), subs=[str(s) for s in subs], assets=out), indent=0)
