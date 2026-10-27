# seq = 1792698180921
# Remake Sephiroth's attack motions: the Masamune hand's bone (L_Weapon_a) in the body's space (relative to Trans, no
# root motion), 30 samples a second, for finding each attack's hits from its sword's speed
import unreal, json, os
AL = unreal.AnimationLibrary
ML = unreal.MathLibrary
EAL = unreal.EditorAssetLibrary
B = '/Game/GameContents/Motion/Enemy/EB0021_Sephiroth/'
chain = ['C_Hip_a', 'C_Spine_a', 'C_Spine_b', 'C_Spine_c', 'C_Spine_d', 'L_Shoulder_a', 'L_UpperArm_a', 'L_Forearm_a', 'L_Hand_a', 'L_Weapon_a']
paths = [a for sub in ('Battle00', 'Battle01') for a in EAL.list_assets(B + sub, recursive=False, include_folder=False) if '/B_Atk' in a]
out = {}
for path in paths:
    anim = unreal.load_asset(path)
    if not isinstance(anim, unreal.AnimSequence):
        continue
    length = anim.get_editor_property('sequence_length')
    rows = []
    f = 0
    while True:
        t = min(length, f / 30.0)
        cs = unreal.Transform()
        for b in chain:
            local = AL.get_bone_pose_for_time(anim, b, t, False)
            cs = ML.compose_transforms(local, cs)
        q = cs.rotation
        rows.append([round(t, 4), round(cs.translation.x, 2), round(cs.translation.y, 2), round(cs.translation.z, 2), round(q.x, 5), round(q.y, 5), round(q.z, 5), round(q.w, 5)])
        if t >= length:
            break
        f += 1
    out[path.rsplit('.', 1)[0]] = {'length': length, 'samples': rows}
dst = 'C:/FF7R2UProj/Saved/RebirthSkelCompat/RemakeForms/sword_eb0021.json'
json.dump(out, open(dst, 'w'))
result = {'animations': len(out), 'file': dst}
