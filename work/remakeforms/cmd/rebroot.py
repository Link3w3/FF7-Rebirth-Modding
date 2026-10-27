# Root (Trans) motion and hip height of Rebirth's own Sephiroth animations made from Remake's boss ones, 15 samples a
# second, to see how the game's player versions travel (for the REMAKE forms' abilities)
import json
AL = unreal.AnimationLibrary
P = '/Game/Motion/Player/PC0010_Sephiroth/Battle00/'
T = '/Game/Motion/Player/PC0010_Sephiroth_Transform/Battle00/'
names = [P + n for n in ('B_AtkLimit01_0', 'B_AtkLimit01_1', 'B_AtkBurst02_0', 'B_AtkBurst02_1', 'B_AtkBurst01_0', 'B_AtkBurst01_1', 'B_SAttack01_0', 'B_NAttack04_0', 'B_NPAttack01', 'B_SAttack10_0')] + \
        [T + n for n in ('B_AtkTenshi01_0', 'B_AtkTenshi01_1', 'B_AtkStab01', 'B_AtkZekkuu01_0', 'B_AtkZekkuu01_1', 'B_AtkZekkuu01_2', 'B_AtkMag01_0', 'B_AtkMag01_1', 'B_AtkMag01_2', 'B_AtkLimit01_2', 'B_AtkLimit01_3', 'B_AtkLimit01_4')]
out = {}
for path in names:
    anim = unreal.load_asset(path)
    if not anim:
        out[path] = 'missing'
        continue
    length = anim.get_editor_property('sequence_length')
    rows = []
    f = 0
    while True:
        t = min(length, f / 15.0)
        r = AL.get_bone_pose_for_time(anim, 'Trans', t, False)
        h = AL.get_bone_pose_for_time(anim, 'C_Hip_a', t, False)
        rows.append([round(t, 3), round(r.translation.x), round(r.translation.y), round(r.translation.z), round(r.rotation.rotator().yaw, 1), round(h.translation.z)])
        if t >= length:
            break
        f += 1
    out[path.rsplit('/', 1)[1]] = {'length': length, 'rows': rows}
result = out
