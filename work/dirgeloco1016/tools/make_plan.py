"""The plan of Vincent's Dirge of Cerberus battle walk and run (dirge_locomotion_plan.json, read by the editor script):
each walk, run and strafe animation name of his battle set built as a move over a Dirge of Cerberus motion of his (Base)
from Cloud's animation of that name (its root motion moves him; the project has Cloud's battle animations, not Vincent's
game ones, whose root motion is the same: cloud_loco.json / Vincent's decoded from the game).
    make_plan.py <out json>"""
import json, sys

DOC = '/Game/Motion/Player/PC0011_00_Vincent/Battle00/p000_m001_h_%s_remap'
CLOUD = '/Game/Motion/Player/PC0000_Cloud/Battle00/%s'
# the Dirge of Cerberus motions' lengths (cook1/motions.json, as the editor measured them)
DOC_LEN = {'rn': 0.6333, 'wk': 1.3, 'wk_a': 0.9667, 'brn_a': 0.6333, 'lrn_a': 0.6333, 'rrn_a': 0.6333, 'st': 5.3, 'st_a': 1.9667}
CLOUD_LEN = json.load(open('/work/galian1016/cloud_loco.json'))
PROLOGUE = ['PC0000_04_Cloud_ZackCostume', 'PC0000_12_Cloud_ZackCostumeDirty', 'PC0000_18_Cloud_ZackCostumeAge21',
            'PC0000_19_Cloud_ZackCostumeDirtyAge21', 'PC0000_23_Cloud_ZackCostumeWet']

# key -> (Dirge of Cerberus motion, Cloud's animation; None: the key's own)
MOVES = [
    ('B_Run01_0', 'rn', 'B_Run01_0_L0'), ('B_Run01_0_L0', 'rn', None), ('B_Run01_0_L90', 'rn', None), ('B_Run01_0_L180', 'rn', None),
    ('B_Run01_0_R90', 'rn', None), ('B_Run01_0_R180', 'rn', None), ('B_Run01_1', 'rn', None), ('B_Run01_1_L180', 'rn', None),
    ('B_Run01_1_R180', 'rn', None), ('B_Run01_Up', 'rn', None), ('B_Run01_2', 'st', None), ('B_Run01_2l', 'st', None), ('B_Run01_2r', 'st', None),
    ('B_Walk01_0', 'wk', 'B_Walk01_0_L0'), ('B_Walk01_0_L0', 'wk', None), ('B_Walk01_0_L90', 'wk', None), ('B_Walk01_0_L180', 'wk', None),
    ('B_Walk01_0_R90', 'wk', None), ('B_Walk01_0_R180', 'wk', None), ('B_Walk01_1', 'wk', None), ('B_Walk01_2l', 'st', None), ('B_Walk01_2r', 'st', None),
    ('B_WalkF01_0', 'wk_a', None), ('B_WalkF01_1', 'wk_a', None), ('B_WalkF01_2l', 'st_a', None), ('B_WalkF01_2r', 'st_a', None),
    ('B_WalkB01_0', 'brn_a', None), ('B_WalkB01_1', 'brn_a', None), ('B_WalkB01_2l', 'st_a', None), ('B_WalkB01_2r', 'st_a', None),
    ('B_WalkBL01_1', 'brn_a', None), ('B_WalkBR01_1', 'brn_a', None),
    ('B_WalkL01_0', 'lrn_a', None), ('B_WalkL01_0l', 'lrn_a', None), ('B_WalkL01_1', 'lrn_a', None), ('B_WalkL01_2l', 'st_a', None),
    ('B_WalkL01_2r', 'st_a', None), ('B_WalkFL01_1', 'lrn_a', None),
    ('B_WalkR01_0', 'rrn_a', None), ('B_WalkR01_1', 'rrn_a', None), ('B_WalkR01_2l', 'st_a', None), ('B_WalkR01_2r', 'st_a', None),
    ('B_WalkFR01_1', 'rrn_a', None),
]
# starts too short for one Dirge of Cerberus cycle are played slower to fill one (no jump into the loop)
STRETCH = {'B_WalkB01_0', 'B_WalkL01_0', 'B_WalkL01_0l', 'B_Walk01_0', 'B_Walk01_0_L0'}


def main(out):
    moves = []
    for key, doc, cloud in MOVES:
        source = cloud or key
        clip = CLOUD_LEN[source]['length']
        base_len = DOC_LEN[doc]
        stop = doc in ('st', 'st_a')
        speed = 1.0
        if key in STRETCH:
            speed = round(clip / base_len, 4)
        loops = max(1, round(base_len / (clip / speed)))
        loop = not stop and loops == 1
        move = {'set': 'Battle00', 'name': key, 'animation': CLOUD % source, 'notifies_from': CLOUD % source,
                'base': DOC % doc, 'base_loop': loop, 'speed': speed}
        # what the built move should do (checked against the build's own report and the built animation)
        length = base_len if loop else clip / speed
        dist = CLOUD_LEN[source]['dist']
        move['expect'] = {'length': round(length, 3), 'root_travel': dist, 'speed_cm_s': round(dist / length, 1) if length else 0,
                          'game_speed_cm_s': round(dist / clip, 1), 'yaw': CLOUD_LEN[source]['yaw']}
        moves.append(move)
    describe = sorted({m['animation'] for m in moves} | {m['base'] for m in moves})
    plan = {
        'plan': "Vincent: the Dirge of Cerberus battle walk and run, moving him (built moves)",
        'data_object': '/Game/Character/Player/PC0011_00_Vincent_Standard/Model/Vincent_Moves',
        'row_character': 'PC0000_00_Cloud_Standard',
        'add_characters': PROLOGUE,
        'skeleton': '/Game/Character/Player/PC0011_00_Vincent_Standard/Model/PC0011_00_Skeleton.PC0011_00_Skeleton',
        'bone_map': 'Trans=Trans',
        'build_folder': '/Game/RebirthSkelCompat/Built/Vincent',
        'moves': moves,
        'describe': describe,
    }
    with open(out, 'w', newline='\n') as f:
        json.dump(plan, f, indent=1)
    for m in moves:
        e = m['expect']
        print('%-16s base %-6s %-5s x%-6s %.2f s, %5.0f cm/s (game %5.0f), yaw %+.0f' % (
            m['name'], m['base'].split('_h_')[1][:-6], 'loop' if m['base_loop'] else '', m['speed'], e['length'], e['speed_cm_s'], e['game_speed_cm_s'], e['yaw']))
    print(len(moves), 'moves;', len(describe), 'animations to load')


if __name__ == '__main__':
    main(sys.argv[1])
