# step 3c: the raw data of each new animation marked changed (a curve added and taken away again: each does
# MarkRawDataAsModified), so its compression is made anew without the curves that are gone from its raw data (the cook
# kept the old compressed curves: the raw data guid had not changed), then saved through Copy Notifies Onto (CA_Empty).
AL = unreal.AnimationLibrary
EMPTY = '/Game/RebirthSkelCompat/Imported/CloudActionTools/CA_Empty.CA_Empty'
FLOAT = unreal.RawCurveTrackTypes.RCT_FLOAT
out = []
for k in K:
    tos, notes = [], []
    for c, s in pairs(k):
        a = unreal.load_asset(s)
        try:
            AL.add_curve(a, 'AutoSaccadeX', FLOAT, False)
            AL.remove_curve(a, 'AutoSaccadeX', False)
        except Exception as e:
            notes.append('%s: %s' % (s.rsplit('.', 1)[1], str(e)[:120]))
        tos.append(s)
    rep = LIB.copy_notifies_onto([EMPTY] * len(tos), tos, False)
    left = sum(1 for s in tos if len(AL.get_animation_curve_names(unreal.load_asset(s), FLOAT)))
    out.append(dict(job=JOBS[k][0], n=len(tos), left=left, notes=notes[:3], report=rep.strip().splitlines()[-1][:120] if rep.strip() else ''))
result = json.dumps(out, indent=1)
