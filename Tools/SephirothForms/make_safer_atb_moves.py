"""Safer Sephiroth's ATB abilities and transformation entrance (Battle06), for build_safer_update.py (editor 1.12.3):
  - the twelve Bizarro abilities' animations (their AnimationString_Array names), made of Bizarro Sephiroth's: the little
    Sephiroth on Bizarro's head drives Safer's upper body (Bone Map: his spine, neck, head, shoulders, arms and hands onto
    Safer's, the motion taken relative to C_SmlSpine_Spo, so Bizarro's body moving under him is left out; Source Turn 90:
    Bizarro faces +X, Safer +Y), over Safer's idle (Base), Safer's root kept (no root motion), the notifies (hits, damage
    sources) and sounds of Bizarro's animation, not its effects (Bizarro's own sockets and size);
  - Safer's own animations where Bizarro's cannot be sampled (Quat_128: B_AtkMagB01_2, B_AtkStigma01_0) or are composites
    (B_AtkStigma01_1_Comp, B_AtkEyeMagic01_1_Comp_3, the gates' B_AtkGokumonShort / Long): the notifies of Bizarro's, the
    length of Bizarro's ("match": build_safer_update.py sets the speed from the editor's lengths);
  - the gates' end (B_SaferGokumon01_1: the compat file chains it after B_AtkHellsGate01 / B_AtkUnholyGate01, as Bizarro's
    Battle05 does with B_AtkGokumon01_1);
  - B_SaferEnter01: Safer's cutscene entrance (he comes down from the sky), whole, for the SAFER form's "entrance".
    make_safer_atb_moves.py <out json>"""
import json, sys

SET = 'Battle06'
B00 = '/Game/Motion/Enemy/EB2210_BizarroSephiroth/Battle00/'
B00C = '/Game/Motion/Enemy/EB2210_BizarroSephiroth/Battle00_Comp/'
B01 = '/Game/Motion/Enemy/EB2210_BizarroSephiroth/Battle01/'
B01C = '/Game/Motion/Enemy/EB2210_BizarroSephiroth/Battle01_Comp/'
SF = '/Game/Motion/Player/PC0010_999_Safer_Sephiroth/Battle00/anim_mo572_%s_Rebirth_BindingRepair'
SEPH = '/Game/Motion/Player/PC0010_Sephiroth/Battle00/'
IDLE = SF % 'idle_001_02_lp'                    # 8.0 s
S6 = SF % 'skill_006'                           # 3.70 s: a slow cast
ST1, ST2, ST3 = SF % 'status_001_01', SF % 'status_001_02_lp', SF % 'status_001_03'   # 1.80 s / 3.00 s (loop) / 1.07 s
ENTER = SF % 'cutscene_boss_enter_01'           # 8.0 s: he comes down from the sky

# Bizarro's little Sephiroth -> Safer (Source=Target; @: the bone the motion is taken relative to)
BONE_MAP = ', '.join([
    'C_SmlSpine_a=C_Spine_b', 'C_SmlSpine_b=C_Spine_c', 'C_SmlSpine_c=C_Spine_d', 'C_SmlNeck_a=C_Neck_a', 'C_SmlHead_a=C_Head_a',
    'L_SmlShoulder_a=L_Shoulder_a', 'L_SmlUpperArm_a=L_UpperArm_a', 'L_SmlForearm_a=L_Forearm_a', 'L_SmlHand_a=L_Hand_a',
    'R_SmlShoulder_a=R_Shoulder_a', 'R_SmlUpperArm_a=R_UpperArm_a', 'R_SmlForearm_a=R_Forearm_a', 'R_SmlHand_a=R_Hand_a',
    '@C_SmlSpine_Spo'])
SOURCE_TURN = 90.0

# the abilities (PC0010_BZ_*, the data container's BattleAbility rows) and their animations
ABILITIES = {
    'PC0010_BZ_Octaslash': ['B_AtkOmniSlash01_0', 'B_AtkOmniSlash01_1', 'B_AtkOmniSlash01_2'],
    'PC0010_BZ_Zanshin': ['B_AtkZanShin01_0'],
    'PC0010_BZ_ZanshinProfaned': ['B_AtkZanShin01_1'],
    'PC0010_BZ_HellsGate': ['B_AtkHellsGate01'],
    'PC0010_BZ_UnholyGate': ['B_AtkUnholyGate01'],
    'PC0010_BZ_Swarm': ['B_AtkMagB01_0', 'B_AtkMagB01_1', 'B_AtkMagB01_2', 'B_AtkMagB01_3', 'B_AtkMagB01_4'],   # (+ B_AtkMagB01_add: an additive, left out)
    'PC0010_BZ_HeartlessAngel': ['B_AtkAngel01_0', 'B_AtkAngel01_1', 'B_AtkAngel01_2'],
    'PC0010_BZ_ApocalypticFire': ['B_AtkBodyExplode01'],
    'PC0010_BZ_Profane': ['B_AtkStigma01_0', 'B_AtkStigma01_1_Comp', 'B_AtkStigma01_2'],
    'PC0010_BZ_WhisperVortex': ['B_AtkFeelerWingSmash01'],
    'PC0010_BZ_Atonement': ['B_AtkWingSmashR01'],
    'PC0010_BZ_LacrymaDeus': ['B_AtkEyeMagic01_0', 'B_AtkEyeMagic01_1', 'B_AtkEyeMagic01_1_Comp_3', 'B_AtkEyeMagic01_2'],
}
FOLDER = {'B_AtkStigma01_2': B01}
# Safer's own animation (clip: None = whole) under the notifies of Bizarro's, as long as Bizarro's
STAND_INS = {
    'B_AtkMagB01_2': (ST2, None, B00 + 'B_AtkMagB01_2'),                       # (Quat_128) Swarm's cast, held
    'B_AtkStigma01_0': (ST1, None, B01 + 'B_AtkStigma01_0'),                   # (Quat_128) Profane's start
    'B_AtkStigma01_1_Comp': (ST2, None, B01C + 'B_AtkStigma01_1_Comp'),        # (composite) Profane's beams
    'B_AtkEyeMagic01_1_Comp_3': (ST2, None, B00C + 'B_AtkEyeMagic01_1_Comp_3'),  # (composite) Lacryma Deus's eye beams
    'B_AtkHellsGate01': (S6, None, B00C + 'B_AtkGokumonShort'),                # (composite) Hell's Gate
    'B_AtkUnholyGate01': (S6, None, B00C + 'B_AtkGokumonLong'),                # (composite) Unholy Gate
}
GATE_END = 'B_SaferGokumon01_1'
CHAINS = {'B_AtkHellsGate01': [GATE_END], 'B_AtkUnholyGate01': [GATE_END]}   # (the compat file plays the end after the gate)
ENTRANCE = 'B_SaferEnter01'


def path(p):
    return p if '.' in p.rsplit('/', 1)[-1] else p + '.' + p.rsplit('/', 1)[-1]


def main(out):
    moves = []
    for ability, names in ABILITIES.items():
        for name in names:
            if name in STAND_INS:
                anim, clip, notifies = STAND_INS[name]
                m = {'name': name, 'set': SET, 'animation': path(anim), 'build': True, 'notifies_from': path(notifies), 'match': path(notifies),
                     'ability': ability, 'kind': 'stand_in'}
                if clip:
                    m['clip'] = list(clip)
            else:
                source = path(FOLDER.get(name, B00) + name)
                m = {'name': name, 'set': SET, 'animation': source, 'build': True, 'retarget': 'motion', 'bone_map': BONE_MAP,
                     'source_turn': SOURCE_TURN, 'base': path(IDLE), 'base_loop': False, 'keep_base_root': True, 'notifies_from': source,
                     'source_effects': True, 'source_sounds_only': True, 'ability': ability, 'kind': 'bizarro'}
            moves.append(m)
    moves.append({'name': GATE_END, 'set': SET, 'animation': path(ST3), 'build': True, 'notifies_from': path(B00 + 'B_AtkGokumon01_1'),
                  'match': path(B00 + 'B_AtkGokumon01_1'), 'kind': 'gate_end'})
    moves.append({'name': ENTRANCE, 'set': SET, 'animation': path(ENTER), 'build': True, 'notifies_from': path(SEPH + 'B_Idle01_1'),
                  'kind': 'entrance'})
    names = [m['name'] for m in moves]
    assert len(names) == len(set(names)), 'a name twice'
    plan = {'set': SET, 'moves': moves, 'abilities': ABILITIES, 'chains': CHAINS, 'entrance': ENTRANCE, 'bone_map': BONE_MAP,
            'describe': sorted({m['notifies_from'] for m in moves} | {m['animation'] for m in moves} | {path(IDLE)})}
    json.dump(plan, open(out, 'w'), indent=1)
    kinds = {}
    for m in moves:
        kinds[m['kind']] = kinds.get(m['kind'], 0) + 1
    print('%d moves (%s) -> %s' % (len(moves), ', '.join('%d %s' % (n, k) for k, n in kinds.items()), out))


if __name__ == '__main__':
    main(sys.argv[1])
