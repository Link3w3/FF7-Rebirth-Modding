import unreal, json
AL = unreal.AnimationLibrary
BONES = json.load(open(r'C:/FF7R2UProj/Tools/CrisisCore/work/reb_bones.json'))
ANIMS = ['/Game/Motion/Player/PC0010_Sephiroth/Battle00/B_Idle01_1', '/Game/Motion/Player/PC0010_Sephiroth/Battle00/B_NAttack01_0',
         '/Game/Motion/Player/PC0010_Sephiroth/Battle00/B_NAttack03_0', '/Game/Motion/Player/PC0010_Sephiroth/Neutral00/N_Run01_1']
out = {}
for a in ANIMS:
    seq = unreal.load_asset(a)
    if seq is None:
        out[a] = 'not loaded'; continue
    L = AL.get_sequence_length(seq)
    frames = []
    for k in range(6):
        t = L * k / 5.0
        bones = {}
        for b in BONES:
            try:
                tr = AL.get_bone_pose_for_time(seq, b, t, False)
                q = tr.rotation; v = tr.translation
                bones[b] = [q.x, q.y, q.z, q.w, v.x, v.y, v.z]
            except Exception as e:
                bones[b] = None
        frames.append(dict(time=t, bones=bones))
    out[a] = dict(length=L, frames=frames)
json.dump(out, open(r'C:/FF7R2UProj/Tools/CrisisCore/work/reb_anim_samples.json', 'w'))
result = {a: (v if isinstance(v, str) else dict(length=v['length'], n=len(v['frames']), missing=[b for b, x in v['frames'][0]['bones'].items() if x is None][:10])) for a, v in out.items()}
