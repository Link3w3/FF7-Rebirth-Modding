"""Combined swap test: Sephiroth in Cloud's place (the user's SephirothOverCloud_P, every file as it is) and Cloud in
Sephiroth's place (the CloudOverSephiroth test packs) in one container, with one CharaSpec table that has both.
Two containers that both carry the CharaSpec table cannot work together: only one table is used.
    build_swap.py <out dir>
KH2Sephiroth_P (Sephiroth's model, from the same zip) stays its own pak; nothing in it overlaps."""
import hashlib, os, shutil, struct, sys
sys.path.insert(0, '/work/seph1012/tools'); sys.path.insert(0, '/work/swap1012/tools')
import build_cos_test as cos
from build_cos_test import W, Zen, Toc, cp, PKG, OBJ
from hdr import parse_header

NAME = 'SephirothCloudSwap_TEST_P'
# Cloud in Sephiroth's place keeps Sephiroth's moveset: Sephiroth's rows keep their own AnimationSetParentFolder
# (field actions), and the compat file lists Sephiroth's motion folder first.
cos.CLOUD_FIELD_ACTIONS = False
WEAPON_SOCKET = 'Attach_Weapon_Left01'   # where Cloud holds the sword in Sephiroth's place (None: Cloud's own default)
SOC = '/work/swap1012/soc_zip/SephirothOverCloud_P.utoc'
RETAIL_TABLE = '/work/cs/raw/retail_CharaSpec.uasset'
MOUNT = '../../../End/Content/'
TABLE = 'DataObject/Resident/CharaSpec.uasset'
NULL = 0xFFFFFFFFFFFFFFFF
MASAMUNE = 'WE1021_00_SephirothIllusion_Masamune'

def text(v):
    if isinstance(v, list): return '[' + ', '.join(text(x) for x in v) + ']'
    if isinstance(v, (bytes, bytearray)): return v[:-2].decode('utf-16-le')
    if isinstance(v, tuple) and len(v) == 2 and isinstance(v[0], str): return v[0]
    return repr(v)

def graph_ids(d):
    z = Zen(d)
    o = z.graph_off; n = struct.unpack_from('<i', d, o)[0]; o += 4; out = []
    for _ in range(n):
        pid, na = struct.unpack_from('<Qi', d, o); out.append(pid); o += 12 + 8 * na
    return out

LOCALIZED = ('/Game/Sound/Voice/', '/Game/LipSync/Lsd/')

def header_imports(d):
    """The packages a store entry lists, as the game's cooker writes them: the graph without the US/DE/FR copies of voice
    and lip sync (the game reaches those from the JP one for the voice language; listing them loads every language at
    once, and the parallel loader then crashes in them), plus the package of every object import (BattleTalk is imported
    without a graph entry). Matches the retail header for every retail CharaSpec pack checked."""
    keep = []
    for pid in graph_ids(d):
        path = PKG.get(pid, '')
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

def entry(pid, d):
    z = Zen(d)
    return dict(id=pid, size=len(d), export_count=len(z.exports), export_bundle_count=cos.bundle_count(z), load_order=0, imports=header_imports(d))

def pack_contents(d):
    """What a CharaSpec pack loads: blueprint, voice, effect packs, SE/AS."""
    names = [OBJ.get(v & ~(3 << 62)) for v in Zen(d).imports if v != NULL]
    names = [n for n in names if n]
    short = lambda n: n.rsplit('.', 1)[1]
    bp = [short(n)[:-2] for n in names if '/BluePrint/Character/' in n and n.endswith('_C') and '.Default__' not in n]
    vo = sorted(short(n) for n in names if '/Sound/Voice/' in n)
    fx = sorted(short(n) for n in names if n.endswith('_Effect__Pack'))
    se = sorted(short(n) for n in names if '/Sound/SE/' in n and short(n).startswith('SE_'))
    return bp, vo, fx, se

def main():
    out_dir = sys.argv[1]
    soc = Toc(SOC)
    heads = [i for i in range(soc.entries) if soc.chunk_type(i) == 10]
    assert len(heads) == 1
    _, soc_entries = parse_header(soc.read(heads[0]))

    # ---- the table: the user's table, with our rows taken from retail (our packs are retail packs) and edited
    ti = [i for i in range(soc.entries) if (soc.files.get(i) or '').endswith(TABLE)]
    assert len(ti) == 1
    soc_table = soc.read(ti[0])
    z, e, m, d = cp.decode(soc_table)
    keys = [k[0] for k in d.keys]
    assert cp.encode(soc_table, z, e, m, keys, d.fields, [list(r) for r in d.rows]) == soc_table, 'table round trip differs'
    rows = [list(r) for r in d.rows]
    names = [f[0][0] for f in d.fields]
    fi = {n: i for i, n in enumerate(names)}
    at = {k[0]: i for i, k in enumerate(keys)}
    rz, re_, rm, rd = cp.decode(open(RETAIL_TABLE, 'rb').read())
    assert [f[0][0] for f in rd.fields] == names
    rat = {k[0][0]: i for i, k in enumerate(rd.keys)}
    for row in cos.PACKS:
        if list(rows[at[row]]) != list(rd.rows[rat[row]]):
            print('our row %s: the user\'s table had changed it; starting from retail (our pack is the retail pack)' % row)
        rows[at[row]] = list(rd.rows[rat[row]])
    changed = cos.edit_table(keys, d.fields, rows)
    def put(row, field, value):
        r = rows[at[row]]
        if r[fi[field]] != value:
            changed.setdefault(row, []).append((field, r[fi[field]], value))
            r[fi[field]] = value
    # Shared specs that now spawn the other weapon: the Buster Sword spec spawns the Masamune here and the other way round.
    for row in cos.PACKS:
        if row.startswith('WE1021'):
            put(row, 'SharedCharaSpecList_Array', [])
    # Cloud in Sephiroth's place plays Sephiroth's moves, which swing the sword with the left hand: the weapon of slot 0
    # (the equipped one, or the Masamune row the boss forms equip) goes to the left-hand socket, the way the game's
    # shield soldiers put their shields there (OverrideWeaponSocketNames lines up with EquipmentCharaSpecList).
    if WEAPON_SOCKET:
        for row in cos.PACKS:
            if row.startswith('PC0010'):
                put(row, 'OverrideWeaponSocketNames_Array', [(WEAPON_SOCKET, 0)])
    for row, ch in changed.items():
        print(row); [print('    %s: %s -> %s' % (f, text(a), text(b))) for f, a, b in ch]

    # ---- every pack in the container against its row
    soc_chunks = []
    for i in range(soc.entries):
        if soc.chunk_type(i) != 2: continue
        path = soc.files[i].replace(MOUNT, '', 1)
        assert soc.chunk_id64(i) == W.package_id('/Game/' + path[:-len('.uasset')]), path
        soc_chunks.append((path, soc.chunk_id64(i), soc.read(i)))
    our_packs = {}
    for row, (objs, pkgs, nulls) in cos.PACKS.items():
        data = open(cos.SRC + 'Game__DataAsset__Game__CharaSpec__CharaSpec_%s.uasset' % row, 'rb').read()
        new, count, missing, swapped, deps = cos.patch_pack(data, objs, pkgs, nulls)
        assert not missing, (row, missing)
        our_packs[row] = new
    packs = {p.rsplit('CharaSpec_', 1)[1][:-7]: dat for p, _, dat in soc_chunks if '/CharaSpec/' in p}
    assert not set(packs) & set(our_packs), set(packs) & set(our_packs)
    packs.update(our_packs)
    fix = {}
    for row, dat in sorted(packs.items()):
        bp, vo, fx, se = pack_contents(dat)
        r = rows[at[row]]
        model = text(r[fi['ContentsModel']])
        problems = []
        if bp != [model]:
            problems.append('spawns %s, row model %s' % (bp, model))
            if len(bp) == 1: fix[row] = bp[0]
        rvo = sorted(text(x) for x in (r[fi['ContentSoundVoice_Array']] or []))
        if vo and rvo != vo: problems.append('voice %s, row %s' % (vo, rvo))
        rfx = sorted(text(x) for x in (r[fi['ContentsEffect_Array']] or []))
        if rfx != fx: problems.append('effects %s, row %s' % (fx, rfx))
        rse = sorted(text(x) for x in (r[fi['ContentsSoundSE_Array']] or []))
        if rse != se: problems.append('SE %s, row %s' % (se, rse))
        print('%-46s %-40s %s' % (row, bp[0] if bp else '-', '; '.join(problems) if problems else 'row agrees'))
    for row, model in fix.items():
        put(row, 'ContentsModel', (model, 0))
        print('fixed %s: ContentsModel -> %s (what its pack spawns)' % (row, model))

    # ---- shared specs must not loop
    shared = {k[0]: [x[0] for x in (rows[i][fi['SharedCharaSpecList_Array']] or [])] for i, k in enumerate(keys)}
    def loop_from(start):
        stack, seen = [(start, [start])], set()
        while stack:
            node, path = stack.pop()
            for nxt in shared.get(node, []):
                if nxt == start: return path + [nxt]
                if nxt not in seen:
                    seen.add(nxt); stack.append((nxt, path + [nxt]))
        return None
    loops = [loop_from(k) for k in shared if shared[k]]
    loops = [l for l in loops if l]
    assert not loops, ('shared spec loops', loops[:5])
    print('shared spec lists: no loops')

    table = cp.encode(soc_table, z, e, m, keys, d.fields, rows)
    z2, e2, m2, d2 = cp.decode(table)
    for k, a, b in zip(keys, rows, d2.rows):
        assert list(b) == a, ('row differs after encode', k)

    # ---- container: the user's files as they are (their header entries), the new table, our packs
    chunks, entries = [None], []
    for path, pid, dat in soc_chunks:
        if path == TABLE:
            dat = table
            ent = entry(pid, dat)
            old = soc_entries[pid]
            assert (ent['export_count'], ent['export_bundle_count']) == (old['export_count'], old['export_bundle_count'])
            ent['imports'] = old['imports']
        else:
            old = soc_entries[pid]
            ent = dict(id=pid, size=old['size'], export_count=old['export_count'], export_bundle_count=old['export_bundle_count'],
                       load_order=old['load_order'], imports=old['imports'])
        chunks.append(dict(id64=pid, type=2, data=dat, path=path))
        entries.append(ent)
    for row, dat in our_packs.items():
        path = 'DataAsset/Game/CharaSpec/CharaSpec_%s.uasset' % row
        pid = W.package_id('/Game/' + path[:-7])
        chunks.append(dict(id64=pid, type=2, data=dat, path=path))
        entries.append(entry(pid, dat))
    cid = W.container_id_from_name(NAME)
    chunks[0] = dict(id64=cid, type=10, data=W.container_header(cid, entries), path=None)
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.join(out_dir, NAME)
    W.write_container(base, NAME, chunks, mount=MOUNT)
    shutil.copy('/work/hang1012/out/FullyPlayableVincentAssets_P.pak', base + '.pak')
    back = Toc(base + '.utoc')
    assert back.container_id == cid and back.entries == len(chunks)
    for i, c in enumerate(chunks):
        assert back.read(i) == c['data'] and back.chunk_id64(i) == c['id64'] and back.chunk_type(i) == c['type']
        if c['path']:
            assert back.files.get(i) == MOUNT + c['path'], back.files.get(i)
    _, ents = parse_header(back.read(0))
    assert set(ents) == {c['id64'] for c in chunks[1:]}
    print(len(chunks) - 1, 'packages:', len(soc_chunks), 'from SephirothOverCloud_P (table merged),', len(our_packs), 'Cloud-over-Sephiroth packs')
    for f in sorted(os.listdir(out_dir)):
        p = os.path.join(out_dir, f)
        print('%-36s %9d %s' % (f, os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest()))

if __name__ == '__main__':
    main()
