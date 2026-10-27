"""Evil Cloud's boss fights in FullyPlayableSephirothDataAssets_P (the container build_levelsets.py made, the one installed):
  * his 115 moves (EvilCloudBoss_P: pakchunk52 laid out like the game's by align_only.py) added as they are, every chunk
    byte for byte with its header entry (the moves keep their alignment shift);
  * the boss's feeler attacks read as Cloud's: the boss's BattleDamageSource rows (PC0010_10_*: only the boss's abilities
    use them, the playable Sephiroth's are PC0010_P_*) lose the feeler (the tentacle actor EN9000_22_Feeler_BlackBulletEnd2)
    and get Cloud's effects (his effect pack, which EvilCloudBoss.json puts into the boss's packs): Blade Burst's wave for
    the feeler bullets, Finishing Touch's burst for their bursts, a beam of his for the feeler lasers, Finishing Touch's
    whirlwind for Whisper Whirlwind's, and his sword wave's hit for their hits. The wing's break effect (on a wing bone Evil
    Cloud does not have) is left out. The ground omens, the sword's aura and its break stay (they warn and show the state).
Only the damage table, the container header and the new packages are written: the new .ucas is the old one with their
blocks after it (<out>/<NAME>.ucas.tail is what to append to the old .ucas; <out>/<NAME>.ucas is the whole of it, read back
here chunk by chunk).
    build_evilcloud_data.py <out dir (new)> <base .utoc> <moves .utoc>"""
import hashlib, os, shutil, struct, sys
from common import *
import iostore_write as W
import hdr
import align_moves as A
from iostore import Toc

NAME = M.NAME
MOUNT = M.MOUNT
BLOCK = W.BLOCK
MOVES_PREFIX = 'RebirthSkelCompat/Built/EvilCloudBoss/'
FEELER_ACTOR = 'EN9000_22_Feeler_BlackBulletEnd2'
EFFECTS = {   # the boss's feeler effect -> Cloud's (all in effect category 10: the attacker's own effect packs)
    'FX_PC0010_10_FeelerBullet_Bullet_01': 'FX_PC0000_Burst05_Bullet_01',          # Blade Burst's wave
    'FX_PC0010_10_FeelerBullet_Exp_01': 'FX_PC0000_Limit03_Exp_01',                # Finishing Touch's burst
    'FX_PC0010_10_FeelerLaser_Bullet_01': 'FX_PC0000_ChainChargeMagic_Beam_01',    # a beam of his (a synergy's)
    'FX_PC0010_10_FeelerTornado_Bullet_01': 'FX_PC0000_Limit03_Wind_01',           # Finishing Touch's whirlwind
    'FX_PC0010_10_BreakFeeler_Wing_01': None,                                      # no wing
}
HITS = {'FX_PC0010_10_FeelerBullet_Hit_01': 'FX_PC0000_ChargeAttack_Hit_01'}       # his sword wave's hit
CLOUD_SOURCES = {   # where each of Cloud's effects is used by his own damage sources (checked: the same category)
    'FX_PC0000_Burst05_Bullet_01': ('PC0000_AtkBurst05_02', 'BindEffectResourceName', 'BindEffectResourceCategory'),
    'FX_PC0000_Limit03_Exp_01': ('PC0000_Limit003_08', 'CreateEffectResourceName', 'CreateEffectResourceCategory'),
    'FX_PC0000_ChainChargeMagic_Beam_01': ('PC0000_ChainCharge2_UC_02', 'BindEffectResourceName', 'BindEffectResourceCategory'),
    'FX_PC0000_Limit03_Wind_01': ('PC0000_Limit003_02', 'BindEffectResourceName', 'BindEffectResourceCategory'),
}


def edit_damage(ds):
    """The boss's feeler damage sources made Cloud's (in place). Returns the report lines."""
    for effect, (row, field, cat) in CLOUD_SOURCES.items():
        r = ds.row(row)
        assert ds.get(r, field) == effect and ds.get(r, cat) == 10, (row, ds.get(r, field), ds.get(r, cat))
    r = ds.row('PC0000_NDAtk_1_02')
    assert ds.get(r, 'HitEffectResourceName_Array') == ['FX_PC0000_ChargeAttack_Hit_01'] and ds.get(r, 'HitEffectResourceCategory_Array') == [10]
    report, counts = [], {}
    for key in sorted(ds.at):
        if not key.startswith('PC0010_10_'):
            continue
        r = ds.row(key)
        changes = []
        if ds.get(r, 'CharaSpecID') == FEELER_ACTOR:
            ds.set(r, 'CharaSpecID', None)
            ds.set(r, 'CharaSpecMotionName', None)
            changes.append('no feeler')
            counts['feeler'] = counts.get('feeler', 0) + 1
        for field, cat in (('BindEffectResourceName', 'BindEffectResourceCategory'), ('CreateEffectResourceName', 'CreateEffectResourceCategory')):
            v = ds.get(r, field)
            if v in EFFECTS:
                assert ds.get(r, cat) == 10, (key, field, ds.get(r, cat))
                ds.set(r, field, EFFECTS[v])
                changes.append('%s %s -> %s' % (field[:-len('ResourceName')], v, EFFECTS[v]))
                counts[v] = counts.get(v, 0) + 1
        hits = ds.get(r, 'HitEffectResourceName_Array') or []
        if any(h in HITS for h in hits):
            cats = ds.get(r, 'HitEffectResourceCategory_Array') or []
            assert all(c == 10 for c, h in zip(cats, hits) if h in HITS), (key, hits, cats)
            ds.set(r, 'HitEffectResourceName_Array', [HITS.get(h, h) for h in hits])
            changes.append('hit -> %s' % ', '.join(HITS.get(h, h) for h in hits))
            counts['hit'] = counts.get('hit', 0) + 1
        if changes:
            report.append('%s: %s' % (key, '; '.join(changes)))
    # nothing of the boss's feelers is left in his rows (the omens, the sword's aura and its break stay on purpose)
    for key in ds.at:
        if not key.startswith('PC0010_10_'):
            continue
        r = ds.row(key)
        names = [ds.get(r, f) for f in ('CharaSpecID', 'BindEffectResourceName', 'CreateEffectResourceName')] + list(ds.get(r, 'HitEffectResourceName_Array') or [])
        left = [n for n in names if n and (n == FEELER_ACTOR or n in EFFECTS or n in HITS)]
        assert not left, (key, left)
    return report, counts


def append_container(old, base_ucas, changes, additions, utoc_path, tail_path):
    """The old container with `changes` (chunk index -> new data) and `additions` (new chunks: id64, type, data, path):
    their data in new blocks after the old .ucas, every other chunk's blocks as they are. Writes the new .utoc and the tail
    (the bytes to append to the old .ucas)."""
    b = old.b
    size = os.path.getsize(base_ucas)
    last = old.blocks[-1]
    assert size % 16 == 0 and last[0] + ((last[1] + 15) & ~15) == size, 'the .ucas does not end with its last block'
    assert old.nmethods == 0 and not old.flags & 0x4 and old.flags & 0x8 and old.partcount == 1 and old.blocksz == BLOCK
    blocks = list(old.blocks)
    offlen = list(old.offlen)
    ids = list(old.chunk_ids)
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
        if c['path']:
            files[i] = MOUNT + c['path']
    for i, p in files.items():
        assert p.startswith(MOUNT), p
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


def main(out, base_utoc, moves_utoc):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    base_ucas = base_utoc[:-len('.utoc')] + '.ucas'
    old = Toc(base_utoc)
    heads = [i for i in range(old.entries) if old.chunk_type(i) == 10]
    tables = [i for i in range(old.entries) if old.files.get(i) == MOUNT + DAMAGE]
    assert heads == [0] and len(tables) == 1, (heads, tables)
    ti = tables[0]
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
    # the damage table
    ds = quiet(B.Table, old.read(ti))
    report, counts = edit_damage(ds)
    table = quiet(ds.encode)
    t2 = quiet(B.Table, table)
    assert t2.keys == ds.keys
    e = [x for x in entries if x['id'] == old.chunk_id64(ti)][0]
    if e['size']:
        e['size'] = (e['size'] & (3 << 62)) | len(table)
    # the moves, as they are in their container
    moves, mstore = M.read(moves_utoc)
    have = set(order) | {old.chunk_id64(i) for i in range(old.entries)}
    additions = []
    for c in moves:
        assert c['type'] == 2 and c['path'].startswith(MOVES_PREFIX), c['path']
        assert c['id64'] not in have, ('already in the container', c['path'])
        se = mstore[c['id64']]
        additions.append(c)
        entries.append(dict(id=c['id64'], size=se['size'], export_count=se['export_count'], export_bundle_count=se['export_bundle_count'],
                            load_order=se['load_order'], imports=list(se['imports'])))
    assert len(additions) == len(mstore)
    new_head = W.container_header(cid, entries)
    # the container
    os.makedirs(out)
    path = os.path.join(out, NAME)
    changes = {0: new_head, ti: table}
    append_container(old, base_ucas, changes, additions, path + '.utoc', path + '.ucas.tail')
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
        else:
            c = additions[i - old.entries]
            assert data == c['data'] and new.chunk_id64(i) == c['id64'] and new.chunk_type(i) == c['type'] and new.files.get(i) == MOUNT + c['path']
            aligned += A.verify(data, c['path'])
        assert hashlib.sha1(data).digest() == new.b[new.metas_off + 33 * i:new.metas_off + 33 * i + 20], i
    cid2, store2 = hdr.parse_header(new.read(0))
    assert cid2 == cid and len(store2) == len(store) + len(additions)
    for p in order:
        a, z = store[p], store2[p]
        for key in ('export_count', 'export_bundle_count', 'load_order', 'imports'):
            assert a[key] == z[key], (p, key)
        assert a['size'] == z['size'] or p == old.chunk_id64(ti), p
    for c in additions:
        a, z = mstore[c['id64']], store2[c['id64']]
        for key in ('size', 'export_count', 'export_bundle_count', 'load_order', 'imports'):
            assert a[key] == z[key], (c['path'], key)
    chunks2, _ = M.read(path + '.utoc')
    t3 = quiet(B.Table, [c for c in chunks2 if c['path'] == DAMAGE][0]['data'])
    for key in ds.at:
        assert t3.rows[t3.at[key]] == ds.rows[ds.at[key]], key
    open(os.path.join(out, 'damage_changes.txt'), 'w').write('\n'.join(report) + '\n')
    print('BattleDamageSource: %d of the boss\'s rows changed (%s)' % (len(report), ', '.join('%s x%d' % kv for kv in sorted(counts.items()))))
    print('%s: %d chunks (%d before: the damage table %d -> %d bytes, the header; %d moves added, %d ACL blocks 16-aligned), read back as written;'
          ' the .ucas is the old one plus %d bytes' % (NAME, new.entries, old.entries, len(old.read(ti)), len(table), len(additions), aligned,
                                                      os.path.getsize(path + '.ucas.tail')))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3])
