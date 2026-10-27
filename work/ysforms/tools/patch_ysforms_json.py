"""The forms update (Create a Character System 3.12) in the forms files:
  YoungSephirothForms.json: YOUNG SEPHIROTH plays its own pack Battle07 (Sephiroth's Battle00 sets with his built Ever
    Crisis moves over them; Skewer's composite as in Battle00), its ATB commands and weapon abilities those of his
    Battle00; the casts of the transformed abilities built for your abilities' IDs (Battle02, Battle03 and Battle00);
  SephirothForms.json: the casts in Battle02 and Battle03.
WINGED's moves made again keep their paths (the data container has them).
    patch_ysforms_json.py <plan.json> <in SephirothForms.json> <in YoungSephirothForms.json> <out dir>"""
import copy, json, os, sys

P = '/Game/Motion/Player/PC0010_Sephiroth/'
BUILT = '/Game/RebirthSkelCompat/Built/SephirothForms/'
SOURCE_ADD = (' (Create a Character System 3.12: YOUNG SEPHIROTH fights with his own Ever Crisis moves (Battle07): his combo, air '
              'combo, abilities, limits, casts, items and summons, idle, run, reactions, death and victory are his own skills\' '
              'motions, with Sephiroth\'s combo, cancel and dodge windows, damage, swings, trails and slashes on his blows; the '
              'rest of his moves are Sephiroth\'s. WINGED\'s moves play the transformed Sephiroth\'s feeler slashes, and Zanshin '
              'and Hell\'s Gate loose his feelers, out of the ground for Hell\'s Gate; the transformed casts show their effects '
              'for your abilities: Ground Feeler\'s feelers burst out of the ground. The moves are in the data container.)')


def built_path(s, name):
    return '%s%s/%s.%s' % (BUILT, s, name, name)


def build_of(m):
    b = {'from': m['animation'], 'notifies_from': m['notifies_from']}
    if m.get('hits'):
        b['hits'] = [{'time': h['time']} for h in m['hits']]
    if m.get('clip'):
        b['clip'] = m['clip']
    if m.get('speed'):
        b['speed'] = m['speed']
    return b


def patch(doc, plan, young):
    r = doc['animation_sets'][0]
    moves = r['moves']
    by = {(m['set'], m['key']): m for m in moves}
    planned = {(m['set'], m['name']): m for m in plan['moves']}
    report = []
    # the casts built for your abilities (Battle02; Battle03 plays Battle02's, as its other moves of that set)
    for name in ('B_AtkMag01_1', 'B_AtkMag01_3'):
        m = planned[('Battle02', name)]
        for s in ('Battle02', 'Battle03'):
            assert (s, name) not in by, (s, name)
            e = {'set': s, 'key': name, 'animation': built_path('Battle02', name)}
            if s == 'Battle02':
                e['build'] = build_of(m)
            moves.append(e)
        report.append('Battle02 and Battle03: %s built' % name)
    if young:
        # Battle00's cast (OLDER SEPHIROTH's T abilities): built
        e = by[('Battle00', 'B_AtkMag01_1')]
        e['animation'] = built_path('Battle00', 'B_AtkMag01_1')
        e['build'] = build_of(planned[('Battle00', 'B_AtkMag01_1')])
        report.append('Battle00: B_AtkMag01_1 built')
        # YOUNG SEPHIROTH: Battle07
        assert not any(m['set'] == 'Battle07' for m in moves), 'already has Battle07'
        r['battle'].append({'from': P + 'Battle00.Battle00', 'as': 'Battle07'})
        r['battle'].append({'from': P + 'Battle00_Comp.Battle00_Comp', 'as': 'Battle07'})
        chained = {x for v in plan['chains'].values() for x in v}
        n = 0
        for m in plan['moves']:
            if m['set'] != 'Battle07' or m['name'] in chained:
                continue
            e = {'set': 'Battle07', 'key': m['name'], 'animation': built_path('Battle07', m['name']), 'build': build_of(m)}
            if m['name'] in plan['chains']:
                e['animation'] = [built_path('Battle07', m['name'])] + [built_path('Battle07', x) for x in plan['chains'][m['name']]]
            moves.append(e)
            n += 1
        for key in plan['keep_from_battle00']:
            e = copy.deepcopy(by[('Battle00', key)])
            e['set'] = 'Battle07'
            moves.append(e)
            n += 1
        base = [a for a in r['abilities'] if a['pack'] == 'Battle00']
        assert len(base) == 1 and not any(a['pack'] == 'Battle07' for a in r['abilities'])
        r['abilities'].append({'pack': 'Battle07', 'commands': list(base[0]['commands']), 'weapon_abilities': dict(base[0]['weapon_abilities'])})
        form = r['forms']['list'][0]
        assert form['name'] == 'YOUNG SEPHIROTH' and 'pack' not in form, form['name']
        form['pack'] = 'Battle07'
        report.append('Battle07: %d moves (%d built, chains %s, kept from Battle00 %s); YOUNG SEPHIROTH plays it, with Battle00\'s commands' % (
            n, n - len(plan['keep_from_battle00']), plan['chains'], plan['keep_from_battle00']))
    doc['source'] = doc['source'] + SOURCE_ADD
    return doc, report


if __name__ == '__main__':
    plan = json.load(open(sys.argv[1]))
    out = sys.argv[4]
    os.makedirs(out, exist_ok=True)
    for src, young in ((sys.argv[2], False), (sys.argv[3], True)):
        doc = json.load(open(src, encoding='utf-8'))
        before = len(doc['animation_sets'][0]['moves'])
        doc, report = patch(doc, plan, young)
        dst = os.path.join(out, os.path.basename(src))
        with open(dst, 'w', encoding='utf-8') as f:
            json.dump(doc, f, indent=1, ensure_ascii=False)
        r = doc['animation_sets'][0]
        print('%s: %d -> %d moves; %s' % (os.path.basename(src), before, len(r['moves']), '; '.join(report)))
