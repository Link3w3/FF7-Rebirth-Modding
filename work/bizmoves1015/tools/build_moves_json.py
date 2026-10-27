"""BizarroSummon.json with Bizarro Sephiroth's own attacks: the summon's battle sets (Alexander's Battle00 and Battle00_Comp)
also take Bizarro Sephiroth's own sets (Battle00 and Battle01 -> Battle00, their _Comp sets -> Battle00_Comp), so the
animations his abilities name (the summon's abilities play them after build_bizarro_moves_data.py) are there. The moves
(the summon's own names: appearing, idling, warping, leaving, built from his animations) stay and still win.
    build_moves_json.py <BizarroSummon.json> <survey.json> <out json>"""
import json, sys

base, survey_path, out = sys.argv[1:4]
j = json.load(open(base, encoding='utf-8'))
survey = json.load(open(survey_path, encoding='utf-8'))
sets = {x['path']: x['animations'] for x in survey if x['class'] == 'EndAnimSet'}
ROOT = '/Game/Motion/Enemy/EB2210_BizarroSephiroth/'
BATTLE = [(ROOT + 'Battle00.Battle00', 'Battle00'), (ROOT + 'Battle01.Battle01', 'Battle00'),
          (ROOT + 'Battle00_Comp.Battle00_Comp', 'Battle00_Comp'), (ROOT + 'Battle01_Comp.Battle01_Comp', 'Battle00_Comp')]
# the animations the summon's abilities play now (build_bizarro_moves_data.py), each in the set it fills
USED = ['B_AtkWingSwingR01', 'B_AtkWingSwingL01', 'B_AtkBodyExplode01', 'B_AtkMagB01_add', 'B_AtkEyeMagic01_0',
        'B_AtkEyeMagic01_1', 'B_AtkEyeMagic01_1_Comp_3', 'B_AtkEyeMagic01_1_Comp_4', 'B_AtkEyeMagic01_2', 'B_AtkWindBlow01',
        'B_AtkOmniSlash01_0', 'B_AtkOmniSlash01_1', 'B_AtkOmniSlash01_2', 'B_AtkAngel01_0', 'B_AtkAngel01_1', 'B_AtkAngel01_2',
        'B_AtkZanShin01_0', 'B_AtkFeelerWingSmash01', 'B_AtkStigma01_0', 'B_AtkStigma01_1_Comp', 'B_AtkStigma01_2'] + \
       ['B_AtkMagB01_%d' % i for i in range(5)]

assert len(j['animation_sets']) == 1
row = j['animation_sets'][0]
assert row['characters'] == ['SU2030_00_Alexander_Standard'], row['characters']
assert 'battle' not in row and 'field' not in row, 'already has sources'
assert row['skeleton'].endswith('/EB2210_00_Skeleton.EB2210_00_Skeleton'), row['skeleton']
for path, _ in BATTLE:
    assert path in sets, ('not one of his sets', path)
filled = {}
for path, target in BATTLE:
    for name in sets[path]:
        filled.setdefault(target, {}).setdefault(name, path)
for name in USED:
    assert any(name in names for names in filled.values()), ('no set has', name)
moved = {(m['set'], m['key']) for m in row['moves']}
new_row = {}
for key, value in row.items():
    new_row[key] = value
    if key == 'characters':
        new_row['battle'] = [{'from': path, 'as': target} for path, target in BATTLE]
j['animation_sets'][0] = new_row
j['source'] = ('Bizarro Sephiroth as a summon in Alexander\'s place (Create a Character System 3.5): the summon keeps Alexander\'s '
               'AI and summon settings and fights with Bizarro Sephiroth\'s own attacks: its abilities play his animations (his '
               'Battle00 and Battle01 sets fill the summon\'s Battle00, their _Comp sets its Battle00_Comp), with his effects and '
               'damage. The summon\'s own animation names (appearing, idling, warping, leaving) play moves built from his '
               'animations with Alexander\'s gameplay notifies. Goes with FullyPlayableSephirothDataAssets_P (the summon\'s '
               'CharaSpec row, pack, abilities and damage) and BizarroSummon_P (the moves).')
open(out, 'w', encoding='utf-8').write(json.dumps(j, indent=1, ensure_ascii=False) + '\n')
names = {t: len(n) for t, n in filled.items()}
overlap = sorted((s, k) for s, k in moved if k in filled.get(s, {}))
print('battle sources: %s; names they bring: %s; %d moves (still win over %d of his names: %s)' % (
    ', '.join('%s -> %s' % (p.rsplit('.', 1)[-1], t) for p, t in BATTLE), names, len(row['moves']), len(overlap),
    ', '.join(k for _, k in overlap)))
