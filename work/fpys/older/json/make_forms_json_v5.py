"""Fully Playable Young Sephiroth's forms JSON, v5 (Create a Character System 3.9.3): v4's (make_forms_json_v4.py) with
  * WINGED (Battle02) given every ATB ability FLYING (Battle03) has: its own commands first, then FLYING's commands and
    FLYING's weapon abilities as more commands (3.9.3 shows a pack's commands 5 at a time, L1 / R1 between the pages), and
    the Transform Battle01 animations those play (Feeler Tornado, Warp Stab, Feeler Laser, Last Attack) as Battle02 moves
    (the ones it lacks; the others it already has from the Transform Battle00 sets);
  * the forms' Masamune aura (FX_PC0010_10_SetFeeler_Sword_01, the data container v7's WE1021_10 resident effect) preloaded.
Written in the file's own format.
    make_forms_json_v5.py <make_forms_json_v4.py's .json> <out .json>"""
import hashlib, json, sys

BATTLE01 = '/Game/Motion/Player/PC0010_Sephiroth_Transform/Battle01/%s.%s'
# FLYING's abilities' animations WINGED does not have (checked against its sources and moves: make_forms_json_v5 notes)
NEW_MOVES = ['B_AtkFeelerTornado01_0', 'B_AtkFeelerTornado01_1', 'B_AtkFeelerTornado01_2', 'B_AtkStab01',
             'B_AtkFeelerLaser01_0', 'B_AtkFeelerLaserL01_1', 'B_AtkFeelerLaserR01_1', 'B_AtkFeelerLaser01_2',
             'B_AtkFinalAttack01_0', 'B_AtkFinalAttack01_1', 'B_AtkFinalAttack01_2']
SWORD_AURA = '/Game/Effect/Character/Player/PC0010_10_Sephiroth_Transform/Particle/FX_PC0010_10_SetFeeler_Sword_01.FX_PC0010_10_SetFeeler_Sword_01'
WING_AURA = '/Game/Effect/Character/Player/PC0010_10_Sephiroth_Transform/Particle/FX_PC0010_10_SetFeeler_Wing_01.FX_PC0010_10_SetFeeler_Wing_01'
NOTE = (' (Create a Character System 3.9.3: WINGED has every ATB ability FLYING has, on pages of 5 (L1 / R1); the forms\' '
        'Masamune wears the PC0010_10 boss\'s sword aura.)')


def main(src, out):
    raw = open(src, 'rb').read()
    d = json.loads(raw)
    assert json.dumps(d, indent=1, ensure_ascii=False).encode('utf-8') == raw, 'the file is not in the format this writes'
    row = d['animation_sets'][0]
    packs = {a['pack']: a for a in row['abilities']}
    winged, flying = packs['Battle02'], packs['Battle03']
    before = list(winged['commands'])
    extra = []
    for name in list(flying['commands']) + list(flying['weapon_abilities'].values()):
        if name not in before and name not in extra:
            extra.append(name)
    winged['commands'] = before + extra
    # the moves: after Battle02's last
    have = {m['key'] for m in row['moves'] if m['set'] == 'Battle02'}
    last = max(i for i, m in enumerate(row['moves']) if m['set'] == 'Battle02')
    added = []
    for key in NEW_MOVES:
        assert key not in have, key
        added.append({'set': 'Battle02', 'key': key, 'animation': BATTLE01 % (key, key)})
    row['moves'][last + 1:last + 1] = added
    # the aura
    assert SWORD_AURA not in row['preload']
    row['preload'].insert(row['preload'].index(WING_AURA) + 1, SWORD_AURA)
    assert NOTE not in d['source']
    d['source'] += NOTE
    text = json.dumps(d, indent=1, ensure_ascii=False).encode('utf-8')
    json.loads(text)
    open(out, 'wb').write(text)
    print('WINGED commands (%d, %d pages of 5): %s' % (len(winged['commands']), (len(winged['commands']) + 4) // 5, ', '.join(winged['commands'])))
    print('FLYING commands (%d): %s' % (len(flying['commands']), ', '.join(flying['commands'])))
    print('Battle02 moves added: %d (%s)' % (len(added), ', '.join(m['key'] for m in added)))
    print('preload: +%s' % SWORD_AURA.rsplit('.', 1)[1])
    print('%s -> %s (%d -> %d bytes) md5 %s' % (src, out, len(raw), len(text), hashlib.md5(text).hexdigest()))


if __name__ == '__main__':
    main(*sys.argv[1:3])
