"""Create a Character System 3.13.0: writes the Customization screen's catalog (what it offers), from
  * the game's own containers (their directory indexes): every playable character's models and their materials, and
    their voices (VOICES), and the weapons characters hold (WEAPONS: the playable characters' and the hand weapons of
    the enemies, bosses and summons),
  * the voices made for the mod, while their containers are in ~mods (Young Sephiroth, Classic Sephiroth),
  * the End project's Game Materials (Saved\\RebirthGameMaterials\\made\\manifest.json): your custom materials,
  * the skins (ue4ss\\Mods\\RebirthSkelCompat\\skins\\*\\skin.json) and the models the compat files' forms wear (and
    their weapons),
  * a few parts (Sephiroth's wing, a white one, and (3.13.0) one with the boss's feelers on it),
  * (3.13.0) effects the EFFECTS page keeps on a weapon, a part or the body: a few of the game's (auras, the boss
    Sephiroth's feelers, charged swords), those the game has.
Run it again after making materials or skins (Python 3, no editor needed):
    py make_customization_catalog.py [--game "C:\\...\\FINAL FANTASY VII REBIRTH"] [--project C:\\FF7R2UProj]
Writes <game>\\End\\Binaries\\Win64\\ue4ss\\Mods\\RebirthSkelCompat\\customization\\catalog.json (the old one kept as catalog.json.bak).
Entries you add by hand go in catalog.extra.json next to it ({"materials": [...], "models": [...], "parts": [...],
"voices": [{"name": ..., "bank": "/Game/Sound/Voice/{language}/.../VO_..."}],
"weapons": [{"name": ..., "path": "/Game/.../WE0000_00_Cloud_BusterSword"} or {"name": ..., "class": "/Game/....X_C"}],
"effects": [{"name": ..., "effect": "/Game/Effect/.../FX_...", "on": "weapon" | "part" | "body" | "any", "socket": ..., "scale": 1}]}):
they are merged in, first, every time (a part of catalog.extra.json takes the place of a part of the same id made
here: the editor's Parts Builder writes its parts there). Skins that hold a Customization part's own assets ("part":
true in their skin.json, made by the Parts Builder) are not models to wear: they are left out of the models."""
import argparse, glob, json, os, re, struct, sys

DEFAULT_GAME = r'C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH'
DEFAULT_PROJECT = r'C:\FF7R2UProj'
# (3.11.1) the voices made for the mod: (its container, the name shown, its bank)
MOD_VOICES = [('ClassicSephirothVoice_P', 'Classic Sephiroth', '/Game/Sound/Voice/{language}/Character/Player/VO_PC0010_15_ClassicSephiroth'),
              ('YoungSephirothVoice_P', 'Young Sephiroth', '/Game/Sound/Voice/{language}/Character/Player/VO_PC0010_13_YoungSephiroth')]
# (3.13.0) effects the EFFECTS page offers: (name, the system under /Game/Effect/, what it goes on, its socket or bone, a note)
P10 = 'Character/Player/PC0010_10_Sephiroth_Transform/Particle/'
EFFECTS = [
    ("Feelers (Sephiroth's sword)", P10 + 'FX_PC0010_10_SetFeeler_Sword_01', 'weapon', 'C_Body_a', "the boss Sephiroth's feelers on his sword"),
    ("Feelers (Sephiroth's wing)", P10 + 'FX_PC0010_10_SetFeeler_Wing_01', 'any', 'R_FeatherD_b_Phy', "the boss Sephiroth's feelers on his wing (a wing part, or a model with his wing)"),
    ("Sephiroth's sword aura", 'Character/Player/PC0010_Sephiroth/Particle/FX_PC0010_Weapon_Aura_01', 'weapon', '', ''),
    ("Zack's weapon aura", 'Character/Player/PC0009_Zack/Particle/FX_PC0009_Burst02_WeaponAura_01', 'weapon', '', ''),
    ("Cloud's charged sword", 'Character/Player/PC0000_Cloud/Particle/FX_PC0000_ChainChargeMagic_ChargeSword_01', 'weapon', '', ''),
    ("Cloud's sword (Sephiroth's charge)", 'Character/Player/PC0000_Cloud/Particle/FX_PC0000_ChainChargeSephiroth_ChargeSword_01', 'weapon', '', ''),
    ("Cloud's limit sword", 'Character/Player/PC0000_Cloud/Particle/FX_PC0000_Limit02_Sword_01', 'weapon', '', ''),
    ("Rufus's fire gun aura", 'Character/Enemy/EB0016_Rufus/Particle/FX_EB0016_FireBreak_GunAura_01', 'weapon', '', ''),
    ("Sephiroth's aura", 'Character/Player/PC0010_Sephiroth/Particle/FX_PC0010_Aura_Body_01', 'body', 'C_Spine_c', "the boss Sephiroth's aura"),
    ("Sephiroth's limit aura", 'Character/Player/PC0010_Sephiroth/Particle/FX_PC0010_Limit01_BodyAura_01', 'body', '', ''),
    ("Bizarro's core feeler", 'Character/Enemy/EB2210_BizarroSephiroth/Particle/FX_EB2210_CoreFeeler_Loop_01', 'any', '', ''),
    ("Bizarro: fire", 'Character/Enemy/EB2210_BizarroSephiroth/Particle/FX_EB2210_MagicMode_Fire_Loop_01', 'any', '', ''),
    ("Bizarro: ice", 'Character/Enemy/EB2210_BizarroSephiroth/Particle/FX_EB2210_MagicMode_Ice_Loop_01', 'any', '', ''),
    ("Bizarro: lightning", 'Character/Enemy/EB2210_BizarroSephiroth/Particle/FX_EB2210_MagicMode_Elec_Loop_01', 'any', '', ''),
    ("Bizarro: wind", 'Character/Enemy/EB2210_BizarroSephiroth/Particle/FX_EB2210_MagicMode_Wind_Loop_01', 'any', '', ''),
    ("Black aura (Soul Fire)", 'Character/Enemy/EB2145_SoulFire/Particle/FX_EB2145_BlackAura_Loop_01', 'body', '', ''),
    ("Cloud's aura", 'Character/Player/PC0000_Cloud/Particle/FX_PC0000_BurstChain00_03_Aura_01', 'body', '', ''),
    ("Barret's aura", 'Character/Player/PC0001_Barret/Particle/FX_PC0001_Burst08_Aura_01', 'body', '', ''),
    ("Tifa's aura trail", 'Character/Player/PC0002_Tifa/Particle/FX_PC0002_Cmn_AuraTrail_01', 'body', '', ''),
    ("Aerith's aura", 'Character/Player/PC0003_Aerith/Particle/FX_PC0003_Burst07_Aura_01', 'body', '', ''),
    ("Red XIII's aura", 'Character/Player/PC0004_RedXIII/Particle/FX_PC0004_Burst09_Aura_01', 'body', '', ''),
    ("Yuffie's aura", 'Character/Player/PC0005_Yuffie/Particle/FX_PC0005_BurstChain03_05_02_Aura_01', 'body', '', ''),
    ("Zack's limit aura", 'Character/Player/PC0009_Zack/Particle/FX_PC0009_Limit01_Aura_01', 'body', '', ''),
    ("Odin's aura", 'Character/Summon/SU2010_Odin/Particle/FX_SU2010_Appear_BodyAura_01', 'body', '', ''),
    ("Leviathan's aura", 'Character/Summon/SU0004_Leviathan/Particle/FX_SU0004_Body_Aura_01', 'body', '', ''),
    ("Reno's mode aura", 'Character/Enemy/EB0003_Reno/Particle/FX_EB0003_ModeChange_Aura_01', 'any', '', ''),
    ("Rude's mode aura", 'Character/Enemy/EB0005_Rude/Particle/FX_EB0005_ModeChange_Aura_01', 'any', '', ''),
    ("Ancient aura", 'Action/0110-GILGA/Particle/FX_0110-GILGA_Ancient_Aura_01', 'body', '', ''),
    ("Lifestream", 'Action/2430-GONGS/Particle/FX_2430-GONGS_Life_Loop_01', 'body', '', ''),
    ("Electric aura", 'Ability/EneSkill01/Particle/FX_EneSkill01_Electric_Aura_01', 'any', '', ''),
    ("Healing wind", 'Ability/EneSkill01/Particle/FX_EneSkill01_HealWind_Aura_01', 'any', '', ''),
    ("Poison cloud", 'Ability/Bio01/Particle/FX_Bio01_Loop_01', 'any', '', ''),
]


def fstr(d, p):
    n = struct.unpack_from('<i', d, p)[0]
    p += 4
    if n < 0:
        return d[p:p - 2 * n].decode('utf-16-le').rstrip('\0'), p - 2 * n
    return d[p:p + n].decode('latin-1').rstrip('\0'), p + n


def toc_files(toc):
    """The file names of a UE 4.26 IoStore .utoc's directory index (None: it has none)."""
    if toc[:16] != b'-==--==--==--==-':
        return None
    hs, n, nblocks, bsize, ncomp, compnamelen, blocksize, dirsize, parts = struct.unpack_from('<9I', toc, 20)
    flags = toc[16 + 4 + 36 + 8 + 16]
    p = hs + 12 * n + 10 * n + bsize * nblocks + ncomp * compnamelen
    if flags & 2:
        hsz = struct.unpack_from('<i', toc, p)[0]
        p += 4 + 2 * hsz + 20 * nblocks
    if not (flags & 8) or not dirsize:
        return None
    d = toc[p:p + dirsize]
    mount, q = fstr(d, 0)
    nd = struct.unpack_from('<i', d, q)[0]; q += 4
    dirs = [struct.unpack_from('<4I', d, q + 16 * i) for i in range(nd)]; q += 16 * nd
    nf = struct.unpack_from('<i', d, q)[0]; q += 4
    fents = [struct.unpack_from('<3I', d, q + 12 * i) for i in range(nf)]; q += 12 * nf
    ns = struct.unpack_from('<i', d, q)[0]; q += 4
    strings = []
    for _ in range(ns):
        s, q = fstr(d, q)
        strings.append(s)
    out = []
    none = 0xFFFFFFFF

    def walk(di, path):
        name, child, sib, first = dirs[di]
        here = path + (strings[name] + '/' if name != none else '')
        f = first
        while f != none:
            fname, nxt, _ = fents[f]
            out.append(mount + here + strings[fname])
            f = nxt
        c = child
        while c != none:
            walk(c, here)
            c = dirs[c][2]
    if nd:
        walk(0, '')
    return out


def game_packages(game):
    paks = os.path.join(game, 'End', 'Content', 'Paks')
    names = set()
    for toc in sorted(glob.glob(os.path.join(paks, '*.utoc'))):
        try:
            files = toc_files(open(toc, 'rb').read())
        except Exception as e:
            print('  (skipped %s: %s)' % (os.path.basename(toc), e))
            continue
        for f in files or ():
            f = f.replace('\\', '/')
            if not f.endswith('.uasset'):
                continue
            i = f.find('/Content/')
            if i < 0:
                continue
            names.add('/Game/' + f[i + 9:-7])
    return names


def pretty(word):
    return re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', word)


# (3.12.0) WEAPONS: the game's weapon blueprints a character can hold. Left out: what is not held in a hand (traps, mines,
# grenades, stones and rocks, ore, arrows, shells and bombs, currency and throwing items, backpacks, crowns, hats, basins,
# bands, sunglasses, comets, dice, toy boxes, the dolphin, Mu holes, icicles) and the minigame / special series (WE7xxx,
# WE9xxx). Weapons made for their character's body (Tifa's gloves, Barret's arm, Red XIII's collars) are offered to
# that character only ("for").
WEAPON_SKIP = re.compile(r'(Trap|Landmine|Mine|Grenade|Stone|Rock|Ore$|Arrow|Shell|Bomb|Currency|ThrowingItem|Backpack|Crown|Hat$|Tarai|'
                         r'Band$|Sunglass|Comet|Dice|Toybox|Dolphin|MuHole|Icicles|Missile|Drone|_Weapon$)', re.I)
WEAPON_OWN_BODY = {'WE0001': 'Barret', 'WE0002': 'Tifa', 'WE0004': 'Red XIII'}
WEAPON_WHO = {'SephirothIllusion': 'Sephiroth', 'SecuritySoldier': 'Security Soldier', 'CorneoLackey': 'Corneo Lackey',
              'Soldier3rd': 'SOLDIER 3rd Class', 'GiNattak': 'Gi Nattak', 'GiSpector': 'Gi Specter', 'IronMan': 'Iron Man',
              'MythrilGolem': 'Mythril Golem', 'CaitSith': 'Cait Sith', 'RedXIII': 'Red XIII'}


def weapon_name(leaf):
    """WE0000_11_Cloud_END2Weapon1 -> ('WE0000', 'Cloud: Rebirth weapon 1')"""
    bits = leaf.split('_', 3)
    if len(bits) < 4:
        return bits[0], pretty(leaf)
    who = WEAPON_WHO.get(bits[2], pretty(bits[2]))
    what = bits[3]
    m = re.match(r'END2Weapon(\d+)$', what)
    if m:
        what = 'Rebirth weapon %s' % m.group(1)
    else:
        what = pretty(what.replace('End2', '').replace('END2', '').replace('DBShotgun', 'DoubleBarrelShotgun').replace('MythrilColor', 'MythrilCollar'))
    return bits[0], '%s: %s' % (who, what)


def game_weapons(names):
    out = []
    for package in sorted(n for n in names if n.startswith('/Game/BluePrint/Character/Weapon/WE')):
        leaf = package.rsplit('/', 1)[-1]
        if not re.match(r'WE\d{4}_\d{2}_', leaf) or leaf[2] in '79' or WEAPON_SKIP.search(leaf):
            continue
        who, name = weapon_name(leaf)
        entry = {'name': name, 'path': package, 'who': who}
        if who in WEAPON_OWN_BODY:
            entry['for'] = [who]
            entry['note'] = 'made for %s\'s body: offered to %s only' % (WEAPON_OWN_BODY[who], WEAPON_OWN_BODY[who])
        if 'Cut' in leaf.split('_', 3)[-1] and leaf.startswith('WE1021'):
            entry['note'] = "a cutscene's"
        out.append(entry)
    # (two of the same name: numbered)
    counts = {}
    for e in out:
        counts[e['name']] = counts.get(e['name'], 0) + 1
    seen = {}
    for e in out:
        if counts[e['name']] > 1:
            seen[e['name']] = seen.get(e['name'], 0) + 1
            if seen[e['name']] > 1:
                e['name'] = '%s (%d)' % (e['name'], seen[e['name']])
    return out


def class_of(path):
    """A weapon blueprint's class: /Game/.../X -> /Game/.../X.X_C (a class path stays)"""
    leaf = path.rsplit('/', 1)[-1]
    if '.' in leaf:
        return path if path.endswith('_C') else path + '_C'
    return '%s.%s_C' % (path, leaf)


def obj(path):
    leaf = path.rsplit('/', 1)[-1]
    return path if '.' in leaf else path + '.' + leaf


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--game', default=DEFAULT_GAME)
    ap.add_argument('--project', default=DEFAULT_PROJECT)
    a = ap.parse_args()
    mod = os.path.join(a.game, 'End', 'Binaries', 'Win64', 'ue4ss', 'Mods', 'RebirthSkelCompat')
    out_dir = os.path.join(mod, 'customization')
    os.makedirs(out_dir, exist_ok=True)
    print('reading the game\'s containers ...')
    names = game_packages(a.game)
    print('  %d packages' % len(names))
    materials, models, parts, weapons = [], [], [], []
    # your custom Game Materials
    groups = [('/Game/GameContents/Character/Player/PC0000_00_Cloud_Standard/', 'Remake Cloud'),
              ('/Game/GameContents/Character/Enemy/EB0021_00_Sephiroth_Standard/', 'Remake Sephiroth'),
              ('/Game/GameContents/Character/Enemy/EB0021_01_Sephiroth_Transform/', 'Remake Sephiroth (transformed)'),
              ('/Game/Character/Player/PC0010_10_Young_Sephiroth_Outfit_Transformed/', 'Young Sephiroth'),
              ('/Game/Character/Weapon/WE1021_49_Nameless/', 'Nameless'),
              ('/Game/Shader/KadeMats/Material_Instances/', 'KadeMats')]
    manifest = os.path.join(a.project, 'Saved', 'RebirthGameMaterials', 'made', 'manifest.json')
    made = 0
    if os.path.isfile(manifest):
        for package, info in sorted(json.load(open(manifest, encoding='utf-8')).items()):
            if '/Renderer/Material/' in package or package.endswith('/RM_SurfaceRemake'):
                continue   # (masters, not a character's materials)
            path = info.get('material') or obj(package)
            leaf = package.rsplit('/', 1)[-1]
            group = next((g for prefix, g in groups if package.startswith(prefix)), 'My materials')
            part = re.sub(r'^(PC|EB|WE)\d{4}_\d{2}_', '', leaf)
            part = re.sub(r'^mat_ch\d+_\d+_', '', part)
            materials.append({'name': '%s: %s' % (group, pretty(part)), 'path': path})
            made += 1
    print('  %d of your materials' % made)
    # the game's: each playable character's outfits, for the same part of that character
    game_mats = 0
    for package in sorted(n for n in names if n.startswith('/Game/Character/Player/') and '/Material/' in n):
        folder = package.split('/')[4]                      # PC0000_04_Cloud_ZackCostume
        bits = folder.split('_')
        if len(bits) < 4 or not re.match(r'PC\d{4}$', bits[0]):
            continue
        leaf = package.rsplit('/', 1)[-1]
        m = re.match(r'PC\d{4}_\d{2}_(.+)$', leaf)
        if not m:
            continue
        part = m.group(1)
        who = '%s %s' % (bits[2], pretty('_'.join(bits[3:])))
        materials.append({'name': '%s: %s' % (who, pretty(part)), 'path': obj(package), 'for': [bits[0] + '_*'], 'slots': ['*' + part]})
        game_mats += 1
    print('  %d of the game\'s character materials' % game_mats)
    # models: every playable character's (each outfit), any character can wear them
    for package in sorted(n for n in names if n.startswith('/Game/Character/Player/') and '/Model/' in n):
        folder, leaf = package.split('/')[4], package.rsplit('/', 1)[-1]
        if not re.match(r'PC\d{4}_\d{2}$', leaf) or not folder.startswith(leaf + '_'):
            continue
        bits = folder.split('_')
        models.append({'name': '%s: %s' % (bits[2], pretty('_'.join(bits[3:]))), 'path': obj(package)})
    # the skins' models and the forms' models
    seen = {m['path'].lower() for m in models}
    for skin in sorted(glob.glob(os.path.join(mod, 'skins', '*', 'skin.json'))):
        try:
            s = json.load(open(skin, encoding='utf-8'))
        except Exception:
            continue
        if s.get('part'):
            continue   # (3.12.1: a Customization part's assets, not a model to wear)
        model = s.get('model')
        if model and obj(model).lower() not in seen:
            models.append({'name': 'Skin: %s' % (s.get('name') or os.path.basename(os.path.dirname(skin))), 'path': obj(model)})
            seen.add(obj(model).lower())
    for compat in sorted(glob.glob(os.path.join(mod, 'compat', '*.json'))):
        try:
            text = open(compat, encoding='utf-8').read()
        except Exception:
            continue
        for model in re.findall(r'"model"\s*:\s*"(/Game/[^"]+)"', text):
            if obj(model).lower() in seen:
                continue
            leaf = model.rsplit('/', 1)[-1].split('.')[0]
            models.append({'name': 'Form model: %s' % leaf, 'path': obj(model)})
            seen.add(obj(model).lower())
    print('  %d models' % len(models))
    # (3.12.0) weapons: the game's, then the skins' and the forms' (a class each)
    weapons = game_weapons(names)
    seen_w = {class_of(w['path']).lower() for w in weapons}
    for skin in sorted(glob.glob(os.path.join(mod, 'skins', '*', 'skin.json'))):
        try:
            s = json.load(open(skin, encoding='utf-8'))
        except Exception:
            continue
        weapon = s.get('weapon')
        if s.get('part') or not weapon or class_of(weapon).lower() in seen_w:
            continue
        name = s.get('name') or os.path.basename(os.path.dirname(skin))
        leaf = class_of(weapon).rsplit('.', 1)[-1][:-2]
        weapons.append({'name': "Skin %s: %s" % (name, weapon_name(leaf)[1].split(': ', 1)[-1]), 'class': class_of(weapon), 'note': "the %s skin's" % name})
        seen_w.add(class_of(weapon).lower())
    for compat in sorted(glob.glob(os.path.join(mod, 'compat', '*.json'))):
        try:
            text = open(compat, encoding='utf-8').read()
        except Exception:
            continue
        for weapon in re.findall(r'"weapon"\s*:\s*"(/Game/[^"]+)"', text):
            if class_of(weapon).lower() in seen_w:
                continue
            leaf = class_of(weapon).rsplit('.', 1)[-1][:-2]
            weapons.append({'name': 'Form weapon: %s' % weapon_name(leaf)[1], 'class': class_of(weapon), 'note': os.path.basename(compat)})
            seen_w.add(class_of(weapon).lower())
    print('  %d weapons' % len(weapons))
    # (3.11.1) voices: the mod's (their containers anywhere under ~mods), then every playable character's of the game
    voices = []
    installed = set()
    for root, dirs, files in os.walk(os.path.join(a.game, 'End', 'Content', 'Paks', '~mods')):
        installed.update(f[:-5].lower() for f in files if f.lower().endswith('.utoc'))
    for container, name, bank in MOD_VOICES:
        if container.lower() in installed:
            voices.append({'name': name, 'bank': bank, 'note': container})
    for package in sorted(n for n in names if n.startswith('/Game/Sound/Voice/JP/') and re.search(r'/VO_PC\d{4}_\d{2}_[A-Za-z0-9]+$', n)):
        who = pretty(package.rsplit('/', 1)[-1].split('_', 3)[3])
        voices.append({'name': who, 'bank': package.replace('/Sound/Voice/JP/', '/Sound/Voice/{language}/', 1), 'note': "the game's"})
    print('  %d voices' % len(voices))
    # parts
    wing = {'model': '/Game/Character/Player/PC0010_10_Sephiroth_Transform/Model/PC0010_10.PC0010_10', 'bone': 'C_Spine_d', 'sections': [10],
            'idle': '/Game/Motion/Player/PC0010_Sephiroth_Transform/Battle00/B_Idle01_1.B_Idle01_1', 'component_class': '/Script/EndGame.EndSkeletalMeshComponent',
            # (KH3-style sync) the wing plays its own motion of the name of the one the character plays (its motions are the
            # winged Sephiroth's: /Game/Motion/Player/PC0010_Sephiroth_Transform/<Folder>/<the same name>), else its idle
            'sync': True}
    parts.append(dict(wing, id='sephiroth_wing', name="Sephiroth's wing"))
    parts.append(dict(wing, id='sephiroth_wing_white', name="Sephiroth's wing (white)", tint_texture='/Game/Renderer/Texture/FFFFFFFF_sRGB.FFFFFFFF_sRGB',
                      tint_texture_param='Color'))
    # (3.13.0) the wing with the boss's feelers on it (its own effect: on while it is worn)
    feeler_wing = '/Game/Effect/' + P10 + 'FX_PC0010_10_SetFeeler_Wing_01'
    if feeler_wing in names:
        parts.append(dict(wing, id='sephiroth_wing_feelers', name="Sephiroth's wing (feelers)", effects=[{'effect': obj(feeler_wing), 'socket': 'R_FeatherD_b_Phy'}]))
    # (3.13.0) effects (those the game has)
    effects = []
    for name, rel, on, socket, note in EFFECTS:
        package = '/Game/Effect/' + rel
        if package not in names:
            continue
        e = {'name': name, 'effect': obj(package), 'on': on}
        if socket:
            e['socket'] = socket
        if note:
            e['note'] = note
        effects.append(e)
    print('  %d effects' % len(effects))
    # what you added by hand
    extra = os.path.join(out_dir, 'catalog.extra.json')
    if os.path.isfile(extra):
        try:
            e = json.load(open(extra, encoding='utf-8'))
            materials = list(e.get('materials', [])) + materials
            models = list(e.get('models', [])) + models
            mine = [p for p in e.get('parts', []) if isinstance(p, dict)]
            ids = {str(p.get('id') or p.get('name') or '').lower() for p in mine}
            # (3.12.1) a part of the same id as one of yours is yours (the Parts Builder edits the made ones there)
            parts = mine + [p for p in parts if str(p.get('id') or p.get('name') or '').lower() not in ids]
            voices = list(e.get('voices', [])) + voices
            weapons = list(e.get('weapons', [])) + weapons
            effects = [x for x in e.get('effects', []) if isinstance(x, (dict, str))] + effects   # (3.13.0)
            print('  + catalog.extra.json')
        except Exception as ex:
            print('  catalog.extra.json NOT read: %s' % ex)
    catalog = {
        'about': 'Create a Character System: what the Customization screen offers (made by make_customization_catalog.py; add your own in catalog.extra.json)',
        'preview': {'key_lux': 1.5, 'fill_lux': 0.45, 'rim_lux': 1.1, 'zoom': 1.0},   # (3.11.1: the menu preview world's scale: its own light is 3 lux)
        'materials': materials, 'models': models, 'parts': parts, 'voices': voices, 'weapons': weapons, 'effects': effects}
    path = os.path.join(out_dir, 'catalog.json')
    if os.path.isfile(path):
        try:
            os.replace(path, path + '.bak')
        except OSError:
            pass
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, indent=1)
    print('wrote %s: %d materials, %d models, %d parts, %d voices, %d weapons, %d effects' % (path, len(materials), len(models), len(parts), len(voices),
                                                                                            len(weapons), len(effects)))


if __name__ == '__main__':
    main()
