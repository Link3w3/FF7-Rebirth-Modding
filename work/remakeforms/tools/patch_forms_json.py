"""The REMAKE and REMAKE WINGED forms in the Fully Playable Sephiroth's forms files (SephirothForms.json, adult) and the
Fully Playable Young Sephiroth's (YoungSephirothForms.json): their packs (Battle08, Battle09: Sephiroth's Battle00 sets
with the built Remake moves over them), their ATB commands, and the two forms at the end of the forms menu.
    patch_forms_json.py <plan.json> <in SephirothForms.json> <in YoungSephirothForms.json> <out dir>"""
import json, os, sys

P = '/Game/Motion/Player/PC0010_Sephiroth/'
SE = '/Game/Sound/SE/Character/Player/SE_PC0010_00_Sephiroth_Standard.SE_PC0010_00_Sephiroth_Standard'
VO = '/Game/Sound/Voice/{language}/Character/Player/VO_PC0010_00_Sephiroth.VO_PC0010_00_Sephiroth'
MASAMUNE = '/Game/BluePrint/Character/Weapon/WE1021_10_SephirothIllusion_MasamuneCutScale.WE1021_10_SephirothIllusion_MasamuneCutScale_C'
EB0 = '/Game/GameContents/Character/Enemy/EB0021_00_Sephiroth_Standard/Model/EB0021_00.EB0021_00'
EB1 = '/Game/GameContents/Character/Enemy/EB0021_01_Sephiroth_Transform/Model/EB0021_01_Body.EB0021_01_Body'
EB1_WING = '/Game/GameContents/Character/Enemy/EB0021_01_Sephiroth_Transform/Model/EB0021_01_Wing.EB0021_01_Wing'
FX = '/Game/Effect/Character/Player/PC0010_Sephiroth/Particle/'
FEATHER = '/Game/Effect/Cut/8800-FOREE/EV_FOREE_7250/Particle/FX_EV_FOREE_7250_BlackFeather_01.FX_EV_FOREE_7250_BlackFeather_01'
FEATHER_AURA = '/Game/Effect/Cut/8800-FOREE/EV_FOREE_7250/Particle/FX_EV_FOREE_7250_BlackFeather_Aura_01.FX_EV_FOREE_7250_BlackFeather_Aura_01'
COMMANDS = ['PC0010_RM_Octaslash', 'PC0010_RM_Scintilla', 'PC0010_RM_ShadowFlare', 'PC0010_RM_HellsGate', 'PC0010_T_HeartlessAngel']
WEAPON_ABILITIES = {'PC0000_AtkBurst02': 'PC0010_T_Blizzaga', 'PC0000_AtkBurst04': 'PC0010_W3_InfernalGate', 'PC0000_AtkBurst05': 'PC0010_T_Aeroga',
                    'PC0000_AtkBurst06': 'PC0010_W3_SwordDance', 'PC0000_AtkBurst07': 'PC0010_T_OctaslashPrime',
                    'PC0000_AtkBurst08': 'PC0010_W2_ZanshinRising', 'PC0000_AtkBurst09': 'PC0010_T_Thundaga'}
SOURCE_ADD = (' (Create a Character System 3.11.4: REMAKE and REMAKE WINGED, at the end of the forms menu: he becomes FINAL FANTASY '
              'VII REMAKE\'s Sephiroth, its model from CreateACharacterSkins_P (without it he keeps his own), and fights with Remake '
              'Sephiroth\'s own moves: his combo the boss\'s Assault chain and full-moon slash, his hold Square Ichijin (on the ground and '
              'in the air), each of its two slashes loosing one of Bizarro Sephiroth\'s Zanshin waves, his spells cast '
              'as Remake\'s, and his ATB commands Remake\'s Octaslash, Scintilla, Shadow Flare, Hell\'s Gate and Heartless Angel (Battle08); '
              'REMAKE WINGED (Battle09) wears Remake\'s winged Sephiroth, his black wing included, with the winged phase\'s Shadow Flare '
              'and Heartless Angel. The moves are in the data container.)')


def remake_forms(young):
    common = {'as_look': True}
    if young:
        common.update({'weapon': MASAMUNE, 'voice': 'own'})
    remake = dict(name='REMAKE', pack='Battle08', model=EB0, **common)
    remake['effects'] = [{'effect': FX + 'FX_PC0010_Warp_FadeApp_01.FX_PC0010_Warp_FadeApp_01', 'socket': 'C_Spine_c'},
                         {'effect': FX + 'FX_PC0010_Aura_Body_01.FX_PC0010_Aura_Body_01'}]
    remake['sounds'] = [{'bank': SE, 'cue': 'B_AtkHattou01_0_bell'}, {'bank': VO, 'cue': 'Atk_Ability_02'}]
    winged = dict(name='REMAKE WINGED', pack='Battle09', model=EB1, meshes=[EB1_WING], **common)
    winged['effects'] = [{'effect': FEATHER, 'socket': 'C_Spine_c'}, {'effect': FEATHER_AURA},
                         {'effect': FX + 'FX_PC0010_Limit01_BodyAura_01.FX_PC0010_Limit01_BodyAura_01'}]
    winged['sounds'] = [{'bank': SE, 'cue': 'B_AtkTenshi01_wing'}, {'bank': VO, 'cue': 'Atk_Ability_01'}]
    return [remake, winged]


def move_entries(plan):
    built = {(m['set'], m['name']): m for m in plan['moves']}
    out = []
    for s in ('Battle08', 'Battle09'):
        for key, anim in sorted(plan['keys'][s].items()):
            e = {'set': s, 'key': key, 'animation': anim}
            m = built.get((s, key))
            if m:
                b = {'from': m['animation'] + '.' + m['animation'].rsplit('/', 1)[1], 'notifies_from': m['notifies_from'] + '.' + m['notifies_from'].rsplit('/', 1)[1]}
                if m['hits']:
                    b['hits'] = [dict({'time': h['time']}, **({'window': h['window']} if 'window' in h else {}), **({'damage': h['damage']} if 'damage' in h else {}))
                                 for h in m['hits']]
                if m.get('clip'):
                    b['clip'] = m['clip']
                if m.get('speed'):
                    b['speed'] = m['speed']
                e['build'] = b
            out.append(e)
    return out


def patch(doc, plan, young):
    r = doc['animation_sets'][0]
    assert not any(m['set'] in ('Battle08', 'Battle09') for m in r['moves']), 'already has the REMAKE packs'
    assert not any(f['name'].startswith('REMAKE') for f in r['forms']['list'])
    for s in ('Battle08', 'Battle09'):
        r['battle'].append({'from': P + 'Battle00.Battle00', 'as': s})
        r['battle'].append({'from': P + 'Battle00_Comp.Battle00_Comp', 'as': s})
        r['abilities'].append({'pack': s, 'commands': list(COMMANDS), 'weapon_abilities': dict(WEAPON_ABILITIES)})
    r['moves'] += move_entries(plan)
    r['forms']['list'] += remake_forms(young)
    doc['source'] = doc['source'] + SOURCE_ADD
    return doc


if __name__ == '__main__':
    plan = json.load(open(sys.argv[1]))
    out = sys.argv[4]
    os.makedirs(out, exist_ok=True)
    for src, young in ((sys.argv[2], False), (sys.argv[3], True)):
        doc = json.load(open(src, encoding='utf-8'))
        before = len(doc['animation_sets'][0]['moves'])
        doc = patch(doc, plan, young)
        dst = os.path.join(out, os.path.basename(src))
        with open(dst, 'w', encoding='utf-8') as f:
            json.dump(doc, f, indent=1, ensure_ascii=False)
        r = doc['animation_sets'][0]
        print('%s: %d -> %d moves; forms %s' % (os.path.basename(src), before, len(r['moves']), [f['name'] for f in r['forms']['list']]))
