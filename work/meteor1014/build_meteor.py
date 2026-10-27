"""Meteor cast with a raised hand: his normal form's spell cast (PC0010_Sephiroth Battle00 B_MagAttack01_0/_1/_2) plays
under B_AtkLimit03_0 (the Meteor limit and the Meteor ATB move) in every form. That cast's damage notify names no
damage source of its own, so the move's ReplaceDamageSourceID itself is created: BattleDamageSource gets PC0010_Meteor,
the falling meteor (as PC0010_Meteor_01, which the old animation made).
    build_meteor.py <out dir> <json in> <json out>"""
import json, os, shutil, sys, io, contextlib
sys.path[:0] = ['/work/sephatb/tools', '/work/iostore', '/work/cs', '/work/tools',
                '/work/evil1013/tools', '/work/swap1012/tools', '/work/vincentfix',
                '/work/weap1012/tools']
import build_atb as B
from iostore import Toc
import iostore_write as W
from hdr import parse_header

NAME = B.NAME
BASE = '/work/stab1014/out1/' + NAME          # what is installed (Skewer reach, Meteor ATB)
MOUNT = B.MOUNT
KEY = 'B_AtkLimit03_0'
CAST = ['/Game/Motion/Player/PC0010_Sephiroth/Battle00/B_MagAttack01_%d.B_MagAttack01_%d' % (i, i) for i in range(3)]


def quiet(f, *a):
    with contextlib.redirect_stdout(io.StringIO()):
        return f(*a)


def main():
    out_dir, json_in, json_out = sys.argv[1:4]
    base = Toc(BASE + '.utoc')
    head = [i for i in range(base.entries) if base.chunk_type(i) == 10]
    cid, base_entries = parse_header(base.read(head[0]))
    chunks, entries = [None], []
    for i in range(base.entries):
        if base.chunk_type(i) != 2:
            continue
        path = base.files[i].replace(MOUNT, '', 1)
        pid = base.chunk_id64(i)
        e = base_entries[pid]
        chunks.append(dict(id64=pid, type=2, data=base.read(i), path=path))
        entries.append(dict(id=pid, size=e['size'], export_count=e['export_count'], export_bundle_count=e['export_bundle_count'],
                            load_order=e['load_order'], imports=e['imports']))
    paths = [c['path'] for c in chunks[1:]]
    k = paths.index(B.DAMAGE_TABLE) + 1
    dm = quiet(B.Table, chunks[k]['data'])
    assert 'PC0010_Meteor' not in dm.at and 'PC0010_Meteor_01' in dm.at
    dm.add('PC0010_Meteor', list(dm.row('PC0010_Meteor_01')))
    data = dm.encode()
    chunks[k]['data'] = data
    entries[k - 1]['size'] = len(data)
    cid2 = W.container_id_from_name(NAME)
    assert cid2 == cid
    chunks[0] = dict(id64=cid2, type=10, data=W.container_header(cid2, entries), path=None)
    os.makedirs(out_dir, exist_ok=True)
    outb = os.path.join(out_dir, NAME)
    W.write_container(outb, NAME, chunks, mount=MOUNT)
    shutil.copy(BASE + '.pak', outb + '.pak')
    back = Toc(outb + '.utoc')
    for i, c in enumerate(chunks):
        assert back.read(i) == c['data'] and back.chunk_id64(i) == c['id64'] and back.chunk_type(i) == c['type']
    dm0 = quiet(B.Table, base.read([i for i in range(base.entries) if base.files.get(i) == MOUNT + B.DAMAGE_TABLE][0]))
    dm1 = quiet(B.Table, back.read(k))
    assert dm1.keys == dm0.keys + [B.name_tuple('PC0010_Meteor')]
    assert all(dm1.row(n) == dm0.row(n) for n in dm0.at) and dm1.row('PC0010_Meteor') == dm0.row('PC0010_Meteor_01')
    print('BattleDamageSource: PC0010_Meteor (as PC0010_Meteor_01)')

    raw = open(json_in, encoding='utf-8').read()
    j = json.loads(raw)
    s = j['animation_sets'][0]
    changed = 0
    for m in s['moves']:
        if m.get('key') == KEY:
            print('%s %s: %s -> %s' % (m['set'], KEY, m['animation'], CAST))
            m['animation'] = list(CAST)
            changed += 1
    assert changed == 3, changed
    open(json_out, 'w', encoding='utf-8').write(json.dumps(j, indent=1, ensure_ascii=False) + ('\n' if raw.endswith('\n') else ''))


if __name__ == '__main__':
    main()
