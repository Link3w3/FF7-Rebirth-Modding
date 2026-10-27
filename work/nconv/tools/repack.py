"""A game Niagara package re-encoded under a new package path with the converter's own writers (nio + nzen + image
alignment): a control for in-game tests. If the original plays and this copy does not, the package writing is at
fault; if both play, a converted effect that fails is failing on its contents.
    repack.py <game zen package> <new package path> <out dir>"""
import json, os, struct, sys
sys.path[:0] = ['/work/nconv/tools', '/work/fx1018/editor/Python', '/work/iostore',
                '/work/cs']
import nio, nzen
import nconvert as C
from rebirth_fx import uwrite
from zen import Zen
import scriptobjs

NULL = 0xFFFFFFFFFFFFFFFF


def graph_packages(z):
    """imported package ids listed in a zen package's graph"""
    d = z.d
    p = z.graph_off
    n = struct.unpack_from('<i', d, p)[0]; p += 4
    out = []
    for _ in range(n):
        pid, nb = struct.unpack_from('<Qi', d, p); p += 12
        p += 8 * nb
        out.append(pid)
    return out


def bundle_order(z):
    total = 2 * len(z.exports)
    heads, seen, p = [], 0, z.eb_off
    while seen < total:
        first, count = struct.unpack_from('<II', z.d, p); p += 8
        heads.append((first, count)); seen += count
    ents = [struct.unpack_from('<II', z.d, p + 8 * k) for k in range(total)]
    order = []
    for first, count in heads:
        order += [tuple(x) for x in ents[first:first + count]]
    return order


def main(src, package, out_dir):
    sp, _ = scriptobjs.load()
    z = Zen(open(src, 'rb').read())
    u = nio.usmap()
    names = uwrite.Names([package])
    w = nio.Writer(names, exact=False)
    datas = []
    for i in range(len(z.exports)):
        cls, v, extra, raw = nio.read_export(z, i, sp)
        body = bytearray()
        if extra.get('image') is not None:
            body += w.memory_image(extra['image'])
        body += w.props(cls, v)
        tail = extra['tail']
        if cls == 'NiagaraSystem':
            guid, n = struct.unpack_from('<Ii', tail, 0)
            assert guid == 0
            r = nio.Reader(u, z.names, tail, 8, len(tail))
            structs = [r.props('NiagaraEmitterCompiledData') for _ in range(n)]
            assert r.p == len(tail), 'system tail not fully read'
            body += tail[:8]
            for st in structs:
                body += w.props('NiagaraEmitterCompiledData', st)
        else:
            assert not any(tail), (cls, tail.hex())      # (no names in it)
            body += tail
        datas.append(bytes(body))
    old_pkg_name = z.names[z.name_mapped & 0x3fffffff]
    exports = []
    for i, e in enumerate(z.exports):
        nm = e['name']
        if nm == old_pkg_name.rsplit('/', 1)[-1]:
            nm = package.rsplit('/', 1)[-1]                 # the asset itself takes the new package's name
        exports.append(dict(name=nm, outer=None if e['outer'] == NULL else e['outer'], cls=e['cls'], template=e['template'],
                            public=e['global_import'] != NULL, oflags=e['oflags'], filter=e['fflags'], data=datas[i],
                            path=package + '.' + nm))
    order = bundle_order(z)
    pkgs = graph_packages(z)
    data, entry = nzen.write(package, names, list(z.imports), pkgs, exports, order)
    aligned = C.align_images(data, [e['data'] for e in exports], sp)
    for e, d in zip(exports, aligned):
        e['data'] = d
    data, entry = nzen.write(package, names, list(z.imports), pkgs, exports, order)
    bad = [x for x in C.image_alignment(data, sp) if x[2]]
    assert not bad, bad
    # the copy reads back to the same property trees as the original
    z2 = Zen(data)
    for i in range(len(z.exports)):
        a = nio.read_export(z, i, sp)
        b = nio.read_export(z2, i, sp)
        assert a[0] == b[0]
    os.makedirs(out_dir, exist_ok=True)
    open(os.path.join(out_dir, package.rsplit('/', 1)[1] + '.zen'), 'wb').write(data)
    json.dump({'package': package, 'entry': entry, 'report': {'repacked_from': src}},
              open(os.path.join(out_dir, 'report.json'), 'w'), indent=1)
    print(package, len(data), 'bytes,', len(exports), 'exports, imports', [hex(x) for x in entry['imports']])


if __name__ == '__main__':
    main(*sys.argv[1:4])
