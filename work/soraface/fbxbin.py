"""A small binary FBX reader: the node tree (name, properties, children), arrays as numpy."""
import struct
import zlib
import numpy as np

ARR = {b'f': ('<f4', 4), b'd': ('<f8', 8), b'l': ('<i8', 8), b'i': ('<i4', 4), b'b': ('?', 1)}


class Node:
    __slots__ = ('name', 'props', 'kids')

    def __init__(self, name, props, kids):
        self.name, self.props, self.kids = name, props, kids

    def find(self, name):
        for k in self.kids:
            if k.name == name:
                return k
        return None

    def findall(self, name):
        return [k for k in self.kids if k.name == name]

    def __repr__(self):
        return 'Node(%s, %s, %d kids)' % (self.name, [p if not isinstance(p, np.ndarray) else 'arr%d' % len(p) for p in self.props][:4], len(self.kids))


def read(path):
    d = open(path, 'rb').read()
    assert d[:20] == b'Kaydara FBX Binary  ', d[:20]
    ver = struct.unpack_from('<I', d, 23)[0]
    wide = ver >= 7500
    hdr = 25 if wide else 13

    def prop(o):
        t = d[o:o + 1]; o += 1
        if t == b'Y': return struct.unpack_from('<h', d, o)[0], o + 2
        if t == b'C': return d[o] != 0, o + 1
        if t == b'I': return struct.unpack_from('<i', d, o)[0], o + 4
        if t == b'F': return struct.unpack_from('<f', d, o)[0], o + 4
        if t == b'D': return struct.unpack_from('<d', d, o)[0], o + 8
        if t == b'L': return struct.unpack_from('<q', d, o)[0], o + 8
        if t in (b'S', b'R'):
            n = struct.unpack_from('<I', d, o)[0]; raw = d[o + 4:o + 4 + n]
            return (raw.decode('utf-8', 'replace') if t == b'S' else raw), o + 4 + n
        if t in ARR:
            n, enc, clen = struct.unpack_from('<III', d, o); o += 12
            raw = d[o:o + clen]
            if enc == 1:
                raw = zlib.decompress(raw)
            dt, sz = ARR[t]
            return np.frombuffer(raw, dt, n).copy(), o + clen
        raise ValueError('prop type %r at %d' % (t, o - 1))

    def node(o):
        if wide:
            end, nprops, plen = struct.unpack_from('<QQQ', d, o); o += 24
        else:
            end, nprops, plen = struct.unpack_from('<III', d, o); o += 12
        if end == 0:
            return None, o
        nl = d[o]; name = d[o + 1:o + 1 + nl].decode('ascii', 'replace'); o += 1 + nl
        props = []
        for _ in range(nprops):
            v, o = prop(o); props.append(v)
        kids = []
        while o < end:
            k, o2 = node(o)
            if k is None:
                o = o2
                break
            kids.append(k); o = o2
        return Node(name, props, kids), end

    o = 27
    top = []
    while o < len(d) - hdr:
        n, o2 = node(o)
        if n is None:
            break
        top.append(n); o = o2
    return Node('root', [], top), ver
