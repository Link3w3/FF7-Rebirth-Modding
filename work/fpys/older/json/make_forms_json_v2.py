"""Fully Playable Young Sephiroth's forms JSON, v2: make_forms_json.py's (YOUNG SEPHIROTH, OLDER SEPHIROTH and the rest)
with the young forms' switch lines spoken by his own voice bank, VO_PC0010_13_YoungSephiroth (YoungSephirothVoice_P):
WINGED and FLYING; OLDER SEPHIROTH, KH2, BIZARRO and SAFER keep Sephiroth's (adult) voice. Written in the file's own format.
(v2c: KH2, BIZARRO and SAFER speak with adult Sephiroth's voice, as the user asked; v2 had them young:
make_forms_json_v2_kh2young.py)
    make_forms_json_v2.py <make_forms_json.py's .json> <out .json>"""
import hashlib, json, sys

OLD_VO = '/Game/Sound/Voice/{language}/Character/Player/VO_PC0010_00_Sephiroth.VO_PC0010_00_Sephiroth'
YOUNG_VO = '/Game/Sound/Voice/{language}/Character/Player/VO_PC0010_13_YoungSephiroth.VO_PC0010_13_YoungSephiroth'
YOUNG_FORMS = ['YOUNG SEPHIROTH', 'WINGED', 'FLYING']   # (KH2, BIZARRO and SAFER: adult Sephiroth's voice, like OLDER SEPHIROTH)
NOTE = (' The young forms\' switch lines are his own voice (VO_PC0010_13_YoungSephiroth in YoungSephirothVoice_P: Sephiroth\'s lines '
        'made younger); OLDER SEPHIROTH, KH2, BIZARRO and SAFER speak with adult Sephiroth\'s.')


def main(src, out):
    raw = open(src, 'rb').read()
    d = json.loads(raw)
    assert json.dumps(d, indent=1, ensure_ascii=False).encode('utf-8') == raw, 'the file is not in the format this writes'
    forms = d['animation_sets'][0]['forms']['list']
    names = [f['name'] for f in forms]
    assert names == ['YOUNG SEPHIROTH', 'OLDER SEPHIROTH', 'WINGED', 'FLYING', 'KH2', 'BIZARRO', 'SAFER'], names
    changed = []
    for f in forms:
        for s in f.get('sounds', []):
            if s.get('bank') == OLD_VO and f['name'] in YOUNG_FORMS:
                s['bank'] = YOUNG_VO
                changed.append('%s: %s' % (f['name'], s['cue']))
    assert len(changed) == 2, changed
    adult = [f['name'] for f in forms for s in f.get('sounds', []) if s.get('bank') == OLD_VO]
    assert adult == ['OLDER SEPHIROTH', 'KH2', 'SAFER'], adult   # (BIZARRO's line is the cutscene's)
    assert NOTE not in d['source']
    d['source'] += NOTE
    text = json.dumps(d, indent=1, ensure_ascii=False).encode('utf-8')
    json.loads(text)
    open(out, 'wb').write(text)
    print('young voice:', changed)
    print('%s -> %s (%d -> %d bytes) md5 %s' % (src, out, len(raw), len(text), hashlib.md5(text).hexdigest()))


if __name__ == '__main__':
    main(*sys.argv[1:3])
