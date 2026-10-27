# where the cooked curves of the new animations come from (raw curves are gone, the cooks still have AutoSaccadeX/Y)
AL = unreal.AnimationLibrary
out = {}
for c, s in pairs(0)[:3] + pairs(45)[:2]:
    a = unreal.load_asset(s)
    d = {}
    for t in ('RCT_FLOAT', 'RCT_VECTOR', 'RCT_TRANSFORM'):
        try:
            d[t] = [str(n) for n in AL.get_animation_curve_names(a, getattr(unreal.RawCurveTrackTypes, t))]
        except Exception as e:
            d[t] = str(e)[:80]
    for n in ('AutoSaccadeX', 'Attach_Item'):
        try:
            d['exists ' + n] = AL.does_curve_exist(a, n, unreal.RawCurveTrackTypes.RCT_FLOAT)
        except Exception as e:
            d['exists ' + n] = str(e)[:80]
    d['dirty'] = unreal.EditorAssetLibrary.save_loaded_asset(a, True) if False else None
    out[s.rsplit('/', 1)[1]] = d
sk = unreal.load_asset(SKEL)
try:
    out['skeleton curve names'] = [str(n) for n in sk.get_editor_property('smart_names')][:5] if False else None
except Exception as e:
    out['skeleton'] = str(e)[:100]
result = json.dumps(out, indent=1)
