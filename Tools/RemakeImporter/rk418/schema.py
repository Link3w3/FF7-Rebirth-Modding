"""The Remake reflection schema (remake_schema.json, from extract_schema.py) behind the same interface as usmap.Usmap."""
import json, os

TYPE = {'Byte': 'ByteProperty', 'Int8': 'Int8Property', 'Int16': 'Int16Property', 'Int': 'IntProperty', 'Int64': 'Int64Property',
        'UInt16': 'UInt16Property', 'UInt32': 'UInt32Property', 'UInt64': 'UInt64Property', 'UnsizedInt': 'IntProperty',
        'UnsizedUInt': 'UInt32Property', 'Float': 'FloatProperty', 'Double': 'DoubleProperty', 'Bool': 'BoolProperty',
        'SoftClass': 'SoftObjectProperty', 'WeakObject': 'WeakObjectProperty', 'LazyObject': 'LazyObjectProperty',
        'SoftObject': 'SoftObjectProperty', 'Class': 'ObjectProperty', 'Object': 'ObjectProperty', 'Interface': 'InterfaceProperty',
        'Name': 'NameProperty', 'Str': 'StrProperty', 'Array': 'ArrayProperty', 'Map': 'MapProperty', 'Set': 'SetProperty',
        'Struct': 'StructProperty', 'Delegate': 'DelegateProperty', 'MulticastDelegate': 'MulticastDelegateProperty',
        'Text': 'TextProperty', 'Enum': 'EnumProperty'}
STRUCT_IMMUTABLE = 0x20


class PropType:
    __slots__ = ('type', 'inner', 'value', 'struct', 'enum', 'cls')

    def __init__(self, typ, inner=None, value=None, struct=None, enum=None, cls=None):
        self.type, self.inner, self.value, self.struct, self.enum, self.cls = typ, inner, value, struct, enum, cls

    def __repr__(self):
        if self.type == 'StructProperty':
            return 'Struct<%s>' % self.struct
        if self.type == 'EnumProperty':
            return 'Enum<%s:%r>' % (self.enum, self.inner)
        if self.type in ('ArrayProperty', 'SetProperty'):
            return '%s<%r>' % (self.type[:-8], self.inner)
        if self.type == 'MapProperty':
            return 'Map<%r,%r>' % (self.inner, self.value)
        return self.type[:-8]


class Prop:
    __slots__ = ('index', 'array_dim', 'name', 'ptype', 'flags')

    def __init__(self, index, array_dim, name, ptype, flags=0):
        self.index, self.array_dim, self.name, self.ptype, self.flags = index, array_dim, name, ptype, flags

    def __repr__(self):
        return '%d%s %s: %r' % (self.index, ('[%d]' % self.array_dim) if self.array_dim > 1 else '', self.name, self.ptype)


class Struct:
    __slots__ = ('name', 'super', 'count', 'props', 'by_index', 'flags', 'is_class', 'by_name')

    def __init__(self, name, sup, props, flags=0, is_class=False):
        self.name, self.super, self.props, self.flags, self.is_class = name, sup, props, flags, is_class
        self.by_index, self.by_name = {}, {}
        n = 0
        for p in props:
            for k in range(p.array_dim):
                self.by_index[p.index + k] = (p, k)
            self.by_name[p.name] = p
            n = max(n, p.index + p.array_dim)
        self.count = n


def ptype(d):
    t = TYPE[d['type']]
    if d['type'] == 'Byte' and d.get('enum'):
        return PropType('EnumProperty', inner=PropType('ByteProperty'), enum=d['enum'])
    if t == 'EnumProperty':
        return PropType(t, inner=ptype(d['underlying']), enum=d['enum'])
    if t == 'StructProperty':
        return PropType(t, struct=d['struct'])
    if t in ('ArrayProperty', 'SetProperty'):
        return PropType(t, inner=ptype(d['inner']))
    if t == 'MapProperty':
        return PropType(t, inner=ptype(d['key']), value=ptype(d['value']))
    if t == 'ObjectProperty':
        return PropType(t, cls=d.get('class'))
    return PropType(t)


class Schema:
    def __init__(self, path=None):
        path = path or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'remake_schema.json')
        j = json.load(open(path))
        self.structs, self.enums, self.enum_values = {}, {}, {}
        for kind in ('structs', 'classes'):
            for name, s in j[kind].items():
                props, idx = [], 0
                for d in s['props']:
                    dim = max(1, d['dim'])
                    props.append(Prop(idx, dim, d['name'], ptype(d), d.get('flags', 0)))
                    idx += dim
                self.structs[name] = Struct(name, s['super'], props, s.get('flags', 0), kind == 'classes')
        for name, e in j['enums'].items():
            vals = {}
            for n, v in e['values']:
                vals[v] = n.split('::')[-1]
            self.enum_values[name] = vals
            mx = max(vals) if vals else -1
            self.enums[name] = [vals.get(i, str(i)) for i in range(mx + 1)] if 0 <= mx < 4096 else []

    def immutable(self, name):
        s = self.structs.get(name)
        return bool(s and not s.is_class and s.flags & STRUCT_IMMUTABLE)

    def chain(self, name):
        out = []
        while name is not None:
            s = self.structs.get(name)
            if s is None:
                raise KeyError('no %s in the schema' % name)
            out.append(s)
            name = s.super
        return out

    def prop_at(self, name, index):
        for s in self.chain(name):
            if index < s.count:
                hit = s.by_index.get(index)
                return (hit[0], hit[1], s.name) if hit else (None, 0, s.name)
            index -= s.count
        return (None, 0, None)

    def total(self, name):
        return sum(s.count for s in self.chain(name))

    def find(self, name, prop):
        for s in self.chain(name):
            if prop in s.by_name:
                return s.by_name[prop], s.name
        return None, None
