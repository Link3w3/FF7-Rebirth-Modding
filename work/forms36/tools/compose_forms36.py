"""SephirothForms.json for Create a Character System 3.6: the installed one (his forms' moves, abilities, preload) plus
  * "forms": his forms menu (hold Triangle in battle): NORMAL, WINGED, FLYING, KH2 and BIZARRO, each with its pack, its
    parts (his wing), its switch effects and sounds; FLYING flies (and comes by itself after Heartless Angel); BIZARRO wears
    Bizarro Sephiroth (his body, AnimBlueprint and six parts, at a size of his own), hides his sword, conjures Bizarro's
    sword in his sword attacks, has super armor and lasts 60 s (then 30 s before it can be chosen again),
  * Battle05 (BIZARRO): Bizarro's own sets, his moves built from Bizarro's animations (make_bizarro_moves.py) and his
    commands: Bizarro's attacks (Octaslash, Zanshin, Hell's Gate, Swarm, Heartless Angel), and in place of his
    weapon abilities seven more of Bizarro's,
  * pack_assets: Bizarro's effect pack.
    compose_forms36.py <installed SephirothForms.json> <bizarro_moves.json> <out SephirothForms.json> <out forms_import.json>
                       [failed moves json (the editor's result: moves left out)]"""
import json, sys

SET = 'Battle05'
BUILT = '/Game/RebirthSkelCompat/Built/SephirothForms/'
FEATHERS = '/Game/Effect/Cut/8800-FOREE/EV_FOREE_7250/Particle/FX_EV_FOREE_7250_BlackFeather_01.FX_EV_FOREE_7250_BlackFeather_01'
FEATHER_AURA = '/Game/Effect/Cut/8800-FOREE/EV_FOREE_7250/Particle/FX_EV_FOREE_7250_BlackFeather_Aura_01.FX_EV_FOREE_7250_BlackFeather_Aura_01'
WING_ROOT = 'R_FeatherShoulder_a'
SE = '/Game/Sound/SE/Character/Player/SE_PC0010_00_Sephiroth_Standard.SE_PC0010_00_Sephiroth_Standard'
VOICE = '/Game/Sound/Voice/{language}/Character/Player/VO_PC0010_00_Sephiroth.VO_PC0010_00_Sephiroth'
FX = '/Game/Effect/Character/Player/PC0010_Sephiroth/Particle/'
FX10 = '/Game/Effect/Character/Player/PC0010_10_Sephiroth_Transform/Particle/'
BZ_FX = '/Game/Effect/Character/Enemy/EB2210_BizarroSephiroth/Particle/'
BZ_PACK = '/Game/Effect/Character/Enemy/EB2210_BizarroSephiroth/Build/EB2210_BizarroSephiroth_Effect__Pack.EB2210_BizarroSephiroth_Effect__Pack'
ENEMY = '/Game/Character/Enemy/'
BIZARRO_SCALE = 0.1      # Bizarro Sephiroth is 54 m tall: 5.4 m (0.08 until 2026-10-15: "a little bigger")
GROW = 10.0              # effects made for Sephiroth's size, on Bizarro's mesh (1 / its size above)
# Sephiroth's line in the finale (EV_FOREE_8630): "Alone at last. Shall we?" (text $C3510_MAIN_3400_0400_00_sep, in the
# game's voice language; it plays only while the game has that cutscene's voices loaded: DLL 3.6.3 loads no voice bank)
ALONE_AT_LAST = {'bank': '/Game/Sound/Voice/{language}/Cut/8800-FOREE/EV_FOREE_8630/C3510_MAIN_3400_0400_00_sep.C3510_MAIN_3400_0400_00_sep',
                 'cue': 'C3510_MAIN_3400_0400_00_sep'}


def fx(folder, name, socket=None, scale=None, seconds=None):
    e = {'effect': folder + name + '.' + name}
    if socket:
        e['socket'] = socket
    if scale:
        e['scale'] = scale
    if seconds:
        e['seconds'] = seconds
    return e


def mesh(folder, name):
    return ENEMY + folder + '/Model/' + name + '.' + name


FORMS = {
    'button': 'Gamepad_FaceButton_Top',
    'hold_seconds': 0.35,
    'title': 'FORMS',
    'parts': ['PC0010_10_Wing', 'Wing'],
    'show_effects': [{'effect': FEATHERS, 'socket': WING_ROOT}],
    'hide_effects': [{'effect': FEATHERS, 'socket': WING_ROOT}],
    'effect_seconds': 2.5,
    'list': [
        {'name': 'NORMAL',
         'effects': [fx(FX, 'FX_PC0010_Aura_Body_01')],
         'sounds': [{'bank': SE, 'cue': 'SE_PC0010_10_B_AtkTenshi01_1_squat'}]},
        {'name': 'WINGED', 'pack': 'Battle02', 'show': ['PC0010_10_Wing', 'Wing'],
         'effects': [fx(FX, 'FX_PC0010_Limit01_BodyAura_01'), fx(FX10, 'FX_PC0010_10_SetFeeler_Wing_01')],
         'sounds': [{'bank': SE, 'cue': 'SE_PC0010_10_B_AtkTenshi01_0_whoosh'}, {'bank': VOICE, 'cue': 'Atk_Ability_02'}]},
        {'name': 'FLYING', 'pack': 'Battle03', 'show': ['PC0010_10_Wing', 'Wing'], 'fly': True, 'after': 'PC0000_Limit002',
         'effects': [fx(FX10, 'FX_PC0010_10_Tenshi_Charge_01'), fx(FX10, 'FX_PC0010_10_SetFeeler_Wing_01')],
         'sounds': [{'bank': SE, 'cue': 'SE_PC0010_10_B_AtkTenshi01_1_jump'}, {'bank': VOICE, 'cue': 'Atk_Ability_01'}]},
        {'name': 'KH2', 'pack': 'Battle04', 'show': ['PC0010_10_Wing', 'Wing'],
         'effects': [{'effect': FEATHERS, 'socket': WING_ROOT}, {'effect': FEATHER_AURA}],
         'sounds': [{'bank': SE, 'cue': 'SE_PC0010_10_B_AtkTenshi01_0_whoosh'}, {'bank': VOICE, 'cue': 'Atk_Ability_01'}]},
        {'name': 'BIZARRO', 'pack': SET,
         'model': mesh('EB2210_00_BizarroSephiroth_Standard', 'EB2210_00_Body'),
         'anim_class': '/Game/BluePrint/Animation/Enemy/EB2210_00_BizarroSephiroth_Standard_Animation.EB2210_00_BizarroSephiroth_Standard_Animation_C',
         'scale': BIZARRO_SCALE,
         'meshes': [mesh('EB2210_10_BizarroSephiroth_WingR', 'EB2210_10'), mesh('EB2210_20_BizarroSephiroth_WingL', 'EB2210_20'),
                    mesh('EB2210_30_BizarroSephiroth_Top', 'EB2210_30'), mesh('EB2210_40_BizarroSephiroth_Face', 'EB2210_40'),
                    mesh('EB2210_45_BizarroSephiroth_HornR', 'EB2210_45'), mesh('EB2210_50_BizarroSephiroth_BodyCore', 'EB2210_50')],
         'hide_weapon': True,
         # his transformation: Bizarro's reverse energy gathering at his core, a shock wave, a storm of black feathers
         'effects': [fx(BZ_FX, 'FX_EB2210_ReverseEnergy_Charge_01', 'C_Core_a', seconds=3.0), fx(BZ_FX, 'FX_EB2210_WindBlow_Shock_01'),
                     {'effect': FEATHERS, 'socket': 'C_Core_a', 'scale': GROW}, {'effect': FEATHER_AURA, 'scale': GROW}],
         'sounds': [{'bank': SE, 'cue': 'SE_PC0010_10_B_AtkTenshi01_0_whoosh'}, ALONE_AT_LAST],
         # Bizarro's conjured swords, in his sword attacks only
         'ability_effects': [
             {'abilities': ['PC0010_BZ_Octaslash', 'PC0000_Limit001', 'PC0010_SAtk_8', 'PC0000_AtkBurst05'],
              'effects': [fx(BZ_FX, 'FX_EB2210_OmniSlash_Sword_01', 'Attack_Sword')]},
             {'abilities': ['PC0010_BZ_Zanshin', 'PC0010_BZ_ZanshinProfaned', 'PC0000_AtkBurst02', 'PC0010_NAtk_3', 'PC0010_NAtk_4',
                            'PC0010_JAtk_3', 'PC0010_SAtk_1', 'PC0010_SAtk_9', 'PC0010_SAtk_6', 'PC0000_AtkBurst04'],
              'effects': [fx(BZ_FX, 'FX_EB2210_LongSword_Sword_01', 'Attack_Sword')]}],
         'super_armor': True, 'seconds': 60, 'cooldown': 30},
    ],
}
ABILITIES = {'pack': SET,
             # (a player row takes 5 commands; Meteor is his level 3 limit)
             'commands': ['PC0010_BZ_Octaslash', 'PC0010_BZ_Zanshin', 'PC0010_BZ_HellsGate', 'PC0010_BZ_Swarm', 'PC0010_BZ_HeartlessAngel'],
             'weapon_abilities': {'PC0000_AtkBurst02': 'PC0010_BZ_ZanshinProfaned', 'PC0000_AtkBurst04': 'PC0010_BZ_UnholyGate',
                                  'PC0000_AtkBurst05': 'PC0010_BZ_ApocalypticFire', 'PC0000_AtkBurst06': 'PC0010_BZ_Profane',
                                  'PC0000_AtkBurst07': 'PC0010_BZ_WhisperVortex', 'PC0000_AtkBurst08': 'PC0010_BZ_Atonement',
                                  'PC0000_AtkBurst09': 'PC0010_BZ_LacrymaDeus'}}
SOURCE_TEXT = ("Sephiroth's forms on Cloud's ability IDs (Create a Character System 3.6): your playable Sephiroth (Cloud's rows, including "
               "the prologue's Cloud in Zack's SOLDIER outfit) has five forms on the forms menu (hold Triangle in battle, pick one with "
               "up / down, let go): NORMAL (Battle00), WINGED (Battle02 = the transformed Sephiroth's Battle00), FLYING (Battle03 = his "
               "Battle01 wing moves, then his Battle00; it also comes by itself after Heartless Angel), KH2 (Battle04: his Kingdom Hearts "
               "II moves) and BIZARRO (Battle05: he becomes Bizarro Sephiroth, with Bizarro's attacks as his commands and in place of his "
               "weapon abilities, his moves made of Bizarro's animations, Bizarro's conjured sword in his sword attacks, super armor; "
               "it lasts 60 s, then 30 s before it can be chosen again). His limits are Cloud's (level 1 Octaslash, 2 Heartless "
               "Angel, 3 Meteor: they unlock like Cloud's), the abilities Cloud's weapons give are his moves and switch with the form "
               "(weapon_abilities), and each form has its own ATB commands. His rows load the transformed Sephiroth's and Bizarro's "
               "effects (pack_assets) and the Fire/Blizzard/Thunder/Aero ability resources (preload). Goes with "
               "FullyPlayableSephirothDataAssets_P (his abilities, limits, damage and rows) and SephirothForms_P (the built moves). "
               "Field sets (Neutral00, Neutral20, Emotion00, Facial00): his own first, then Cloud's. Summons: Cloud's summon cast "
               "(B_MagSummon01) in every form but BIZARRO.")


def battle_moves(plan, failed):
    out = []
    for m in plan['moves']:
        if m['name'] in failed:
            continue
        if m['build']:
            build = {'from': m['animation'], 'notifies_from': m['notifies_from']}
            if m.get('hits'):
                build['hits'] = [dict({'time': h['time']}, **({'damage': h['damage']} if h.get('damage') else {})) for h in m['hits']]
            if m.get('clip'):
                build['clip'] = m['clip']
            if m.get('speed'):
                build['speed'] = m['speed']
            out.append({'set': SET, 'key': m['name'], 'animation': BUILT + SET + '/' + m['name'] + '.' + m['name'], 'build': build})
        elif m.get('then'):
            out.append({'set': SET, 'key': m['name'], 'animation': [m['animation']] + m['then']})
        else:
            out.append({'set': SET, 'key': m['name'], 'animation': m['animation']})
    return out


def main(installed, plan_path, out_path, import_path, failed_path=None):
    j = json.load(open(installed))
    plan = json.load(open(plan_path))
    failed = set(json.load(open(failed_path))) if failed_path else set()
    row = j['animation_sets'][0]
    assert not any(m['set'] == SET for m in row['moves']), 'already has Battle05 moves'
    row['battle'] = [s for s in row['battle'] if s.get('as') != SET] + [{'from': s['path'], 'as': SET} for s in plan['sources']]
    row['moves'] = row['moves'] + battle_moves(plan, failed)
    row['abilities'] = [a for a in row['abilities'] if a['pack'] != SET] + [ABILITIES]
    if BZ_PACK not in row['pack_assets']:
        row['pack_assets'].append(BZ_PACK)
    row['forms'] = FORMS
    j['source'] = SOURCE_TEXT
    json.dump(j, open(out_path, 'w'), indent=1)
    # for the data object (Import From Game Json): the forms of the row, by its characters
    json.dump({'schema': j['schema'], 'pairs': [], 'animation_sets': [{'characters': row['characters'], 'forms': FORMS}]},
              open(import_path, 'w'), indent=1)
    print('%s: %d moves (%d of %s), %d packs of abilities, forms %s; %s' % (out_path, len(row['moves']), sum(1 for m in row['moves'] if m['set'] == SET), SET,
                                                                       len(row['abilities']), [f['name'] for f in FORMS['list']], import_path))
    if failed:
        print('left out (not built): ' + ', '.join(sorted(failed)))


if __name__ == '__main__':
    main(*sys.argv[1:6])
