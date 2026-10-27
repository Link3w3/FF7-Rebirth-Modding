"""SephirothForms.json with field sources for his row: his own field sets first, then Cloud's (Neutral20 and Emotion00 from
Cloud's folder, Cloud's animations wherever his Neutral00 / Facial00 lack a name), as the Evil Cloud rows do.
    add_field.py <installed json> <out json>"""
import json, sys
src, out = sys.argv[1:3]
raw = open(src, encoding='utf-8').read()
j = json.loads(raw)
s = j['animation_sets'][0]
assert s['characters'][0] == 'PC0000_00_Cloud_Standard' and 'field' not in s
FIELD = ['/Game/Motion/Player/PC0010_Sephiroth', '/Game/Motion/Player/PC0000_Cloud']
row = {}
for k, v in s.items():
    row[k] = v
    if k == 'battle':
        row['field'] = FIELD
j['animation_sets'][0] = row
note = ' Field sets (Neutral00, Neutral20, Emotion00, Facial00): his own first, then Cloud\'s (Neutral20 and Emotion00 are Cloud\'s).'
if 'Field sets' not in j['source']:
    j['source'] = j['source'].rstrip() + note
open(out, 'w', encoding='utf-8').write(json.dumps(j, indent=1, ensure_ascii=False) + ('\n' if raw.endswith('\n') else ''))
back = json.load(open(out, encoding='utf-8'))
b = back['animation_sets'][0]
assert b['field'] == FIELD and {k: v for k, v in b.items() if k != 'field'} == s
assert {k: v for k, v in back.items() if k not in ('animation_sets', 'source')} == {k: v for k, v in j.items() if k not in ('animation_sets', 'source')}
print('field', b['field'], '| keys', list(b))
