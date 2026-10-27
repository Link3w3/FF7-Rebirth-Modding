"""Fully Playable Young Sephiroth's forms JSON, v3 (Create a Character System 3.9.0): v2c's (make_forms_json_v2.py: the
switch lines of WINGED and FLYING in his young voice) with his voice per form ("voice", 3.9.0): the row speaks with his own
voice bank, VO_PC0010_13_YoungSephiroth (YoungSephirothVoice_P), in place of Sephiroth's VO_PC0010_00_Sephiroth, so the
voice lines of his moves are young in YOUNG SEPHIROTH, WINGED and FLYING (and in the field); OLDER SEPHIROTH, KH2, BIZARRO
and SAFER speak with Sephiroth's own ("own"). Written in the file's own format.
    make_forms_json_v3.py <make_forms_json_v2.py's .json> <out .json>"""
import hashlib, json, sys

OLD_VO = '/Game/Sound/Voice/{language}/Character/Player/VO_PC0010_00_Sephiroth'
YOUNG_VO = '/Game/Sound/Voice/{language}/Character/Player/VO_PC0010_13_YoungSephiroth'
ADULT_FORMS = ['OLDER SEPHIROTH', 'KH2', 'BIZARRO', 'SAFER']
NOTE = (' (Create a Character System 3.9.0 "voice": the voice lines of his moves are his own young voice in YOUNG SEPHIROTH, '
        'WINGED and FLYING and in the field, Sephiroth\'s in OLDER SEPHIROTH, KH2, BIZARRO and SAFER.)')


def main(src, out):
    raw = open(src, 'rb').read()
    d = json.loads(raw)
    assert json.dumps(d, indent=1, ensure_ascii=False).encode('utf-8') == raw, 'the file is not in the format this writes'
    row = d['animation_sets'][0]
    forms = row['forms']['list']
    names = [f['name'] for f in forms]
    assert names == ['YOUNG SEPHIROTH', 'OLDER SEPHIROTH', 'WINGED', 'FLYING', 'KH2', 'BIZARRO', 'SAFER'], names
    assert 'voice' not in row and not any('voice' in f for f in forms)
    # the row's voice, its keys placed after "forms" (the order the file's readers do not care about)
    row['voice'] = {'bank': YOUNG_VO, 'replaces': [OLD_VO]}
    for f in forms:
        if f['name'] in ADULT_FORMS:
            f['voice'] = 'own'
    assert NOTE not in d['source']
    d['source'] += NOTE
    text = json.dumps(d, indent=1, ensure_ascii=False).encode('utf-8')
    json.loads(text)
    open(out, 'wb').write(text)
    print('row voice:', row['voice'])
    print('own voice:', [f['name'] for f in forms if f.get('voice') == 'own'])
    print('%s -> %s (%d -> %d bytes) md5 %s' % (src, out, len(raw), len(text), hashlib.md5(text).hexdigest()))


if __name__ == '__main__':
    main(*sys.argv[1:3])
