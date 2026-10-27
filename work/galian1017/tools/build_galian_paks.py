"""VincentGalian_P: the Galian Beast form's container (its own name, so its id clashes with no other mod's pakchunk):
  * the moves build_galian_moves.py built, from the project's packaging (pakchunk55: RebirthSkelCompat/Built/VincentGalian/
    Battle07 and Battle08), each laid out the way the game reads its own animations (align_moves: PKG_Cooked, 16-byte
    exports, alignment shift 4),
  * the beast's player AnimBlueprint (make_galian_abp.py: BluePrint/Animation/Player/PC0011_20_GalianBeast_Standard_Animation),
  * its ten blend spaces (make_galian_blendspaces.py: RebirthSkelCompat/Built/VincentGalian/<set>/B_StrafingWalk01_*, B_Turn01),
every chunk read back and checked (data, id, path, header entry, the game's reading of every animation export).
    build_galian_paks.py <out dir (new)> <pakchunk55 .utoc> [blend spaces dir]"""
import hashlib, json, os, shutil, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(HERE, 'tools'), '/work/iostore', '/work/cs', '/work/swap1012/tools',
                '/work/sephforms/tools', '/work/shooter1016/tools', '/work/vincentfix',
                '/work/weap1012/tools', '/work/evil1013/tools']
from iostore import Toc
from zen import Zen
import iostore_write as W
import hdr
import align_moves as A
import build_dirge_paks as P
import make_galian_abp

NAME = 'VincentGalian_P'
MOUNT = P.MOUNT
BUILT = 'RebirthSkelCompat/Built/VincentGalian/'
PLAN = os.path.join(HERE, 'plan', 'galian_moves.json')
STUB = '/work/gunshop1017/out1/FullyPlayableVincentAssets_P.pak'   # (an IoStore container's .pak: its mount point only)


def write(out, chunks, entries, animations):
    cid = W.container_id_from_name(NAME)
    allc = [dict(id64=cid, type=10, data=W.container_header(cid, entries), path=None)] + chunks
    base = os.path.join(out, NAME)
    W.write_container(base, NAME, allc, mount=MOUNT)
    shutil.copy(STUB, base + '.pak')
    back = Toc(base + '.utoc')
    assert back.entries == len(allc)
    cid2, ents = hdr.parse_header(back.read(0))
    assert cid2 == cid and len(ents) == len(entries)
    by = {e['id']: e for e in entries}
    for i in range(1, back.entries):
        c = allc[i]
        data = back.read(i)
        assert data == c['data'] and back.chunk_id64(i) == c['id64'] and back.chunk_type(i) == c['type'], c['path']
        assert back.files.get(i) == (MOUNT + c['path'] if c['path'] else None), (back.files.get(i), c['path'])
        if c['type'] == 2:
            e, b = by[c['id64']], ents[c['id64']]
            assert (b['size'], b['export_count'], b['export_bundle_count'], b['load_order'], list(b['imports'])) == \
                   (e['size'], e['export_count'], e['export_bundle_count'], e['load_order'], e['imports']), c['path']
            if c['path'] in animations:
                assert b['size'] >> 60 == A.SHIFT and P.verify(data, c['path']) >= 1, c['path']
    files = {}
    for ext in ('utoc', 'ucas', 'pak'):
        p = base + '.' + ext
        files[ext] = (os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest())
    return cid, files


def main(out, chunk55, bs_dir=os.path.join(HERE, 'bs1')):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    plan = json.load(open(PLAN))
    built = {'%s%s/%s.uasset' % (BUILT, m['set'], m['name']) for m in plan['moves'] if m['build']}
    report = []
    # 1. the built moves of pakchunk55
    src, store = P.read(chunk55)
    moves = [c for c in src if c['path'] and c['path'].startswith(BUILT)]
    other = sorted(c['path'] or '(bulk %d)' % c['type'] for c in src if not (c['path'] and c['path'].startswith(BUILT)))
    assert all(c['type'] == 2 for c in moves), 'a built move with bulk data'
    got = {c['path'] for c in moves}
    unplanned = sorted(got - built)
    assert not unplanned, ('pakchunk55 has moves the plan does not', unplanned[:5])
    missing = sorted(built - got)
    chunks = [dict(c) for c in moves]
    entries = [P.entry(c, store[c['id64']]) for c in moves]
    animations = {c['path'] for c in chunks}
    anims, blocks = P.lay_out(chunks, entries)
    assert anims == len(moves)
    report.append('the built moves: %d of the plan\'s %d (%d animations laid out like the game\'s, %d ACL blocks aligned)%s; '
                  'pakchunk55\'s others, not taken: %s' % (len(moves), len(built), anims, blocks,
                                                         ('; NOT in pakchunk55: ' + ', '.join(missing)) if missing else '', ', '.join(other) or 'none'))
    # 2. the AnimBlueprint
    data, entry = make_galian_abp.make()
    rel = make_galian_abp.NEW_PKG[len('/Game/'):] + '.uasset'
    chunks.append(dict(id64=entry['id'], type=2, data=data, path=rel))
    entries.append(entry)
    report.append('the AnimBlueprint %s (%d bytes; class %s)' % (rel, len(data), make_galian_abp.CLASS))
    # 3. the blend spaces
    made = json.load(open(os.path.join(bs_dir, 'blendspaces.json')))
    for b in made:
        d = open(b['file'], 'rb').read()
        z = Zen(d)
        assert z.mapped(z.name_mapped) == b['package'] and b['entry']['size'] == len(d)
        chunks.append(dict(id64=b['entry']['id'], type=2, data=d, path=b['path']))
        entries.append(dict(b['entry']))
    # each blend space's samples are built moves in this container (or the beast's own animations, in the game's)
    have = {W.package_id('/Game/' + c['path'][:-len('.uasset')]) for c in chunks}
    built_ids = {W.package_id('/Game/' + p[:-len('.uasset')]): p for p in built}
    for b in made:
        lost = [built_ids[pid] for pid in b['entry']['imports'] if pid in built_ids and pid not in have]
        assert not lost, (b['package'], 'samples moves the build left out', lost)
    report.append('the blend spaces: ' + ', '.join(b['set'] + '/' + b['name'] for b in made))
    ids = [e['id'] for e in entries]
    assert len(ids) == len(set(ids)), 'a package id twice'
    os.makedirs(out)
    cid, files = write(out, chunks, entries, animations)
    report.append('%s (%016x): %d packages; %s' % (NAME, cid, len(entries), files))
    open(os.path.join(out, 'paks_report.txt'), 'w').write('\n'.join(report) + '\n')
    print('\n'.join(report))


if __name__ == '__main__':
    main(*sys.argv[1:])
