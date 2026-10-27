"""BizarroSummon.json, the Create a Character System compat file of the Bizarro Sephiroth summon, from the editor's export
of DO_BizarroSummon: his own battle sets fill the summon's (the plan's "battle" sources: his attacks, which the summon's
abilities play), and every animation name of Alexander's summon sets (Battle00, Battle00_Comp) plays the move built from
Bizarro Sephiroth's animation, all of them in BizarroSummon_P.
    build_summon_json.py <editor export json> <BizarroSummon_P.utoc> <plan json> <out json>"""
import json, sys
sys.path[:0] = ['/work/iostore', '/work/cs']
from iostore import Toc

exported, utoc, plan_path, out = sys.argv[1:5]
j = json.load(open(exported, encoding='utf-8'))
plan = json.load(open(plan_path, encoding='utf-8'))
assert len(j['animation_sets']) == 1, len(j['animation_sets'])
row = j['animation_sets'][0]
assert row['characters'] == plan['characters'], row['characters']
assert row.get('requires_paks') == plan['requires_paks'], row.get('requires_paks')
want_battle = [{'from': b['path'], 'as': b['as_']} for b in plan.get('battle', [])]
assert row.get('battle', []) == want_battle, ('battle sources', row.get('battle'))
moves = row['moves']
want = {(m['set'], m['name']) for m in plan['moves']}
got = {(m['set'], m['key']) for m in moves}
assert got == want, (want - got, got - want)
mount = '../../../End/Content/'
files = {('/Game/' + p[len(mount):-len('.uasset')]) for p in Toc(utoc).files.values() if p.endswith('.uasset')}
for m in moves:
    package = m['animation'].split('.', 1)[0]
    assert package in files, ('not in the moves pak', m['key'], m['animation'])
j['source'] = ('Bizarro Sephiroth as a summon in Alexander\'s place (Create a Character System 3.5): the summon keeps Alexander\'s '
               'AI and summon settings and fights with Bizarro Sephiroth\'s own attacks: its abilities play his animations (his '
               'Battle00 and Battle01 sets fill the summon\'s Battle00, their _Comp sets its Battle00_Comp), with his effects and '
               'damage. The summon\'s own animation names (appearing, idling, warping, leaving) play moves built from his '
               'animations with Alexander\'s gameplay notifies. Goes with FullyPlayableSephirothDataAssets_P (the summon\'s '
               'CharaSpec row, pack, abilities and damage) and BizarroSummon_P (the moves).')
open(out, 'w', encoding='utf-8').write(json.dumps(j, indent=1, ensure_ascii=False) + '\n')
print('%d moves, all in %s; characters %s; requires %s' % (len(moves), utoc.rsplit('/', 1)[-1], row['characters'], row['requires_paks']))
