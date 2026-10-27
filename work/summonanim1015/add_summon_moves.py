"""SephirothForms.json with Cloud's summon cast (B_MagSummon01_0 .. _4) in every one of his battle sets (Battle00, and the
forms' Battle02, Battle03, Battle04): his own sets have no summon animation, so a summon left him stuck. Cloud's animations
play on his skeleton through the Sephiroth/Cloud family (PlayableSephiroth_Swap.json's pair).
    add_summon_moves.py <installed json> <out json>"""
import gzip, json, sys
src, out = sys.argv[1:3]
raw = open(src, encoding='utf-8').read()
j = json.loads(raw)
row = j['animation_sets'][0]
assert row['characters'][0] == 'PC0000_00_Cloud_Standard'
SETS = ['Battle00', 'Battle02', 'Battle03', 'Battle04']
KEYS = ['B_MagSummon01_%d' % k for k in range(5)]
CLOUD = '/Game/Motion/Player/PC0000_Cloud/Battle00/'
game = {l.split('\t', 1)[1].strip() for l in gzip.open('/work/gamelist/gamefiles.txt.gz', 'rt')}
for k in KEYS:
    assert '../../../End/Content/Motion/Player/PC0000_Cloud/Battle00/%s.uasset' % k in game, k
have = {(m['set'], m['key']) for m in row['moves']}
added = []
for s in SETS:
    for k in KEYS:
        assert (s, k) not in have, (s, k)
        row['moves'].append({'set': s, 'key': k, 'animation': CLOUD + k + '.' + k})
        added.append((s, k))
note = ' Summons: Cloud\'s summon cast (B_MagSummon01) in every form.'
if 'summon cast' not in j['source']:
    j['source'] = j['source'].rstrip() + note
open(out, 'w', encoding='utf-8').write(json.dumps(j, indent=1, ensure_ascii=False) + ('\n' if raw.endswith('\n') else ''))
back = json.load(open(out, encoding='utf-8'))
b = back['animation_sets'][0]
assert len(b['moves']) == len(json.loads(raw)['animation_sets'][0]['moves']) + len(added)
print('%d moves added (%s), %d moves now' % (len(added), ', '.join(SETS), len(b['moves'])))
