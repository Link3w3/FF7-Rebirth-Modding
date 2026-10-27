"""A built-moves form's moves in a Fully Playable (Young) Sephiroth data container, built on the INSTALLED container
without its 260 MB .ucas (made from ccanim/forms/tools/build_ccform_data.py and newcloud/tools/build_newcloud_data.py):
  * the installed container's blocks stay as they are; the new and changed chunks go in new blocks after them (the .tail,
    which the installer appends to the installed .ucas, checked by size and MD5);
  * the moves of the moves container (RebirthSkelCompat/Built/SephirothForms/<pack>/<name>, built by run_dnt_form.cmd)
    added (or made again in place when the container has them already), each laid out the way the game reads its own
    animations (align_moves.realign, checked against the game's reader);
  * CharaSpec: Cloud's 9 rows (Sephiroth's in the Fully Playable mods) list the battle pack(s) (Battle*);
  * the container header lists the added packages.
The chunks this has to read (CharaSpec, the header) come from the installed build's own tail (the build before this one
changed them; each checked against the container's hash), or from the full .ucas when it is next to the .utoc.
    build_form_data.py <installed .utoc> <installed build's .tail or -> <moves .utoc> <out dir (new)> <pack> [<pack> ...]"""
import contextlib, hashlib, io, json, os, struct, sys
sys.path[:0] = ['/work/sephatb/tools', '/work/iostore', '/work/cs', '/work/tools',
                '/work/evil1013/tools', '/work/swap1012/tools', '/work/vincentfix',
                '/work/weap1012/tools', '/work/evilboss1016/data', '/work/sephforms/tools']
import build_atb as B
from iostore import Toc
import iostore_write as W
import hdr
import align_moves as A

MOUNT = '../../../End/Content/'
CHARASPEC = 'DataObject/Resident/CharaSpec.uasset'
MOVES = 'RebirthSkelCompat/Built/SephirothForms/'
BLOCK = 0x10000
ROWS = ['PC0000_00_Cloud_Standard', 'PC0000_08_Cloud_SoldierNoHelmet', 'PC0000_09_Cloud_CostaClothing', 'PC0000_10_Cloud_CostaClothing2',
        'PC0000_04_Cloud_ZackCostume', 'PC0000_12_Cloud_ZackCostumeDirty', 'PC0000_18_Cloud_ZackCostumeAge21',
        'PC0000_19_Cloud_ZackCostumeDirtyAge21', 'PC0000_23_Cloud_ZackCostumeWet']


def quiet(f, *a):
    with contextlib.redirect_stdout(io.StringIO()):
        return f(*a)


class Installed:
    def __init__(self, utoc, tail):
        ucas = utoc[:-5] + '.ucas'
        self.full = os.path.isfile(ucas)
        self.t = Toc(utoc, ucas=ucas if self.full else '/nonexistent')
        t = self.t
        last = t.blocks[-1]
        self.size = last[0] + ((last[1] + 15) & ~15)
        if self.full:
            assert os.path.getsize(ucas) == self.size, 'the .ucas next to the .utoc is not its own'
        assert t.nmethods == 0 and not t.flags & 0x4 and t.flags & 0x8 and t.partcount == 1 and t.blocksz == BLOCK
        self.tail = open(tail, 'rb').read() if tail not in (None, '-') else b''
        self.tail_at = self.size - len(self.tail)
        self.by_path = {p[len(MOUNT):]: i for i, p in t.files.items()}

    def sha(self, i):
        return self.t.b[self.t.metas_off + 33 * i:self.t.metas_off + 33 * i + 20]

    def read(self, i):
        t = self.t
        if self.full:
            data = t.read(i)
        else:
            off, ln = t.offlen[i]
            first, last = off // BLOCK, (off + ln - 1) // BLOCK
            out = bytearray()
            for bi in range(first, last + 1):
                pos, cs, us, m = t.blocks[bi]
                assert m == 0 and cs == us, 'compressed block'
                assert pos >= self.tail_at, 'chunk %d (%s) is not in the tail of the installed build' % (i, t.files.get(i))
                out += self.tail[pos - self.tail_at:pos - self.tail_at + cs]
            s = off - first * BLOCK
            data = bytes(out[s:s + ln])
        assert hashlib.sha1(data).digest() == self.sha(i), 'chunk %d is not what the container says' % i
        return data


def moves_from(utoc, packs):
    """The built moves of the moves container in `packs`: (chunk, store entry), each laid out like the game's animations."""
    src = Toc(utoc)
    heads = [i for i in range(src.entries) if src.chunk_type(i) == 10]
    assert len(heads) == 1
    _, store = hdr.parse_header(src.read(heads[0]))
    out, left = [], []
    for i in range(src.entries):
        if src.chunk_type(i) == 10:
            continue
        path = src.files.get(i, '')
        assert path.startswith(MOUNT), path
        rel = path[len(MOUNT):]
        if not rel.startswith(MOVES) or rel[len(MOVES):].split('/', 1)[0] not in packs:
            left.append(rel)
            continue
        assert src.chunk_type(i) == 2, (rel, src.chunk_type(i))
        pid = src.chunk_id64(i)
        se = store[pid]
        data = A.realign(src.read(i))
        A.verify(data, rel)
        out.append((dict(id64=pid, type=2, data=data, path=rel),
                    dict(id=pid, size=len(data) | (A.SHIFT << 60), export_count=se['export_count'], export_bundle_count=se['export_bundle_count'],
                         load_order=se['load_order'], imports=list(se['imports']))))
    return out, left


def append(old, size, changes, additions, utoc_path, tail_path):
    """build_evilcloud_data.append_container, with the installed .ucas's size given (it is not here)."""
    b = old.b
    blocks, offlen, ids = list(old.blocks), list(old.offlen), list(old.chunk_ids)
    metas = bytearray(b[old.metas_off:])
    assert len(metas) == 33 * old.entries
    tail = bytearray()

    def put(data):
        start = len(blocks) * BLOCK
        for k in range(0, len(data), BLOCK):
            piece = data[k:k + BLOCK]
            blocks.append((size + len(tail), len(piece), len(piece), 0))
            tail.extend(piece)
            while len(tail) % 16:
                tail.append(0)
        return start, len(data)
    for i in sorted(changes):
        offlen[i] = put(changes[i])
        metas[33 * i:33 * i + 20] = hashlib.sha1(changes[i]).digest()
    files = dict(old.files)
    for c in additions:
        i = len(ids)
        ids.append(struct.pack('<QHBB', c['id64'], 0, 0, c['type']))
        offlen.append(put(c['data']))
        metas += hashlib.sha1(c['data']).digest() + b'\0' * 12 + bytes([0])
        files[i] = MOUNT + c['path']
    dindex = W.directory_index(MOUNT, [(files[i][len(MOUNT):], i) for i in sorted(files)])
    head = bytearray(b[:old.hdrsize])
    struct.pack_into('<I', head, 24, len(ids))
    struct.pack_into('<I', head, 28, len(blocks))
    struct.pack_into('<I', head, 48, len(dindex))
    toc = bytearray(head)
    for x in ids:
        toc += x
    for off, ln in offlen:
        toc += off.to_bytes(5, 'big') + ln.to_bytes(5, 'big')
    for pos, cs, us, m in blocks:
        toc += pos.to_bytes(5, 'little') + cs.to_bytes(3, 'little') + us.to_bytes(3, 'little') + bytes([m])
    toc += dindex + metas
    open(utoc_path, 'wb').write(toc)
    open(tail_path, 'wb').write(tail)
    return bytes(tail)


def main(utoc, tail, moves_utoc, out, packs):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    name = os.path.basename(utoc)[:-len('.utoc')]
    inst = Installed(utoc, tail)
    old = inst.t
    assert [i for i in range(old.entries) if old.chunk_type(i) == 10] == [0]
    cid, store = hdr.parse_header(inst.read(0))
    assert cid == W.container_id_from_name(name), 'the container is not called ' + name
    order = [old.chunk_id64(i) for i in range(old.entries) if old.chunk_type(i) == 2]
    entries = [dict(id=p, size=store[p]['size'], export_count=store[p]['export_count'], export_bundle_count=store[p]['export_bundle_count'],
                    load_order=store[p]['load_order'], imports=list(store[p]['imports'])) for p in order]
    assert W.container_header(cid, entries) == inst.read(0), 'the header does not write back as it is'
    entry_of = {e['id']: e for e in entries}
    changes, additions, report = {}, [], []
    moves, left = moves_from(moves_utoc, packs)
    assert moves, 'the moves container has no moves of ' + ', '.join(packs)
    replaced, added = [], []
    for chunk, entry in moves:
        i = inst.by_path.get(chunk['path'])
        if i is not None:
            assert old.chunk_id64(i) == chunk['id64'] and old.chunk_type(i) == 2, chunk['path']
            changes[i] = chunk['data']
            e = entry_of[chunk['id64']]
            for key in ('size', 'export_count', 'export_bundle_count', 'load_order', 'imports'):
                e[key] = entry[key]
            replaced.append(chunk['path'])
        else:
            assert chunk['id64'] not in entry_of, ('the package id is taken', chunk['path'])
            additions.append(chunk)
            entries.append(entry)
            added.append(chunk['path'])
    report.append('Moves: %d made again in place, %d added (%s); not taken from the moves container: %s' % (
        len(replaced), len(added), ', '.join(packs), ', '.join(left) or 'nothing'))
    # CharaSpec: Sephiroth's rows (Cloud's) list the battle packs (a field set, e.g. Neutral10, is not listed: the game mod
    # gives it from the pack's own sets when a skin's or form's "sets" ask for it)
    battle_packs = [p for p in packs if p.startswith('Battle')]
    ci = inst.by_path[CHARASPEC]
    cs = quiet(B.Table, inst.read(ci))
    cs0 = {k: list(cs.row(k)) for k in cs.at}
    report.append('CharaSpec:')
    for row_name in ROWS:
        row = cs.row(row_name)
        have = cs.get(row, 'AnimationSetList_Array')
        used = {cs.get(row, f) for f in ('GroundAnimationBattlePackIndex', 'GroundAnimationFieldPackIndex', 'FlyAnimationBattlePackIndex',
                                         'FlyAnimationFieldPackIndex')}
        for pack in battle_packs:
            if pack not in have:
                free = [i for i, v in enumerate(have) if v is None and i not in used]
                if free:
                    have[free[0]] = pack
                else:
                    have.append(pack)
        cs.set(row, 'AnimationSetList_Array', have)
        report.append('  %s: %s' % (row_name, have))
    data = quiet(cs.encode)
    e = entry_of[old.chunk_id64(ci)]
    assert e['size'] >> 60 == 0
    e['size'] = len(data)
    changes[ci] = data
    cs2 = quiet(B.Table, data)
    for k, r in cs0.items():
        if k not in ROWS:
            assert cs2.row(k) == r, k
        else:
            assert all(p in cs2.get(cs2.row(k), 'AnimationSetList_Array') for p in battle_packs), k
    assert set(cs2.at) == set(cs0)
    changes[0] = W.container_header(cid, entries)
    # the container: the installed blocks, then the new
    os.makedirs(out)
    path = os.path.join(out, name)
    tail_new = append(old, inst.size, changes, additions, path + '.utoc', path + '.ucas.tail')
    new = Toc(path + '.utoc', ucas='/nonexistent')
    assert new.container_id == cid and new.entries == old.entries + len(additions)

    def new_read(k):
        off, ln = new.offlen[k]
        first, last = off // BLOCK, (off + ln - 1) // BLOCK
        buf = bytearray()
        for bi in range(first, last + 1):
            pos, csz, usz, m = new.blocks[bi]
            assert pos >= inst.size, (k, 'not in the new tail')
            buf += tail_new[pos - inst.size:pos - inst.size + csz]
        s = off - first * BLOCK
        return bytes(buf[s:s + ln])
    same = 0
    for k in range(new.entries):
        meta = new.b[new.metas_off + 33 * k:new.metas_off + 33 * k + 20]
        if k < old.entries:
            assert new.files.get(k) == old.files.get(k) and new.chunk_id64(k) == old.chunk_id64(k)
            if k in changes:
                d = new_read(k)
                assert d == changes[k] and hashlib.sha1(d).digest() == meta
                if k and old.files.get(k, '').startswith(MOUNT + MOVES):
                    A.verify(d, old.files[k][len(MOUNT):])
            else:
                assert new.offlen[k] == old.offlen[k] and meta == inst.sha(k)
                same += 1
        else:
            c = additions[k - old.entries]
            d = new_read(k)
            assert d == c['data'] and hashlib.sha1(d).digest() == meta and new.chunk_id64(k) == c['id64'] and new.files.get(k) == MOUNT + c['path']
            A.verify(d, c['path'])
    cid2, ents = hdr.parse_header(new_read(0))
    assert cid2 == cid and len(ents) == len(entries)
    for e in entries:
        bb = ents[e['id']]
        for key in ('size', 'export_count', 'export_bundle_count', 'load_order', 'imports'):
            assert bb[key] == e[key], key
    sums = dict(base_size=inst.size, base_utoc_md5=hashlib.md5(old.b).hexdigest(),
                utoc_md5=hashlib.md5(open(path + '.utoc', 'rb').read()).hexdigest(),
                tail_size=len(tail_new), tail_md5=hashlib.md5(tail_new).hexdigest(), ucas_size=inst.size + len(tail_new))
    json.dump(sums, open(os.path.join(out, 'build.json'), 'w'), indent=1)
    report.append('%s: %d chunks (%d before; %d as they were; %d changed: the CharaSpec table, the header%s; %d added); .ucas %d -> %d bytes' % (
        name, new.entries, old.entries, same, len(changes), ' and %d move(s) made again' % len(replaced) if replaced else '', len(additions),
        inst.size, inst.size + len(tail_new)))
    open(os.path.join(out, 'report.txt'), 'w').write('\n'.join(report) + '\n')
    print('\n'.join(report))
    print(json.dumps(sums))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5:])
