"""Reader for editor-saved (uncooked) Unreal packages of the End editor (UE4 object version 513, licensee 0): summary,
names, imports, exports, and every export's tagged properties decoded to Python values.

    upkg.py <file.uasset> [export name ...]     prints the imports, the exports and the named exports' properties
"""
import struct, sys

VER_SOFT_OBJECT_PATH = 514
VER_LOCALIZATION_ID = 516
VER_PACKAGE_OWNER = 518


class Reader:
    def __init__(self, data, pos=0):
        self.d = data
        self.p = pos

    def u8(self):
        v = self.d[self.p]; self.p += 1; return v

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

    def f32(self):
        v = struct.unpack_from('<f', self.d, self.p)[0]; self.p += 4; return v

    def floats(self, n):
        v = struct.unpack_from('<%df' % n, self.d, self.p); self.p += 4 * n; return list(v)

    def guid(self):
        v = self.d[self.p:self.p + 16]; self.p += 16; return v.hex()

    def fstr(self):
        n = self.i32()
        if n == 0:
            return ''
        if n < 0:
            s = self.d[self.p:self.p + (-n) * 2].decode('utf-16-le'); self.p += (-n) * 2
        else:
            s = self.d[self.p:self.p + n].decode('latin-1'); self.p += n
        return s.rstrip('\0')


class Obj:
    """A reference to another object of the package (an import or an export) or null."""
    __slots__ = ('pkg', 'index')

    def __init__(self, pkg, index):
        self.pkg, self.index = pkg, index

    @property
    def path(self):
        return self.pkg.path_of(self.index)

    @property
    def name(self):
        return self.pkg.name_of(self.index)

    @property
    def cls(self):
        return self.pkg.class_of(self.index)

    def __bool__(self):
        return self.index != 0

    def __repr__(self):
        return '<%s>' % (self.path if self.index else 'null')


class Struct(dict):
    """A struct value: its fields, and the struct's name in .type."""

    def __init__(self, typ, fields=None):
        super().__init__(fields or {})
        self.type = typ

    def __repr__(self):
        return '%s%s' % (self.type, dict.__repr__(self))


# structs serialized natively (not as tagged properties): name -> reader(r, pkg, size)
def _vec(n):
    return lambda r, pkg, size: r.floats(n)


def _expression_input(r, pkg, size, with_constant=None):
    start = r.p
    v = Struct('ExpressionInput')
    v['Expression'] = Obj(pkg, r.i32())
    v['OutputIndex'] = r.i32()
    v['InputName'] = pkg.fname(r) if pkg.pins_store_fname else r.fstr()
    v['Mask'] = r.i32()
    v['MaskR'], v['MaskG'], v['MaskB'], v['MaskA'] = r.i32(), r.i32(), r.i32(), r.i32()
    left = size - (r.p - start)
    if left >= 4:
        v['UseConstant'] = r.u32() != 0
        left -= 4
        if left == 4 and with_constant == 'color':
            b, g, rr, a = r.d[r.p:r.p + 4]; r.p += 4
            v['Constant'] = [rr, g, b, a]
        elif left > 0 and left % 4 == 0 and with_constant != 'attributes':
            v['Constant'] = r.floats(left // 4)
        elif left > 0:
            v['Raw'] = r.d[r.p:r.p + left].hex(); r.p += left
    elif left > 0:
        v['Raw'] = r.d[r.p:r.p + left].hex(); r.p += left
    return v


NATIVE = {
    'Vector': _vec(3), 'Vector2D': _vec(2), 'Vector4': _vec(4), 'LinearColor': _vec(4), 'Rotator': _vec(3),
    'Quat': _vec(4), 'Plane': _vec(4), 'Box2D': lambda r, pkg, size: r.floats(4) + [r.u8()],
    'Box': lambda r, pkg, size: r.floats(6) + [r.u8()],
    'IntPoint': lambda r, pkg, size: [r.i32(), r.i32()], 'IntVector': lambda r, pkg, size: [r.i32(), r.i32(), r.i32()],
    'Color': lambda r, pkg, size: (lambda b: [b[2], b[1], b[0], b[3]])(r.d[r.p:r.p + 4]) if not setattr(r, 'p', r.p + 4) else None,
    'Guid': lambda r, pkg, size: r.guid(),
    'DateTime': lambda r, pkg, size: r.i64(), 'Timespan': lambda r, pkg, size: r.i64(),
    'ExpressionInput': lambda r, pkg, size: _expression_input(r, pkg, size),
    'ColorMaterialInput': lambda r, pkg, size: _expression_input(r, pkg, size, 'color'),
    'ScalarMaterialInput': lambda r, pkg, size: _expression_input(r, pkg, size, 'float'),
    'VectorMaterialInput': lambda r, pkg, size: _expression_input(r, pkg, size, 'float'),
    'Vector2MaterialInput': lambda r, pkg, size: _expression_input(r, pkg, size, 'float'),
    'MaterialAttributesInput': lambda r, pkg, size: _expression_input(r, pkg, size, 'attributes'),
    'SoftObjectPath': lambda r, pkg, size: pkg.soft_path(r), 'SoftClassPath': lambda r, pkg, size: pkg.soft_path(r),
    'PerPlatformFloat': lambda r, pkg, size: [r.u32(), r.f32()] if size == 8 else r.d[r.p - 0:r.p + size].hex(),
}


class Package:
    def __init__(self, data, label=''):
        self.d = data
        self.label = label
        r = Reader(data)
        assert r.u32() == 0x9E2A83C1, 'not a package'
        self.legacy = r.i32()
        if self.legacy != -4:
            self.ue3 = r.i32()
        self.ue4 = r.i32()
        self.licensee = r.i32()
        self.custom_versions = [(r.guid(), r.i32()) for _ in range(r.i32())]
        self.total_header = r.i32()
        self.folder = r.fstr()
        self.flags = r.u32()
        self.editor = not (self.flags & 0x80000000)
        name_count, name_off = r.i32(), r.i32()
        if self.ue4 >= VER_LOCALIZATION_ID and self.editor:
            self.localization_id = r.fstr()
        self.gather_count, self.gather_off = r.i32(), r.i32()
        export_count, export_off = r.i32(), r.i32()
        import_count, import_off = r.i32(), r.i32()
        self.depends_off = r.i32()
        self.soft_count, self.soft_off = r.i32(), r.i32()
        self.searchable_off = r.i32()
        self.thumb_off = r.i32()
        self.guid = r.guid()
        if self.ue4 >= VER_PACKAGE_OWNER and self.editor:
            r.guid()
            r.guid()
        self.generations = [(r.i32(), r.i32()) for _ in range(r.i32())]
        self.saved_by = (r.u16(), r.u16(), r.u16(), r.u32(), r.fstr())
        self.compatible = (r.u16(), r.u16(), r.u16(), r.u32(), r.fstr())
        self.compression = r.u32()
        assert r.i32() == 0, 'compressed package'
        self.source = r.u32()
        self.additional = [r.fstr() for _ in range(r.i32())]
        if self.legacy > -7:
            r.i32()
        self.registry_off = r.i32()
        self.bulk_start = r.i64()
        self.world_tile_off = r.i32()
        self.chunks = [r.i32() for _ in range(r.i32())]
        self.preload_count, self.preload_off = r.i32(), r.i32()
        q = Reader(data, name_off)
        self.names = []
        for _ in range(name_count):
            self.names.append(q.fstr())
            q.p += 4
        q = Reader(data, import_off)
        self.imports = []
        for _ in range(import_count):
            class_package = self.fname(q)
            class_name = self.fname(q)
            outer = q.i32()
            name = self.fname(q)
            self.imports.append(dict(class_package=class_package, cls=class_name, outer=outer, name=name))
        q = Reader(data, export_off)
        self.exports = []
        for _ in range(export_count):
            e = dict(cls=q.i32(), sup=q.i32(), template=q.i32(), outer=q.i32(), name=self.fname(q), flags=q.u32(),
                     size=q.i64(), offset=q.i64(), forced=q.i32(), not_client=q.i32(), not_server=q.i32(),
                     package_guid=q.guid(), package_flags=q.u32(), not_always_editor=q.i32(), is_asset=q.i32(),
                     first_dep=q.i32(), sbs=q.i32(), cbs=q.i32(), sbc=q.i32(), cbc=q.i32())
            self.exports.append(e)
        self._props = {}
        # FFrameworkObjectVersion::PinsStoreFName (32): expression inputs keep their input name as an FName
        fw = dict(self.custom_versions).get('3f74fccf8044b043df14919373201d17', -1)
        self.pins_store_fname = fw >= 32

    # names and references ----------------------------------------------------------------------------------------
    def fname(self, r):
        i, num = r.i32(), r.i32()
        s = self.names[i] if 0 <= i < len(self.names) else '?%d' % i
        return s if num == 0 else '%s_%d' % (s, num - 1)

    def soft_path(self, r):
        if self.ue4 < VER_SOFT_OBJECT_PATH:
            return r.fstr()
        a = self.fname(r)
        b = r.fstr()
        return a + (':' + b if b else '')

    def name_of(self, index):
        if index < 0:
            return self.imports[-index - 1]['name']
        if index > 0:
            return self.exports[index - 1]['name']
        return None

    def outer_of(self, index):
        if index < 0:
            return self.imports[-index - 1]['outer']
        if index > 0:
            return self.exports[index - 1]['outer']
        return 0

    def class_of(self, index):
        if index < 0:
            return self.imports[-index - 1]['cls']
        if index > 0:
            c = self.exports[index - 1]['cls']
            return self.name_of(c) if c else 'Class'
        return None

    def path_of(self, index):
        if index == 0:
            return None
        chain = []
        i = index
        while i != 0:
            chain.append(self.name_of(i))
            i = self.outer_of(i)
        chain.reverse()
        if index > 0:
            chain.insert(0, self.package_name)
        out = chain[0]
        for k, part in enumerate(chain[1:]):
            out += ('.' if k == 0 else ':') + part
        return out

    @property
    def package_name(self):
        # the package's own name: the outermost export with no outer is its asset, the folder name says the package
        if self.folder and self.folder != 'None':
            return self.folder
        return self.label or '/Temp/Unknown'

    def export_index(self, name):
        for i, e in enumerate(self.exports):
            if e['name'] == name:
                return i + 1
        return None

    def children(self, index):
        return [i + 1 for i, e in enumerate(self.exports) if e['outer'] == index]

    # properties --------------------------------------------------------------------------------------------------
    def props(self, index):
        """The tagged properties of export `index` (1-based): {name: value} (static arrays: name[i])."""
        if index in self._props:
            return self._props[index]
        e = self.exports[index - 1]
        r = Reader(self.d, e['offset'])
        end = e['offset'] + e['size']
        out = self._tagged(r, end)
        out['_end'] = r.p - e['offset']
        out['_size'] = e['size']
        self._props[index] = out
        return out

    def _tagged(self, r, end):
        out = Struct('')
        while r.p < end:
            name = self.fname(r)
            if name == 'None':
                break
            typ = self.fname(r)
            size = r.i32()
            aidx = r.i32()
            extra = {}
            if typ == 'StructProperty':
                extra['struct'] = self.fname(r)
                r.guid()
            elif typ == 'BoolProperty':
                extra['bool'] = r.u8()
            elif typ in ('ByteProperty', 'EnumProperty'):
                extra['enum'] = self.fname(r)
            elif typ in ('ArrayProperty', 'SetProperty'):
                extra['inner'] = self.fname(r)
            elif typ == 'MapProperty':
                extra['inner'] = self.fname(r)
                extra['value'] = self.fname(r)
            if r.u8():
                r.guid()
            start = r.p
            try:
                v = self._value(r, typ, extra, size, top=True)
            except Exception as ex:
                v = ('?', typ, str(ex))
            r.p = start + size
            key = name if aidx == 0 else '%s[%d]' % (name, aidx)
            if aidx and name in out and '%s[0]' % name not in out:
                out['%s[0]' % name] = out[name]
            out[key] = v
        return out

    def _value(self, r, typ, extra, size, top=False):
        if typ == 'BoolProperty':
            return bool(extra.get('bool')) if top else bool(r.u8())
        if typ == 'IntProperty':
            return r.i32()
        if typ == 'UInt32Property':
            return r.u32()
        if typ == 'Int64Property':
            return r.i64()
        if typ == 'UInt64Property':
            return r.u64()
        if typ == 'Int16Property':
            return struct.unpack_from('<h', r.d, r.p)[0] if not setattr(r, 'p', r.p + 2) else None
        if typ == 'UInt16Property':
            return r.u16()
        if typ == 'Int8Property':
            v = struct.unpack_from('<b', r.d, r.p)[0]; r.p += 1; return v
        if typ == 'FloatProperty':
            return r.f32()
        if typ == 'DoubleProperty':
            v = struct.unpack_from('<d', r.d, r.p)[0]; r.p += 8; return v
        if typ == 'NameProperty':
            return self.fname(r)
        if typ == 'StrProperty':
            return r.fstr()
        if typ == 'TextProperty':
            return self._text(r, size)
        if typ in ('ObjectProperty', 'ClassProperty', 'WeakObjectProperty', 'LazyObjectProperty', 'InterfaceProperty'):
            return Obj(self, r.i32())
        if typ in ('SoftObjectProperty', 'SoftClassProperty', 'AssetObjectProperty'):
            return self.soft_path(r)
        if typ in ('ByteProperty',):
            if not top:
                return r.u8()
            if extra.get('enum') and extra['enum'] != 'None':
                return self.fname(r)
            return r.u8()
        if typ == 'EnumProperty':
            return self.fname(r)
        if typ == 'StructProperty':
            return self._struct(r, extra.get('struct'), size)
        if typ in ('ArrayProperty', 'SetProperty'):
            start = r.p
            if typ == 'SetProperty':
                r.i32()   # removed
            n = r.i32()
            inner = extra['inner']
            if inner == 'StructProperty':
                # the inner tag
                self.fname(r)
                self.fname(r)
                isize = r.i64()
                sname = self.fname(r)
                r.guid()
                if r.u8():
                    r.guid()
                each = isize // n if n else 0
                out = []
                for _ in range(n):
                    s = r.p
                    out.append(self._struct(r, sname, each if sname in NATIVE else None))
                    if sname in NATIVE and each:
                        r.p = s + each
                return out
            if inner == 'ByteProperty':
                left = size - (r.p - start)
                if left == n:
                    v = list(r.d[r.p:r.p + n]); r.p += n; return v
                return [self.fname(r) for _ in range(n)]
            if inner == 'BoolProperty':
                return [bool(r.u8()) for _ in range(n)]
            return [self._value(r, inner, {}, 0) for _ in range(n)]
        if typ == 'MapProperty':
            r.i32()   # removed
            n = r.i32()
            out = []
            for _ in range(n):
                k = self._value(r, extra['inner'], {}, 0)
                v = self._value(r, extra['value'], {}, 0)
                out.append((k, v))
            return out
        raise ValueError('unknown property type %s' % typ)

    def _struct(self, r, sname, size):
        if sname in NATIVE:
            return NATIVE[sname](r, self, size if size is not None else 0)
        s = self._tagged(r, len(self.d))
        s.type = sname
        return s

    def _text(self, r, size):
        start = r.p
        flags = r.u32()
        history = struct.unpack_from('<b', r.d, r.p)[0]; r.p += 1
        if history == -1:
            has = r.u32()
            return r.fstr() if has else ''
        if history == 0:
            ns = r.fstr(); key = r.fstr(); src = r.fstr()
            return src
        r.p = start + size
        return ('text', history)


def summarize(p):
    print('package', p.package_name, 'ue4', p.ue4, 'licensee', p.licensee, 'flags %x' % p.flags, 'saved by', p.saved_by)
    for i, im in enumerate(p.imports):
        print('  import %d %s %s (outer %d)' % (-i - 1, im['cls'], p.path_of(-i - 1), im['outer']))
    for i, e in enumerate(p.exports):
        print('  export %d %s %s size %d' % (i + 1, p.class_of(i + 1), p.path_of(i + 1), e['size']))


if __name__ == '__main__':
    pk = Package(open(sys.argv[1], 'rb').read())
    summarize(pk)
    for n in sys.argv[2:]:
        idx = pk.export_index(n)
        print('==', n)
        for k, v in pk.props(idx).items():
            print('   ', k, '=', v)
