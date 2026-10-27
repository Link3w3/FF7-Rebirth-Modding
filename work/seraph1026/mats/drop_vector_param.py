"""A cooked material instance (zen, UE 4.26) with its VectorParameterValues tag taken out when every entry in it is one
of the names given (each such parameter then comes from its parent, as on the game's own material): the Essence Shard's
WE1021_15_Body_Inst overrides GenericVector1Context (one of the game's runtime "context" vectors) with zero, which no
other material of the skin, nor the Masamune's own WE1021_00_Body, does. The export's size in the export map made to
match; nothing else changes.
    drop_vector_param.py <in.uasset> <out.uasset> NAME [NAME ...]"""
import struct
import sys
sys.path[:0] = ['/work/cs', '/work/fpys/tools', '/work/iostore', '/work/weap1012/tools',
                '/work/evilboss1016/data', '/work/swap1012/tools', '/work/evil1013/tools',
                '/work/vincentfix']
from zen import Zen
from build_fpys_data_v6 import Tags


def entry_names(t, x, p):
    n = struct.unpack_from('<i', x, p['value'])[0]
    inner = t.tag(p['value'] + 4)
    o = inner['value']
    names = []
    for _ in range(n):
        name = None
        while True:
            s = t.tag(o)
            if s['name'] == 'None':
                o = s['end']
                break
            if s['name'] == 'ParameterInfo':
                u = s['value']
                while True:
                    v = t.tag(u)
                    if v['name'] == 'None':
                        break
                    if v['name'] == 'Name':
                        name = t.fname(v['value'])[0]
                    u = v['end']
            o = s['end']
        names.append(name)
    return names


def main(src, out, allowed):
    d = open(src, 'rb').read()
    z = Zen(d)
    assert len(z.exports) == 1
    start, size = z.bundle_positions()[0]
    assert start == z.header_end and start + size == len(d)
    x = d[start:start + size]
    t = Tags(z.names, x)
    keep, o, dropped = [], 0, None
    while True:
        p = t.tag(o)
        if p['name'] == 'None':
            keep.append(x[p['start']:p['end']])
            o = p['end']
            break
        if p['name'] == 'VectorParameterValues':
            dropped = entry_names(t, x, p)
            if not dropped or any(n not in allowed for n in dropped):
                raise SystemExit('VectorParameterValues holds %s: not only %s' % (dropped, allowed))
        else:
            keep.append(x[p['start']:p['end']])
        o = p['end']
    assert dropped, 'no VectorParameterValues tag'
    rest = x[o:]
    assert rest == b'\0\0\0\0', 'more than the object guid after the properties'
    new = b''.join(keep) + rest
    hdr = bytearray(d[:start])
    struct.pack_into('<Q', hdr, z.exp_off + 8, len(new))
    outb = bytes(hdr) + new
    c = Zen(outb)
    assert c.bundle_positions()[0] == (start, len(new)) and c.names == z.names and c.imports == z.imports
    t2 = Tags(c.names, outb[start:])
    o, names = 0, []
    while True:
        p = t2.tag(o)
        names.append(p['name'])
        if p['name'] == 'None':
            assert p['end'] + 4 == len(new)
            break
        o = p['end']
    open(out, 'wb').write(outb)
    print('%s: %d -> %d bytes; VectorParameterValues %s taken out; tags now %s' % (src.split('/')[-1], len(d), len(outb), dropped, names))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], set(sys.argv[3:]))
