# step 1: import the key animations of jobs K (Create a Character System's Import Key Animations, the game's ACL settings)
out = []
for k in K:
    folder, dest, n, clouds = JOBS[k]
    r = LIB.import_key_animations(os.path.join(KEYS, folder.replace('\\', os.sep)), SKEL, dest)
    ok, report = (r[0], r[1]) if isinstance(r, tuple) else (r, '')
    made = sum(1 for c, s in pairs(k) if unreal.EditorAssetLibrary.does_asset_exist(s.split('.')[0]))
    out.append(dict(job=folder, ok=ok, files=n, made=made, report=report[-400:]))
result = json.dumps(out, indent=1)
