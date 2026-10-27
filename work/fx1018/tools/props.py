"""UE 4.26 tagged property reader for cooked zen (and legacy) packages, for looking at FINAL FANTASY VII REBIRTH's
cooked assets (Niagara systems, material instances). Values are decoded where the type is plain; native structs and
anything else stay raw bytes (with their offsets, so a value can be patched in place).

    props.py <zen package> [export name or index ...]
"""
import struct, sys, os
sys.path[:0] = ['/work/iostore', '/work/cs']
from zen import Zen

# structs whose tagged value is a native binary layout (no property stream inside)
NATIVE_STRUCTS = {
    'Vector': '<3f', 'Vector2D': '<2f', 'Vector4': '<4f', 'LinearColor': '<4f', 'Color': '<4B', 'Quat': '<4f', 'Rotator': '<3f',
    'IntPoint': '<2i', 'IntVector': '<3i', 'Guid': '<4I', 'Box': '<3f3fB', 'Box2D': '<2f2fB', 'Plane': '<4f',
    'FrameNumber': '<i', 'DateTime': '<q', 'Timespan': '<q', 'SoftObjectPath': None, 'SoftClassPath': None,
    'PerPlatformFloat': None, 'PerPlatformInt': None, 'PerPlatformBool': None, 'MovieSceneFrameRange': None,
    'RichCurveKey': '<BBBfffff', 'Matrix': '<16f', 'Transform': None, 'BoxSphereBounds': '<7f', 'Sphere': '<4f',
    'NiagaraVariable': None, 'NiagaraVariableBase': None, 'NiagaraTypeDefinition': None, 'NiagaraDataSetID': None,
}


class Reader:
    def __init__(self, d, pos=0, end=None, names=None):
        self.d, self.p, self.end, self.names = d, pos, (len(d) if end is None else end), names

    def u8(self):
        v = self.d[self.p]; self.p += 1; return v

    def i32(self):
        v = struct.unpack_from('<i', self.d, self.p)[0]; self.p += 4; return v

    def u32(self):
        v = struct.unpack_from('<I', self.d, self.p)[0]; self.p += 4; return v

    def i64(self):
        v = struct.unpack_from('<q', self.d, self.p)[0]; self.p += 8; return v

    def f32(self):
        v = struct.unpack_from('<f', self.d, self.p)[0]; self.p += 4; return v

    def name(self):
        idx, num = struct.unpack_from('<II', self.d, self.p); self.p += 8
        i = idx & 0x3fffffff
        s = self.names[i] if i < len(self.names) else '?name%d' % i
        return s if num == 0 else '%s_%d' % (s, num - 1)

    def guid(self):
        v = self.d[self.p:self.p + 16]; self.p += 16; return v.hex()

    def fstring(self):
        n = self.i32()
        if n == 0: return ''
        if n < 0:
            s = self.d[self.p:self.p - n * 2].decode('utf-16-le', 'replace'); self.p += -n * 2
        else:
            s = self.d[self.p:self.p + n].decode('latin-1'); self.p += n
        return s.rstrip('\0')


class Prop:
    def __init__(self, name, typ, size, index, at, value_at, extra=None, value=None):
        self.name, self.type, self.size, self.index, self.at, self.value_at, self.extra, self.value = name, typ, size, index, at, value_at, extra or {}, value

    def __repr__(self):
        return '%s:%s[%d]@%d(%d)=%r' % (self.name, self.type, self.index, self.value_at, self.size, self.value)


def read_tag(r):
    at = r.p
    name = r.name()
    if name == 'None':
        return None
    typ = r.name()
    size = r.i32()
    index = r.i32()
    extra = {}
    if typ == 'StructProperty':
        extra['struct'] = r.name(); extra['guid'] = r.guid()
    elif typ == 'BoolProperty':
        extra['bool'] = r.u8()
    elif typ in ('ByteProperty', 'EnumProperty'):
        extra['enum'] = r.name()
    elif typ in ('ArrayProperty', 'SetProperty'):
        extra['inner'] = r.name()
    elif typ == 'MapProperty':
        extra['inner'] = r.name(); extra['value'] = r.name()
    has_guid = r.u8()
    if has_guid:
        extra['propguid'] = r.guid()
    return Prop(name, typ, size, index, at, r.p, extra)


def read_value(r, typ, size, extra, end, depth=0):
    """Decode a value of `typ` from r.p (r.p left at its end)."""
    start = r.p
    if typ == 'BoolProperty':
        return bool(extra.get('bool'))
    if typ == 'IntProperty': return r.i32()
    if typ == 'UInt32Property': return r.u32()
    if typ == 'Int64Property': return r.i64()
    if typ == 'UInt64Property':
        v = struct.unpack_from('<Q', r.d, r.p)[0]; r.p += 8; return v
    if typ == 'UInt16Property':
        v = struct.unpack_from('<H', r.d, r.p)[0]; r.p += 2; return v
    if typ == 'Int16Property':
        v = struct.unpack_from('<h', r.d, r.p)[0]; r.p += 2; return v
    if typ == 'Int8Property':
        v = struct.unpack_from('<b', r.d, r.p)[0]; r.p += 1; return v
    if typ == 'FloatProperty': return r.f32()
    if typ == 'DoubleProperty':
        v = struct.unpack_from('<d', r.d, r.p)[0]; r.p += 8; return v
    if typ in ('NameProperty',): return r.name()
    if typ in ('StrProperty',): return r.fstring()
    if typ == 'ByteProperty':
        if size == 1: return r.u8()
        return r.name()
    if typ == 'EnumProperty':
        return r.name()
    if typ in ('ObjectProperty', 'ClassProperty', 'WeakObjectProperty', 'LazyObjectProperty', 'InterfaceProperty'):
        v = r.i32()
        return ('obj', v)
    if typ in ('SoftObjectProperty', 'SoftClassProperty'):
        path = r.name(); sub = r.fstring()
        return ('soft', path, sub)
    if typ == 'TextProperty':
        r.p = start + size
        return ('text', r.d[start:start + size].hex())
    if typ == 'StructProperty':
        return read_struct(r, extra.get('struct'), size, end, depth)
    if typ in ('ArrayProperty', 'SetProperty'):
        inner = extra.get('inner')
        count = r.i32()
        if typ == 'SetProperty':
            # removed count + elements
            removed = count; count = r.i32()
        items = []
        if inner == 'StructProperty':
            # inner tag
            inner_tag = read_tag(r)
            sname = inner_tag.extra.get('struct') if inner_tag else None
            each = (inner_tag.size // count) if (inner_tag and count) else 0
            for k in range(count):
                s0 = r.p
                items.append(read_struct(r, sname, each if NATIVE_STRUCTS.get(sname) is None and sname in NATIVE_STRUCTS else -1, end, depth + 1, at=s0))
            return {'struct': sname, 'items': items}
        for k in range(count):
            items.append(read_value(r, inner, 0, {}, end, depth + 1))
        return items
    if typ == 'MapProperty':
        removed = r.i32()
        count = r.i32()
        items = []
        for k in range(count):
            key = read_value(r, extra.get('inner'), 0, {}, end, depth + 1) if extra.get('inner') != 'StructProperty' else read_struct(r, None, -1, end, depth + 1)
            val = read_value(r, extra.get('value'), 0, {}, end, depth + 1) if extra.get('value') != 'StructProperty' else read_struct(r, None, -1, end, depth + 1)
            items.append((key, val))
        return {'map': items}
    # unknown: raw
    r.p = start + size
    return ('raw', r.d[start:start + size].hex())


def read_struct(r, sname, size, end, depth=0, at=None):
    start = r.p
    fmt = NATIVE_STRUCTS.get(sname, 'tagged') if sname else 'tagged'
    if sname in NATIVE_STRUCTS and fmt:
        n = struct.calcsize(fmt)
        v = struct.unpack_from(fmt, r.d, r.p); r.p += n
        return {'@': start, sname: list(v)}
    if sname in NATIVE_STRUCTS and fmt is None:
        if size and size > 0:
            r.p = start + size
            return {'@': start, sname: ('raw', r.d[start:start + size].hex())}
        if sname in ('SoftObjectPath', 'SoftClassPath'):
            return {'@': start, sname: (r.name(), r.fstring())}
        raise ValueError('native struct %s of unknown size at %d' % (sname, start))
    # tagged struct: a property stream
    props = read_props(r, end, depth + 1)
    return {'@': start, 'struct': sname, 'props': props}


def read_props(r, end, depth=0):
    out = []
    while r.p < end:
        tag = read_tag(r)
        if tag is None:
            break
        vstart = r.p
        try:
            tag.value = read_value(r, tag.type, tag.size, tag.extra, vstart + tag.size, depth)
        except Exception as e:
            tag.value = ('error', str(e), r.d[vstart:vstart + min(tag.size, 64)].hex())
        if r.p != vstart + tag.size:
            # trust the tag size
            tag.extra['consumed'] = r.p - vstart
            r.p = vstart + tag.size
        out.append(tag)
    return out


def export_props(z, i):
    data = z.export_bytes(i)
    r = Reader(data, 0, len(data), z.names)
    props = read_props(r, len(data))
    return props, r.p, data


def show(props, indent='  ', limit=200):
    for p in props:
        v = p.value
        if isinstance(v, dict) and 'props' in v:
            print('%s%s (%s %s) @%d size %d' % (indent, p.name, p.type, p.extra.get('struct'), p.value_at, p.size))
            show(v['props'], indent + '  ', limit)
        elif isinstance(v, dict) and 'items' in v:
            print('%s%s [%s x%d] @%d size %d' % (indent, p.name, v['struct'], len(v['items']), p.value_at, p.size))
            for k, it in enumerate(v['items'][:limit]):
                if isinstance(it, dict) and 'props' in it:
                    print('%s  [%d] @%d' % (indent, k, it['@']))
                    show(it['props'], indent + '    ', limit)
                else:
                    print('%s  [%d] %r' % (indent, k, it))
        else:
            s = repr(v)
            print('%s%s (%s%s) @%d size %d = %s' % (indent, p.name, p.type, (' ' + str(p.extra.get('struct') or p.extra.get('inner') or p.extra.get('enum') or '')) if p.extra else '',
                                                   p.value_at, p.size, s[:300]))


if __name__ == '__main__':
    z = Zen(open(sys.argv[1], 'rb').read())
    want = sys.argv[2:]
    for i, e in enumerate(z.exports):
        if want and e['name'] not in want and str(i) not in want:
            continue
        props, end, data = export_props(z, i)
        print('== export %d %s: %d bytes, tagged properties end at %d (native data after: %d bytes)' % (i, e['name'], len(data), end, len(data) - end))
        show(props)
