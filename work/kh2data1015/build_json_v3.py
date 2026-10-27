"""SephirothForms.json for the 2026-10-15 build: the installed one (kh2data1014/out6: KH2 form, Meteor cast, aura and menu
art preloaded) with the KH2 form's moves (Battle04) as this build made them (now with B_Run01_0_R90, its notifies from
L90) and the flying form's 44 flight moves (Battle03: his idle, walks, runs, turns and falls made from his flight in the
game's final cutscenes) in place of its earlier locomotion.
    build_json_v3.py <installed json> <editor export json> <kh2_result.json> <out json>"""
import json, sys
installed, exported, result, out = sys.argv[1:5]
raw = open(installed, encoding='utf-8').read()
j = json.loads(raw)
s = j['animation_sets'][0]
e = json.load(open(exported, encoding='utf-8'))['animation_sets'][0]
r = json.load(open(result))
assert r.get('done') and not r.get('failed'), r.get('failed')
FLIGHT = '/Game/RebirthSkelCompat/Imported/SephirothFlight/'
kh2 = [m for m in e['moves'] if m['set'] == 'Battle04']
flight = [m for m in e['moves'] if m['set'] == 'Battle03' and m.get('build', {}).get('from', '').startswith(FLIGHT)]
assert len(kh2) == 54 and len(flight) == 44, (len(kh2), len(flight))
keys = {m['key'] for m in flight}
before = len(s['moves'])
moves = [m for m in s['moves'] if m['set'] != 'Battle04' and not (m['set'] == 'Battle03' and m['key'] in keys)]
replaced = before - len(moves)
moves += kh2 + flight
s['moves'] = moves
for b in e['battle']:
    if b['as'] == 'Battle04':
        assert b in s['battle'], b
if 'flying form' not in j['source'].lower():
    j['source'] = j['source'].rstrip('.') + '. Flying form (Battle03): his idle, walks, runs and turns from his flight in the final cutscenes.'
open(out, 'w', encoding='utf-8').write(json.dumps(j, indent=1, ensure_ascii=False) + ('\n' if raw.endswith('\n') else ''))
print('moves %d -> %d (%d replaced: Battle04 %d, Battle03 flight %d)' % (before, len(moves), replaced, len(kh2), len(flight)))
