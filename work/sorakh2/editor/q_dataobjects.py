import unreal, json
reg = unreal.AssetRegistryHelpers.get_asset_registry()
flt = unreal.ARFilter(class_names=['EndSkeletonCompatDataObject'], recursive_classes=True)
assets = reg.get_assets(flt)
out = []
for ad in assets:
    p = str(ad.object_path)
    a = ad.get_asset()
    rows = []
    try:
        for r in a.get_editor_property('animation_sets'):
            rows.append(dict(chars=len(r.get_editor_property('characters')), first=(list(r.get_editor_property('characters')) or [''])[0],
                             skel=str(r.get_editor_property('character_skeleton')), moves=len(r.get_editor_property('moves')),
                             build_folder=str(r.get_editor_property('build_folder'))))
    except Exception as e:
        rows = 'ERR ' + str(e)[:200]
    out.append(dict(path=p, rows=rows))
result = json.dumps(out, indent=0)
