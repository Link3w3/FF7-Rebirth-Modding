"""Binary FBX reader: the node tree, plus the scene (models, bones, animation curves, connections) for animation work."""
import struct, zlib


class Node:
    __slots__ = ('name', 'props', 'children')

    def __init__(self, name, props, children):
        self.name, self.props, self.children = name, props, children

    def find(self, name):
        for c in self.children:
            if c.name == name:
                return c
        return None

    def findall(self, name):
        return [c for c in self.children if c.name == name]

    def __repr__(self):
        return 'Node(%s, %r, %d children)' % (self.name, self.props[:4], len(self.children))


def _array(data, pos, code):
    n, enc, clen = struct.unpack_from('<III', data, pos)
    pos += 12
    raw = data[pos:pos + clen]
    pos += clen
    if enc == 1:
        raw = zlib.decompress(raw)
    fmt = {'f': 'f', 'd': 'd', 'l': 'q', 'i': 'i', 'b': 'B'}[code]
    return list(struct.unpack('<%d%s' % (n, fmt), raw[:n * struct.calcsize(fmt)])), pos


def _prop(data, pos):
    code = chr(data[pos])
    pos += 1
    if code == 'Y':
        return struct.unpack_from('<h', data, pos)[0], pos + 2
    if code == 'C':
        return bool(data[pos]), pos + 1
    if code == 'I':
        return struct.unpack_from('<i', data, pos)[0], pos + 4
    if code == 'F':
        return struct.unpack_from('<f', data, pos)[0], pos + 4
    if code == 'D':
        return struct.unpack_from('<d', data, pos)[0], pos + 8
    if code == 'L':
        return struct.unpack_from('<q', data, pos)[0], pos + 8
    if code in 'fdlib':
        return _array(data, pos, code)
    if code in 'SR':
        n = struct.unpack_from('<I', data, pos)[0]
        raw = data[pos + 4:pos + 4 + n]
        pos += 4 + n
        if code == 'S':
            try:
                return raw.decode('utf-8'), pos
            except UnicodeDecodeError:
                return raw.decode('latin-1'), pos
        return raw, pos
    raise ValueError('bad property type %r at %d' % (code, pos - 1))


def parse(data):
    assert data[:21] == b'Kaydara FBX Binary  \x00', 'not a binary FBX'
    version = struct.unpack_from('<I', data, 23)[0]
    wide = version >= 7500
    hdr = 25 if wide else 13
    null = hdr

    def node(pos):
        if wide:
            end, nprops, plen = struct.unpack_from('<QQQ', data, pos)
            pos += 24
        else:
            end, nprops, plen = struct.unpack_from('<III', data, pos)
            pos += 12
        nlen = data[pos]
        pos += 1
        if end == 0:
            return None, pos
        name = data[pos:pos + nlen].decode('latin-1')
        pos += nlen
        props = []
        for _ in range(nprops):
            v, pos = _prop(data, pos)
            props.append(v)
        children = []
        while pos < end:
            if end - pos == null and data[pos:pos + null] == b'\0' * null:
                pos += null
                break
            c, pos = node(pos)
            if c is None:
                break
            children.append(c)
        return Node(name, props, children), end

    pos = 27
    top = []
    while pos < len(data) - null:
        n, pos2 = node(pos)
        if n is None:
            break
        top.append(n)
        pos = pos2
    return version, Node('', [], top)


def props70(node):
    """Properties70 -> {name: values}."""
    out = {}
    p = node.find('Properties70') if node else None
    if p:
        for c in p.findall('P'):
            out[c.props[0]] = c.props[4:]
    return out


KTIME = 46186158000   # FBX time units per second


class Scene:
    def __init__(self, path):
        self.version, self.root = parse(open(path, 'rb').read())
        gs = self.root.find('GlobalSettings')
        self.settings = props70(gs)
        objs = self.root.find('Objects')
        self.objects = {}
        for o in objs.children:
            if o.props and isinstance(o.props[0], int):
                name = o.props[1] if len(o.props) > 1 else ''
                if isinstance(name, str) and '\x00\x01' in name:
                    name = name.split('\x00\x01')[0]
                self.objects[o.props[0]] = (o.name, name, o.props[2] if len(o.props) > 2 else '', o)
        self.conns = []   # (kind, child, parent, prop)
        for c in self.root.find('Connections').findall('C'):
            self.conns.append((c.props[0], c.props[1], c.props[2], c.props[3] if len(c.props) > 3 else None))
        self.parent = {}
        for kind, child, parent, prop in self.conns:
            if kind == 'OO':
                co, po = self.objects.get(child), self.objects.get(parent)
                if co and co[0] == 'Model' and (parent == 0 or (po and po[0] == 'Model')):
                    self.parent[child] = parent

    def models(self):
        return {k: v for k, v in self.objects.items() if v[0] == 'Model'}

    def model_children(self, mid):
        return [c for c, p in self.parent.items() if p == mid]

    def stacks(self):
        out = []
        for k, (kind, name, sub, node) in self.objects.items():
            if kind == 'AnimationStack':
                p = props70(node)
                out.append((name, p.get('LocalStart', [0])[0] / KTIME, p.get('LocalStop', [0])[0] / KTIME, k))
        return out

    def curves(self):
        """bone name -> {'T'|'R'|'S': {'d|X': (times, values)}} for every animated model property."""
        curve_node_of = {}
        for kind, child, parent, prop in self.conns:
            co, po = self.objects.get(child), self.objects.get(parent)
            if co and po and co[0] == 'AnimationCurveNode' and po[0] == 'Model' and kind == 'OP':
                curve_node_of[child] = (po[1], prop)
        out = {}
        for kind, child, parent, prop in self.conns:
            co, po = self.objects.get(child), self.objects.get(parent)
            if co and po and co[0] == 'AnimationCurve' and po[0] == 'AnimationCurveNode' and kind == 'OP':
                target = curve_node_of.get(parent)
                if not target:
                    continue
                bone, channel = target
                node = co[3]
                times = node.find('KeyTime').props[0]
                values = node.find('KeyValueFloat').props[0]
                out.setdefault(bone, {}).setdefault(channel, {})[prop] = ([t / KTIME for t in times], values)
        return out
