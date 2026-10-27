"""Sephiroth's cutscene line "Alone at last. Shall we?" (EV_FOREE_8630, C3510_MAIN_3400_0400_00_sep) loaded with him in Cloud's
slot, for BIZARRO's entrance: in each Cloud-slot CharaSpec pack of FullyPlayableSephirothDataAssets_P (EndAssetDataAsset,
tagged properties) the line's voice is
  * imported (the JP path, in one of the cooker's free import slots: the game's own packs import their voices by the JP
    path and the game loads the voice language's),
  * one more entry of AssetDataList[0].AssetUserData (the pack's hard references, which the game keeps loaded with the
    character),
  * its package in the pack's entry of the container header (the packages loaded with it: the JP one, which the game's
    loader turns into the voice language's when it mounts the containers, as for the game's own packs),
  * its package in every voice language (JP, US, DE, FR) in the pack's graph, one arc each from the voice's export bundle,
    as the cooker writes the game's packs: the loader finds a graph entry by the id of the package it loads (the voice
    language's), so the pack's export waits for the voice and its reference is there, not null. The pack's own voice and
    lip sync (Sephiroth's VO_PC0010_00_Sephiroth, LSD_PC0010_00_Sephiroth) had their JP entry only (their four arcs on it):
    they get theirs in every language the same way.
Every other chunk of the container byte for byte, with its header entry.
    add_pack_voice.py <out dir (new)> <FullyPlayableSephirothDataAssets_P.utoc>"""
import os, shutil, struct, sys
sys.path[:0] = ['/work/neutral20/tools', '/work/safer1016/tools', '/work/iostore', '/work/cs',
                '/work/swap1012/tools', '/work/sephforms/tools', '/work/vincentfix',
                '/work/weap1012/tools', '/work/evil1013/tools', '/work/hang1012/tools']
import drop_pack_asset as D
import merge_fullyplayable as M
from iostore import Toc
from zen import Zen
import iostore_write as W
import hdr
import gameids
import align_moves as A

NAME = M.NAME
MOUNT = M.MOUNT
NULL = 0xFFFFFFFFFFFFFFFF
VOICE_PKG = '/Game/Sound/Voice/JP/Cut/8800-FOREE/EV_FOREE_8630/C3510_MAIN_3400_0400_00_sep'
VOICE = VOICE_PKG + '.C3510_MAIN_3400_0400_00_sep'
ROWS = ['PC0000_00_Cloud_Standard', 'PC0000_04_Cloud_ZackCostume', 'PC0000_08_Cloud_SoldierNoHelmet', 'PC0000_09_Cloud_CostaClothing',
        'PC0000_10_Cloud_CostaClothing2', 'PC0000_12_Cloud_ZackCostumeDirty', 'PC0000_18_Cloud_ZackCostumeAge21',
        'PC0000_19_Cloud_ZackCostumeDirtyAge21', 'PC0000_23_Cloud_ZackCostumeWet']
SUMMARY = ['nm_off', 'nm_size', 'nh_off', 'nh_size', 'imp_off', 'exp_off', 'eb_off', 'graph_off', 'graph_size', 'pad']
LANGUAGES = ['JP', 'US', 'DE', 'FR']           # the game's voice languages (its packs' graphs list all four)
LOCALIZED = ('/Game/Sound/Voice/JP/', '/Game/LipSync/Lsd/JP/')
ARC = struct.pack('<iii', 1, 0, 0)             # one arc: from the package's export bundle 0 to the pack's (the game's packs)
_PKG = None


def game_packages():
    global _PKG
    if _PKG is None:
        _PKG = gameids.load()[0]
    return _PKG


def variants(jp_package):
    """The package ids of a JP voice / lip sync package in every voice language (each one in the game)."""
    out = []
    for lang in LANGUAGES:
        path = jp_package.replace('/JP/', '/%s/' % lang, 1)
        pid = W.package_id(path)
        assert pid in game_packages(), path + ' is not in the game'
        out.append(pid)
    return out


def localized_graph(g):
    """The graph with each JP voice / lip sync package as the game's packs have it: an entry for every language."""
    PKG = game_packages()
    out, seen, fixed = [], set(), []
    for pid, raw in g:
        path = PKG.get(pid, '')
        lang = next((L for L in LANGUAGES if path.startswith(LOCALIZED[0].replace('/JP/', '/%s/' % L)) or
                     path.startswith(LOCALIZED[1].replace('/JP/', '/%s/' % L))), None)
        if lang is None:
            assert pid not in seen
            out.append((pid, raw)); seen.add(pid)
            continue
        jp = path.replace('/%s/' % lang, '/JP/', 1)
        for q in variants(jp):
            if q not in seen:
                out.append((q, struct.pack('<Q', q) + ARC)); seen.add(q)
        fixed.append(jp.rsplit('/', 1)[1])
    return out, fixed


def imp(path):
    return (2 << 62) | (gameids.objhash(path) & ~(3 << 62))


def one(tags, name):
    hits = [t for t in tags if t.name == name]
    assert len(hits) == 1, (name, len(hits))
    return hits[0]


def user_data(z, e):
    """AssetDataList's tags (the list, its inner struct tag, the first element's AssetUserData) and the references in it."""
    r = D.tagged.Reader(z, bytes(e))
    top = D.tags(r, len(e))
    adl = one(top, 'AssetDataList')
    assert adl.type == 'ArrayProperty' and adl.inner == 'StructProperty'
    r.p = adl.value_at
    count = r.i32()
    assert count >= 1
    inner = D.Tag(r)
    assert inner.type == 'StructProperty' and inner.struct == 'EndAssetData', (inner.type, inner.struct)
    aud = one(D.tags(r, adl.end), 'AssetUserData')
    assert aud.type == 'ArrayProperty' and aud.inner == 'ObjectProperty'
    n = struct.unpack_from('<i', e, aud.value_at)[0]
    assert aud.size == 4 + 4 * n
    refs = list(struct.unpack_from('<%di' % n, e, aud.value_at + 4))
    return top, adl, inner, aud, refs


def add_voice(data):
    z = Zen(data)
    assert len(z.exports) == 1
    want = imp(VOICE)
    assert want not in z.imports, 'the pack imports the line already'
    free = [k for k, v in enumerate(z.imports) if v == NULL]
    assert free, 'no free import slot'
    slot = free[0]
    ref = -(slot + 1)
    # export: one more reference in AssetDataList[0].AssetUserData (the array's count and the sizes of its tag, of the
    # element struct's inner tag and of AssetDataList's tag; all of them before the new reference)
    e = bytearray(z.export_data(0))
    assert len(e) == z.exports[0]['serial_size']
    top, adl, inner, aud, refs = user_data(z, e)
    at = aud.value_at + 4 + 4 * len(refs)
    assert adl.size_at < inner.size_at < aud.size_at < at
    e[at:at] = struct.pack('<i', ref)
    struct.pack_into('<i', e, aud.value_at, len(refs) + 1)
    struct.pack_into('<i', e, aud.size_at, aud.size + 4)
    struct.pack_into('<i', e, inner.size_at, inner.size + 4)
    struct.pack_into('<i', e, adl.size_at, adl.size + 4)
    # header: the import, the graph (the last part of the header) with the voice's package, the export's size
    pid = W.package_id(VOICE_PKG)
    g = D.graph_entries(data, z)
    assert pid not in [p for p, _ in g]
    g_new, fixed = localized_graph(g + [(pid, struct.pack('<Q', pid) + ARC)])
    gb = struct.pack('<i', len(g_new)) + b''.join(b for _, b in g_new)
    assert z.graph_off + z.graph_size == z.header_end
    vals = list(struct.unpack_from('<10i', data, 24))
    assert vals[SUMMARY.index('graph_off')] == z.graph_off and vals[SUMMARY.index('graph_size')] == z.graph_size
    d = bytearray(data[:z.header_end])
    struct.pack_into('<Q', d, z.imp_off + 8 * slot, want)
    d[z.graph_off:z.graph_off + z.graph_size] = gb
    struct.pack_into('<i', d, 24 + 4 * SUMMARY.index('graph_size'), len(gb))
    struct.pack_into('<Q', d, z.exp_off + 8, len(e))
    out = bytes(d) + bytes(e)
    # checks: the package reads back with the one new import, reference and graph entry, everything else as it was
    z2 = Zen(out)
    imports = list(z.imports); imports[slot] = want
    assert z2.imports == imports and len(z2.exports) == 1 and z2.header_end == z.header_end + len(gb) - z.graph_size
    assert z2.names == z.names and z2.exports[0]['serial_offset'] == z.exports[0]['serial_offset']
    e2 = bytes(z2.export_data(0))
    assert len(e2) == len(e) == len(z.export_data(0)) + 4
    top2, adl2, inner2, aud2, refs2 = user_data(z2, e2)
    assert refs2 == refs + [ref] and z2.imports[-refs2[-1] - 1] == want
    old = bytes(z.export_data(0))
    o_at = aud.value_at + 4 + 4 * len(refs)
    assert e2[o_at + 4:] == old[o_at:] and old[-4:] == b'\0\0\0\0'          # AssetClassList and the rest as they were
    p_old = D.tagged.export_props(z, 0)
    p_new = D.tagged.export_props(z2, 0)
    assert p_old['AssetClassList'] == p_new['AssetClassList']
    assert [x for x in p_new['AssetDataList'][0]['AssetUserData']] == [x for x in p_old['AssetDataList'][0]['AssetUserData']] + [('obj', ref)]
    g2 = D.graph_entries(out, z2)
    assert g2 == g_new
    # every other entry as it was; each voice and lip sync package in every language, with one arc
    PKG = game_packages()
    plain = [(p, b) for p, b in g if not any(PKG.get(p, '').startswith(x.replace('/JP/', '/%s/' % L)) for x in LOCALIZED for L in LANGUAGES)]
    assert [x for x in g2 if x in plain] == plain
    for jp in [VOICE_PKG] + ['/Game/Sound/Voice/JP/Character/Player/VO_PC0010_00_Sephiroth', '/Game/LipSync/Lsd/JP/Character/Player/LSD_PC0010_00_Sephiroth']:
        for q in variants(jp):
            assert [b[8:] for p, b in g2 if p == q] == [ARC], (jp, '%016x' % q)
    return out, pid, slot, len(refs) + 1, g2, fixed


def main(out, base_utoc):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    chunks, store = M.read(base_utoc)
    paths = [c['path'] for c in chunks]
    entries = []
    for c in chunks:
        if c['type'] == 2:
            se = store[c['id64']]
            entries.append(dict(id=c['id64'], size=se['size'], export_count=se['export_count'], export_bundle_count=se['export_bundle_count'],
                                load_order=se['load_order'], imports=list(se['imports'])))
    by = {e['id']: e for e in entries}
    report = []
    for row in ROWS:
        path = 'DataAsset/Game/CharaSpec/CharaSpec_%s.uasset' % row
        c = chunks[paths.index(path)]
        e = by[c['id64']]
        new, pid, slot, n, graph, fixed = add_voice(c['data'])
        assert pid not in e['imports']
        c['data'] = new
        # the entry's size as the game writes it (0, as the game's own entries) or the package's new size (as the others)
        if e['size']:
            e['size'] = (e['size'] & (3 << 62)) | len(new)
        e['imports'].append(pid)
        # the loader in every voice language: the pack's imports (JP ones redirected to that language's) each with their
        # graph entry (but the battle talk blueprint, which the game's pack has without one)
        ids = [p for p, _ in graph]
        for lang in LANGUAGES:
            for q in e['imports']:
                path = game_packages().get(q, '')
                if path.startswith(LOCALIZED):
                    q = W.package_id(path.replace('/JP/', '/%s/' % lang, 1))
                assert q in ids or 'BattleTalk' in path, (row, lang, path)
        report.append('%s: import %d, %d assets, %d packages loaded with it, graph %d entries (every language of %s)'
                      % (row, slot, n, len(e['imports']), len(graph), ', '.join(fixed)))
    os.makedirs(out)
    cid = W.container_id_from_name(NAME)
    allchunks = [dict(id64=cid, type=10, data=W.container_header(cid, entries), path=None)] + chunks
    base = os.path.join(out, NAME)
    W.write_container(base, NAME, allchunks, mount=MOUNT)
    shutil.copy(base_utoc[:-len('.utoc')] + '.pak', base + '.pak')
    # read back: every chunk as written, every header entry, the moves' ACL blocks still 16-aligned
    back = Toc(base + '.utoc')
    assert back.entries == len(allchunks)
    cid2, ents = hdr.parse_header(back.read(0))
    assert cid2 == cid and len(ents) == len(entries)
    old = Toc(base_utoc)
    old_by = {(old.chunk_id64(i), old.chunk_type(i)): i for i in range(old.entries)}
    changed = aligned = 0
    for i in range(1, back.entries):
        c = allchunks[i]
        data = back.read(i)
        assert data == c['data'] and back.chunk_id64(i) == c['id64'] and back.chunk_type(i) == c['type'], c['path']
        if c['path']:
            assert back.files.get(i) == MOUNT + c['path']
        if data != old.read(old_by[(c['id64'], c['type'])]):
            changed += 1
        if c['type'] == 2:
            e, b = by[c['id64']], ents[c['id64']]
            assert (b['size'], b['export_count'], b['export_bundle_count'], b['load_order'], list(b['imports'])) == \
                   (e['size'], e['export_count'], e['export_bundle_count'], e['load_order'], e['imports']), c['path']
            if c['path'] and c['path'].startswith('RebirthSkelCompat/Built/'):
                aligned += A.verify(data, c['path'])
    assert changed == len(ROWS), changed
    for line in report:
        print(line)
    print('%s: %d chunks, %d changed (the Cloud-slot packs); read back as written; %d ACL blocks of the moves 16-aligned'
          % (NAME, len(allchunks) - 1, changed, aligned))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
