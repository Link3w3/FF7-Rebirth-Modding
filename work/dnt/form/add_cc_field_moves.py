"""The CRISIS CORE skins' field set (Neutral10) added to a moves plan (plan.json, built with the DISSIDIA NT form's moves in
one go): Crisis Core Reunion Sephiroth's own field idle, walk and run (and his battle run as the field dash), retargeted
onto Rebirth Sephiroth's skeleton for the CRISIS CORE form (/Game/Motion/Player/PC0010_16_CrisisCore_Sephiroth/CCRoot, in
the project since that build), built as Sephiroth's Neutral00 moves of those names (their gameplay notifies: footsteps).
In game the CRISIS CORE skins name the set ("sets": {"Neutral00": "Neutral10"}: while one is worn, the game's lookups of
Neutral00 get Neutral10, made from Sephiroth's Neutral00 with these moves over it); everything else in the field stays his.
    add_cc_field_moves.py <plan.json in> <plan.json out>"""
import json
import sys

SET = 'Neutral10'
CC = '/Game/Motion/Player/PC0010_16_CrisisCore_Sephiroth/CCRoot/'
SEPH = '/Game/Motion/Player/PC0010_Sephiroth/Neutral00/'
MOVES = {                      # Sephiroth's field move -> Crisis Core's animation (in-place loops)
    'N_Idle01_1': 'CC_gnm_stand',
    'N_Walk01_1': 'CC_gnm_walk',
    'N_Run01_1': 'CC_gnm_run',
    'N_Dash01_1': 'CC_btm_run1',
}


def main(src, dst):
    plan = json.load(open(src))
    assert not any(m['set'] == SET for m in plan['moves']), 'the plan has ' + SET + ' already'
    for name, anim in MOVES.items():
        plan['moves'].append({'set': SET, 'name': name, 'animation': CC + anim, 'notifies_from': SEPH + name, 'hits': [],
                              'source': anim})
        plan['keys'].setdefault(SET, {})[name] = '/Game/RebirthSkelCompat/Built/SephirothForms/%s/%s.%s' % (SET, name, name)
    plan.setdefault('field_sets', {})[SET] = {'from': '/Game/Motion/Player/PC0010_Sephiroth/Neutral00.Neutral00', 'for': 'the CRISIS CORE skins'}
    json.dump(plan, open(dst, 'w'), indent=1)
    print('%s: %d moves (%s)' % (dst, len(plan['moves']), ', '.join('%s %d' % (s, sum(1 for m in plan['moves'] if m['set'] == s))
                                                             for s in sorted(set(m['set'] for m in plan['moves'])))))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
