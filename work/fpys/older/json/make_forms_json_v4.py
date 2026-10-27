"""Fully Playable Young Sephiroth's forms JSON, v4 (Create a Character System 3.9.1): v3's (make_forms_json_v3.py: his
voice per form) with his row's looks from Cloud's blueprint ("looks_from"): Sephiroth's blueprint has no looks, so the
Toad status gave him the frog's moves on his own model; with Cloud's looks it turns him into the frog Cloud turns into.
Written in the file's own format.
    make_forms_json_v4.py <make_forms_json_v3.py's .json> <out .json>"""
import hashlib, json, sys

LOOKS = '/Game/BluePrint/Character/Player/PC0000_00_Cloud_Standard'
NOTE = (' (Create a Character System 3.9.1 "looks_from": the Toad status turns him into the frog Cloud turns into: '
        'Sephiroth\'s blueprint has no frog.)')


def main(src, out):
    raw = open(src, 'rb').read()
    d = json.loads(raw)
    assert json.dumps(d, indent=1, ensure_ascii=False).encode('utf-8') == raw, 'the file is not in the format this writes'
    row = d['animation_sets'][0]
    assert 'voice' in row and 'looks_from' not in row
    row['looks_from'] = LOOKS
    assert NOTE not in d['source']
    d['source'] += NOTE
    text = json.dumps(d, indent=1, ensure_ascii=False).encode('utf-8')
    json.loads(text)
    open(out, 'wb').write(text)
    print('looks_from:', row['looks_from'], 'characters:', len(row['characters']))
    print('%s -> %s (%d -> %d bytes) md5 %s' % (src, out, len(raw), len(text), hashlib.md5(text).hexdigest()))


if __name__ == '__main__':
    main(*sys.argv[1:3])
