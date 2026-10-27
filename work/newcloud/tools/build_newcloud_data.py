"""The new Cloud's rows in the Fully Playable (Young) Sephiroth data container (FPYS keeps the tables both mods change, so
they are changed in it: two containers overriding one package do not mix). The installed container's blocks stay as
they are; the changed chunks go after them (the .tail, appended to the installed .ucas by the installer):
  * CharaSpec: the new Cloud's rows: the game's own rows of Cloud's 6 outfits (each with its _NoBattle and _Reserve) and
    of his 9 weapons, under his names (<row>_CACS...), the outfits' spawning his blueprints and naming his NoBattle and
    Reserve rows; the weapons' spawning the game's own weapons;
  * BattlePlayerParameter: pt_Cloud_CACS, the game's own pt_Cloud (FPYS's pt_Cloud is Sephiroth's: the CHARACTER page
    puts this row's content into pt_Cloud while the new Cloud has the slot);
  * BattleAbility: the game's own rows of the 11 abilities FPYS gives Sephiroth's moves (Cloud's weapon abilities and
    limits) as <ID>_CACS (new UniqueIds), for the same (the page copies them into the rows, their UniqueIds kept);
  * Effect2SoundTable: his packs next to Cloud's in every row that names Cloud's (the effects whose sounds they play).
Everything else in the container is unchanged.
    build_newcloud_data.py <installed .utoc> <the .tail of the installed build> <out dir (new)>"""
import contextlib, hashlib, io, json, os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, '/work/sephatb/tools', '/work/iostore', '/work/cs', '/work/tools',
                '/work/evil1013/tools', '/work/swap1012/tools', '/work/vincentfix',
                '/work/weap1012/tools']
import build_atb as B
from iostore import Toc
import iostore_write as W
import hdr
import make_newcloud as N

MOUNT = '../../../End/Content/'
GX = '/work/owncloud/gx/'
BLOCK = 0x10000
TABLES = {   # table -> (installed version, as extracted and checked against the container's hashes; the game's own)
    'CharaSpec': ('fpys', 'van3'),
    'BattlePlayerParameter': ('fpys', 'van3'),
    'BattleAbility': ('fpys2', 'van3'),
    'Effect2SoundTable': ('fpys', 'van3'),
}
ABILITIES = ['PC0000_AtkBurst02', 'PC0000_AtkBurst04', 'PC0000_AtkBurst05', 'PC0000_AtkBurst06', 'PC0000_AtkBurst07', 'PC0000_AtkBurst08',
             'PC0000_AtkBurst09', 'PC0000_AtkBurst10', 'PC0000_Limit001', 'PC0000_Limit002', 'PC0000_Limit003']
PLAYER_ROW = 'pt_Cloud'


def quiet(f, *a):
    with contextlib.redirect_stdout(io.StringIO()):
        return f(*a)


def table_path(name):
    return 'DataObject/Resident/%s.uasset' % name


def gx(block, name):
    return open(os.path.join(GX, block, 'pkgs', table_path(name).replace('/', '__')), 'rb').read()


class Installed:
    """The installed container: its .utoc, and the chunks this needs (the tables, as extracted; the header, from the tail
    of its build), each checked against the container's own hash."""
    def __init__(self, utoc, tail):
        self.t = Toc(utoc, ucas='/nonexistent')
        t = self.t
        last = t.blocks[-1]
        self.size = last[0] + ((last[1] + 15) & ~15)
        self.tail = open(tail, 'rb').read()
        self.tail_at = self.size - len(self.tail)
        assert t.nmethods == 0 and not t.flags & 0x4 and t.flags & 0x8 and t.partcount == 1 and t.blocksz == BLOCK
        self.by_path = {p[len(MOUNT):]: i for i, p in t.files.items()}

    def sha(self, i):
        return self.t.b[self.t.metas_off + 33 * i:self.t.metas_off + 33 * i + 20]

    def from_tail(self, i):
        t = self.t
        off, ln = t.offlen[i]
        first, last = off // BLOCK, (off + ln - 1) // BLOCK
        out = bytearray()
        for bi in range(first, last + 1):
            pos, cs, us, m = t.blocks[bi]
            assert m == 0 and cs == us and pos >= self.tail_at, ('chunk %d is not in the tail' % i)
            out += self.tail[pos - self.tail_at:pos - self.tail_at + cs]
        s = off - first * BLOCK
        data = bytes(out[s:s + ln])
        assert hashlib.sha1(data).digest() == self.sha(i), 'chunk %d of the tail is not what the container says' % i
        return data

    def table(self, name, block):
        i = self.by_path[table_path(name)]
        data = gx(block, name)
        assert hashlib.sha1(data).digest() == self.sha(i), name + ': the extracted table is not the installed one'
        return i, data


def append(old, size, changes, utoc_path, tail_path):
    """The old container with `changes` (chunk index -> new data) in new blocks after its .ucas (`size` bytes), every other
    chunk's blocks as they are (build_evilcloud_data.append_container, without additions)."""
    b = old.b
    blocks, offlen = list(old.blocks), list(old.offlen)
    metas = bytearray(b[old.metas_off:])
    assert len(metas) == 33 * old.entries
    tail = bytearray()
    for i in sorted(changes):
        data = changes[i]
        start = len(blocks) * BLOCK
        for k in range(0, len(data), BLOCK):
            piece = data[k:k + BLOCK]
            blocks.append((size + len(tail), len(piece), len(piece), 0))
            tail.extend(piece)
            while len(tail) % 16:
                tail.append(0)
        offlen[i] = (start, len(data))
        metas[33 * i:33 * i + 20] = hashlib.sha1(data).digest()
    dindex = W.directory_index(MOUNT, [(old.files[i][len(MOUNT):], i) for i in sorted(old.files)])
    head = bytearray(b[:old.hdrsize])
    struct.pack_into('<I', head, 28, len(blocks))
    struct.pack_into('<I', head, 48, len(dindex))
    toc = bytearray(head)
    for x in old.chunk_ids:
        toc += x
    for off, ln in offlen:
        toc += off.to_bytes(5, 'big') + ln.to_bytes(5, 'big')
    for pos, cs, us, m in blocks:
        toc += pos.to_bytes(5, 'little') + cs.to_bytes(3, 'little') + us.to_bytes(3, 'little') + bytes([m])
    toc += dindex + metas
    open(utoc_path, 'wb').write(toc)
    open(tail_path, 'wb').write(tail)


def charaspec(cs, van, report):
    """His rows: the game's own, his names."""
    if any(N.new_row(o) in cs.at for o in N.OUTFITS):
        raise AssertionError('the installed CharaSpec has his rows already')
    for m in N.OUTFITS:
        for kind in N.KINDS:
            row = m + kind
            vals = list(van.row(row))
            assert van.get(vals, 'ContentsModel') == m, (row, van.get(vals, 'ContentsModel'))
            cs.set(vals, 'ContentsModel', m + N.SUFFIX)
            for field, k in (('NoBattleCharaSpec', '_NoBattle'), ('ReserveCharaSpec', '_Reserve')):
                have = van.get(vals, field)
                if kind:
                    assert have is None, (row, field, have)
                else:
                    assert have == m + k, (row, field, have)
                    cs.set(vals, field, N.new_row(m + k))
            cs.add(N.new_row(row), vals)
            report.append('  %-46s spawns %-36s NoBattle %-48s Reserve %s' % (
                N.new_row(row), cs.get(vals, 'ContentsModel'), cs.get(vals, 'NoBattleCharaSpec'), cs.get(vals, 'ReserveCharaSpec')))
    for w in N.WEAPONS:
        vals = list(van.row(w))
        assert van.get(vals, 'ContentsModel') == w, w
        cs.add(N.new_row(w), vals)
        report.append('  %-46s spawns %s (the game\'s own)' % (N.new_row(w), w))


def player(pp, van, report):
    row = PLAYER_ROW + N.SUFFIX
    assert row not in pp.at
    pp.add(row, list(van.row(PLAYER_ROW)))
    differs = [f[0][0] for f in pp.fields if pp.get(pp.row(PLAYER_ROW), f[0][0]) != van.get(van.row(PLAYER_ROW), f[0][0])]
    report.append('  %s: the game\'s own %s (the installed %s differs in %d field(s): %s)' % (row, PLAYER_ROW, PLAYER_ROW, len(differs),
                                                                                     ', '.join(differs)))


def abilities(ab, van, report):
    ids = iter(B.unique_ids(ab, len(ABILITIES), 1026))
    for key in ABILITIES:
        new = key + N.SUFFIX
        assert new not in ab.at
        vals = list(van.row(key))
        ab.set(vals, 'UniqueId', next(ids))   # (the rest the game's own: the CHARACTER page copies it into the row, its UniqueId kept)
        ab.add(new, vals)
        report.append('  %-24s the game\'s %-18s %-26s anims %s  damage %s' % (new, key, ab.get(vals, 'Name'), ab.get(vals, 'AnimationString_Array'),
                                                                         ab.get(vals, 'ReplaceDamageSourceID')))


def effect_sounds(es, report):
    packs = {}
    for m in N.OUTFITS:
        for kind in N.KINDS:
            for var in N.VARIANTS:
                packs['CharaSpec_' + m + kind + var] = 'CharaSpec_' + N.new_row(m + kind + var)
    for w in N.WEAPONS:
        packs['CharaSpec_' + w] = 'CharaSpec_' + N.new_row(w)
    rows, names = 0, 0
    for k in list(es.at):
        vals = es.row(k)
        have = es.get(vals, 'ResourceLevelName_Array')
        add = [packs[n] for n in have if n in packs and packs[n] not in have]
        if add:
            es.set(vals, 'ResourceLevelName_Array', have + add)
            rows += 1
            names += len(add)
    report.append('  his packs added to %d row(s) (%d name(s))' % (rows, names))


def main(utoc, tail, out):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    os.makedirs(out)
    name = os.path.basename(utoc)[:-len('.utoc')]
    old = Installed(utoc, tail)
    t = old.t
    assert [i for i in range(t.entries) if t.chunk_type(i) == 10] == [0]
    head = old.from_tail(0)
    cid, store = hdr.parse_header(head)
    assert cid == W.container_id_from_name(name) == t.container_id, 'the container is not called ' + name
    order = [t.chunk_id64(i) for i in range(t.entries) if t.chunk_type(i) == 2]
    entries = [dict(id=p, size=store[p]['size'], export_count=store[p]['export_count'], export_bundle_count=store[p]['export_bundle_count'],
                    load_order=store[p]['load_order'], imports=list(store[p]['imports'])) for p in order]
    assert W.container_header(cid, entries) == head, 'the header does not write back as it is'
    entry_of = {e['id']: e for e in entries}
    changes, report = {}, []
    edits = {'CharaSpec': lambda tab, van: charaspec(tab, van, report),
             'BattlePlayerParameter': lambda tab, van: player(tab, van, report),
             'BattleAbility': lambda tab, van: abilities(tab, van, report),
             'Effect2SoundTable': lambda tab, van: effect_sounds(tab, report)}
    for tname, (block, van_block) in TABLES.items():
        i, data = old.table(tname, block)
        tab = quiet(B.Table, data)
        van = quiet(B.Table, gx(van_block, tname))
        assert [f[0] for f in tab.fields] == [f[0] for f in van.fields], tname + ': the installed table has other fields than the game\'s'
        before = {k: list(tab.row(k)) for k in tab.at}
        report.append(tname + ':')
        edits[tname](tab, van)
        new = quiet(tab.encode)
        check = quiet(B.Table, new)
        for k, r in before.items():
            if tname != 'Effect2SoundTable':
                assert check.row(k) == r, (tname, 'row changed', k)
        assert set(check.at) >= set(before)
        report.append('  %d rows -> %d, %d bytes -> %d' % (len(before), len(check.at), len(data), len(new)))
        os.makedirs(os.path.join(out, 'tables'), exist_ok=True)
        open(os.path.join(out, 'tables', tname + '.uasset'), 'wb').write(new)
        e = entry_of[t.chunk_id64(i)]
        if e['size']:   # (some of the container's entries say 0, which the game takes: kept so)
            assert e['size'] >> 60 == 0 and e['size'] == len(data), tname
            e['size'] = len(new)
        changes[i] = new
    changes[0] = W.container_header(cid, entries)

    path = os.path.join(out, name)
    append(t, old.size, changes, path + '.utoc', path + '.ucas.tail')

    # read back: every chunk but the changed ones where it was, the changed ones in the tail as made
    new = Toc(path + '.utoc', ucas='/nonexistent')
    tail_new = open(path + '.ucas.tail', 'rb').read()
    assert new.entries == t.entries and new.container_id == cid and new.files == t.files
    assert new.blocks[:len(t.blocks)] == t.blocks
    for k in range(new.entries):
        assert new.chunk_ids[k] == t.chunk_ids[k]
        sha = new.b[new.metas_off + 33 * k:new.metas_off + 33 * k + 20]
        if k not in changes:
            assert new.offlen[k] == t.offlen[k] and sha == old.sha(k), k
            continue
        off, ln = new.offlen[k]
        first, last = off // BLOCK, (off + ln - 1) // BLOCK
        got = bytearray()
        for bi in range(first, last + 1):
            pos, cs, us, m = new.blocks[bi]
            assert pos >= old.size and m == 0
            got += tail_new[pos - old.size:pos - old.size + cs]
        got = bytes(got[off - first * BLOCK:off - first * BLOCK + ln])
        assert got == changes[k] and hashlib.sha1(got).digest() == sha, k
    cid2, ents = hdr.parse_header(changes[0])
    assert cid2 == cid and len(ents) == len(entries)
    for e in entries:
        assert all(ents[e['id']][f] == e[f] for f in ('size', 'export_count', 'export_bundle_count', 'load_order', 'imports'))
    sums = dict(base_size=old.size, base_utoc_md5=hashlib.md5(t.b).hexdigest(), utoc_md5=hashlib.md5(open(path + '.utoc', 'rb').read()).hexdigest(),
                tail_size=len(tail_new), tail_md5=hashlib.md5(tail_new).hexdigest(), ucas_size=old.size + len(tail_new))
    json.dump(sums, open(os.path.join(out, 'build.json'), 'w'), indent=1)
    report.append('%s: %d chunks, %d changed (%s and the header); .ucas %d -> %d bytes' % (
        name, new.entries, len(changes), ', '.join(TABLES), old.size, old.size + len(tail_new)))
    open(os.path.join(out, 'report.txt'), 'w').write('\n'.join(report) + '\n')
    print('\n'.join(report))
    print(json.dumps(sums, indent=1))


if __name__ == '__main__':
    main(*sys.argv[1:])
