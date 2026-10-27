"""VincentGalian.json: the Create a Character System's file for Vincent's Galian Beast form (game mod 3.7.5), in Cloud's
slot (his six CharaSpec rows, joined with Vincent_Moves.json's and VincentDirge.json's rows of them):
  * the GALIAN BEAST form on the forms menu (hold Triangle): the beast's model (EB2160_00_Body, its own size) running
    the beast's player AnimBlueprint (make_galian_abp.py), its weapons hidden, no shooter, super armor, 60 s then
    back to Vincent (30 s before it can be chosen again), the battle camera further back; its sets ("sets", 3.7.5:
    the game's Battle00 lookups get Battle07, Punisher mode's Battle01 Battle08, its face's Facial00 Facial07); its
    entrance: the transformation cutscene's shots (EV_NIBLE_8310: Vincent's change, the beast's roar),
  * its packs' animations: the beast's own sets under Battle07 and Battle08 (and its face under Facial07), every move
    built in the End editor (galian_moves.json; a move the build left out plays the beast's animation it was made of),
    the commands' chains, the blend spaces (make_galian_blendspaces.py),
  * its abilities in Battle07 (build_galian_data.py: commands, the abilities in place of his weapons', limit breaks),
  * what it needs loaded: the beast's and the cutscene's effects, the beast's sounds, the cutscene's animations,
  * (3.7.7) the CHAOS form: Chaos's model (PC0011_10, VincentChaos_P; in the Cloud family: VincentChaos.json) playing
    Vincent's moves, a shooter of its own (Chaos's Dirge of Cerberus motions, p007_; one gun, the DEATH PENALTY, the
    user's model (VincentDeathPenalty_P) on Vincent's gun, firing beams of light: build_chaos_beams.py's rows), flying
    (hovering; up and down on the D-pad, its stance and shots in the air Chaos's own), super armor, 150 s; its change a
    burst of chaos energy (the Galian boss's Chaos Flare explosion, big, and its sound), nothing else.
    compose_galian_json.py <out json> [build_result.json]"""
import json, os, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAN = os.path.join(HERE, 'plan', 'galian_moves.json')
DATA = os.path.join(HERE, 'data4', 'galian_data.json')
ENTRANCE = os.path.join(HERE, 'galian_entrance.json')
BLEND = os.path.join(HERE, 'bs1', 'blendspaces.json')
E = '/Game/Motion/Enemy/EB2160_VincentValentine/'
MODEL = '/Game/Character/Enemy/EB2160_00_VincentValentine_Standard/Model/EB2160_00_Body.EB2160_00_Body'
ANIM_CLASS = '/Game/BluePrint/Animation/Player/PC0011_20_GalianBeast_Standard_Animation.PC0011_20_GalianBeast_Standard_Animation_C'
CUT = '/Game/Cut/Game/8700-NIBLE/EV_NIBLE_8310'
FX = '/Game/Effect/Cut/8700-NIBLE/EV_NIBLE_8310/'
PACK_ASSETS = [
    '/Game/Effect/Character/Enemy/EB2160_VincentValentine/Build/EB2160_VincentValentine_Effect__Pack.EB2160_VincentValentine_Effect__Pack',
    FX + 'Build/EV_NIBLE_8310_Effect__Pack.EV_NIBLE_8310_Effect__Pack',
    FX + 'Build/EV_NIBLE_8310_2_Effect__Pack.EV_NIBLE_8310_2_Effect__Pack',
    '/Game/Sound/SE/Character/Enemy/SE_EB2160_00_VincentValentine_Standard.SE_EB2160_00_VincentValentine_Standard',
]
# the beast's arms and feet: meshes of their own on its skeleton (EB2160_00_Skeleton) that the boss puts on its body; the
# form adds them to the model, following its pose
PARTS = ['/Game/Character/Enemy/EB2160_0%d_VincentValentine_%s/Model/EB2160_0%d.EB2160_0%d' % (n, part, n, n)
         for n, part in ((1, 'LargeArmR'), (2, 'LargeArmL'), (3, 'LargeFootR'), (4, 'LargeFootL'))]
# (3.7.7) the CHAOS form
CHAOS_MODEL = '/Game/Character/Player/PC0011_10_Chaos/Model/PC0011_10.PC0011_10'
DEATH_PENALTY = '/Game/Character/Weapon/WE011_10_Chaos_DeathPenialty/Model/WE0011_10.WE0011_10'
CHAOS_FLARE = '/Game/Effect/Character/Enemy/EB2160_VincentValentine/Particle/FX_EB2160_ChaosFlare_Exp_01.FX_EB2160_ChaosFlare_Exp_01'
EB2160_SE = '/Game/Sound/SE/Character/Enemy/SE_EB2160_00_VincentValentine_Standard.SE_EB2160_00_VincentValentine_Standard'
BEAM = 'PC0011_Chaos_DeathPenalty_Feeler'   # (3.7.8: its beam the transformed Sephiroth's feeler laser, from an effect pack no
#   party member loads: Aerith's, added to Cloud's pack while she is in the party, is the suspect of the loading crashes)
BEAM_PACK = '/Game/Effect/Character/Player/PC0003_Aerith/Build/PC0003_Aerith_Effect__Pack.PC0003_Aerith_Effect__Pack'
BEAM_OPTIONS = {
    'PC0011_Chaos_DeathPenalty': ("Aerith's light beam", BEAM_PACK),
    'PC0011_Chaos_DeathPenalty_Alexander': ("Alexander's laser", '/Game/Effect/Character/Summon/SU2030_Alexander/Build/SU2030_Alexander_Effect__Pack.SU2030_Alexander_Effect__Pack'),
    'PC0011_Chaos_DeathPenalty_Feeler': ("the transformed Sephiroth's feeler laser",
                                         '/Game/Effect/Character/Player/PC0010_10_Sephiroth_Transform/Build/PC0010_10_Sephiroth_Transform_Effect__Pack.PC0010_10_Sephiroth_Transform_Effect__Pack'),
    'PC0011_Chaos_DeathPenalty_Barret': ("Barret's limit beam", '/Game/Effect/Character/Player/PC0001_Barret/Build/PC0001_Barret_Effect__Pack.PC0001_Barret_Effect__Pack'),
    'PC0011_Chaos_DeathPenalty_Cloud': ("Cloud's charged magic beam", '/Game/Effect/Character/Player/PC0000_Cloud/Build/PC0000_Cloud_Effect__Pack.PC0000_Cloud_Effect__Pack'),
}
CHAOS_PAKS = ['VincentChaos_P', 'VincentDeathPenalty_P']


def chaos_form():
    return {
        # (3.7.8) "as_look": on the game's way (its look change) with Vincent's own AnimBlueprint: the game sets its physics and
        # bone tables up for Chaos's bones (the wings sit in the middle of Vincent's bone order)
        'name': 'CHAOS', 'model': CHAOS_MODEL, 'as_look': True, 'super_armor': True, 'seconds': 150, 'cooldown': 30,
        'fly': {'height': 250, 'speed': 600, 'max': 3000},
        'effects': [{'effect': CHAOS_FLARE, 'scale': 1.3, 'seconds': 3.0}],
        'sounds': [{'bank': EB2160_SE, 'cue': 'FX_EB2160_ChaosFlare_Exp_01'}],
        'camera': {'distance': 100, 'height': 40, 'blend': 0.8},
        'shooter': {
            'camera': {'distance': 300, 'side': 60, 'height': 35, 'aim_distance': 170, 'aim_side': 60, 'aim_height': 25, 'pivot': 70},
            'gun_mesh': DEATH_PENALTY,
            'motions': {'folder': '/Game/RebirthSkelCompat/Dirge/Chaos', 'prefix': 'p007_', 'fly_stance': 'm004_cf_st_a'},
            'weapons': [{'name': 'DEATH PENALTY', 'set': 'm001_h', 'fly_set': 'm004_hf', 'damage_source': BEAM, 'clip': 8, 'interval': 0.35,
                         'reload': 1.2, 'range': 4000.0, 'spread': 0.2, 'recoil': 3.0, 'reticle': 'reticle_ornate'}],
        },
    }


MENU_ART = ['/Game/Menu/Resident/Texture/%s.%s' % (n, n) for n in ('U_Command_Base_11', 'U_Command_BtnBase_06', 'U_Command_Base_03', 'U_Command_Header_02',
                                                                 'U_Command_Arrow_01', 'U_TargetCursor_Arrow_00', 'U_Command_BtnBase_08')]


def main(out, result_file=None):
    plan = json.load(open(PLAN))
    data = json.load(open(DATA))
    entrance = json.load(open(ENTRANCE))
    blend = json.load(open(BLEND))
    failed = set()
    if result_file:
        result = json.load(open(result_file))
        assert result.get('done'), 'the build did not finish'
        failed = {f.split(' ')[0] for f in result.get('failed', [])}
    built = plan['build_folder']
    by = {(m['set'], m['name']): m for m in plan['moves']}

    def own_of(m):
        """What a move the build left out plays instead: the beast's animation it was made of."""
        if m.get('mode') == 'root':
            return m['base']
        return m['animation']

    def target(m):
        if m['build']:
            key = m['set'] + '/' + m['name']
            return '%s/%s/%s.%s' % (built, m['set'], m['name'], m['name']) if key not in failed else own_of(m)
        return m['animation']

    def resolve(path):
        """A path in the plan: a built move's (its fallback if the build left it out) or a game animation."""
        if path.startswith(built + '/'):
            set_name, rest = path[len(built) + 1:].split('/', 1)
            return target(by[(set_name, rest.split('.')[0])])
        return path

    moves, fallbacks = [], []
    for m in plan['moves']:
        if m['kind'] == 'chain':
            animation = [resolve(m['animation'])] + [resolve(p) for p in m['then']]
        elif m['kind'] == 'shared':
            animation = resolve(m['animation'])
        else:
            animation = target(m)
            if m['build'] and (m['set'] + '/' + m['name']) in failed:
                fallbacks.append(m['set'] + '/' + m['name'])
        moves.append({'set': m['set'], 'key': m['name'], 'animation': animation})
    for b in blend:
        moves.append({'set': b['set'], 'key': b['name'], 'animation': b['object']})
    keys = [(m['set'], m['key']) for m in moves]
    assert len(keys) == len(set(keys)), 'a move twice'
    cut_anims = sorted({s['animation'] for s in entrance['shots']})
    cut_fx = sorted({e['effect'] for s in entrance['shots'] for e in s.get('effects', [])})
    cut_se = sorted({x['bank'] for s in entrance['shots'] for x in s.get('sounds', []) if x.get('bank')})
    form = {
        'name': 'GALIAN BEAST', 'pack': 'Battle07', 'model': MODEL, 'anim_class': ANIM_CLASS, 'scale': 1.0, 'meshes': PARTS,
        'hide_weapon': True, 'shooter': False, 'super_armor': True, 'seconds': 150, 'cooldown': 30,
        'sets': {'Battle00': 'Battle07', 'Battle01': 'Battle08', 'Facial00': 'Facial07'},
        'camera': {'distance': 220, 'height': 60, 'blend': 0.8},
        'effects': [{'effect': FX + 'Particle/FX_EV_NIBLE_8310_Roar_Smoke_01.FX_EV_NIBLE_8310_Roar_Smoke_01', 'seconds': 2.0}],
        'entrance': entrance,
    }
    normal = {'name': 'NORMAL', 'effects': [{'effect': FX + 'Particle/FX_EV_NIBLE_8310_BodyAura_01.FX_EV_NIBLE_8310_BodyAura_01', 'socket': 'C_Hip_a',
                                            'seconds': 1.5}]}
    row = {
        'characters': plan['characters'],
        'player': 'pt_Cloud',
        'abilities': data['abilities'],
        'battle': [{'from': b['path'], 'as': b['as_']} for b in plan['battle']],
        'moves': moves,
        'preload': cut_anims + cut_fx + cut_se + MENU_ART,
        'pack_assets': PACK_ASSETS,
        'build_folder': built,
        'requires_paks': plan['requires_paks'],
        'enabled': True,
        'forms': {'button': 'Gamepad_FaceButton_Top', 'hold_seconds': 0.35, 'title': 'FORMS', 'effect_seconds': 2.5,
                  'list': [normal, form, chaos_form()]},
    }
    row['pack_assets'] = row['pack_assets'] + [BEAM_OPTIONS[BEAM][1]]
    row['requires_paks'] = row['requires_paks'] + CHAOS_PAKS
    doc = {'schema': 'RebirthSkelCompat/1', 'source': plan['data_object'],
           '_chaos_beams': ['CHAOS\'s DEATH PENALTY fires %s ("damage_source": %s). Its other beams: %s; each needs its effect pack in "pack_assets" '
                            '(in place of %s)' % (BEAM_OPTIONS[BEAM][0], BEAM, '; '.join('%s: %s (%s)' % (k, v[0], v[1]) for k, v in BEAM_OPTIONS.items() if k != BEAM),
                                                   BEAM_OPTIONS[BEAM][1])],
           'animation_sets': [row]}
    json.dump(doc, open(out, 'w'), indent=1)
    print('%s: %d moves (%d built, %d left out of the build: the beast\'s own play), %d blend spaces, %d preloaded, abilities %s' % (
        out, len(moves), sum(1 for m in plan['moves'] if m['build']) - len(fallbacks), len(fallbacks), len(blend), len(row['preload']),
        {k: (len(v) if isinstance(v, (list, dict)) else v) for k, v in data['abilities'][0].items()}))
    if fallbacks:
        print('left out of the build:', ', '.join(fallbacks))


if __name__ == '__main__':
    main(*sys.argv[1:])
