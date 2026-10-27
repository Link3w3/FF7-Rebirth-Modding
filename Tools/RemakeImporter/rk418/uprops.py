"""Unversioned property reader for FF7 Remake's cooked UE 4.18 packages, driven by the schema read from the game's exe.

Every decoded value remembers where it is (V.at, V.size).
    uprops.py <package.uasset> [export index ...]"""
import struct, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schema import Schema


class ParseError(Exception):
    pass


class V:
    __slots__ = ('kind', 'type', 'at', 'size', 'value', 'zero')

    def __init__(self, kind, typ, at, size, value, zero=False):
        self.kind, self.type, self.at, self.size, self.value, self.zero = kind, typ, at, size, value, zero

    def __repr__(self):
        return 'V(%s %s @%d+%d %r)' % (self.kind, self.type, self.at, self.size, self.value if self.kind != 'struct' else '{...}')

    def py(self):
        """plain python value"""
        if self.kind == 'struct':
            return {k: v.py() for k, v in self.value.items()}
        if self.kind in ('array', 'set'):
            return [v.py() for v in self.value]
        if self.kind == 'map':
            return [(a.py(), b.py()) for a, b in self.value]
        if self.kind == 'native' and isinstance(self.value, dict):
            return {k: (v.py() if isinstance(v, V) else v) for k, v in self.value.items()}
        return self.value


class Reader:
    def __init__(self, schema, names, data, pos=0, end=None):
        self.s, self.names, self.d, self.p = schema, names, data, pos
        self.end = len(data) if end is None else end
        self.natives = dict(NATIVES)
        self.trace = []

    def need(self, n):
        if self.p + n > self.end:
            raise ParseError('read of %d past the end at %d (end %d) in %s' % (n, self.p, self.end, '/'.join(self.trace[-6:])))

    def raw(self, n):
        self.need(n); v = self.d[self.p:self.p + n]; self.p += n; return v

    def unpack(self, fmt):
        n = struct.calcsize(fmt); self.need(n)
        v = struct.unpack_from(fmt, self.d, self.p); self.p += n; return v

    def u8(self): return self.unpack('<B')[0]
    def u16(self): return self.unpack('<H')[0]
    def i32(self): return self.unpack('<i')[0]
    def u32(self): return self.unpack('<I')[0]
    def f32(self): return self.unpack('<f')[0]

    def name(self):
        idx, num = self.unpack('<ii')
        if not 0 <= idx < len(self.names):
            raise ParseError('bad name index %d at %d in %s' % (idx, self.p - 8, '/'.join(self.trace[-6:])))
        s = self.names[idx]
        return s if num == 0 else '%s_%d' % (s, num - 1)

    def fstring(self):
        n = self.i32()
        if n == 0:
            return ''
        if n < 0:
            if -n > 1 << 20: raise ParseError('bad string length %d at %d' % (n, self.p - 4))
            return self.raw(-n * 2).decode('utf-16-le', 'replace').rstrip('\0')
        if n > 1 << 20: raise ParseError('bad string length %d at %d' % (n, self.p - 4))
        return self.raw(n).decode('latin-1').rstrip('\0')

    def header(self):
        frags = []
        while True:
            v = self.u16()
            frags.append((v & 0x7f, bool(v & 0x80), v >> 9, bool(v & 0x100)))
            if v & 0x100:
                break
        zn = sum(f[2] for f in frags if f[1])
        mask = []
        if zn:
            if zn <= 8:
                w = self.u8(); mask = [(w >> b) & 1 for b in range(8)]
            elif zn <= 16:
                w = self.u16(); mask = [(w >> b) & 1 for b in range(16)]
            else:
                for _ in range((zn + 31) // 32):
                    w = self.u32(); mask += [(w >> b) & 1 for b in range(32)]
        out, idx, zi = [], 0, 0
        for skip, hz, num, last in frags:
            idx += skip
            for _ in range(num):
                zero = False
                if hz:
                    zero = bool(mask[zi]); zi += 1
                out.append((idx, zero))
                idx += 1
        return out

    def struct(self, sname):
        start = self.p
        nat = self.natives.get(sname)
        if nat is not None:
            self.trace.append(sname)
            try:
                v = nat(self, sname)
            finally:
                self.trace.pop()
            return V('native', sname, start, self.p - start, v)
        if self.s.immutable(sname):
            return self.binary(sname)
        return self.props(sname)

    def binary(self, sname):
        """UScriptStruct::SerializeBin: every property in order, no header"""
        start = self.p
        out = {}
        for st in self.s.chain(sname):
            for p in st.props:
                for k in range(p.array_dim):
                    key = p.name if p.array_dim == 1 else '%s[%d]' % (p.name, k)
                    out[key] = self.value(p.ptype)
        return V('struct', sname, start, self.p - start, out)

    def props(self, sname):
        start = self.p
        self.trace.append(sname)
        try:
            out = {}
            for idx, zero in self.header():
                prop, elem, owner = self.s.prop_at(sname, idx)
                if prop is None:
                    raise ParseError('%s has no property at index %d (at %d)' % (sname, idx, self.p))
                key = prop.name if prop.array_dim == 1 else '%s[%d]' % (prop.name, elem)
                self.trace.append(key)
                try:
                    out[key] = V('prim', prop.ptype.type, self.p, 0, 0, zero=True) if zero else self.value(prop.ptype)
                finally:
                    self.trace.pop()
            return V('struct', sname, start, self.p - start, out)
        finally:
            self.trace.pop()

    def value(self, pt):
        t = pt.type
        at = self.p
        if t == 'BoolProperty':
            return V('prim', t, at, 1, bool(self.u8()))
        if t == 'ByteProperty':
            return V('prim', t, at, 1, self.u8())
        if t == 'Int8Property':
            return V('prim', t, at, 1, self.unpack('<b')[0])
        if t == 'Int16Property':
            return V('prim', t, at, 2, self.unpack('<h')[0])
        if t == 'UInt16Property':
            return V('prim', t, at, 2, self.u16())
        if t == 'IntProperty':
            return V('prim', t, at, 4, self.i32())
        if t == 'UInt32Property':
            return V('prim', t, at, 4, self.u32())
        if t == 'Int64Property':
            return V('prim', t, at, 8, self.unpack('<q')[0])
        if t == 'UInt64Property':
            return V('prim', t, at, 8, self.unpack('<Q')[0])
        if t == 'FloatProperty':
            return V('prim', t, at, 4, self.f32())
        if t == 'DoubleProperty':
            return V('prim', t, at, 8, self.unpack('<d')[0])
        if t == 'NameProperty':
            return V('name', t, at, 8, self.name())
        if t == 'StrProperty':
            s = self.fstring()
            return V('str', t, at, self.p - at, s)
        if t == 'EnumProperty':
            inner = self.value(pt.inner)
            iv = inner.value
            nm = self.s.enum_values.get(pt.enum, {}).get(iv, iv)
            return V('enum', pt.enum, at, self.p - at, nm)
        if t in ('ObjectProperty', 'WeakObjectProperty', 'InterfaceProperty'):
            return V('obj', t, at, 4, self.i32())
        if t == 'LazyObjectProperty':
            return V('obj', t, at, 16, self.raw(16).hex())
        if t == 'SoftObjectProperty':
            n = self.name(); sub = self.fstring()
            return V('str', t, at, self.p - at, (n, sub))
        if t == 'StructProperty':
            return self.struct(pt.struct)
        if t == 'ArrayProperty':
            n = self.i32()
            if n < 0 or n > 1 << 22:
                raise ParseError('bad array count %d at %d in %s' % (n, at, '/'.join(self.trace[-6:])))
            items = [self.value(pt.inner) for _ in range(n)]
            return V('array', repr(pt.inner), at, self.p - at, items)
        if t == 'SetProperty':
            removed = self.i32()
            if removed:
                raise ParseError('set with removed elements at %d' % at)
            n = self.i32()
            items = [self.value(pt.inner) for _ in range(n)]
            return V('set', repr(pt.inner), at, self.p - at, items)
        if t == 'MapProperty':
            removed = self.i32()
            if removed:
                raise ParseError('map with removed keys at %d' % at)
            n = self.i32()
            if n < 0 or n > 1 << 20:
                raise ParseError('bad map count %d at %d' % (n, at))
            items = [(self.value(pt.inner), self.value(pt.value)) for _ in range(n)]
            return V('map', '%r,%r' % (pt.inner, pt.value), at, self.p - at, items)
        if t == 'TextProperty':
            return V('text', t, at, 0, self.text())
        if t == 'DelegateProperty':
            o = self.i32(); fn = self.name()
            return V('prim', t, at, 12, (o, fn))
        if t == 'MulticastDelegateProperty':
            n = self.i32(); items = [(self.i32(), self.name()) for _ in range(n)]
            return V('prim', t, at, self.p - at, items)
        raise ParseError('cannot read a %s at %d' % (t, at))

    def text(self):
        flags = self.u32()
        hist = self.unpack('<b')[0]
        if hist == -1:
            return ('none',)
        if hist == 0:
            return ('base', self.fstring(), self.fstring(), self.fstring())
        if hist == 11:
            return ('table', self.name(), self.fstring())
        raise ParseError('FText history %d at %d' % (hist, self.p))


def _soft_path(r, s):
    return (r.name(), r.fstring())


def _rich_curve_key(r, s):
    v = r.unpack('<3B6f')
    return {'InterpMode': v[0], 'TangentMode': v[1], 'TangentWeightMode': v[2], 'Time': v[3], 'Value': v[4],
            'ArriveTangent': v[5], 'ArriveTangentWeight': v[6], 'LeaveTangent': v[7], 'LeaveTangentWeight': v[8]}


def _nothing(r, s):
    return None


NATIVES = {
    'SoftObjectPath': _soft_path, 'SoftClassPath': _soft_path, 'StringAssetReference': _soft_path, 'StringClassReference': _soft_path,
    'RichCurveKey': _rich_curve_key, 'KeyHandleMap': _nothing,
    # (4.18: FSmartName::Serialize, the display name only)
    'SmartName': lambda r, s: r.name(),
}


def read_export(schema, pkg, i):
    """(class name, V struct, end of the properties)"""
    e = pkg.exports[i]
    cls = pkg.classname(e)
    r = Reader(schema, pkg.names, pkg.d, e['off'], e['off'] + e['size'])
    v = r.props(cls)
    return cls, v, r.p


def dump(v, indent='', out=None, limit=40):
    out = out if out is not None else sys.stdout
    w = out.write
    if v.kind == 'struct':
        w('%s{%s} @%d+%d\n' % (indent, v.type, v.at, v.size))
        for k, x in v.value.items():
            w('%s  %s:' % (indent, k))
            if x.kind in ('struct', 'array', 'map', 'set') or (x.kind == 'native' and isinstance(x.value, dict)):
                w('\n'); dump(x, indent + '    ', out, limit)
            else:
                w(' '); dump(x, '', out, limit)
    elif v.kind in ('array', 'set'):
        w('%s[%s x%d]\n' % (indent, v.type, len(v.value)))
        for k, x in enumerate(v.value[:limit]):
            w('%s  [%d]' % (indent, k))
            if x.kind in ('struct', 'array', 'map', 'set') or (x.kind == 'native' and isinstance(x.value, dict)):
                w('\n'); dump(x, indent + '    ', out, limit)
            else:
                w(' '); dump(x, '', out, limit)
        if len(v.value) > limit:
            w('%s  ... %d more\n' % (indent, len(v.value) - limit))
    elif v.kind == 'map':
        w('%s{map x%d}\n' % (indent, len(v.value)))
        for a, b in v.value[:limit]:
            w('%s  %r ->' % (indent, a.py()))
            if b.kind in ('struct', 'array', 'map', 'set'):
                w('\n'); dump(b, indent + '    ', out, limit)
            else:
                w(' %r\n' % (b.py(),))
    elif v.kind == 'native' and isinstance(v.value, dict):
        w('%s<%s> %r\n' % (indent, v.type, {k: (x.py() if isinstance(x, V) else x) for k, x in v.value.items()}))
    else:
        val = v.value
        if isinstance(val, float): val = round(val, 6)
        w('%s%r%s\n' % (indent, val, ' (zero)' if v.zero else ''))


if __name__ == '__main__':
    import pkg418
    S = Schema()
    p = pkg418.Package(sys.argv[1])
    idx = [int(x) for x in sys.argv[2:]] or range(len(p.exports))
    for i in idx:
        e = p.exports[i]
        try:
            cls, v, end = read_export(S, p, i)
            print('export %d %s (%s): props end at %d of %d..%d (native %d bytes)' % (i, e['name'], cls, end, e['off'], e['off'] + e['size'], e['off'] + e['size'] - end))
            dump(v, '  ')
        except Exception as ex:
            print('export %d %s (%s): FAILED %s' % (i, e['name'], p.classname(e), ex))
