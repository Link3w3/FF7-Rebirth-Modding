"""A small reader for UE 4.26 editor (uncooked, versioned) packages: names, imports, exports and their tagged properties,
enough to print a material's expression graph (each expression's class, settings and what feeds its inputs, the Custom
nodes' code, what feeds the material's pins).
    uasset_graph.py <file.uasset> [--code]"""
import struct, sys

MAT_INPUTS = {'ExpressionInput', 'ColorMaterialInput', 'ScalarMaterialInput', 'VectorMaterialInput', 'Vector2MaterialInput',
              'ShadingModelMaterialInput', 'MaterialAttributesInput'}


class R:
    def __init__(self, data, pos=0):
        self.d, self.p = data, pos

    def i32(self):
        v = struct.unpack_from('<i', self.d, self.p)[0]; self.p += 4; return v

    def u32(self):
        v = struct.unpack_from('<I', self.d, self.p)[0]; self.p += 4; return v

    def i64(self):
        v = struct.unpack_from('<q', self.d, self.p)[0]; self.p += 8; return v

    def u16(self):
        v = struct.unpack_from('<H', self.d, self.p)[0]; self.p += 2; return v

    def u8(self):
        v = self.d[self.p]; self.p += 1; return v

    def f32(self):
        v = struct.unpack_from('<f', self.d, self.p)[0]; self.p += 4; return v

    def guid(self):
        v = self.d[self.p:self.p + 16]; self.p += 16; return v.hex()

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
        d = open(path, 'rb').read()
        self.d = d
        r = R(d)
        assert r.u32() == 0x9E2A83C1
        legacy = r.i32()
        if legacy != -4:
            r.i32()
        self.ver = r.i32()
        r.i32()
        if legacy <= -2:
            n = r.i32()
            for _ in range(n):
                r.guid(); r.i32()
        r.i32()  # total header size
        r.fstr()  # folder
        self.flags = r.u32()
        name_count, name_off = r.i32(), r.i32()
        editor = not (self.flags & 0x80000000)
        if self.ver >= 516 and editor:
            r.fstr()
        if self.ver >= 459:
            r.i32(); r.i32()
        exp_count, exp_off, imp_count, imp_off = r.i32(), r.i32(), r.i32(), r.i32()
        # names
        r2 = R(d, name_off)
        self.names = []
        for _ in range(name_count):
            self.names.append(r2.fstr())
            if self.ver >= 504:
                r2.u16(); r2.u16()
        # imports
        r2 = R(d, imp_off)
        self.imports = []
        for _ in range(imp_count):
            cp, cn, outer, on = self.fname(r2), self.fname(r2), r2.i32(), self.fname(r2)
            if self.ver >= 520 and editor:
                self.fname(r2)
            self.imports.append((cp, cn, outer, on))
        # exports
        r2 = R(d, exp_off)
        self.exports = []
        for _ in range(exp_count):
            e = {}
            e['class'], e['super'] = r2.i32(), r2.i32()
            if self.ver >= 508:
                r2.i32()
            e['outer'] = r2.i32()
            e['name'] = self.fname(r2)
            r2.u32()
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
        for e in self.exports:
            e['props'] = self.tagged(R(d, e['off']), e['off'] + e['size'])

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
        if typ == 'ObjectProperty' or typ == 'ClassProperty':
            return self.ref(r.i32())
        if typ == 'SoftObjectProperty':
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
                # the inner tag
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
        # a struct of tagged properties
        return {n: v for n, t, i, v in self.tagged(r, len(self.d))}


def show(path, code=False):
    pk = Package(path)
    for k, e in enumerate(pk.exports):
        cls = pk.classname(e)
        print('E%d %s %s' % (k, cls, e['name']))
        for n, t, i, v in e['props']:
            if n in ('MaterialExpressionEditorX', 'MaterialExpressionEditorY', 'MaterialExpressionGuid', 'ExpressionGUID', 'Material',
                     'StateId', 'bCollapsed', 'Desc', 'Outputs'):
                continue
            if n == 'Code' and not code:
                v = '<%d chars>' % len(v)
            if isinstance(v, dict) and 'from' in v:
                if v['from'] is None and not v.get('useconst'):
                    continue
                v = '<- %s[%d]%s' % (v['from'], v['out'], (' const=%s' % (v.get('const'),)) if v.get('useconst') else '')
            elif isinstance(v, list) and v and isinstance(v[0], dict):
                v = [{kk: ('<- %s[%d]' % (vv['from'], vv['out']) if isinstance(vv, dict) and 'from' in vv else vv) for kk, vv in x.items()} for x in v]
            s = repr(v)
            print('    %s%s = %s' % (n, '[%d]' % i if i else '', s if (code and n == 'Code') else s[:300]))


if __name__ == '__main__':
    show(sys.argv[1], '--code' in sys.argv)
