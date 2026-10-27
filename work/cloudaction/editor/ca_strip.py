# step 3b: the curves Copy Notifies Onto put on the new animations taken off again (Sora's game skeleton has none of their
# names, and the game read past the end of a buffer on them: the door crash), each saved through Copy Notifies Onto from an
# animation with nothing to copy (CA_Empty: no notifies, sync markers or curves), so the plugin's save path saves it.
AL = unreal.AnimationLibrary
TOOLS = '/Game/RebirthSkelCompat/Imported/CloudActionTools'
EMPTY = TOOLS + '/CA_Empty.CA_Empty'
if not unreal.EditorAssetLibrary.does_asset_exist(EMPTY.split('.')[0]):
    LIB.import_key_animations(os.path.join(BASE, 'empty'), SKEL, TOOLS)
out = []
for k in K:
    prs = pairs(k)
    tos, had = [], 0
    for c, s in prs:
        a = unreal.load_asset(s)
        n = len(AL.get_animation_curve_names(a, unreal.RawCurveTrackTypes.RCT_FLOAT))
        if n:
            AL.remove_all_curve_data(a)
            had += 1
        tos.append(s)
    rep = LIB.copy_notifies_onto([EMPTY] * len(tos), tos, False)
    left = sum(1 for s in tos if len(AL.get_animation_curve_names(unreal.load_asset(s), unreal.RawCurveTrackTypes.RCT_FLOAT)))
    out.append(dict(job=JOBS[k][0], n=len(tos), had_curves=had, left=left, report=rep.strip().splitlines()[-1][:200] if rep.strip() else ''))
result = json.dumps(out, indent=1)
