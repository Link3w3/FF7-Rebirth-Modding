"""The CRISIS CORE form in a forms file (YoungSephirothForms.json or SephirothForms.json, Create a Character System):
  * its pack Battle10: Sephiroth's Battle00 sets (and Battle00_Comp's composites) with the 18 built Crisis Core moves
    over them (the moves are in the data container, RebirthSkelCompat/Built/SephirothForms/Battle10);
  * its ATB commands and weapon abilities: those of his Battle00 (the CRISIS CORE moves play under his own commands);
  * the form at the end of the forms menu: Crisis Core Reunion Sephiroth's model (PC0010_16, as a look: the skin's
    package), his wing hidden (the forms' parts), the REMAKE form's change effects and sounds.
    patch_ccform_json.py <plan.json> <in forms .json> <out dir>"""
import copy
import json
import os
import sys

P = '/Game/Motion/Player/PC0010_Sephiroth/'
BUILT = '/Game/RebirthSkelCompat/Built/SephirothForms/'
SET = 'Battle10'
MODEL = '/Game/Character/Player/PC0010_16_CrisisCore_Sephiroth/Model/PC0010_16.PC0010_16'
SOURCE_ADD = (' (CRISIS CORE (Battle10): Crisis Core Reunion Sephiroth in his own model, fighting with his own Crisis Core '
              'motions: his combo (the downward cut and sweep, the quick and lunging cuts, the rising and leaping cuts, the '
              'iaido dash), hold Square (the rising thrust), Triangle (the leap and plunge), his limit (Octaslash), casts, '
              'idle, damage and victory, with Sephiroth\'s combo, cancel and dodge windows and damage on his blows, the '
              'Masamune\'s trail and swing on every slash; the rest of his moves are Sephiroth\'s. The moves are in the '
              'data container.)')


def obj(p):
    return p if '.' in p.rsplit('/', 1)[-1] else p + '.' + p.rsplit('/', 1)[-1]


def build_of(m):
    b = {'from': obj(m['animation']), 'notifies_from': obj(m['notifies_from'])}
    if m.get('hits'):
        b['hits'] = [{'time': h['time']} for h in m['hits']]
    if m.get('clip'):
        b['clip'] = m['clip']
    if m.get('speed'):
        b['speed'] = m['speed']
    return b


def patch(doc, plan):
    r = doc['animation_sets'][0]
    assert not any(m['set'] == SET for m in r['moves']), 'already has ' + SET
    assert not any(f['name'] == 'CRISIS CORE' for f in r['forms']['list']), 'already has the CRISIS CORE form'
    r['battle'].append({'from': P + 'Battle00.Battle00', 'as': SET})
    r['battle'].append({'from': P + 'Battle00_Comp.Battle00_Comp', 'as': SET})
    for m in plan['moves']:
        assert m['set'] == SET
        r['moves'].append({'set': SET, 'key': m['name'], 'animation': '%s%s/%s.%s' % (BUILT, SET, m['name'], m['name']),
                           'build': build_of(m)})
    base = [a for a in r['abilities'] if a['pack'] == 'Battle00']
    assert len(base) == 1 and not any(a['pack'] == SET for a in r['abilities'])
    r['abilities'].append({'pack': SET, 'commands': list(base[0]['commands']), 'weapon_abilities': dict(base[0]['weapon_abilities'])})
    remake = [f for f in r['forms']['list'] if f['name'] == 'REMAKE']
    assert remake, 'no REMAKE form to take the change effects from'
    form = {'name': 'CRISIS CORE', 'pack': SET, 'model': MODEL, 'as_look': True,
            'effects': copy.deepcopy(remake[0]['effects']), 'sounds': copy.deepcopy(remake[0]['sounds'])}
    r['forms']['list'].append(form)
    doc['source'] = doc['source'] + SOURCE_ADD
    return doc, '%s: %d moves; the form %d of %d' % (SET, len(plan['moves']), len(r['forms']['list']), len(r['forms']['list']))


if __name__ == '__main__':
    plan = json.load(open(sys.argv[1]))
    src, out = sys.argv[2], sys.argv[3]
    os.makedirs(out, exist_ok=True)
    doc = json.load(open(src, encoding='utf-8'))
    before = len(doc['animation_sets'][0]['moves'])
    doc, report = patch(doc, plan)
    dst = os.path.join(out, os.path.basename(src))
    with open(dst, 'w', encoding='utf-8') as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
    print('%s: %d -> %d moves; %s' % (os.path.basename(src), before, len(doc['animation_sets'][0]['moves']), report))
