"""Tagged (versioned) UE4 property streams with every position kept, so object references can be changed in place and
arrays rebuilt: the reader for KH3's cooked packages and the editor packages built from them.

    props = parse(data, start, end, names)      -> [Prop] up to and including 'None'; props.end
    Prop: name, type, size, index, struct, enum, inner, guid, tag_start, value_start, value_end, refs (positions of
          object references inside the value), elements (array: per element (start, end, refs)), children (struct)
"""
import struct

NATIVE = {
    'Vector': 12, 'Vector2D': 8, 'Vector4': 16, 'Rotator': 12, 'Quat': 16, 'LinearColor': 16, 'Color': 4, 'Guid': 16,
    'IntPoint': 8, 'IntVector': 12, 'Box': 25, 'Box2D': 17, 'Plane': 16, 'Matrix': 64, 'TwoVectors': 24,
    'PerPlatformFloat': None, 'PerPlatformInt': None, 'FloatRange': 20, 'Int32Range': 20, 'SoftObjectPath': None,
    'SoftClassPath': None, 'DateTime': 8, 'Timespan': 8,
}
OBJECT_TYPES = ('ObjectProperty', 'ClassProperty', 'WeakObjectProperty', 'LazyObjectProperty', 'InterfaceProperty')


class Prop(object):
    __slots__ = ('name', 'type', 'size', 'index', 'struct', 'enum', 'inner', 'guid', 'bool', 'tag_start', 'size_at',
                 'value_start', 'value_end', 'refs', 'elements', 'children', 'inner_tag')

    def __init__(self):
        self.struct = self.enum = self.inner = self.guid = self.bool = self.inner_tag = None
        self.refs, self.elements, self.children = [], None, None

    def __repr__(self):
        return '<%s %s %d @%d>' % (self.type, self.name, self.size, self.value_start)


class Props(list):
    end = 0


def _name(d, p, names):
    i, n = struct.unpack_from('<ii', d, p)
    s = names[i]
    return s if n == 0 else '%s_%d' % (s, n - 1)


def read_tag(d, p, names):
    """(Prop or None at 'None', position after the tag)."""
    t = Prop()
    t.tag_start = p
    t.name = _name(d, p, names)
    p += 8
    if t.name == 'None':
        return None, p
    t.type = _name(d, p, names)
    p += 8
    t.size_at = p
    t.size, t.index = struct.unpack_from('<ii', d, p)
    p += 8
    if t.type == 'StructProperty':
        t.struct = _name(d, p, names)
        p += 8 + 16
    elif t.type == 'BoolProperty':
        t.bool = d[p]
        p += 1
    elif t.type in ('ByteProperty', 'EnumProperty'):
        t.enum = _name(d, p, names)
        p += 8
    elif t.type in ('ArrayProperty', 'SetProperty'):
        t.inner = _name(d, p, names)
        p += 8
    elif t.type == 'MapProperty':
        t.inner = (_name(d, p, names), _name(d, p + 8, names))
        p += 16
    has_guid = d[p]
    p += 1
    if has_guid:
        t.guid = d[p:p + 16]
        p += 16
    t.value_start = p
    t.value_end = p + t.size
    return t, p


def _is_native(struct_name, size):
    n = NATIVE.get(struct_name, 0)
    if n is None:
        return True
    return n != 0 and (size is None or size == n)


def _struct_value(d, p, end, names, struct_name, size):
    """(children Props or None for a native struct, refs)."""
    if _is_native(struct_name, size):
        return None, []
    try:
        ch = parse(d, p, end, names)
    except (ValueError, IndexError, struct.error):
        return None, []                          # natively serialized (e.g. FExpressionInput): no tags inside
    refs = []
    for c in ch:
        refs.extend(c.refs)
    return ch, refs


def parse(d, start, end, names):
    out = Props()
    p = start
    while True:
        t, p = read_tag(d, p, names)
        if t is None:
            out.end = p
            return out
        if t.value_end > end:
            raise ValueError('property %s runs past its object (%d > %d)' % (t.name, t.value_end, end))
        v = t.value_start
        if t.type in OBJECT_TYPES:
            t.refs = [v]
        elif t.type == 'StructProperty':
            t.children, t.refs = _struct_value(d, v, t.value_end, names, t.struct, t.size)
        elif t.type == 'ArrayProperty':
            count = struct.unpack_from('<i', d, v)[0]
            q = v + 4
            t.elements = []
            if t.inner == 'StructProperty':
                it, q = read_tag(d, q, names)
                t.inner_tag = it
                per = (t.value_end - q) // count if count else 0
                for _ in range(count):
                    if _is_native(it.struct, per if it.struct in NATIVE else None):
                        n = NATIVE.get(it.struct) or per
                        t.elements.append((q, q + n, []))
                        q += n
                    else:
                        ch = parse(d, q, t.value_end, names)
                        refs = [r for c in ch for r in c.refs]
                        t.elements.append((q, ch.end, refs))
                        q = ch.end
            elif t.inner in OBJECT_TYPES:
                for _ in range(count):
                    t.elements.append((q, q + 4, [q]))
                    q += 4
            else:
                q = t.value_end            # other element types carry no references
            for _, _, refs in t.elements:
                t.refs.extend(refs)
            if t.elements and q != t.value_end:
                raise ValueError('array %s: %d bytes read of %d' % (t.name, q - v, t.size))
        out.append(t)
        p = t.value_end


def find(props, name):
    for t in props:
        if t.name == name:
            return t
    return None
