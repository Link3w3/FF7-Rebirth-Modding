"""Create a Character System 3.12.2: the boss Sephiroth's feelers on the playable Sephiroths' winged forms.

In the boss fight, Sephiroth's AI puts his feelers on with two of the game's special state effects (its
BattleSpecialStateEffect table): BossSephiroth_FeelerSword (FX_PC0010_10_SetFeeler_Sword_01 on his sword's C_Body_a) and
BossSephiroth_FeelerWing (FX_PC0010_10_SetFeeler_Wing_01 on his wing's R_FeatherD_b_Phy). The game mod 3.12.2 puts a
form's "state_effects" on the same way while the character is in that form in battle. This gives WINGED and FLYING both
(the wing's only while the model has that wing bone: Remake Sephiroth's model has no wing), and "watch_damage": the
feeler bullets of Zanshin, Hell's Gate, Grip of Fate and Ground Feeler (and Feeler Tornado / Laser), whose counts the
mod's log gives a moment into each of the form's abilities (made or not).

    patch_feelers_3122.py <the mod's compat folder>

Each compat file changed is kept first as <name>.before3122 (once). Exit 0: done (or nothing to do); 1: a file could
not be read or written (said; that file is as it was)."""
import json, os, shutil, sys

FILES = ['YoungSephirothForms.json', 'SephirothForms.json']
FORMS = ['WINGED', 'FLYING']
STATES = ['BossSephiroth_FeelerSword', {'state': 'BossSephiroth_FeelerWing', 'needs': 'R_FeatherD_b_Phy'}]
WATCH = ['PC0010_10_Zanshin01_Feeler_03', 'PC0010_10_Zanshin02_Feeler_05', 'PC0010_10_Gokumon02_Feeler_03',
         'PC0010_P_BindFeeler_01', 'PC0010_P_GroundFeelerBullet', 'PC0010_P_FeelerTornado_01', 'PC0010_P_FeelerLaser_01']


def patch(path):
    with open(path, encoding='utf-8') as f:
        text = f.read()
    data = json.loads(text)
    changed = []
    for row in data.get('animation_sets', []):
        forms = row.get('forms')
        items = forms.get('list', []) if isinstance(forms, dict) else (forms if isinstance(forms, list) else [])
        for form in items:
            if not isinstance(form, dict) or str(form.get('name', '')).upper() not in FORMS:
                continue
            if form.get('state_effects') != STATES:
                form['state_effects'] = STATES
                changed.append(form['name'] + ' state_effects')
            if form.get('watch_damage') != WATCH:
                form['watch_damage'] = WATCH
                changed.append(form['name'] + ' watch_damage')
    if not changed:
        print('   %s: already has the feelers' % os.path.basename(path))
        return True
    keep = path + '.before3122'
    if not os.path.exists(keep):
        shutil.copy2(path, keep)
    temp = path + '.new3122'
    with open(temp, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, indent=1, ensure_ascii=True)   # (as the files are written: no newline at the end)
    with open(temp, encoding='utf-8') as f:
        json.load(f)   # (it reads back)
    os.replace(temp, path)
    print('   %s: %s (the old one: %s)' % (os.path.basename(path), ', '.join(changed), os.path.basename(keep)))
    return True


def main():
    folder = sys.argv[1]
    bad = 0
    found = 0
    for name in FILES:
        path = os.path.join(folder, name)
        if not os.path.isfile(path):
            continue
        found += 1
        try:
            patch(path)
        except Exception as ex:   # (that file stays as it was)
            print('   %s NOT changed: %s' % (name, ex))
            bad += 1
    if not found:
        print('   no Sephiroth forms file in %s (nothing to do)' % folder)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
