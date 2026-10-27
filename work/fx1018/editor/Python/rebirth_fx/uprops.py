"""Unversioned (PKG_UnversionedProperties) property reader for UE 4.26 cooked zen packages, driven by a .usmap.

Every decoded value remembers where it is (V.at, V.size) so a value can be patched in place.

    uprops.py <usmap> <zen package> [export name or index ...]
"""
import struct, sys
from .usmap import Usmap


class ParseError(Exception):
    pass


class V:
    """A decoded value. kind: 'prim', 'struct', 'array', 'map', 'set', 'obj', 'name', 'str', 'enum', 'native', 'text'."""
    __slots__ = ('kind', 'type', 'at', 'size', 'value', 'zero')

    def __init__(self, kind, typ, at, size, value, zero=False):
        self.kind, self.type, self.at, self.size, self.value, self.zero = kind, typ, at, size, value, zero

    def __repr__(self):
        return 'V(%s %s @%d+%d %r)' % (self.kind, self.type, self.at, self.size, self.value if self.kind != 'struct' else '{...}')


# immutable structs: binary layout, no unversioned header (UScriptStruct::UseBinarySerialization)
BINARY = {
    'Vector': '<3f', 'Vector2D': '<2f', 'Vector4': '<4f', 'IntPoint': '<2i', 'IntVector': '<3i', 'Color': '<4B',
    'LinearColor': '<4f', 'Quat': '<4f', 'Rotator': '<3f', 'Plane': '<4f', 'Matrix': '<16f', 'Box': '<6fB',
    'Box2D': '<4fB', 'BoxSphereBounds': '<7f', 'Sphere': '<4f', 'Guid': '<4I', 'Transform': '<10f', 'TwoVectors': '<6f',
    'FrameNumber': '<i', 'DateTime': '<q', 'Timespan': '<q', 'RichCurveKey': '<3B6f', 'SimpleCurveKey': '<2f',
    'IntVector4': '<4i', 'Vector_NetQuantize': '<3f', 'Vector_NetQuantize10': '<3f', 'Vector_NetQuantize100': '<3f',
    'Vector_NetQuantizeNormal': '<3f', 'FloatInterval': '<2f', 'Int32Interval': '<2i', 'PackedNormal': '<4B',
    'PackedRGB10A2N': '<I', 'PackedRGBA16N': '<4H', 'Vector3f': '<3f', 'Vector2f': '<2f', 'Vector4f': '<4f',
}
VFX1 = 0x56465831


class Reader:
    def __init__(self, usmap, names, data, pos=0, end=None, imports=None, natives=None):
        self.u, self.names, self.d, self.p = usmap, names, data, pos
        self.end = len(data) if end is None else end
        self.imports = imports
        self.natives = dict(NATIVES)
        if natives:
            self.natives.update(natives)
        self.trace = []

    # --- primitives
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
        idx, num = self.unpack('<II')
        i = idx & 0x3fffffff
        if i >= len(self.names):
            raise ParseError('bad name index %d at %d in %s' % (i, self.p - 8, '/'.join(self.trace[-6:])))
        s = self.names[i]
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

    # --- unversioned header
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

    # --- structs
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
        if sname in BINARY:
            v = self.unpack(BINARY[sname])
            return V('native', sname, start, self.p - start, list(v))
        return self.props(sname)

    def props(self, sname):
        """A property stream of `sname` (class or struct): header then values. Returns V('struct')."""
        start = self.p
        self.trace.append(sname)
        try:
            out = {}
            for idx, zero in self.header():
                prop, elem, owner = self.u.prop_at(sname, idx)
                if prop is None:
                    raise ParseError('%s has no property at index %d (at %d)' % (sname, idx, self.p))
                key = prop.name if prop.array_dim == 1 else '%s[%d]' % (prop.name, elem)
                self.trace.append(key)
                try:
                    out[key] = self.zero_value(prop.ptype) if zero else self.value(prop.ptype)
                finally:
                    self.trace.pop()
            return V('struct', sname, start, self.p - start, out)
        finally:
            self.trace.pop()

    def zero_value(self, pt):
        return V('prim', pt.type, self.p, 0, 0, zero=True)

    # --- values
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
        if t in ('StrProperty', 'Utf8StrProperty', 'AnsiStrProperty'):
            s = self.fstring()
            return V('str', t, at, self.p - at, s)
        if t == 'EnumProperty':
            inner = self.value(pt.inner)
            vals = self.u.enums.get(pt.enum, [])
            iv = inner.value
            nm = vals[iv] if isinstance(iv, int) and 0 <= iv < len(vals) else iv
            return V('enum', pt.enum, at, self.p - at, nm)
        if t in ('ObjectProperty', 'ClassProperty', 'WeakObjectProperty', 'InterfaceProperty'):
            return V('obj', t, at, 4, self.i32())
        if t == 'LazyObjectProperty':
            return V('obj', t, at, 16, self.raw(16).hex())
        if t in ('SoftObjectProperty', 'AssetObjectProperty', 'SoftClassProperty'):
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
            return V('text', t, at, 0, self.text()) if True else None
        if t == 'DelegateProperty':
            o = self.i32(); fn = self.name()
            return V('prim', t, at, 12, (o, fn))
        if t == 'MulticastDelegateProperty':
            n = self.i32(); items = [(self.i32(), self.name()) for _ in range(n)]
            return V('prim', t, at, self.p - at, items)
        if t == 'FieldPathProperty':
            n = self.i32(); path = [self.name() for _ in range(n)]; owner = self.i32()
            return V('prim', t, at, self.p - at, (path, owner))
        raise ParseError('cannot read a %s at %d' % (t, at))

    def text(self):
        flags = self.u32()
        hist = self.unpack('<b')[0]
        if hist == -1:
            has = self.i32()
            return ('none', self.fstring() if has else None)
        if hist == 0:
            return ('base', self.fstring(), self.fstring(), self.fstring())
        if hist == 11:   # StringTableEntry
            return ('table', self.name(), self.fstring())
        raise ParseError('FText history %d at %d' % (hist, self.p))


# ---------------------------------------------------------------------------------------------------------------
# native struct serializers

def _soft_path(r, s):
    return (r.name(), r.fstring())


def _per_platform(fmt):
    def f(r, s):
        cooked = r.u32()
        v = r.unpack(fmt)[0]
        if not cooked:
            n = r.i32()
            for _ in range(n):
                r.name(); r.unpack(fmt)
        return v
    return f


def _vfx1_envelope(r):
    """SQEX 'VFX1' type envelope written after every FNiagaraTypeDefinition: type hash, version, UnderlyingType, flags."""
    at = r.p
    if r.p + 4 > r.end or struct.unpack_from('<I', r.d, r.p)[0] != VFX1:
        return None
    r.p += 4
    h, ver, utype, res = r.unpack('<IHHI')
    return {'at': at, 'hash': h, 'ver': ver, 'utype': utype, 'res': res}


def _type_definition(r, s):
    td = r.props('NiagaraTypeDefinition')
    return {'props': td, 'vfx1': _vfx1_envelope(r)}


def _vfx1_base(r, s):
    """FNiagaraVariableBase: FName, then the type definition (property stream + VFX1 envelope)."""
    name = r.name()
    td = _type_definition(r, 'NiagaraTypeDefinition')
    return {'Name': name, 'vfx1': td['vfx1']}


def _niagara_variable(r, s):
    out = _vfx1_base(r, s)
    n = r.i32()
    if n < 0 or n > 1 << 20:
        raise ParseError('bad FNiagaraVariable data size %d at %d' % (n, r.p - 4))
    out['data_at'] = r.p
    out['data'] = r.raw(n)
    return out


def _niagara_variable_with_offset(r, s):
    out = _vfx1_base(r, s)
    out['Offset'] = r.i32()
    return out


VFX0 = 0x56465830   # 'VFX0': a frozen memory image (UE FMemoryImage) of an SQEX object, e.g. an inline data interface
KHCV = 0x5643484B   # 'KHCV': the same kind of image at the start of a NiagaraSystem export


def memory_image(r):
    """magic, u32 size, u16 alignment, u16 padding, padding bytes, image, then FMemoryImageResult::SaveToArchive tables:
    vtables (u64 type hash, patches (vtable offset, offset)), script names and minimal names (FName, offsets)."""
    at = r.p
    magic = r.u32()
    extra = None
    if magic == KHCV:
        extra = r.u32()          # 'KHCV' + u32 is a marker; the image itself has no magic
    size = r.u32()
    align, pad = r.unpack('<HH')
    r.raw(pad)
    image_at = r.p
    image = r.raw(size)
    nv, ns, nm = r.unpack('<III')
    vtables = []
    for _ in range(nv):
        h, n = r.unpack('<QI')
        vtables.append((h, [r.unpack('<II') for _ in range(n)]))
    snames, mnames = [], []
    for lst, cnt in ((snames, ns), (mnames, nm)):
        for _ in range(cnt):
            nmv = r.name(); n = r.u32()
            lst.append((nmv, [r.u32() for _ in range(n)]))
    return {'at': at, 'magic': magic, 'extra': extra, 'size': size, 'align': align, 'pad': pad, 'image_at': image_at, 'image': image,
            'vtables': vtables, 'script_names': snames, 'minimal_names': mnames, 'end': r.p}


def _store(r, s):
    """FNiagaraParameterStore and subclasses: properties, then (SQEX, user parameter stores) an optional 'KHCV' marker."""
    v = r.props(s)
    mark = None
    if r.p + 8 <= r.end and struct.unpack_from('<I', r.d, r.p)[0] == KHCV:
        mark = (r.p, struct.unpack_from('<I', r.d, r.p + 4)[0]); r.p += 8
    return {'props': v, 'khcv': mark}


def _di_info(r, s):
    """FNiagaraScriptDataInterfaceInfo: its properties, then (SQEX) the data interface itself as a VFX0 memory image."""
    v = r.props(s)
    img = None
    if r.p + 4 <= r.end and struct.unpack_from('<I', r.d, r.p)[0] == VFX0:
        img = memory_image(r)
    return {'props': v, 'image': img}


def _gameplay_tag_container(r, s):
    n = r.i32()
    return [r.name() for _ in range(n)]


NATIVES = {
    'SoftObjectPath': _soft_path, 'SoftClassPath': _soft_path, 'StringAssetReference': _soft_path,
    'StringClassReference': _soft_path, 'PerPlatformFloat': _per_platform('<f'), 'PerPlatformInt': _per_platform('<i'),
    'PerPlatformBool': _per_platform('<I'),
    'NiagaraVariableBase': _vfx1_base, 'NiagaraVariable': _niagara_variable, 'NiagaraTypeDefinition': _type_definition,
    'NiagaraVariableWithOffset': _niagara_variable_with_offset,
    'GameplayTagContainer': _gameplay_tag_container,
    'NiagaraScriptDataInterfaceInfo': _di_info,
    'NiagaraUserRedirectionParameterStore': _store,
}


# ---------------------------------------------------------------------------------------------------------------
# helpers

def class_of(z, i, script_paths):
    v = z.exports[i]['cls']
    p = script_paths.get(v)
    return p.split('.')[-1] if p else None


def read_export(u, z, i, script_paths):
    cls = class_of(z, i, script_paths)
    data = z.export_bytes(i)
    r = Reader(u, z.names, data, 0, len(data))
    pre = None
    if len(data) >= 4 and struct.unpack_from('<I', data, 0)[0] == KHCV:
        pre = memory_image(r)
    v = r.props(cls)
    if pre is not None:
        v.value['@image'] = V('native', 'KHCV', pre['at'], pre['end'] - pre['at'], pre)
    return cls, v, r.p, data


def dump(v, indent='', out=None, limit=40, show_at=True):
    out = out if out is not None else sys.stdout
    w = out.write
    at = ('  @%d+%d' % (v.at, v.size)) if show_at else ''
    if v.kind == 'struct':
        w('%s{%s}%s\n' % (indent, v.type, at))
        for k, x in v.value.items():
            w('%s  %s:' % (indent, k))
            if x.kind in ('struct', 'array', 'map', 'set') or (x.kind == 'native' and isinstance(x.value, dict)):
                w('\n'); dump(x, indent + '    ', out, limit, show_at)
            else:
                w(' '); dump(x, '', out, limit, show_at)
    elif v.kind in ('array', 'set'):
        w('%s[%s x%d]%s\n' % (indent, v.type, len(v.value), at))
        for k, x in enumerate(v.value[:limit]):
            w('%s  [%d]' % (indent, k))
            if x.kind in ('struct', 'array', 'map', 'set') or (x.kind == 'native' and isinstance(x.value, dict)):
                w('\n'); dump(x, indent + '    ', out, limit, show_at)
            else:
                w(' '); dump(x, '', out, limit, show_at)
        if len(v.value) > limit:
            w('%s  ... %d more\n' % (indent, len(v.value) - limit))
    elif v.kind == 'map':
        w('%s{map x%d}%s\n' % (indent, len(v.value), at))
        for k, (a, b) in enumerate(v.value[:limit]):
            w('%s  key:' % indent); dump(a, '', out, limit, show_at) if a.kind not in ('struct', 'array') else (w('\n'), dump(a, indent + '    ', out, limit, show_at))
            w('%s  val:' % indent)
            if b.kind in ('struct', 'array', 'map', 'set') or (b.kind == 'native' and isinstance(b.value, dict)):
                w('\n'); dump(b, indent + '    ', out, limit, show_at)
            else:
                w(' '); dump(b, '', out, limit, show_at)
    elif v.kind == 'native' and isinstance(v.value, dict):
        w('%s<%s>%s\n' % (indent, v.type, at))
        for k, x in v.value.items():
            if isinstance(x, V):
                w('%s  %s:' % (indent, k))
                if x.kind in ('struct', 'array', 'map', 'set'):
                    w('\n'); dump(x, indent + '    ', out, limit, show_at)
                else:
                    w(' '); dump(x, '', out, limit, show_at)
            elif k == 'data':
                w('%s  data: %s\n' % (indent, x.hex() if len(x) <= 64 else x[:64].hex() + '...(%d)' % len(x)))
            else:
                w('%s  %s: %r\n' % (indent, k, x))
    else:
        val = v.value
        if isinstance(val, float):
            val = round(val, 6)
        elif isinstance(val, list) and val and isinstance(val[0], float):
            val = [round(x, 5) for x in val]
        w('%s%r%s%s\n' % (indent, val, ' (zero)' if v.zero else '', at))


