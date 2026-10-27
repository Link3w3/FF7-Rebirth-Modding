"""The playable Evil Cloud (Sephiroth's slot: chapter 1's Nibelheim) plays like Cloud, from a motion folder of his own,
in FullyPlayableSephirothDataAssets_P (the container the Evil Cloud boss install put in the game):

  * his own motion folder, PC0000_EvilCloud: a copy of every animation set of Cloud's (71: Battle00, Battle01, Emotion00,
    Facial00, Neutral00, Neutral20, the riding sets Mount*, 23 field-action and 34 level sets), each the game's set byte for
    byte but its names (its package; a level or field-action set's object, which is named after its folder) and its public
    export hash. They play Cloud's own animations; Sephiroth's folder (which the playable Sephiroth in Cloud's slot uses)
    is not touched;
  * his four CharaSpec packs (PC0010_00_Sephiroth_Standard, _NoBattle, _Reserve, PC0010_01_Sephiroth_StandardWet) are now
    Cloud's own packs (PC0000_00_Cloud_Standard, _NoBattle, _Reserve, PC0000_22_Cloud_StandardWet) under their names: his
    AI, battle camera (the limit breaks' cameras), effect pack, sound banks and battle talk, with the Evil Cloud blueprint
    (its class, default object and the subobjects the pack names), the sets of his folder and Cloud's insanity voice
    (VO_PC0000_02_Cloud_Insanity, as before) in the place of Cloud's. Their graphs name the swapped packages (every voice
    language, as the cooker writes them); their header entries are the graphs without the US/DE/FR voices plus the
    package of every object import (the game's convention, as build_swap.py has it);
  * the CharaSpec table: those four rows take his folder (AnimationSetParentFolder: field actions and level sets), the
    sets of Cloud's matching row (AnimationSetList), Cloud's AI, auto SE, SE bank and effect pack; all six Evil Cloud rows
    (the two boss rows too) lose the left-hand weapon socket (OverrideWeaponSocketNames: his AnimBlueprint, Cloud's, puts
    the sword in his right hand in battle and on his back outside it; Create a Character System 3.6.16's
    cutscene_weapon_socket keeps it in his left hand in cutscenes, where Sephiroth's animations hold it there);
  * the BattlePlayerParameter row of Sephiroth's slot (pt_Sephiroth) is the game's pt_Cloud: Cloud's combo, Punisher mode,
    guard, dodge, Braver and Triple Slash; his three limit breaks are copies of the game's (the data pak's PC0000_Limit00x
    play the playable Sephiroth's), all three usable;
  * the BattleAbility table: those copies (PC0000_EvilCloud_Limit001 - 003: Cross-Slash, Ascension, Finishing Touch) and
    Focused Thrust's (PC0000_EvilCloud_AtkBurst02, for the Masamune's ability: the compat file's weapon_abilities), each
    the game's row with a new UniqueId (its damage, camera, name and help are Cloud's).
Every other chunk byte for byte with its header entry: only the changed packages, the three tables, the header and the
new sets are written, after the old .ucas (<out>/<NAME>.ucas.tail is what to append to it).
    build_evilplay.py <out dir (new)> <base .utoc>"""
import copy, hashlib, os, shutil, struct, sys, glob
sys.path[:0] = ['/work/evilboss1016/data']
from common import *
sys.path[:0] = ['/work/iostore', '/work/cs', '/work/weap1012/tools', '/work/evil1013/tools']
from zen import Zen
from iostore import Toc
import iostore_write as W
import zenrename
import gameids
import hdr
import make_bp
import align_moves as A
import build_evilcloud_data as BED

NAME = M.NAME
MOUNT = M.MOUNT
NULL = 0xFFFFFFFFFFFFFFFF
PKG, OBJ = gameids.load()
objhash = gameids.objhash
CLOUD, NEW = 'PC0000_Cloud', 'PC0000_EvilCloud'
SETS_DIR = '/work/evilplay1016/cloudsets'
RETAIL = '/work/seph1012/'
GAME_TABLES = '/work/seph1013/tables/'
PACK = '/Game/DataAsset/Game/CharaSpec/CharaSpec_'
BP = '/Game/BluePrint/Character/Player/'
EVIL = 'PC0000_10_Evil_Cloud'
PACKS = {   # Evil Cloud's row -> Cloud's row whose pack (and table fields) it takes
    'PC0010_00_Sephiroth_Standard': 'PC0000_00_Cloud_Standard',
    'PC0010_00_Sephiroth_Standard_NoBattle': 'PC0000_00_Cloud_Standard_NoBattle',
    'PC0010_00_Sephiroth_Standard_Reserve': 'PC0000_00_Cloud_Standard_Reserve',
    'PC0010_01_Sephiroth_StandardWet': 'PC0000_22_Cloud_StandardWet',
}
BOSS_ROWS = ['PC0010_10_Sephiroth_Transform', 'PC0010_20_Sephiroth_VRHard']
CLOUD_BPS = {'PC0000_00_Cloud_Standard', 'PC0000_22_Cloud_StandardWet'}
LANGS = ('JP', 'US', 'DE', 'FR')
VOICE = ('VO_PC0000_00_Cloud', 'VO_PC0000_02_Cloud_Insanity')
LIPSYNC = ('LSD_PC0000_00_Cloud', 'LSD_PC0000_02_Cloud_Insanity')
# CharaSpec fields the four rows take from Cloud's matching row
FROM_CLOUD = ['AnimationSetList_Array', 'End2AIList_Array', 'ContentsSoundAutoSE_Array', 'ContentsSoundSE_Array', 'ContentsEffect_Array']
SOCKETS = 'OverrideWeaponSocketNames_Array'
CLONES = {   # new BattleAbility row -> the game's row it copies
    'PC0000_EvilCloud_Limit001': 'PC0000_Limit001',     # Cross-Slash
    'PC0000_EvilCloud_Limit002': 'PC0000_Limit002',     # Ascension
    'PC0000_EvilCloud_Limit003': 'PC0000_Limit003',     # Finishing Touch
    'PC0000_EvilCloud_AtkBurst02': 'PC0000_AtkBurst02', # Focused Thrust
}
LIMITS = ['PC0000_EvilCloud_Limit001', 'PC0000_EvilCloud_Limit002', 'PC0000_EvilCloud_Limit003']
PLAYER_ROW, PLAYER_FROM = 'pt_Sephiroth', 'pt_Cloud'
LOCALIZED = ('/Game/Sound/Voice/', '/Game/LipSync/Lsd/')


def imp(path):
    return (2 << 62) | objhash(path)


def name_of(v, known):
    return known.get(v & ~(3 << 62)) if v != NULL else None


def graph_entries(d):
    z = Zen(d)
    o = z.graph_off
    n = struct.unpack_from('<i', d, o)[0]
    o += 4
    out = []
    for _ in range(n):
        pid, na = struct.unpack_from('<Qi', d, o)
        out.append((pid, bytes(d[o + 8:o + 12 + 8 * na])))
        o += 12 + 8 * na
    assert o == z.graph_off + z.graph_size
    return out


def bundle_count(z):
    return (z.graph_off - z.eb_off - 16 * len(z.exports)) // 8


# ---- the sets -------------------------------------------------------------------------------------------------------
def set_copy(data):
    """Cloud's set package -> the same set in Evil Cloud's folder: (package bytes, package name, object path)."""
    z = Zen(data)
    old_pkg = z.names[z.name_mapped & 0x3FFFFFFF]
    assert z.names[z.srcname_mapped & 0x3FFFFFFF] == old_pkg and len(z.exports) == 1, old_pkg
    head, folder, obj = old_pkg.rsplit('/', 2)
    if obj == CLOUD:                                    # /Game/Motion/{Level,FieldAction}/<Set>/PC0000_Cloud
        assert head in ('/Game/Motion/Level', '/Game/Motion/FieldAction') and z.exports[0]['name'] == CLOUD, old_pkg
        new_pkg = '%s/%s/%s' % (head, folder, NEW)
        renames = {old_pkg: new_pkg, CLOUD: NEW}
        assert z.names.count(CLOUD) == 1 and NEW not in z.names
        new_obj = NEW
    else:                                               # /Game/Motion/Player/PC0000_Cloud/<Set>
        assert '%s/%s' % (head, folder) == '/Game/Motion/Player/' + CLOUD and z.exports[0]['name'] == obj, old_pkg
        new_pkg = '/Game/Motion/Player/%s/%s' % (NEW, obj)
        renames = {old_pkg: new_pkg}
        new_obj = obj
    assert z.names.count(old_pkg) == 1 and new_pkg not in z.names
    object_path = '%s.%s' % (new_pkg, new_obj)
    assert z.exports[0]['global_import'] == imp('%s.%s' % (old_pkg, z.exports[0]['name'])), old_pkg
    out = zenrename.rebuild(data, renames, {0: imp(object_path)})
    z2 = Zen(out)
    assert z2.names == [renames.get(n, n) for n in z.names]
    assert z2.names[z2.name_mapped & 0x3FFFFFFF] == new_pkg and z2.exports[0]['name'] == new_obj
    assert z2.exports[0]['global_import'] == imp(object_path)
    assert z2.imports == z.imports and z2.flags == z.flags
    for key in ('serial_offset', 'serial_size', 'outer', 'cls', 'super', 'template', 'oflags', 'fflags'):
        assert z2.exports[0][key] == z.exports[0][key], key
    assert out[z2.header_end:] == data[z.header_end:]
    assert out[z2.graph_off:z2.graph_off + z2.graph_size] == data[z.graph_off:z.graph_off + z.graph_size]
    return out, old_pkg, new_pkg, object_path


# ---- the packs ------------------------------------------------------------------------------------------------------
def bp_exports(path, pkg):
    """A blueprint package's public exports: hash -> object path."""
    z = Zen(open(path, 'rb').read()) if isinstance(path, str) else Zen(path)
    out = {}
    for i, e in enumerate(z.exports):
        if e['global_import'] != NULL:
            out[e['global_import'] & ~(3 << 62)] = make_bp.export_path(z, i, pkg)
    return out


def header_imports(d, known):
    """The packages a pack's header entry lists (build_swap.py): its graph without the US/DE/FR voices and lip syncs, plus
    the package of every object import the graph does not name (BattleTalk)."""
    keep = []
    for pid, _ in graph_entries(d):
        path = known.get(pid, '')
        if path.startswith(LOCALIZED) and path.split('/')[4] != 'JP':
            continue
        keep.append(pid)
    for v in Zen(d).imports:
        if v == NULL or (v >> 62) != 2:
            continue
        path = OBJ.get(v & ~(3 << 62))
        if path:
            pid = W.package_id(path.split('.', 1)[0])
            if pid not in keep:
                keep.append(pid)
    return keep


def make_pack(row, cloud_row, set_paths, evil_objs):
    """Cloud's retail pack `cloud_row` as Evil Cloud's pack `row`."""
    data = open(RETAIL + 'Game__DataAsset__Game__CharaSpec__CharaSpec_%s.uasset' % cloud_row, 'rb').read()
    z = Zen(data)
    old_pkg, new_pkg = PACK + cloud_row, PACK + row
    assert z.names[z.name_mapped & 0x3FFFFFFF] == old_pkg and len(z.exports) == 1
    # every import, named (the game's objects, the subobjects of Cloud's blueprints)
    known = dict(OBJ)
    for bp in CLOUD_BPS:
        known.update(bp_exports(RETAIL + 'Game__BluePrint__Character__Player__%s.uasset' % bp, BP + bp))
    objs, pkgs = {}, {}
    for v in z.imports:
        path = name_of(v, known)
        if not path:
            continue
        if path.startswith(BP):
            bp = path[len(BP):].split('.', 1)[0]
            if bp in CLOUD_BPS:
                new = BP + EVIL + '.' + path.split('.', 1)[1].replace(bp, EVIL)
                assert imp(new) & ~(3 << 62) in evil_objs, ('not in the Evil Cloud blueprint', new)
                objs[path] = new
                pkgs[BP + bp] = BP + EVIL
        elif path.startswith('/Game/Motion/Player/%s/' % CLOUD):
            s = path.split('/')[-1].split('.')[0]
            new = '/Game/Motion/Player/%s/%s.%s' % (NEW, s, s)
            assert new in set_paths, ('no such set of his', new)
            objs[path] = new
            pkgs[path.split('.')[0]] = new.split('.')[0]
        elif path.endswith('.' + VOICE[0]) or path.endswith('.' + LIPSYNC[0]):
            old, to = VOICE if VOICE[0] in path else LIPSYNC
            new = path.replace(old, to)
            assert imp(new) & ~(3 << 62) in OBJ, new
            objs[path] = new
            for lang in LANGS:
                a, b = path.split('.')[0].replace('/JP/', '/%s/' % lang), new.split('.')[0].replace('/JP/', '/%s/' % lang)
                assert W.package_id(b) in PKG, b
                pkgs[a] = b
    table = {imp(o): imp(n) for o, n in objs.items()}
    d = bytearray(data)
    done = 0
    for i, v in enumerate(z.imports):
        if v in table:
            struct.pack_into('<Q', d, z.imp_off + 8 * i, table[v])
            done += 1
    assert done == len(objs), (row, done, len(objs))
    left = [name_of(v, known) for v in Zen(bytes(d)).imports if v != NULL and v not in table.values()]
    stale = [p for p in left if p and ('Cloud_Standard.' in p and p.startswith(BP) or '/PC0000_Cloud/' in p and '/Motion/Player/' in p
                                       or 'PC0000_22_Cloud_StandardWet.' in p or VOICE[0] in p or LIPSYNC[0] in p)]
    assert not stale, (row, stale)
    # the graph
    pid_map = {W.package_id(a): W.package_id(b) for a, b in pkgs.items()}
    g = graph_entries(bytes(d))
    swapped = [pid for pid, _ in g if pid in pid_map]
    assert len(swapped) == len(pid_map), (row, len(swapped), len(pid_map), [p for p in pkgs if W.package_id(p) not in [x for x, _ in g]])
    g = sorted([(pid_map.get(pid, pid), rest) for pid, rest in g], key=lambda x: x[0])
    assert len({pid for pid, _ in g}) == len(g)
    gb = bytearray(struct.pack('<i', len(g)))
    for pid, rest in g:
        gb += struct.pack('<Q', pid) + rest
    assert len(gb) == z.graph_size
    d[z.graph_off:z.graph_off + z.graph_size] = gb
    # its own name
    renames = {old_pkg: new_pkg, 'CharaSpec_' + cloud_row: 'CharaSpec_' + row}
    assert all(z.names.count(n) == 1 for n in renames) and not any(n in z.names for n in renames.values())
    out = zenrename.rebuild(bytes(d), renames, {0: imp(new_pkg + '.CharaSpec_' + row)})
    z2 = Zen(out)
    assert z2.names[z2.name_mapped & 0x3FFFFFFF] == new_pkg and z2.exports[0]['name'] == 'CharaSpec_' + row
    assert out[z2.header_end:] == data[z.header_end:], 'the export data changed'
    return out, objs, pkgs


# ---- the tables -----------------------------------------------------------------------------------------------------
def edit_charaspec(t, game):
    report = []
    for row, cloud_row in PACKS.items():
        r, c = t.row(row), game.row(cloud_row)
        for f in FROM_CLOUD:
            before = t.get(r, f)
            r[t.fi[f]] = list(c[game.fi[f]])
            report.append('%s %s: %r -> %r' % (row, f, before, t.get(r, f)))
        before = t.get(r, 'AnimationSetParentFolder')
        assert before == 'PC0010_Sephiroth', (row, before)
        t.set(r, 'AnimationSetParentFolder', NEW)
        report.append('%s AnimationSetParentFolder: %s -> %s' % (row, before, NEW))
    for row in list(PACKS) + BOSS_ROWS:
        r = t.row(row)
        before = t.get(r, SOCKETS)
        assert before == ['Attach_Weapon_Left01'], (row, before)
        t.set(r, SOCKETS, [])
        report.append('%s %s: %r -> []' % (row, SOCKETS, before))
    return report


def edit_player(t, game):
    r = list(game.row(PLAYER_FROM))
    assert game.get(r, 'LimitAbilityID_Array') == ['PC0000_Limit001', 'PC0000_Limit002', 'PC0000_Limit003']
    t.set(r, 'LimitAbilityID_Array', LIMITS)
    t.set(r, 'LimitAbilityUseableFlag_Array', [None, None, None])
    t.set(r, 'FirstLimitAbilityUseableFlag_Array', [None, None, None])
    before = {f[0][0]: t.get(t.row(PLAYER_ROW), f[0][0]) for f in t.fields}
    t.rows[t.at[PLAYER_ROW]] = r
    after = {f[0][0]: t.get(r, f[0][0]) for f in t.fields}
    return ['%s %s: %r -> %r' % (PLAYER_ROW, f, before[f], after[f]) for f in before if before[f] != after[f]]


def edit_abilities(t, game):
    ids = iter(B.unique_ids(t, len(CLONES), 1016))
    report = []
    for key, src in CLONES.items():
        row = list(game.row(src))
        assert t.get(row, 'ReplaceDamageSourceID') == src, (src, t.get(row, 'ReplaceDamageSourceID'))   # (its damage stays Cloud's)
        t.set(row, 'UniqueId', next(ids))
        t.add(key, row)
        report.append('%s: a copy of the game\'s %s (%s, anims %s, damage %s, camera %s, UniqueId %d)' % (
            key, src, t.get(row, 'Name'), t.get(row, 'AnimationString_Array'), t.get(row, 'ReplaceDamageSourceID'),
            t.get(row, 'CameraSequenceID'), t.get(row, 'UniqueId')))
    return report


def main(out, base_utoc):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    base_ucas = base_utoc[:-len('.utoc')] + '.ucas'
    old = Toc(base_utoc)
    assert [i for i in range(old.entries) if old.chunk_type(i) == 10] == [0]
    for i in range(old.entries):   # the container to build on is the one made (every chunk as its hash says)
        assert hashlib.sha1(old.read(i)).digest() == old.b[old.metas_off + 33 * i:old.metas_off + 33 * i + 20], i
    head = old.read(0)
    cid, store = hdr.parse_header(head)
    assert cid == W.container_id_from_name(NAME)
    order = [old.chunk_id64(i) for i in range(old.entries) if old.chunk_type(i) == 2]
    assert len(order) == len(store) and set(order) == set(store)
    entries = [dict(id=p, size=store[p]['size'], export_count=store[p]['export_count'], export_bundle_count=store[p]['export_bundle_count'],
                    load_order=store[p]['load_order'], imports=list(store[p]['imports'])) for p in order]
    assert W.container_header(cid, entries) == head, 'the header does not write back as it is'
    by_path = {old.files[i][len(MOUNT):]: i for i in old.files}
    entry_of = {e['id']: e for e in entries}
    have = {old.chunk_id64(i) for i in range(old.entries)}
    report = []
    changes, additions = {}, []

    # the sets
    files = sorted(glob.glob(os.path.join(SETS_DIR, '*.uasset')))
    assert len(files) == 71, len(files)
    set_paths = set()
    for f in files:
        data = open(f, 'rb').read()
        new, old_pkg, new_pkg, objpath = set_copy(data)
        rel = new_pkg[len('/Game/'):] + '.uasset'
        assert rel not in by_path, rel
        pid = W.package_id(new_pkg)
        assert pid not in PKG and pid not in have, new_pkg
        graph = zenrename.graph_imports(new)
        assert graph and all(p in PKG for p in graph), new_pkg
        z = Zen(new)
        additions.append(dict(id64=pid, type=2, data=new, path=rel))
        entries.append(dict(id=pid, size=len(new), export_count=len(z.exports), export_bundle_count=bundle_count(z), load_order=0, imports=graph))
        have.add(pid)
        set_paths.add(objpath)
        OBJ[imp(objpath) & ~(3 << 62)] = objpath
        PKG[pid] = new_pkg
    kinds = {}
    for p in set_paths:
        k = p.split('/')[3]
        kinds[k] = kinds.get(k, 0) + 1
    report.append('%d sets of Cloud\'s copied into his folder %s (%s)' % (len(set_paths), NEW, ', '.join('%s %d' % kv for kv in sorted(kinds.items()))))

    # the packs
    bp_rel = 'BluePrint/Character/Player/%s.uasset' % EVIL
    evil_bp = old.read(by_path[bp_rel])
    evil_objs = bp_exports(evil_bp, BP + EVIL)
    for h, p in evil_objs.items():
        OBJ.setdefault(h, p)
    PKG[W.package_id(BP + EVIL)] = BP + EVIL
    for row, cloud_row in PACKS.items():
        rel = 'DataAsset/Game/CharaSpec/CharaSpec_%s.uasset' % row
        i = by_path[rel]
        before = old.read(i)
        zb = Zen(before)
        new, objs, pkgs = make_pack(row, cloud_row, set_paths, evil_objs)
        z = Zen(new)
        assert z.exports[0]['global_import'] == zb.exports[0]['global_import'], row
        assert old.chunk_id64(i) == W.package_id(PACK + row)
        # the header entry the old pack had follows the same rule (a check of the rule)
        e = entry_of[old.chunk_id64(i)]
        assert sorted(header_imports(before, PKG)) == sorted(e['imports']), (row, 'the rule does not give the old entry')
        e.update(size=len(new), export_count=len(z.exports), export_bundle_count=bundle_count(z), imports=header_imports(new, PKG))
        assert all(p in PKG for p in e['imports']), (row, [hex(p) for p in e['imports'] if p not in PKG])
        changes[i] = new
        report.append('%s: Cloud\'s pack %s with %d imports swapped (%s); %d packages in its header entry' % (
            row, cloud_row, len(objs), ', '.join(sorted({o.rsplit('/', 1)[1].split('.')[0] for o in objs})), len(e['imports'])))

    # the tables
    game = {k: quiet(B.Table, open(GAME_TABLES + 'game_%s.uasset' % k, 'rb').read()) for k in ('BattleAbility', 'BattlePlayerParameter')}
    game['CharaSpec'] = quiet(B.Table, open('/work/cs/raw/retail_CharaSpec.uasset', 'rb').read())
    edits = (('CharaSpec', B.CHARASPEC_TABLE, edit_charaspec), ('BattlePlayerParameter', B.PLAYER_TABLE, edit_player),
             ('BattleAbility', 'DataObject/Resident/BattleAbility.uasset', edit_abilities))
    tables = {}
    for name, rel, edit in edits:
        i = by_path[rel]
        t = quiet(B.Table, old.read(i))
        assert [f[0][0] for f in t.fields] == [f[0][0] for f in game[name].fields], (name, 'the fields differ from the game\'s')
        assert [f[1] for f in t.fields] == [f[1] for f in game[name].fields], name
        before = {k: copy.deepcopy(t.rows[t.at[k]]) for k in t.at}
        lines = edit(t, game[name])
        data = quiet(t.encode)
        t2 = quiet(B.Table, data)
        assert t2.keys == t.keys
        for k in t.at:
            assert t2.rows[t2.at[k]] == t.rows[t.at[k]], k
        changed = sorted(k for k in t.at if k not in before or before[k] != t.rows[t.at[k]])
        e = entry_of[old.chunk_id64(i)]
        if e['size']:
            e['size'] = (e['size'] & (3 << 62)) | len(data)
        changes[i] = data
        tables[name] = (rel, t, changed)
        report.append('%s: %d rows changed or added (%s)' % (name, len(changed), ', '.join(changed)))
        report.extend('    ' + l for l in lines)

    # the container
    cid_head = W.container_header(cid, entries)
    changes[0] = cid_head
    os.makedirs(out)
    path = os.path.join(out, NAME)
    BED.append_container(old, base_ucas, changes, additions, path + '.utoc', path + '.ucas.tail')
    with open(path + '.ucas', 'wb') as f:
        with open(base_ucas, 'rb') as g:
            shutil.copyfileobj(g, f, 1 << 24)
        f.write(open(path + '.ucas.tail', 'rb').read())
    shutil.copy(base_utoc[:-len('.utoc')] + '.pak', path + '.pak')

    # read back: every chunk, its id, file and hash; the header's entries
    new = Toc(path + '.utoc')
    assert new.entries == old.entries + len(additions)
    assert new.chunk_ids[:old.entries] == old.chunk_ids
    for i in range(old.entries):
        assert new.files.get(i) == old.files.get(i), i
    aligned = 0
    for i in range(new.entries):
        data = new.read(i)
        if i < old.entries:
            assert data == (changes[i] if i in changes else old.read(i)), i
            if i not in changes and old.files.get(i, '').startswith(MOUNT + 'RebirthSkelCompat/Built/'):
                aligned += A.verify(data, old.files[i][len(MOUNT):])
        else:
            c = additions[i - old.entries]
            assert data == c['data'] and new.chunk_id64(i) == c['id64'] and new.chunk_type(i) == c['type'] and new.files.get(i) == MOUNT + c['path']
        assert hashlib.sha1(data).digest() == new.b[new.metas_off + 33 * i:new.metas_off + 33 * i + 20], i
    cid2, store2 = hdr.parse_header(new.read(0))
    assert cid2 == cid and len(store2) == len(store) + len(additions)
    for e in entries:
        z = store2[e['id']]
        for key in ('size', 'export_count', 'export_bundle_count', 'load_order', 'imports'):
            assert z[key] == e[key], (hex(e['id']), key)
    untouched = [p for p in order if p not in {old.chunk_id64(i) for i in changes}]
    for p in untouched:
        for key in ('size', 'export_count', 'export_bundle_count', 'load_order', 'imports'):
            assert store[p][key] == store2[p][key], (hex(p), key)
    chunks2, _ = M.read(path + '.utoc')
    byp = {c['path']: c for c in chunks2 if c['path']}
    for name, (rel, t, changed) in tables.items():
        t3 = quiet(B.Table, byp[rel]['data'])
        assert t3.keys == t.keys
        for k in t.at:
            assert t3.rows[t3.at[k]] == t.rows[t.at[k]], (name, k)
    report.append('%s: %d chunks (%d before: %d packs, 3 tables and the header changed; %d sets added); %d ACL blocks of the built moves '
                  '16-aligned; read back as written; the .ucas is the old one plus %d bytes' % (
                      NAME, new.entries, old.entries, len(PACKS), len(additions), aligned, os.path.getsize(path + '.ucas.tail')))
    open(os.path.join(out, 'changes.txt'), 'w').write('\n'.join(report) + '\n')
    print('\n'.join(report))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
