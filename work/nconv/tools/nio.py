"""Rebirth (UE 5.1 Niagara backported by Square Enix into their 4.26 engine) cooked-data reader and writer.

Reading is rebirth_fx.uprops (unversioned properties driven by the game's .usmap) with everything kept that writing needs:
FNames keep their (name map index, number), strings their encoding, SQEX blocks every byte. Writing is the exact inverse,
so a parsed export can be written back byte for byte, or changed and written.

    nio.py roundtrip <package.uasset> ...     every export read and written back, compared byte for byte
"""
import struct, sys
sys.path[:0] = ['/work/fx1018/editor/Python', '/work/iostore', '/work/cs',
                '/work/fx1018/tools']
from rebirth_fx import uprops, uwrite
from rebirth_fx.uprops import V, ParseError, BINARY, VFX1, VFX0, KHCV

USMAP = '/work/fx1018/Rebirth.usmap'
_usmap = None


def usmap():
    global _usmap
    if _usmap is None:
        from rebirth_fx.usmap import Usmap
        _usmap = Usmap(USMAP)
    return _usmap


class NameStr(str):
    """An FName as text ('Name' or 'Name_3') that remembers its (name map index, number) when read from a package."""
    __slots__ = ('raw',)

    def __new__(cls, s, raw=None):
        o = str.__new__(cls, s)
        o.raw = raw
        return o


class FStr(str):
    """An FString that remembers how it was stored: ('a', byte count incl. null) or ('u', char count incl. null)."""
    __slots__ = ('enc',)

    def __new__(cls, s, enc=None):
        o = str.__new__(cls, s)
        o.enc = enc
        return o


# ----------------------------------------------------------------------------------------------------------------
# reading

def memory_image(r):
    """SQEX frozen memory image (FMemoryImage): magic ('VFX0', or 'KHCV' + u32), u32 size, u16 alignment, u16 padding,
    padding, image, then FMemoryImageResult::SaveToArchive tables (vtables, script names, minimal names)."""
    at = r.p
    magic = r.u32()
    extra = r.u32() if magic == KHCV else None
    size = r.u32()
    align, pad = r.unpack('<HH')
    pad_bytes = r.raw(pad)
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
    return {'at': at, 'magic': magic, 'extra': extra, 'size': size, 'align': align, 'pad': pad, 'pad_bytes': pad_bytes,
            'image_at': image_at, 'image': image, 'vtables': vtables, 'script_names': snames, 'minimal_names': mnames,
            'end': r.p}


def _vfx1_envelope(r):
    if r.p + 4 > r.end or struct.unpack_from('<I', r.d, r.p)[0] != VFX1:
        return None
    at = r.p
    r.p += 4
    h, ver, utype, res = r.unpack('<IHHI')
    return {'at': at, 'hash': h, 'ver': ver, 'utype': utype, 'res': res}


def _type_definition(r, s):
    return {'props': r.props('NiagaraTypeDefinition'), 'vfx1': _vfx1_envelope(r)}


def _var_base(r, s):
    name = r.name()
    return {'Name': name, 'td': _type_definition(r, 'NiagaraTypeDefinition')}


def _var(r, s):
    out = _var_base(r, s)
    n = r.i32()
    if n < 0 or n > 1 << 20:
        raise ParseError('bad FNiagaraVariable data size %d at %d' % (n, r.p - 4))
    out['data_at'] = r.p
    out['data'] = r.raw(n)
    return out


def _var_offset(r, s):
    out = _var_base(r, s)
    out['Offset'] = r.i32()
    return out


def _soft_path(r, s):
    return (r.name(), r.fstring())


def _per_platform(fmt):
    def f(r, s):
        cooked = r.u32()
        v = r.unpack(fmt)[0]
        per = []
        if not cooked:
            for _ in range(r.i32()):
                per.append((r.name(), r.unpack(fmt)[0]))
        return {'cooked': cooked, 'value': v, 'per_platform': per}
    return f


def _store(r, s):
    """FNiagaraUserRedirectionParameterStore: properties, then (SQEX) 'KHCV', u32 n and n (u32 'VFX1', u32) pairs, one per
    user data interface in the store."""
    v = r.props(s)
    mark = None
    if r.p + 8 <= r.end and struct.unpack_from('<I', r.d, r.p)[0] == KHCV:
        n = struct.unpack_from('<I', r.d, r.p + 4)[0]; r.p += 8
        mark = [r.unpack('<II') for _ in range(n)]
        for m, _ in mark:
            if m != VFX1:
                raise ParseError('user store entry magic %08x at %d' % (m, r.p - 8))
    return {'props': v, 'khcv': mark}


def _di_info(r, s):
    v = r.props(s)
    img = None
    if r.p + 4 <= r.end and struct.unpack_from('<I', r.d, r.p)[0] == VFX0:
        img = memory_image(r)
    return {'props': v, 'image': img}


def _tags(r, s):
    return [r.name() for _ in range(r.i32())]


NATIVES = {
    'SoftObjectPath': _soft_path, 'SoftClassPath': _soft_path, 'StringAssetReference': _soft_path,
    'StringClassReference': _soft_path, 'PerPlatformFloat': _per_platform('<f'), 'PerPlatformInt': _per_platform('<i'),
    'PerPlatformBool': _per_platform('<I'),
    'NiagaraVariableBase': _var_base, 'NiagaraVariable': _var, 'NiagaraTypeDefinition': _type_definition,
    'NiagaraVariableWithOffset': _var_offset, 'GameplayTagContainer': _tags,
    'NiagaraScriptDataInterfaceInfo': _di_info, 'NiagaraUserRedirectionParameterStore': _store,
}


class Reader(uprops.Reader):
    def __init__(self, u, names, data, pos=0, end=None):
        super().__init__(u, names, data, pos, end)
        self.natives = dict(NATIVES)

    def name(self):
        idx, num = self.unpack('<II')
        i = idx & 0x3fffffff
        if i >= len(self.names):
            raise ParseError('bad name index %d at %d in %s' % (i, self.p - 8, '/'.join(self.trace[-6:])))
        s = self.names[i]
        return NameStr(s if num == 0 else '%s_%d' % (s, num - 1), (idx, num))

    def fstring(self):
        n = self.i32()
        if n == 0:
            return FStr('', ('a', 0))
        if n < 0:
            if -n > 1 << 20:
                raise ParseError('bad string length %d at %d' % (n, self.p - 4))
            return FStr(self.raw(-n * 2).decode('utf-16-le', 'replace')[:-1], ('u', -n))
        if n > 1 << 20:
            raise ParseError('bad string length %d at %d' % (n, self.p - 4))
        return FStr(self.raw(n)[:-1].decode('latin-1'), ('a', n))


def read_export(z, i, script_paths, u=None):
    """(class name, V of the properties, {'image': KHCV prefix or None, 'tail': bytes after the properties}, raw bytes)"""
    u = u or usmap()
    cls = uprops.class_of(z, i, script_paths)
    data = z.export_bytes(i)
    r = Reader(u, z.names, data, 0, len(data))
    pre = None
    if len(data) >= 4 and struct.unpack_from('<I', data, 0)[0] == KHCV:
        pre = memory_image(r)
    v = r.props(cls)
    return cls, v, {'image': pre, 'tail': data[r.p:], 'props_end': r.p}, data


# ----------------------------------------------------------------------------------------------------------------
# writing

class Writer:
    """Encodes V trees. names: uwrite.Names (the package's name map; names not in it are added at its end).
    exact=True writes FNames with their original (index, number) and strings in their original encoding."""

    def __init__(self, names, u=None, exact=True):
        self.u = u or usmap()
        self.names = names
        self.exact = exact
        self.natives = dict(NATIVE_WRITERS)
        self._schema = {}

    # --- primitives
    def name(self, s):
        raw = getattr(s, 'raw', None)
        if self.exact and raw is not None:
            return struct.pack('<II', *raw)
        return self.names.encode(str(s))

    def fstring(self, s):
        enc = getattr(s, 'enc', None)
        if self.exact and enc is not None:
            kind, n = enc
            if kind == 'a':
                if n == 0:
                    return struct.pack('<i', 0)
                b = str(s).encode('latin-1') + b'\0'
                assert len(b) == n, (s, enc)
                return struct.pack('<i', n) + b
            b = (str(s) + '\0').encode('utf-16-le')
            assert len(b) == 2 * n, (s, enc)
            return struct.pack('<i', -n) + b
        s = str(s)
        if not s:
            return struct.pack('<i', 0)
        try:
            b = s.encode('ascii') + b'\0'
            return struct.pack('<i', len(b)) + b
        except UnicodeEncodeError:
            b = (s + '\0').encode('utf-16-le')
            return struct.pack('<i', -(len(b) // 2)) + b

    # --- schema
    def schema(self, sname):
        sch = self._schema.get(sname)
        if sch is None:
            sch = {}
            for idx, p, k in uwrite.schema(self.u, sname):
                key = p.name if p.array_dim == 1 else '%s[%d]' % (p.name, k)
                sch[key] = (idx, p)
            self._schema[sname] = sch
        return sch

    def props(self, sname, v):
        sch = self.schema(sname)
        items = []
        for key, x in v.value.items():
            if key.startswith('@'):
                continue
            if key not in sch:
                raise KeyError('%s has no property %s' % (sname, key))
            items.append((sch[key][0], key, x))
        items.sort(key=lambda t: t[0])
        out = bytearray(uwrite.header([(idx, x.zero) for idx, key, x in items], self.u.total(sname)))
        for idx, key, x in items:
            if not x.zero:
                out += self.value(sch[key][1].ptype, x)
        return bytes(out)

    def struct(self, sname, x):
        nat = self.natives.get(sname)
        if nat is not None:
            return nat(self, sname, x.value)
        if sname in BINARY:
            return struct.pack(BINARY[sname], *x.value)
        return self.props(sname, x)

    def value(self, pt, x):
        t = pt.type
        val = x.value
        if t == 'BoolProperty':
            return struct.pack('<B', 1 if val else 0)
        if t == 'ByteProperty':
            return struct.pack('<B', val)
        if t == 'Int8Property':
            return struct.pack('<b', val)
        if t == 'Int16Property':
            return struct.pack('<h', val)
        if t == 'UInt16Property':
            return struct.pack('<H', val)
        if t == 'IntProperty':
            return struct.pack('<i', val)
        if t == 'UInt32Property':
            return struct.pack('<I', val)
        if t == 'Int64Property':
            return struct.pack('<q', val)
        if t == 'UInt64Property':
            return struct.pack('<Q', val)
        if t == 'FloatProperty':
            return struct.pack('<f', val)
        if t == 'DoubleProperty':
            return struct.pack('<d', val)
        if t == 'NameProperty':
            return self.name(val)
        if t in ('StrProperty', 'Utf8StrProperty', 'AnsiStrProperty'):
            return self.fstring(val)
        if t == 'EnumProperty':
            vals = self.u.enums.get(pt.enum, [])
            iv = vals.index(val) if isinstance(val, str) and val in vals else val
            return self.value(pt.inner, V('prim', pt.inner.type, 0, 0, iv))
        if t in ('ObjectProperty', 'ClassProperty', 'WeakObjectProperty', 'InterfaceProperty'):
            return struct.pack('<i', val)
        if t == 'LazyObjectProperty':
            return bytes.fromhex(val)
        if t in ('SoftObjectProperty', 'AssetObjectProperty', 'SoftClassProperty'):
            return self.name(val[0]) + self.fstring(val[1])
        if t == 'StructProperty':
            return self.struct(pt.struct, x)
        if t == 'ArrayProperty':
            return struct.pack('<i', len(val)) + b''.join(self.value(pt.inner, y) for y in val)
        if t == 'SetProperty':
            return struct.pack('<ii', 0, len(val)) + b''.join(self.value(pt.inner, y) for y in val)
        if t == 'MapProperty':
            return struct.pack('<ii', 0, len(val)) + b''.join(self.value(pt.inner, a) + self.value(pt.value, b) for a, b in val)
        if t == 'TextProperty':
            return self.text(val)
        if t == 'DelegateProperty':
            return struct.pack('<i', val[0]) + self.name(val[1])
        if t == 'MulticastDelegateProperty':
            return struct.pack('<i', len(val)) + b''.join(struct.pack('<i', o) + self.name(f) for o, f in val)
        if t == 'FieldPathProperty':
            path, owner = val
            return struct.pack('<i', len(path)) + b''.join(self.name(n) for n in path) + struct.pack('<i', owner)
        raise TypeError('cannot write a %s' % t)

    def text(self, val):
        kind = val[0]
        raise TypeError('FText writing not needed yet (%s)' % kind)

    def memory_image(self, m):
        out = bytearray(struct.pack('<I', m['magic']))
        if m['magic'] == KHCV:
            out += struct.pack('<I', m['extra'])
        image = m['image']
        pad_bytes = m.get('pad_bytes', b'\0' * m['pad'])
        out += struct.pack('<IHH', len(image), m['align'], len(pad_bytes)) + pad_bytes + image
        out += struct.pack('<III', len(m['vtables']), len(m['script_names']), len(m['minimal_names']))
        for h, patches in m['vtables']:
            out += struct.pack('<QI', h, len(patches))
            for a, b in patches:
                out += struct.pack('<II', a, b)
        for lst in (m['script_names'], m['minimal_names']):
            for nm, offs in lst:
                out += self.name(nm) + struct.pack('<I', len(offs)) + b''.join(struct.pack('<I', o) for o in offs)
        return bytes(out)


def _w_envelope(w, env):
    if env is None:
        return b''
    return struct.pack('<IIHHI', VFX1, env['hash'], env['ver'], env['utype'], env['res'])


def _w_type_definition(w, s, v):
    return w.props('NiagaraTypeDefinition', v['props']) + _w_envelope(w, v['vfx1'])


def _w_var_base(w, s, v):
    return w.name(v['Name']) + _w_type_definition(w, s, v['td'])


def _w_var(w, s, v):
    return _w_var_base(w, s, v) + struct.pack('<i', len(v['data'])) + v['data']


def _w_var_offset(w, s, v):
    return _w_var_base(w, s, v) + struct.pack('<i', v['Offset'])


def _w_soft_path(w, s, v):
    return w.name(v[0]) + w.fstring(v[1])


def _w_per_platform(fmt):
    def f(w, s, v):
        out = struct.pack('<I', v['cooked']) + struct.pack(fmt, v['value'])
        if not v['cooked']:
            out += struct.pack('<i', len(v['per_platform']))
            for n, x in v['per_platform']:
                out += w.name(n) + struct.pack(fmt, x)
        return out
    return f


def _w_store(w, s, v):
    out = w.props(s, v['props'])
    if v['khcv'] is not None:
        out += struct.pack('<II', KHCV, len(v['khcv'])) + b''.join(struct.pack('<II', a, b) for a, b in v['khcv'])
    return out


def _w_di_info(w, s, v):
    out = w.props(s, v['props'])
    if v['image'] is not None:
        out += w.memory_image(v['image'])
    return out


def _w_tags(w, s, v):
    return struct.pack('<i', len(v)) + b''.join(w.name(n) for n in v)


NATIVE_WRITERS = {
    'SoftObjectPath': _w_soft_path, 'SoftClassPath': _w_soft_path, 'StringAssetReference': _w_soft_path,
    'StringClassReference': _w_soft_path, 'PerPlatformFloat': _w_per_platform('<f'), 'PerPlatformInt': _w_per_platform('<i'),
    'PerPlatformBool': _w_per_platform('<I'),
    'NiagaraVariableBase': _w_var_base, 'NiagaraVariable': _w_var, 'NiagaraTypeDefinition': _w_type_definition,
    'NiagaraVariableWithOffset': _w_var_offset, 'GameplayTagContainer': _w_tags,
    'NiagaraScriptDataInterfaceInfo': _w_di_info, 'NiagaraUserRedirectionParameterStore': _w_store,
}


def write_export(w, cls, v, extra):
    out = bytearray()
    if extra.get('image') is not None:
        out += w.memory_image(extra['image'])
    out += w.props(cls, v)
    out += extra.get('tail', b'')
    return bytes(out)


# ----------------------------------------------------------------------------------------------------------------

def roundtrip(paths, exact=True, verbose=False):
    import os
    from zen import Zen
    import scriptobjs
    spaths, _ = scriptobjs.load()
    total = bad = 0
    for path in paths:
        z = Zen(open(path, 'rb').read())
        names = uwrite.Names(z.names)
        w = Writer(names, exact=exact)
        for i in range(len(z.exports)):
            total += 1
            try:
                cls, v, extra, data = read_export(z, i, spaths)
            except ParseError as ex:
                bad += 1
                print('READ FAIL %s #%d %s: %s' % (os.path.basename(path)[-60:], i, z.exports[i]['name'], str(ex)[:160]))
                continue
            try:
                out = write_export(w, cls, v, extra)
            except Exception as ex:
                bad += 1
                print('WRITE FAIL %s #%d %s %s: %r' % (os.path.basename(path)[-60:], i, z.exports[i]['name'], cls, ex))
                continue
            if out != data:
                bad += 1
                k = next((j for j in range(min(len(out), len(data))) if out[j] != data[j]), min(len(out), len(data)))
                print('DIFF %s #%d %s %s: sizes %d/%d, first difference at %d (props end %d)' % (
                    os.path.basename(path)[-60:], i, z.exports[i]['name'], cls, len(out), len(data), k, extra['props_end']))
            elif verbose:
                print('ok %s #%d %s' % (os.path.basename(path)[-50:], i, cls))
        if names.added:
            print('  names added:', names.added[:10])
    print('%d exports, %d not identical' % (total, bad))
    return bad


if __name__ == '__main__':
    if sys.argv[1] == 'roundtrip':
        sys.exit(1 if roundtrip(sys.argv[2:]) else 0)
