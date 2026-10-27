"""The CLOUD moveset in a forms file (SephirothForms.json or YoungSephirothForms.json, Create a Character System 3.15.1+):
  * its pack Battle11: Sephiroth's Battle00 sets (and Battle00_Comp's composites) with the 123 built CLOUD moves over them
    (Cloud's own Rebirth battle motions built onto Sephiroth's skeleton; the moves are in CloudMovesetMoves_P, at
    /Game/RebirthSkelCompat/Built/SephirothForms/Battle11);
  * the forms' "movesets": [{"name": "CLOUD", "pack": "Battle11"}]: the MOVESET page offers it to every form on his own
    AnimBlueprint (not a form: never on the forms menu, never worn; the form keeps its own commands and abilities).
Each move's "build" (the editor's, the mod skips it) says what it is built from, as the editor writes it: Cloud's motion,
Sephiroth's move for the notifies, Cloud's blows, the clip and speed, "source_effects" (Keep Source Effects).
Cloud's blend spaces (his strafing walks, his turn on the spot) are played as they are: his skeleton is in Sephiroth's
family (PlayableYoungSephiroth_Swap.json, "proportions"), so Sephiroth's mesh plays them with his own build; Build Moves
makes moves of sequences only.
    patch_cloud_moveset_json.py <plan.json> <built.json> <in forms .json> <out .json>"""
import json
import sys

P = '/Game/Motion/Player/PC0010_Sephiroth/'
BUILT = '/Game/RebirthSkelCompat/Built/SephirothForms/'
SET = 'Battle11'
CLOUD = '/Game/Motion/Player/PC0000_Cloud/Battle00/'
DIRECT = ['B_StrafingWalk01_0', 'B_StrafingWalk01_1', 'B_StrafingWalk01_2l', 'B_Turn01']   # (Cloud's blend spaces, as they are)
NAME = 'CLOUD'
WEAPON_SOCKET = 'Attach_Weapon_Right01'   # (Cloud's sword hand: Sephiroth's rules put his weapon in his left)
SOURCE_ADD = (" (CLOUD (Battle11, the Customization screen's MOVESET page): Cloud's own Rebirth battle motions on Sephiroth, his "
              "idles, walks, runs and turns, his combo and air combo, guard, dodge roll, back step, damage, knock-downs, falls, "
              "death and victory, with Sephiroth's combo, cancel and dodge windows and damage on Cloud's blows and Cloud's own "
              "swing sounds, trails and footsteps, and Cloud's own strafing walks and turn on the spot (his blend spaces: his "
              "skeleton is in Sephiroth's family); Sephiroth's Triangle, hold-Square and parry attacks stay his. The built "
              "moves are in CloudMovesetMoves_P.)")


def obj(p):
    return p if '.' in p.rsplit('/', 1)[-1] else p + '.' + p.rsplit('/', 1)[-1]


def build_of(m, built):
    b = {'from': obj(m['animation']), 'notifies_from': obj(m['notifies_from'])}
    if m.get('hits'):
        b['hits'] = [{'time': h['time']} for h in m['hits']]
    clip = m.get('clip')
    if m.get('clip_like_notifies_from'):
        # cut to the length of Sephiroth's move (his turn while guarding): the clip the build used, its built length
        clip = [0.0, round(float(built['length']), 4)]
    if clip:
        b['clip'] = clip
    if m.get('speed'):
        b['speed'] = m['speed']
    b['source_effects'] = True
    return b


def patch(doc, plan, built):
    r = doc['animation_sets'][0]
    assert not any(m['set'] == SET for m in r['moves']), 'already has moves in ' + SET
    assert not any(b.get('as') == SET for b in r['battle']), 'already has a battle source as ' + SET
    assert not any(a['pack'] == SET for a in r.get('abilities', [])), 'already has abilities for ' + SET
    forms = r['forms']
    assert not any(f.get('pack') == SET or f['name'] == NAME for f in forms['list']), 'a form has the name or pack already'
    assert not forms.get('movesets'), 'already has movesets'
    r['battle'].append({'from': P + 'Battle00.Battle00', 'as': SET})
    r['battle'].append({'from': P + 'Battle00_Comp.Battle00_Comp', 'as': SET})
    keys = set()
    for m in plan['moves']:
        assert m['set'] == SET and m['name'] not in keys
        keys.add(m['name'])
        path = '%s%s/%s.%s' % (BUILT, SET, m['name'], m['name'])
        assert path in built and not built[path].get('error'), 'not built: ' + path
        r['moves'].append({'set': SET, 'key': m['name'], 'animation': path, 'build': build_of(m, built[path])})
    for name in DIRECT:
        assert name not in keys
        keys.add(name)
        r['moves'].append({'set': SET, 'key': name, 'animation': '%s%s.%s' % (CLOUD, name, name)})
    forms['movesets'] = [{'name': NAME, 'pack': SET, 'weapon_socket': WEAPON_SOCKET}]   # (3.16.1: the sword in Cloud's right hand)
    doc['source'] = doc['source'] + SOURCE_ADD
    return doc, '%s: %d moves (%d built, %d of Cloud\'s blend spaces); the MOVESET page offers %s' % (SET, len(keys), len(plan['moves']), len(DIRECT), NAME)


if __name__ == '__main__':
    plan = json.load(open(sys.argv[1]))
    built = json.load(open(sys.argv[2]))
    src, dst = sys.argv[3], sys.argv[4]
    raw = open(src, 'rb').read()
    doc = json.loads(raw.decode('utf-8'))
    # written as the mod's files are (one-space indent, UTF-8, no newline at the end): checked against the file itself
    assert json.dumps(doc, indent=1, ensure_ascii=False).encode('utf-8') == raw, 'not written the way this script writes'
    before = len(doc['animation_sets'][0]['moves'])
    doc, report = patch(doc, plan, built)
    with open(dst, 'wb') as f:
        f.write(json.dumps(doc, indent=1, ensure_ascii=False).encode('utf-8'))
    print('%s: %d -> %d moves; %s' % (src.replace('\\', '/').rsplit('/', 1)[-1], before, len(doc['animation_sets'][0]['moves']), report))
