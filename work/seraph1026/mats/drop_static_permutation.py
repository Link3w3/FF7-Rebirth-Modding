"""A cooked material instance (zen, UE 4.26) whose static permutation is only its parent's own switch values, made to
use its parent's shaders: the game has its parent's shader maps, none for a permutation compiled in the editor (a slot
with such a material shows the default material in game: the Seraph Sephiroth skins' body, skirt and Essence Shard).

Its bHasStaticPermutationResource and StaticParameters tags taken out (every switch they override must be named, with
its value, in --same: the parent's own values, checked in the editor) and the inline shader maps after the properties
dropped, as the editor cooks a material instance without static overrides; the export's size in the export map made to
match. Nothing else changes (header, names, imports, the other tags byte for byte).
    drop_static_permutation.py <in.uasset> <out.uasset> --same NAME=1 [NAME=0 ...]"""
import argparse
import struct
import sys
sys.path[:0] = ['/work/cs', '/work/fpys/tools', '/work/iostore', '/work/weap1012/tools',
                '/work/evilboss1016/data', '/work/swap1012/tools', '/work/evil1013/tools',
                '/work/vincentfix']
from zen import Zen
from build_fpys_data_v6 import Tags


def switches(t, x, p):
    """The static switch overrides in a StaticParameters tag: [(name, value, override)]."""
    out = []
    o = p['value']
    while True:
        q = t.tag(o)
        if q['name'] == 'None':
            break
        if q['name'] == 'StaticSwitchParameters':
            n = struct.unpack_from('<i', x, q['value'])[0]
            inner = t.tag(q['value'] + 4)
            r = inner['value']
            for _ in range(n):
                name = value = override = None
                while True:
                    s = t.tag(r)
                    if s['name'] == 'None':
                        r = s['end']
                        break
                    if s['name'] == 'Value':
                        value = x[s['size_at'] + 8]
                    elif s['name'] == 'bOverride':
                        override = x[s['size_at'] + 8]
                    elif s['name'] == 'ParameterInfo':
                        u = s['value']
                        while True:
                            v = t.tag(u)
                            if v['name'] == 'None':
                                break
                            if v['name'] == 'Name':
                                name = t.fname(v['value'])[0]
                            u = v['end']
                    r = s['end']
                out.append((name, value, override))
        elif q['type'] == 'ArrayProperty':
            if struct.unpack_from('<i', x, q['value'])[0] != 0:
                raise SystemExit('StaticParameters has %s entries: not only switches (left as it is)' % q['name'])
        o = q['end']
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('out')
    ap.add_argument('--same', nargs='+', required=True)
    a = ap.parse_args()
    same = {k: int(v) for k, v in (s.split('=') for s in a.same)}
    d = open(a.src, 'rb').read()
    z = Zen(d)
    assert len(z.exports) == 1, 'one export expected'
    start, size = z.bundle_positions()[0]
    assert start == z.header_end and start + size == len(d)
    x = d[start:start + size]
    t = Tags(z.names, x)
    keep, dropped, o = [], [], 0
    found_switches = None
    perm = None
    while True:
        p = t.tag(o)
        if p['name'] == 'None':
            none = x[p['start']:p['end']]
            o = p['end']
            break
        if p['name'] == 'bHasStaticPermutationResource':
            perm = x[p['size_at'] + 8]
            dropped.append(p['name'])
        elif p['name'] == 'StaticParameters':
            found_switches = switches(t, x, p)
            dropped.append(p['name'])
        elif p['name'] == 'BasePropertyOverrides':
            # any bOverride_* tag set in it would need a permutation of its own
            u = p['value']
            while True:
                v = t.tag(u)
                if v['name'] == 'None':
                    break
                if v['name'].startswith('bOverride') and x[v['size_at'] + 8]:
                    raise SystemExit('BasePropertyOverrides overrides %s: it needs a permutation of its own' % v['name'])
                u = v['end']
            keep.append(x[p['start']:p['end']])
        else:
            keep.append(x[p['start']:p['end']])
        o = p['end']
    assert perm == 1, 'no static permutation in it'
    for name, value, override in found_switches or []:
        if override and same.get(name) != value:
            raise SystemExit('switch %s = %d is not named in --same as its parent\'s value' % (name, value))
    guid = x[o:o + 4]
    assert guid == b'\0\0\0\0', 'an object guid follows the properties: not handled'
    new = b''.join(keep) + none + guid
    hdr = bytearray(d[:start])
    off, sz = struct.unpack_from('<QQ', hdr, z.exp_off)
    assert sz == size
    struct.pack_into('<Q', hdr, z.exp_off + 8, len(new))
    out = bytes(hdr) + new
    c = Zen(out)
    s2, n2 = c.bundle_positions()[0]
    assert (s2, n2) == (start, len(new)) and c.names == z.names and c.imports == z.imports
    t2 = Tags(c.names, out[s2:s2 + n2])
    o, names = 0, []
    while True:
        p = t2.tag(o)
        names.append(p['name'])
        if p['name'] == 'None':
            assert p['end'] + 4 == n2
            break
        o = p['end']
    open(a.out, 'wb').write(out)
    print('%s: %d -> %d bytes; dropped %s (overrides: %s) and %d bytes of shader maps; tags now %s' % (
        a.src.split('/')[-1], len(d), len(out), dropped, found_switches, size - (o + 4 + len(guid)) if False else len(x) - len(b''.join(keep)) - len(none) - 4 - sum(0 for _ in [0]), names))


if __name__ == '__main__':
    main()
