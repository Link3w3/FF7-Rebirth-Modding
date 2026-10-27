"""One IoStore container for converted effects: the converted Niagara systems (zen packages from nconvert.py) plus the
container their KH3 textures were cooked into (retoc output). Every import must be a retail package or one of ours.
Read back chunk by chunk.
    build_pack.py <out dir> <container name> <textures .utoc> <run dir>...
each <run dir> holds report.json (package and its store entry) and <package name>.zen."""
import glob, hashlib, json, os, struct, sys
sys.path[:0] = ['/work/soradata', '/work/iostore', '/work/cs',
                '/work/fx1018/editor/Python', '/work/custmat']
import build_sora_assets as B
import build_sora_bps as S
import iostore_write as W
import hdr
from iostore import Toc

MOUNT = '../../../End/Content/'
EXTRA_HEADERS = ['/work/custmat/pakchunk0_container_header.bin',
                 '/work/custmat/pakchunk3_container_header.bin',
                 '/work/custmat/pakchunk4_container_header.bin']


RETAIL_TOCS = '/data/uploads/FINAL FANTASY VII REBIRTH/End/Content/Paks/pakchunk*.utoc'


def in_retail_tocs(pid):
    """the retail container (.utoc) holding package pid's export data, else None (for the containers whose header we
    do not have a copy of, e.g. pakchunk3optional)"""
    cid = struct.pack('<Q', pid) + b'\0\0\0\2'
    for f in sorted(glob.glob(RETAIL_TOCS)):
        if cid in open(f, 'rb').read():
            return os.path.basename(f)
    return None


def retail():
    out = dict(S.retail_entries())
    for p in EXTRA_HEADERS:
        _, ents = hdr.parse_header(open(p, 'rb').read())
        for pid, x in ents.items():
            out.setdefault(pid, (os.path.basename(p), x))
    return out


def main(out_dir, name, tex_utoc, *runs):
    chunks, store = B.read(tex_utoc)
    entries = [B.entry(c, store[c['id64']]) for c in chunks if c['type'] == 2]
    for run in runs:
        rep = json.load(open(os.path.join(run, 'report.json')))
        package = rep['package']
        zen = open(os.path.join(run, package.rsplit('/', 1)[1] + '.zen'), 'rb').read()
        fx = dict(rep['entry'])
        assert fx['id'] == W.package_id(package) and fx['size'] == len(zen), run
        assert fx['id'] not in {e['id'] for e in entries}, package
        chunks.append(dict(id64=fx['id'], type=2, data=zen, path=package[len('/Game/'):] + '.uasset'))
        entries.append(fx)
    ret = retail()
    ours = {e['id'] for e in entries}
    for e in entries:
        for i in e['imports']:
            if i not in ret and i not in ours:
                where = in_retail_tocs(i)
                assert where, (e['id'], hex(i), 'imported package not found')
                ret[i] = (where, None)
    shadow = [hex(e['id']) for e in entries if e['id'] in ret]
    assert not shadow, ('would replace retail packages', shadow)
    B.load_orders(chunks, entries)
    os.makedirs(out_dir, exist_ok=True)
    cid = W.container_id_from_name(name)
    allc = [dict(id64=cid, type=10, data=W.container_header(cid, entries), path=None)] + chunks
    base = os.path.join(out_dir, name)
    W.write_container(base, name, allc, mount=MOUNT)
    open(base + '.pak', 'wb').write(open(tex_utoc[:-5] + '.pak', 'rb').read())
    back = Toc(base + '.utoc')
    _, ents = hdr.parse_header(back.read(0))
    by = {x['id']: x for x in entries}
    assert set(ents) == set(by)
    for i in range(1, back.entries):
        c = allc[i]
        assert back.read(i) == c['data'] and back.chunk_id64(i) == c['id64'], c['path']
        assert back.files.get(i) == MOUNT + c['path'], (back.files.get(i), c['path'])
        if c['type'] == 2:
            b, x = ents[c['id64']], by[c['id64']]
            assert (b['size'], b['load_order'], list(b['imports']), b['export_count']) == \
                   (x['size'], x['load_order'], list(x['imports']), x['export_count']), c['path']
    for c in chunks:
        line = '%-56s type %2d %8d bytes' % (c['path'], c['type'], len(c['data']))
        if c['type'] == 2:
            x = by[c['id64']]
            line += ', load order %d, imports %s' % (x['load_order'], ' '.join(
                ('ours' if i in ours else ret[i][0]) for i in x['imports']))
        print(line)
    for ext in ('utoc', 'ucas', 'pak'):
        p = base + '.' + ext
        print('%-24s %8d %s' % (os.path.basename(p), os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest()))


if __name__ == '__main__':
    main(*sys.argv[1:])
