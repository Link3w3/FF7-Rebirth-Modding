# seq = 1792699288074
# Remake Sephiroth's motions for a contact sheet: every animation of EB0021's Battle00 and Battle01, 15 samples a
# second: the root (Trans, its motion) and 19 body bones relative to it (hips, chest, neck, head, arms, sword hand, legs)
import unreal, json
AL = unreal.AnimationLibrary
ML = unreal.MathLibrary
EAL = unreal.EditorAssetLibrary
B = '/Game/GameContents/Motion/Enemy/EB0021_Sephiroth/'
PARENT = {"C_Hip_a": None, "C_Spine_a": "C_Hip_a", "C_Spine_b": "C_Spine_a", "C_Spine_c": "C_Spine_b", "C_Spine_d": "C_Spine_c", "L_Shoulder_a": "C_Spine_d", "L_UpperArm_a": "L_Shoulder_a", "L_Forearm_a": "L_UpperArm_a", "L_Hand_a": "L_Forearm_a", "L_Weapon_a": "L_Hand_a", "R_Shoulder_a": "C_Spine_d", "R_UpperArm_a": "R_Shoulder_a", "R_Forearm_a": "R_UpperArm_a", "R_Hand_a": "R_Forearm_a", "C_Neck_a": "C_Spine_d", "C_Head_a": "C_Neck_a", "L_UpperLeg_a": "C_Hip_a", "L_Foreleg_a": "L_UpperLeg_a", "L_Foot_a": "L_Foreleg_a", "L_Toe_a": "L_Foot_a", "R_UpperLeg_a": "C_Hip_a", "R_Foreleg_a": "R_UpperLeg_a", "R_Foot_a": "R_Foreleg_a", "R_Toe_a": "R_Foot_a"}
ORDER = ["C_Hip_a", "C_Spine_a", "C_Spine_b", "C_Spine_c", "C_Spine_d", "L_Shoulder_a", "L_UpperArm_a", "L_Forearm_a", "L_Hand_a", "L_Weapon_a", "R_Shoulder_a", "R_UpperArm_a", "R_Forearm_a", "R_Hand_a", "C_Neck_a", "C_Head_a", "L_UpperLeg_a", "L_Foreleg_a", "L_Foot_a", "L_Toe_a", "R_UpperLeg_a", "R_Foreleg_a", "R_Foot_a", "R_Toe_a"]
WANT = ["C_Hip_a", "C_Spine_d", "C_Neck_a", "C_Head_a", "L_UpperArm_a", "L_Forearm_a", "L_Hand_a", "L_Weapon_a", "R_UpperArm_a", "R_Forearm_a", "R_Hand_a", "L_UpperLeg_a", "L_Foreleg_a", "L_Foot_a", "L_Toe_a", "R_UpperLeg_a", "R_Foreleg_a", "R_Foot_a", "R_Toe_a"]
paths = [a for sub in ('Battle00', 'Battle01') for a in EAL.list_assets(B + sub, recursive=False, include_folder=False)]
out = {}
for path in paths:
    anim = unreal.load_asset(path)
    if not isinstance(anim, unreal.AnimSequence):
        continue
    length = anim.get_editor_property('sequence_length')
    rows = []
    f = 0
    while True:
        t = min(length, f / 15.0)
        root = AL.get_bone_pose_for_time(anim, 'Trans', t, False)
        cs = {}
        for b in ORDER:
            local = AL.get_bone_pose_for_time(anim, b, t, False)
            p = PARENT[b]
            cs[b] = ML.compose_transforms(local, cs[p]) if p else local
        r = root.rotation.rotator()
        row = [round(t, 4), round(root.translation.x, 1), round(root.translation.y, 1), round(root.translation.z, 1), round(r.yaw, 1)]
        for b in WANT:
            v = cs[b].translation
            row += [round(v.x, 1), round(v.y, 1), round(v.z, 1)]
        q = cs['L_Weapon_a'].rotation
        row += [round(q.x, 4), round(q.y, 4), round(q.z, 4), round(q.w, 4)]
        rows.append(row)
        if t >= length:
            break
        f += 1
    out[path.rsplit('.', 1)[0].rsplit('/', 2)[-2] + '/' + path.rsplit('.', 1)[1]] = {'length': length, 'samples': rows}
dst = 'C:/FF7R2UProj/Saved/RebirthSkelCompat/RemakeForms/motion_eb0021.json'
json.dump({'bones': WANT, 'animations': out}, open(dst, 'w'))
result = {'animations': len(out), 'file': dst}
