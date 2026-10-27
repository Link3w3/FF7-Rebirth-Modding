"""A built-moves form in a forms file (YoungSephirothForms.json or SephirothForms.json, Create a Character System), the
way the CRISIS CORE form went in (ccanim/forms/tools/patch_ccform_json.py, made general):
  * its pack (e.g. Battle12): Sephiroth's Battle00 sets (and Battle00_Comp's composites) with the plan's built moves over
    them (the moves are in the data container, RebirthSkelCompat/Built/SephirothForms/<pack>);
  * its ATB commands and weapon abilities: those of his Battle00 (its moves play under his own commands);
  * the form at the end of the forms menu: the model as a look (the skin's package), the REMAKE form's change effects
    and sounds.
    patch_form_json.py <plan.json> <in forms .json> <out dir> <form name> <model object path> <source note> [field set ...]"""
import copy
import json
import os
import sys

P = '/Game/Motion/Player/PC0010_Sephiroth/'
BUILT = '/Game/RebirthSkelCompat/Built/SephirothForms/'


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


def patch(doc, plan, name, model, note):
    pack = plan['set']
    r = doc['animation_sets'][0]
    assert not any(m['set'] == pack for m in r['moves']), 'already has ' + pack
    assert not any(b['as'] == pack for b in r['battle']), 'its battle sets already list ' + pack
    assert not any(f['name'] == name for f in r['forms']['list']), 'already has the %s form' % name
    assert not any(f.get('pack') == pack for f in r['forms']['list']), 'a form already plays ' + pack
    assert len(r['forms']['list']) < 13, 'the forms menu holds 13 forms'
    r['battle'].append({'from': P + 'Battle00.Battle00', 'as': pack})
    r['battle'].append({'from': P + 'Battle00_Comp.Battle00_Comp', 'as': pack})
    for m in [m for m in plan['moves'] if m['set'] == pack]:
        r['moves'].append({'set': pack, 'key': m['name'], 'animation': '%s%s/%s.%s' % (BUILT, pack, m['name'], m['name']),
                           'build': build_of(m)})
    base = [a for a in r['abilities'] if a['pack'] == 'Battle00']
    assert len(base) == 1 and not any(a['pack'] == pack for a in r['abilities'])
    r['abilities'].append({'pack': pack, 'commands': list(base[0]['commands']), 'weapon_abilities': dict(base[0]['weapon_abilities'])})
    remake = [f for f in r['forms']['list'] if f['name'] == 'REMAKE']
    assert remake, 'no REMAKE form to take the change effects from'
    form = {'name': name, 'pack': pack, 'model': model, 'as_look': True,
            'effects': copy.deepcopy(remake[0]['effects']), 'sounds': copy.deepcopy(remake[0]['sounds'])}
    r['forms']['list'].append(form)
    doc['source'] = doc['source'] + ' (' + note + ')'
    return doc, '%s: %d moves; the form %d of %d' % (pack, sum(1 for m in plan['moves'] if m['set'] == pack), len(r['forms']['list']),
                                                    len(r['forms']['list']))


def patch_field(doc, plan, name):
    """a field set the plan builds (plan['field_sets'][name]: its source set), as the row's \"field\" source \"as\" it, with
    the plan's moves of that set over it (a skin or form names it in its \"sets\")"""
    r = doc['animation_sets'][0]
    spec = plan['field_sets'][name]
    assert not any(isinstance(f, dict) and f.get('as') == name for f in r['field']), 'its field sources already make ' + name
    assert not any(m['set'] == name for m in r['moves']), 'already has moves of ' + name
    r['field'].append({'from': spec['from'], 'as': name})
    moves = [m for m in plan['moves'] if m['set'] == name]
    for m in moves:
        r['moves'].append({'set': name, 'key': m['name'], 'animation': '%s%s/%s.%s' % (BUILT, name, m['name'], m['name']),
                           'build': build_of(m)})
    return doc, '%s: a field set from %s with %d moves' % (name, spec['from'].rsplit('/', 1)[-1], len(moves))


def main(plan_path, src, out, name, model, note, *field_sets):
    plan = json.load(open(plan_path))
    os.makedirs(out, exist_ok=True)
    doc = json.load(open(src, encoding='utf-8'))
    before = len(doc['animation_sets'][0]['moves'])
    doc, report = patch(doc, plan, name, model, note)
    for fs in field_sets:
        doc, more = patch_field(doc, plan, fs)
        report += '; ' + more
    dst = os.path.join(out, os.path.basename(src))
    with open(dst, 'w', encoding='utf-8') as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
    print('%s: %d -> %d moves; %s' % (os.path.basename(src), before, len(doc['animation_sets'][0]['moves']), report))


if __name__ == '__main__':
    main(*sys.argv[1:])
