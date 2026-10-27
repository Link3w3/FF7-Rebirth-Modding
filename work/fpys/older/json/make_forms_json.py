"""Fully Playable Young Sephiroth's forms JSON with his OLDER SEPHIROTH form: the base form (the list's first, the
character's own model) named YOUNG SEPHIROTH, and right after it OLDER SEPHIROTH: the game's own Sephiroth (PC0010_15, the
copy of Rebirth's PC0010_00 in YoungSephiroth_P) put on the game's way (as_look, as the KH2 form's model), on the normal
form's moves (no pack: Battle00, the form keeps itself when the game goes back to that pack), with the real Masamune.
Everything else as it was. Written in the file's own format (1-space indent, UTF-8, no newline at the end).
    make_forms_json.py <current .json> <out .json>"""
import hashlib, json, sys

MODEL = '/Game/Character/Player/PC0010_15_Sephiroth_Older/Model/PC0010_15.PC0010_15'
MASAMUNE = '/Game/BluePrint/Character/Weapon/WE1021_10_SephirothIllusion_MasamuneCutScale.WE1021_10_SephirothIllusion_MasamuneCutScale_C'
SE = '/Game/Sound/SE/Character/Player/SE_PC0010_00_Sephiroth_Standard.SE_PC0010_00_Sephiroth_Standard'
VO = '/Game/Sound/Voice/{language}/Character/Player/VO_PC0010_00_Sephiroth.VO_PC0010_00_Sephiroth'
OLDER = {
    'name': 'OLDER SEPHIROTH',
    'model': MODEL,
    'as_look': True,
    'effects': [
        {'effect': '/Game/Effect/Character/Player/PC0010_Sephiroth/Particle/FX_PC0010_Warp_FadeApp_01.FX_PC0010_Warp_FadeApp_01', 'socket': 'C_Spine_c'},
        {'effect': '/Game/Effect/Character/Player/PC0010_Sephiroth/Particle/FX_PC0010_Aura_Body_01.FX_PC0010_Aura_Body_01'},
    ],
    'sounds': [
        {'bank': SE, 'cue': 'SE_PC0010_10_B_AtkTenshi01_1_squat'},
        {'bank': VO, 'cue': 'Atk_Ability_02'},
    ],
    'weapon': MASAMUNE,
}
OLD_MENU = '(hold Triangle: NORMAL, WINGED, FLYING, KH2, BIZARRO, SAFER). NORMAL has his base abilities'
NEW_MENU = ('(hold Triangle: YOUNG SEPHIROTH, OLDER SEPHIROTH, WINGED, FLYING, KH2, BIZARRO, SAFER). YOUNG SEPHIROTH, his '
            'normal form, has his base abilities')
OLDER_NOTE = (' OLDER SEPHIROTH: his normal form\'s moves and abilities as the game\'s own Sephiroth (PC0010_15 in YoungSephiroth_P, '
              'a copy of Rebirth\'s PC0010_00 that KH2Sephiroth_P does not replace), with the real Masamune.')


def main(src, out):
    raw = open(src, 'rb').read()
    d = json.loads(raw)
    assert json.dumps(d, indent=1, ensure_ascii=False).encode('utf-8') == raw, 'the file is not in the format this writes'
    sets = d['animation_sets']
    assert len(sets) == 1
    forms = sets[0]['forms']['list']
    names = [f['name'] for f in forms]
    assert names == ['NORMAL', 'WINGED', 'FLYING', 'KH2', 'BIZARRO', 'SAFER'], names
    assert not any('model' in f or 'pack' in f for f in forms[:1])
    assert not any(f.get('revert_to') for f in forms), 'a form names another by name'
    assert d['source'].count(OLD_MENU) == 1
    forms[0]['name'] = 'YOUNG SEPHIROTH'
    forms.insert(1, OLDER)
    d['source'] = d['source'].replace(OLD_MENU, NEW_MENU)
    i = d['source'].find(NEW_MENU)
    end = d['source'].find('. ', i + len(NEW_MENU))
    # the note goes after the sentence about his normal form's abilities
    j = d['source'].find('(the casts and the warp stab come from the transformed Sephiroth\'s sets).')
    assert j > i, 'where the note goes'
    j += len('(the casts and the warp stab come from the transformed Sephiroth\'s sets).')
    d['source'] = d['source'][:j] + OLDER_NOTE + d['source'][j:]
    text = json.dumps(d, indent=1, ensure_ascii=False).encode('utf-8')
    json.loads(text)
    open(out, 'wb').write(text)
    print('forms:', [f['name'] for f in json.loads(text)['animation_sets'][0]['forms']['list']])
    print('%s -> %s (%d -> %d bytes) md5 %s' % (src, out, len(raw), len(text), hashlib.md5(text).hexdigest()))


if __name__ == '__main__':
    main(*sys.argv[1:3])
