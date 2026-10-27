"""Reader for FF7 Remake's cooked UE 4.18 packages (.uasset + .uexp, unversioned): names, imports, exports and their
tagged properties. The material and function graphs that cooking kept, and where each export's data ends.
    pkg418.py <file.uasset> [--props]"""
import struct, sys, os

UE4VER = 517          # 4.18 (VER_UE4_FIX_WIDE_STRING_CRC): unversioned packages are read as this
MAT_INPUTS = {'ExpressionInput', 'ColorMaterialInput', 'ScalarMaterialInput', 'VectorMaterialInput', 'Vector2MaterialInput',
              'MaterialAttributesInput', 'ShadingModelMaterialInput'}


class R:
    def __init__(self, data, pos=0):
        self.d, self.p = data, pos

    def i32(self):
        v = struct.unpack_from('<i', self.d, self.p)[0]; self.p += 4; return v

    def u32(self):
        v = struct.unpack_from('<I', self.d, self.p)[0]; self.p += 4; return v

    def i64(self):
        v = struct.unpack_from('<q', self.d, self.p)[0]; self.p += 8; return v

    def u64(self):
        v = struct.unpack_from('<Q', self.d, self.p)[0]; self.p += 8; return v

    def u16(self):
        v = struct.unpack_from('<H', self.d, self.p)[0]; self.p += 2; return v

    def u8(self):
        v = self.d[self.p]; self.p += 1; return v

    def f32(self):
        v = struct.unpack_from('<f', self.d, self.p)[0]; self.p += 4; return v

    def raw(self, n):
        v = self.d[self.p:self.p + n]; self.p += n; return v

    def guid(self):
        return self.raw(16).hex()

    def fstr(self):
        n = self.i32()
        if n == 0:
            return ''
        if n > 0:
            s = self.d[self.p:self.p + n - 1].decode('latin-1'); self.p += n; return s
        n = -n
        s = self.d[self.p:self.p + 2 * (n - 1)].decode('utf-16-le'); self.p += 2 * n; return s


class Package:
    def __init__(self, path):
        base = path[:-7] if path.endswith('.uasset') else path
        head = open(base + '.uasset', 'rb').read()
        exp = open(base + '.uexp', 'rb').read() if os.path.exists(base + '.uexp') else b''
        self.header_size = len(head)
        d = head + exp
        self.d = d
        self.path = base
        r = R(d)
        assert r.u32() == 0x9E2A83C1
        legacy = r.i32()
        if legacy != -4:
            r.i32()
        ver = r.i32()
        self.ver = ver if ver else UE4VER
        r.i32()
        n = r.i32()
        for _ in range(n):
            r.guid(); r.i32()
        self.total_header = r.i32()
        r.fstr()
        self.flags = r.u32()
        name_count, name_off = r.i32(), r.i32()
        cooked = bool(self.flags & 0x80000000)
        if self.ver >= 516 and not cooked:
            r.fstr()
        if self.ver >= 459:
            r.i32(); r.i32()
        exp_count, exp_off, imp_count, imp_off = r.i32(), r.i32(), r.i32(), r.i32()
        r2 = R(d, name_off)
        self.names = []
        for _ in range(name_count):
            self.names.append(r2.fstr())
            if self.ver >= 504:
                r2.u16(); r2.u16()
        r2 = R(d, imp_off)
        self.imports = []
        for _ in range(imp_count):
            cp, cn, outer, on = self.fname(r2), self.fname(r2), r2.i32(), self.fname(r2)
            self.imports.append((cp, cn, outer, on))
        r2 = R(d, exp_off)
        self.exports = []
        for _ in range(exp_count):
            e = {}
            e['class'], e['super'] = r2.i32(), r2.i32()
            if self.ver >= 508:
                e['template'] = r2.i32()
            e['outer'] = r2.i32()
            e['name'] = self.fname(r2)
            e['flags'] = r2.u32()
            if self.ver >= 511:
                e['size'], e['off'] = r2.i64(), r2.i64()
            else:
                e['size'], e['off'] = r2.i32(), r2.i32()
            r2.i32(); r2.i32(); r2.i32(); r2.guid(); r2.u32()
            if self.ver >= 365:
                r2.i32()
            if self.ver >= 485:
                r2.i32()
            if self.ver >= 507:
                for _ in range(5):
                    r2.i32()
            self.exports.append(e)
        for e in (self.exports if not (self.flags & 0x2000) else []):
            rr = R(d, e['off'])
            try:
                e['props'] = self.tagged(rr, e['off'] + e['size'])
            except Exception as ex:
                # (an export whose data is not tagged properties as read here)
                e['props'], e['error'] = [], str(ex)
            e['props_end'] = rr.p

    def fname(self, r):
        i, n = r.i32(), r.i32()
        s = self.names[i] if 0 <= i < len(self.names) else '?%d' % i
        return s if n == 0 else '%s_%d' % (s, n - 1)

    def ref(self, i):
        if i == 0:
            return None
        if i > 0:
            return 'E%d:%s' % (i - 1, self.exports[i - 1]['name'])
        imp = self.imports[-i - 1]
        return 'I:%s' % imp[3]

    def import_path(self, i):
        parts = []
        while i < 0:
            imp = self.imports[-i - 1]
            parts.append(imp[3])
            i = imp[2]
        return '.'.join(reversed(parts))

    def classname(self, e):
        c = e['class']
        if c < 0:
            return self.imports[-c - 1][3]
        if c > 0:
            return self.exports[c - 1]['name']
        return '?'

    def tagged(self, r, end):
        props = []
        while r.p < end:
            name = self.fname(r)
            if name == 'None':
                break
            typ = self.fname(r)
            size = r.i32()
            idx = r.i32()
            extra = None
            if typ == 'StructProperty':
                extra = self.fname(r)
                if self.ver >= 441:
                    r.guid()
            elif typ == 'BoolProperty':
                extra = r.u8()
            elif typ in ('ByteProperty', 'EnumProperty'):
                extra = self.fname(r)
            elif typ in ('ArrayProperty', 'SetProperty'):
                extra = self.fname(r)
            elif typ == 'MapProperty':
                extra = (self.fname(r), self.fname(r))
            if self.ver >= 503:
                if r.u8():
                    r.guid()
            start = r.p
            try:
                val = self.value(r, typ, extra, size)
            except Exception as ex:
                val = '<?%s>' % ex
            r.p = start + size
            props.append((name, typ, idx, val))
        return props

    def value(self, r, typ, extra, size):
        if typ == 'BoolProperty':
            return bool(extra)
        if typ == 'IntProperty':
            return r.i32()
        if typ == 'UInt32Property':
            return r.u32()
        if typ == 'FloatProperty':
            return r.f32()
        if typ == 'StrProperty':
            return r.fstr()
        if typ == 'NameProperty':
            return self.fname(r)
        if typ in ('ObjectProperty', 'ClassProperty'):
            return self.ref(r.i32())
        if typ in ('SoftObjectProperty', 'AssetObjectProperty'):
            return self.fname(r) + ':' + r.fstr()
        if typ == 'ByteProperty':
            return r.u8() if extra == 'None' or size == 1 else self.fname(r)
        if typ == 'EnumProperty':
            return self.fname(r)
        if typ == 'TextProperty':
            return '<text>'
        if typ == 'StructProperty':
            return self.struct(r, extra, size)
        if typ == 'ArrayProperty':
            n = r.i32()
            if extra == 'StructProperty':
                self.fname(r); self.fname(r); r.i32(); r.i32()
                sname = self.fname(r)
                if self.ver >= 441:
                    r.guid()
                if self.ver >= 503 and r.u8():
                    r.guid()
                return [self.struct(r, sname, None) for _ in range(n)]
            return [self.value(r, extra, None, None) for _ in range(n)]
        return '<%s %d bytes>' % (typ, size or 0)

    def struct(self, r, sname, size):
        if sname in MAT_INPUTS:
            # cooked: the expression reference, output index, input name, mask bits, and the expression's name
            v = {'from': self.ref(r.i32()), 'out': r.i32(), 'name': self.fname(r), 'mask': (r.i32(), r.i32(), r.i32(), r.i32(), r.i32())}
            v['ename'] = self.fname(r)
            if sname != 'ExpressionInput':
                v['useconst'] = r.i32()
                if sname == 'ScalarMaterialInput':
                    v['const'] = r.f32()
                elif sname == 'ColorMaterialInput':
                    v['const'] = r.u32()
                elif sname == 'VectorMaterialInput':
                    v['const'] = (r.f32(), r.f32(), r.f32())
                elif sname == 'Vector2MaterialInput':
                    v['const'] = (r.f32(), r.f32())
                elif sname == 'ShadingModelMaterialInput':
                    v['const'] = r.u32()
            return v
        if sname in ('Vector', 'Rotator'):
            return (r.f32(), r.f32(), r.f32())
        if sname in ('LinearColor', 'Vector4', 'Quat'):
            return (r.f32(), r.f32(), r.f32(), r.f32())
        if sname == 'Vector2D':
            return (r.f32(), r.f32())
        if sname == 'Color':
            return r.u32()
        if sname == 'Guid':
            return r.guid()
        if sname == 'IntPoint':
            return (r.i32(), r.i32())
        return {n: v for n, t, i, v in self.tagged(r, len(self.d))}


def show(path, props=False):
    pk = Package(path)
    print('%s: ver %d, flags %08x, %d names, %d imports, %d exports, header %d' % (os.path.basename(path), pk.ver, pk.flags, len(pk.names), len(pk.imports), len(pk.exports), pk.header_size))
    for k, e in enumerate(pk.exports):
        print('E%d %s %s  [%d..%d) props end %d (%d bytes after)' % (k, pk.classname(e), e['name'], e['off'], e['off'] + e['size'], e['props_end'], e['off'] + e['size'] - e['props_end']))
        if props:
            for n, t, i, v in e['props']:
                s = repr(v)
                print('    %s%s = %s' % (n, '[%d]' % i if i else '', s[:300]))


if __name__ == '__main__':
    show(sys.argv[1], '--props' in sys.argv)
