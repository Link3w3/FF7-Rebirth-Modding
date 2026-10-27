"""Reader for .usmap type mappings (UE4SS / UnrealMappingsDumper format), used to read unversioned cooked properties.

    usmap.py <file.usmap> [StructName ...]     prints the schema of the named structs/classes (with supers)
"""
import struct, sys

PT = ['ByteProperty', 'BoolProperty', 'IntProperty', 'FloatProperty', 'ObjectProperty', 'NameProperty', 'DelegateProperty',
      'DoubleProperty', 'ArrayProperty', 'StructProperty', 'StrProperty', 'TextProperty', 'InterfaceProperty',
      'MulticastDelegateProperty', 'WeakObjectProperty', 'LazyObjectProperty', 'AssetObjectProperty', 'SoftObjectProperty',
      'UInt64Property', 'UInt32Property', 'UInt16Property', 'Int64Property', 'Int16Property', 'Int8Property', 'MapProperty',
      'SetProperty', 'EnumProperty', 'FieldPathProperty', 'OptionalProperty', 'Utf8StrProperty', 'AnsiStrProperty']


class PropType:
    __slots__ = ('type', 'inner', 'value', 'struct', 'enum')

    def __init__(self, typ, inner=None, value=None, struct=None, enum=None):
        self.type, self.inner, self.value, self.struct, self.enum = typ, inner, value, struct, enum

    def __repr__(self):
        if self.type == 'StructProperty':
            return 'Struct<%s>' % self.struct
        if self.type == 'EnumProperty':
            return 'Enum<%s:%r>' % (self.enum, self.inner)
        if self.type in ('ArrayProperty', 'SetProperty', 'OptionalProperty'):
            return '%s<%r>' % (self.type[:-8], self.inner)
        if self.type == 'MapProperty':
            return 'Map<%r,%r>' % (self.inner, self.value)
        return self.type[:-8]


class Prop:
    __slots__ = ('index', 'array_dim', 'name', 'ptype')

    def __init__(self, index, array_dim, name, ptype):
        self.index, self.array_dim, self.name, self.ptype = index, array_dim, name, ptype

    def __repr__(self):
        return '%d%s %s: %r' % (self.index, ('[%d]' % self.array_dim) if self.array_dim > 1 else '', self.name, self.ptype)


class Struct:
    __slots__ = ('name', 'super', 'count', 'props', 'by_index')

    def __init__(self, name, sup, count, props):
        self.name, self.super, self.count, self.props = name, sup, count, props
        self.by_index = {}
        for p in props:
            for k in range(p.array_dim):
                self.by_index[p.index + k] = (p, k)


class Usmap:
    def __init__(self, path):
        d = open(path, 'rb').read()
        magic, ver = struct.unpack_from('<HB', d, 0)
        assert magic == 0x30C4, 'not a usmap'
        p = 3
        if ver >= 1:
            has_versioning = struct.unpack_from('<i', d, p)[0]; p += 4
            if has_versioning:
                raise NotImplementedError('usmap with package versioning')
        comp, csize, dsize = struct.unpack_from('<BII', d, p); p += 9
        if comp != 0:
            raise NotImplementedError('compressed usmap (method %d)' % comp)
        self.version = ver
        body = d[p:p + dsize]
        self._d, self._p = body, 0
        n = self._u32()
        names = []
        for _ in range(n):
            ln = self._u16() if ver >= 2 else self._u8()
            names.append(body[self._p:self._p + ln].decode('utf-8', 'replace')); self._p += ln
        self.names = names
        self.enums = {}
        for _ in range(self._u32()):
            en = names[self._u32()]
            cnt = self._u16() if ver >= 3 else self._u8()
            self.enums[en] = [names[self._u32()] for _ in range(cnt)]
        self.structs = {}
        for _ in range(self._u32()):
            sn = names[self._u32()]
            si = self._u32()
            sup = None if si == 0xFFFFFFFF else names[si]
            count = self._u16()
            ser = self._u16()
            props = []
            for _ in range(ser):
                idx = self._u16(); dim = self._u8(); pn = names[self._u32()]
                props.append(Prop(idx, dim, pn, self._ptype()))
            self.structs[sn] = Struct(sn, sup, count, props)
        del self._d

    def _u8(self):
        v = self._d[self._p]; self._p += 1; return v

    def _u16(self):
        v = struct.unpack_from('<H', self._d, self._p)[0]; self._p += 2; return v

    def _u32(self):
        v = struct.unpack_from('<I', self._d, self._p)[0]; self._p += 4; return v

    def _ptype(self):
        t = PT[self._u8()] if True else None
        if t == 'EnumProperty':
            inner = self._ptype(); en = self.names[self._u32()]
            return PropType(t, inner=inner, enum=en)
        if t == 'StructProperty':
            return PropType(t, struct=self.names[self._u32()])
        if t in ('ArrayProperty', 'SetProperty', 'OptionalProperty'):
            return PropType(t, inner=self._ptype())
        if t == 'MapProperty':
            k = self._ptype(); v = self._ptype()
            return PropType(t, inner=k, value=v)
        return PropType(t)

    def chain(self, name):
        """[Struct, super, super's super, ...]"""
        out = []
        while name is not None:
            s = self.structs.get(name)
            if s is None:
                raise KeyError('no %s in the usmap' % name)
            out.append(s)
            name = s.super
        return out

    def prop_at(self, name, index):
        """(Prop, element, owner struct name) for a schema index of `name` counting its own properties first."""
        for s in self.chain(name):
            if index < s.count:
                hit = s.by_index.get(index)
                return (hit[0], hit[1], s.name) if hit else (None, 0, s.name)
            index -= s.count
        return (None, 0, None)

    def total(self, name):
        return sum(s.count for s in self.chain(name))


if __name__ == '__main__':
    u = Usmap(sys.argv[1])
    print('usmap v%d: %d names, %d enums, %d structs' % (u.version, len(u.names), len(u.enums), len(u.structs)))
    for nm in sys.argv[2:]:
        base = 0
        for s in u.chain(nm):
            print('%s (super %s) count %d, indices from %d' % (s.name, s.super, s.count, base))
            for p in s.props:
                print('   %3d %r' % (base + p.index, p))
            base += s.count
