"""Test pak: Cloud (with the Buster Sword) in Sephiroth's place, everywhere Sephiroth appears.
Retail CharaSpec packs with their imports pointed at Cloud's (Sephiroth's six rows) or at the Buster Sword
(the four Masamune rows), and the retail CharaSpec table with those rows describing what the packs spawn.
    build_cos_test.py <out dir>"""
import hashlib, os, shutil, struct, sys
sys.path.insert(0, '/work/iostore'); sys.path.insert(0, '/work/cs')
sys.path.insert(0, '/work/vincentfix'); sys.path.insert(0, '/work/weap1012/tools')
from iostore import Toc
import iostore_write as W
from zen import Zen
import charaspec_patch as cp
import gameids

NAME = 'CloudOverSephiroth_TEST_P'
SRC = '/work/seph1012/'
PACK = '/Game/DataAsset/Game/CharaSpec/CharaSpec_'
NULL = 0xFFFFFFFFFFFFFFFF
objhash = gameids.objhash
PKG, OBJ = gameids.load()

def imp(path):
    return (2 << 62) | objhash(path)

BP = '/Game/BluePrint/Character/Player/'
WBP = '/Game/BluePrint/Character/Weapon/'
LANGS = ('JP', 'US', 'DE', 'FR')
# Cloud's voice in Sephiroth's place: his "insanity" lines (the voice pack the game switches to with stfCmn_Voice_Cloud_Insanity).
CLOUD_VO, CLOUD_LSD = 'VO_PC0000_02_Cloud_Insanity', 'LSD_PC0000_02_Cloud_Insanity'
# Cloud's field actions (ladders, ledges) in Sephiroth's rows; False keeps Sephiroth's whole moveset.
CLOUD_FIELD_ACTIONS = True

def character_maps(seph_bp, cloud_bp, talk, voice):
    """seph_bp, cloud_bp: blueprint names (PC0010_00_Sephiroth_Standard -> PC0000_00_Cloud_Standard).
    talk: also BattleTalk; voice: (old voice package path stem, old lipsync stem) or None."""
    s, c = BP + seph_bp, BP + cloud_bp
    objs = {
        s + '.' + seph_bp + '_C': c + '.' + cloud_bp + '_C',
        s + '.Default__' + seph_bp + '_C': c + '.Default__' + cloud_bp + '_C',
        s + '.' + seph_bp + '_C:DefaultSceneRoot_GEN_VARIABLE': c + '.' + cloud_bp + '_C:DefaultSceneRoot_GEN_VARIABLE',
    }
    for sub in ('CharMoveComp', 'CollisionCylinder', 'CharacterMesh0'):
        objs[s + '.Default__' + seph_bp + '_C:' + sub] = c + '.Default__' + cloud_bp + '_C:' + sub
    if talk:
        objs[s + '.' + seph_bp + '_C:BattleTalk_Sephiroth_GEN_VARIABLE'] = c + '.' + cloud_bp + '_C:BattleTalk_Cloud_GEN_VARIABLE'
        objs['/Game/BluePrint/Misc/BattleTalk/BattleTalk_Sephiroth.BattleTalk_Sephiroth_C'] = '/Game/BluePrint/Misc/BattleTalk/BattleTalk_Cloud.BattleTalk_Cloud_C'
        objs[s + '.' + seph_bp + '_C:EndBodySubCollisionSetting_GEN_VARIABLE'] = c + '.' + cloud_bp + '_C:EndBodySubCollisionSetting_GEN_VARIABLE'
    pkgs = {s: c}
    if voice:
        (vo_dir, vo_name), (ls_dir, ls_name) = voice
        objs['/Game/Sound/Voice/JP/Character/%s/%s.%s' % (vo_dir, vo_name, vo_name)] = '/Game/Sound/Voice/JP/Character/Player/%s.%s' % (CLOUD_VO, CLOUD_VO)
        objs['/Game/LipSync/Lsd/JP/Character/%s/%s.%s' % (ls_dir, ls_name, ls_name)] = '/Game/LipSync/Lsd/JP/Character/Player/%s.%s' % (CLOUD_LSD, CLOUD_LSD)
        for lang in LANGS:
            pkgs['/Game/Sound/Voice/%s/Character/%s/%s' % (lang, vo_dir, vo_name)] = '/Game/Sound/Voice/%s/Character/Player/%s' % (lang, CLOUD_VO)
            pkgs['/Game/LipSync/Lsd/%s/Character/%s/%s' % (lang, ls_dir, ls_name)] = '/Game/LipSync/Lsd/%s/Character/Player/%s' % (lang, CLOUD_LSD)
    return objs, pkgs

SEPH_VOICE = (('Player', 'VO_PC0010_00_Sephiroth'), ('Player', 'LSD_PC0010_00_Sephiroth'))
BOSS_VOICE = (('Enemy', 'VO_EB0021_00_Sephiroth_Standard'), ('Enemy', 'LSD_EB0021_00_Sephiroth_Standard'))

def weapon_maps(masamune):
    s, c = WBP + masamune, WBP + 'WE0000_00_Cloud_BusterSword'
    sword = 'WE0000_00_Cloud_BusterSword'
    effect_old = '/Game/Effect/Character/Weapon/WE1021_00_SephirothIllusion_Masamune/Build/WE1021_00_SephirothIllusion_Masamune_Effect__Pack'
    effect_new = '/Game/Effect/Character/Weapon/WE0000_00_Cloud_BusterSword/Build/WE0000_00_Cloud_BusterSword_Effect__Pack'
    objs = {
        s + '.' + masamune + '_C': c + '.' + sword + '_C',
        s + '.Default__' + masamune + '_C': c + '.Default__' + sword + '_C',
        s + '.Default__' + masamune + '_C:SkeletalMeshComponent0': c + '.Default__' + sword + '_C:SkeletalMeshComponent0',
        s + '.' + masamune + '_C:DefaultSceneRoot_GEN_VARIABLE': c + '.' + sword + '_C:DefaultSceneRoot_GEN_VARIABLE',
        effect_old + '.' + effect_old.rsplit('/', 1)[1]: effect_new + '.' + effect_new.rsplit('/', 1)[1],
    }
    return objs, {s: c, effect_old: effect_new}

# row -> (object map, package map, nulled object paths)
PACKS = {}
for row in ('PC0010_00_Sephiroth_Standard', 'PC0010_00_Sephiroth_Standard_NoBattle', 'PC0010_00_Sephiroth_Standard_Reserve'):
    PACKS[row] = character_maps('PC0010_00_Sephiroth_Standard', 'PC0000_00_Cloud_Standard', True, SEPH_VOICE) + ([],)
PACKS['PC0010_01_Sephiroth_StandardWet'] = character_maps('PC0010_01_Sephiroth_StandardWet', 'PC0000_22_Cloud_StandardWet', False, None) + ([],)
t = 'PC0010_10_Sephiroth_Transform'
PACKS[t] = character_maps(t, 'PC0000_00_Cloud_Standard', False, BOSS_VOICE) + (
    [BP + t + '.' + t + '_C:' + g for g in ('L_Weapon_a_GEN_VARIABLE', 'R_FeatherElbow_Spo_GEN_VARIABLE', 'R_FeatherFinger_a_GEN_VARIABLE')],)
PACKS['PC0010_20_Sephiroth_VRHard'] = character_maps('PC0010_20_Sephiroth_VRHard', 'PC0000_00_Cloud_Standard', False, BOSS_VOICE) + ([],)
for w in ('WE1021_00_SephirothIllusion_Masamune', 'WE1021_01_SephirothIllusion_MasamuneBrood', 'WE1021_02_SephirothIllusion_MasamuneCut',
          'WE1021_10_SephirothIllusion_MasamuneCutScale'):
    PACKS[w] = weapon_maps(w) + ([],)

# Subobjects each target blueprint has (its export names), to check every new import exists.
TARGET_EXPORTS = {}
for bp in ('Player__PC0000_00_Cloud_Standard', 'Player__PC0000_22_Cloud_StandardWet', 'Weapon__WE0000_00_Cloud_BusterSword'):
    z = Zen(open(SRC + 'Game__BluePrint__Character__%s.uasset' % bp, 'rb').read())
    TARGET_EXPORTS[bp.split('__')[1]] = {e['name'] for e in z.exports}

def exists(path):
    h = objhash(path)
    if h in OBJ:
        return True
    pkg, _, rest = path.partition('.')
    short = pkg.rsplit('/', 1)[1]
    if short in TARGET_EXPORTS and rest:
        return rest.split(':')[-1] in TARGET_EXPORTS[short]
    return False

def patch_pack(data, objs, pkgs, nulls):
    z = Zen(data)
    d = bytearray(data)
    table = {imp(old): imp(new) for old, new in objs.items()}
    for old in nulls:
        table[imp(old)] = NULL
    for new in objs.values():
        assert exists(new), ('target object not found', new)
    done = set()
    for i, v in enumerate(z.imports):
        if v in table:
            struct.pack_into('<Q', d, z.imp_off + 8 * i, table[v])
            done.add(v)
    missing = [p for p in list(objs) + nulls if imp(p) not in done]
    pkg_ids = {W.package_id(o): W.package_id(n) for o, n in pkgs.items()}
    for n in pkgs.values():
        assert W.package_id(n) in PKG, ('target package not in the game', n)
    o = z.graph_off
    n = struct.unpack_from('<i', d, o)[0]; o += 4
    entries = []
    swapped = []
    for _ in range(n):
        pid, na = struct.unpack_from('<Qi', d, o)
        if pid in pkg_ids:
            swapped.append(PKG.get(pid, hex(pid)))
        entries.append((pkg_ids.get(pid, pid), bytes(d[o + 8:o + 12 + 8 * na])))
        o += 12 + 8 * na
    assert o == z.graph_off + z.graph_size
    ids = [e[0] for e in entries]
    assert len(set(ids)) == len(ids), 'two imported packages became one'
    entries.sort(key=lambda e: e[0])
    g = bytearray(struct.pack('<i', n))
    for pid, rest in entries:
        g += struct.pack('<Q', pid) + rest
    d[z.graph_off:z.graph_off + z.graph_size] = g
    return bytes(d), len(done), missing, swapped, [e[0] for e in entries]

def fstr(s): return s.encode('utf-16-le') + b'\0\0'

def edit_table(keys, fields, rows):
    fi = {f[0][0]: i for i, f in enumerate(fields)}
    at = {k[0]: i for i, k in enumerate(keys)}
    changed = {}
    def put(row, field, value):
        r = rows[at[row]]
        before = r[fi[field]]
        if before != value:
            r[fi[field]] = value
            changed.setdefault(row, []).append((field, before, value))
    for row in PACKS:
        if row.startswith('PC0010'):
            put(row, 'ContentsModel', ('PC0000_22_Cloud_StandardWet' if row == 'PC0010_01_Sephiroth_StandardWet' else 'PC0000_00_Cloud_Standard', 0))
            if rows[at[row]][fi['ContentSoundVoice_Array']]:
                put(row, 'ContentSoundVoice_Array', [fstr(CLOUD_VO)])
            shared = list(rows[at[row]][fi['SharedCharaSpecList_Array']] or [])
            if ('PC0000_00_Cloud_Standard_Reserve', 0) not in shared:
                put(row, 'SharedCharaSpecList_Array', shared + [('PC0000_00_Cloud_Standard_Reserve', 0)])
            if CLOUD_FIELD_ACTIONS and row in ('PC0010_00_Sephiroth_Standard', 'PC0010_00_Sephiroth_Standard_NoBattle',
                                               'PC0010_00_Sephiroth_Standard_Reserve', 'PC0010_01_Sephiroth_StandardWet'):
                put(row, 'AnimationSetParentFolder', ('PC0000_Cloud', 0))
        else:
            put(row, 'ContentsModel', ('WE0000_00_Cloud_BusterSword', 0))
            put(row, 'ContentsEffect_Array', [fstr('WE0000_00_Cloud_BusterSword_Effect__Pack')])
            put(row, 'ContentsSoundSE_Array', [])
            put(row, 'SharedCharaSpecList_Array', [('WE0000_00_Cloud_BusterSword', 0)])
    return changed

def bundle_count(z):
    size = z.graph_off - z.eb_off
    return (size - 16 * len(z.exports)) // 8

def main():
    out_dir = sys.argv[1]
    chunks = [None]
    entries = []
    for row, (objs, pkgs, nulls) in PACKS.items():
        path = PACK + row
        data = open(SRC + 'Game__DataAsset__Game__CharaSpec__CharaSpec_%s.uasset' % row, 'rb').read()
        new, count, missing, swapped, deps = patch_pack(data, objs, pkgs, nulls)
        assert not missing, (row, 'imports not found', missing)
        z = Zen(new)
        print('%-45s %d imports retargeted, packages swapped: %s' % (row, count, ', '.join(p.rsplit('/', 1)[1] + ('(' + p.split('/')[4] + ')' if '/Voice/' in p or '/Lsd/' in p else '') for p in swapped)))
        chunks.append(dict(id64=W.package_id(path), type=2, data=new, path=path.replace('/Game/', '', 1) + '.uasset'))
        entries.append(dict(id=W.package_id(path), size=len(new), export_count=len(z.exports), export_bundle_count=bundle_count(z), load_order=0, imports=deps))
    # The table.
    data = open('/work/cs/raw/retail_CharaSpec.uasset', 'rb').read()
    z, e, m, d = cp.decode(data)
    keys = [k[0] for k in d.keys]
    rows = [list(r) for r in d.rows]
    assert cp.encode(data, z, e, m, keys, d.fields, [list(r) for r in d.rows]) == data, 'table round trip differs'
    changed = edit_table(keys, d.fields, rows)
    table = cp.encode(data, z, e, m, keys, d.fields, rows)
    z2, e2, m2, d2 = cp.decode(table)
    for k, a, b in zip(keys, rows, d2.rows):
        assert list(b) == a, ('row differs after encode', k)
    for row, ch in changed.items():
        print(row); [print('    %s: %r -> %r' % c) for c in ch]
    tpath = '/Game/DataObject/Resident/CharaSpec'
    tz = Zen(table)
    chunks.append(dict(id64=W.package_id(tpath), type=2, data=table, path='DataObject/Resident/CharaSpec.uasset'))
    entries.append(dict(id=W.package_id(tpath), size=len(table), export_count=len(tz.exports), export_bundle_count=bundle_count(tz), load_order=0, imports=[]))
    cid = W.container_id_from_name(NAME)
    chunks[0] = dict(id64=cid, type=10, data=W.container_header(cid, entries), path=None)
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.join(out_dir, NAME)
    W.write_container(base, NAME, chunks, mount='../../../End/Content/')
    shutil.copy('/work/hang1012/out/FullyPlayableVincentAssets_P.pak', base + '.pak')
    back = Toc(base + '.utoc')
    assert back.container_id == cid and back.entries == len(chunks)
    for i, c in enumerate(chunks):
        assert back.read(i) == c['data'] and back.chunk_id64(i) == c['id64'] and back.chunk_type(i) == c['type']
        if c['path']:
            assert back.files.get(i) == '../../../End/Content/' + c['path'], back.files.get(i)
    for f in sorted(os.listdir(out_dir)):
        p = os.path.join(out_dir, f)
        print('%-36s %9d %s' % (f, os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest()))

if __name__ == '__main__':
    main()
