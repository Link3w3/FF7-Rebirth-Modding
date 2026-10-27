"""One IoStore container for converted effects, built with the packer the working Sora material pack uses
(custmat/taken/pack.py): the KH3 textures converted from the End editor's cooked copies with zentex (streamed mips'
bulk data headers fixed for IoStore: absolute offsets + BULKDATA_NoOffsetFixUp; retoc's conversion left them as the
legacy loader wants them, which crashes the game's zen loader in FUntypedBulkData::Serialize), and the converted
Niagara systems. Load order: textures before the effects that import them. Read back chunk by chunk.

    build_pack2.py <out dir> <container name> <textures dir: cooked .uasset (+ .ubulk)> <run dir | zen source>...

A zen source, `zen:<container .utoc>:<path substring>`, adds that container's packages whose path has the substring as
they are (the KH3 effect meshes: cooked by the End editor, converted by retoc; inline render data, no bulk chunks)."""
import glob, hashlib, json, os, sys
sys.path[:0] = ['/work/custmat/taken', '/work/custmat', '/work/fx1018/editor/Python',
                '/work/cs', '/work/iostore']
import pack
import zentex
from rebirth_fx import iostore_write as W

TEXTURE_ORDER = 1001
EFFECT_ORDER = 1002


def main(out_dir, name, tex_dir, *runs):
    items = []
    names = {}
    for ua_path in sorted(glob.glob(os.path.join(tex_dir, '*.uasset'))):
        ub_path = ua_path[:-7] + '.ubulk'
        ua = open(ua_path, 'rb').read()
        ub = open(ub_path, 'rb').read() if os.path.isfile(ub_path) else b''
        pkg, bulk, rep = zentex.convert(ua, ub)
        mips = rep.get('mips', [])
        items.append(dict(data=pkg, bulk=bulk if bulk else None, like=None, load_order=TEXTURE_ORDER))
        names[rep['package']] = ('texture', len(pkg), len(bulk), mips)
    for run in runs:
        if run.startswith('zen:'):
            utoc, sub = run[4:].rsplit(':', 1)
            sys.path.insert(0, '/work/soradata')
            import build_sora_assets as B
            chunks, store = B.read(utoc)
            for c in chunks:
                if c['type'] == 2 and sub in c['path']:
                    assert not any(x['type'] != 2 and x['id64'] == c['id64'] for x in chunks), c['path'] + ': bulk chunks'
                    items.append(dict(data=c['data'], bulk=None, like=None, load_order=TEXTURE_ORDER))
                    names[pack.package_name(c['data'])] = ('mesh', len(c['data']), 0, None)
            continue
        rep = json.load(open(os.path.join(run, 'report.json')))
        package = rep['package']
        zen = open(os.path.join(run, package.rsplit('/', 1)[1] + '.zen'), 'rb').read()
        assert pack.package_name(zen) == package, (pack.package_name(zen), package)
        items.append(dict(data=zen, bulk=None, like=None, load_order=rep.get('load_order', EFFECT_ORDER)))
        names[package] = ('effect', len(zen), 0, None)
    ours = {W.package_id(pack.package_name(it['data'])) for it in items}
    paths, entries = pack.build(items, out_dir, name)
    retail = pack.retail_entries()
    for e in entries:
        missing = [hex(i) for i in e['imports'] if i not in ours and i not in retail]
        if missing:
            # retail containers whose header the packer has no copy of (pakchunk3optional...): look the chunk up
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import build_pack
            still = [m for m in missing if not build_pack.in_retail_tocs(int(m, 16))]
            assert not still, (e['name'], still)
    back = pack.read_back(paths[0])
    for it in items:
        pid = W.package_id(pack.package_name(it['data']))
        assert back.get((pid, 2)) == it['data'], pack.package_name(it['data'])
        if it['bulk'] is not None:
            assert back.get((pid, 3)) == it['bulk'], pack.package_name(it['data'])
    for e in entries:
        kind, size, bulk, mips = names[e['name']]
        print('%-58s %-7s %7d bytes%s, load order %d, %d imported packages' % (
            e['name'], kind, size, (' + %d bulk' % bulk) if bulk else '', e['load_order'], len(e['imports'])))
    for p in paths:
        print('%-24s %8d %s' % (os.path.basename(p), os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest()))
    return paths, entries


if __name__ == '__main__':
    main(*sys.argv[1:])
