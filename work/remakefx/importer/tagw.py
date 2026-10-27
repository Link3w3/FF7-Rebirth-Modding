"""UE 4.26 tagged property streams, as an editor (uncooked, versioned) package keeps an object's properties, written from
plain Python values with the End editor's schema (end_fx_schema.json: every Cascade class and the structs and enums they
use, from the End editor's own reflection). Part of the Remake Importer's effect converter (rmcascade.py).

Values: dict (a struct's fields by name), list (an array), float/int/bool, str (an FString), Name (an FName), Enum (an
enum value's name), Obj (a reference: resolved by the writer's objref), None (a null reference)."""
import struct


class Name(str):
    """an FName value"""


class Enum(str):
    """an enum value's name (e.g. EDVLF_YZ)"""


class Obj(object):
    """a reference to an object: key is what the package writer resolves (an export key or an import path)"""
    __slots__ = ('key',)

    def __init__(self, key):
        self.key = key

    def __repr__(self):
        return 'Obj(%r)' % (self.key,)


def split_name(s):
    """an FName's text and number the way the engine splits a string (Name_3 -> ('Name', 4))"""
    i = len(s)
    while i > 1 and s[i - 1].isdigit():
        i -= 1
    if i == len(s) or i < 2 or s[i - 1] != '_':
        return s, 0
    digits = s[i:]
    if digits[0] == '0' and len(digits) > 1:
        return s, 0
    v = int(digits)
    if v > 0x7FFFFFFF:
        return s, 0
    return s[:i - 1], v + 1


class Names(object):
    """the package's name table"""

    def __init__(self):
        self.list = []
        self.index = {}

    def add(self, s):
        base, num = split_name(s)
        if base not in self.index:
            self.index[base] = len(self.list)
            self.list.append(base)
        return self.index[base], num

    def ref(self, s):
        return struct.pack('<ii', *self.add(s))


def fstring(s):
    if s == '':
        return struct.pack('<i', 0)
    try:
        b = s.encode('ascii') + b'\0'
        return struct.pack('<i', len(b)) + b
    except UnicodeEncodeError:
        b = s.encode('utf-16-le') + b'\0\0'
        return struct.pack('<i', -(len(b) // 2)) + b


def _f(v, k, d=0.0):
    if not isinstance(v, dict):
        return d
    x = v.get(k, d)
    return d if x is None else x


NATIVE = {
    'Vector': lambda v: struct.pack('<3f', _f(v, 'X'), _f(v, 'Y'), _f(v, 'Z')),
    'Vector2D': lambda v: struct.pack('<2f', _f(v, 'X'), _f(v, 'Y')),
    'Vector4': lambda v: struct.pack('<4f', _f(v, 'X'), _f(v, 'Y'), _f(v, 'Z'), _f(v, 'W')),
    'Plane': lambda v: struct.pack('<4f', _f(v, 'X'), _f(v, 'Y'), _f(v, 'Z'), _f(v, 'W')),
    'Quat': lambda v: struct.pack('<4f', _f(v, 'X'), _f(v, 'Y'), _f(v, 'Z'), _f(v, 'W', 1.0)),
    'Rotator': lambda v: struct.pack('<3f', _f(v, 'Pitch'), _f(v, 'Yaw'), _f(v, 'Roll')),
    'LinearColor': lambda v: struct.pack('<4f', _f(v, 'R'), _f(v, 'G'), _f(v, 'B'), _f(v, 'A')),
    'Color': lambda v: struct.pack('<4B', int(_f(v, 'B', 0)), int(_f(v, 'G', 0)), int(_f(v, 'R', 0)), int(_f(v, 'A', 0))),
    'Guid': lambda v: struct.pack('<4I', int(_f(v, 'A', 0)) & 0xFFFFFFFF, int(_f(v, 'B', 0)) & 0xFFFFFFFF,
                                  int(_f(v, 'C', 0)) & 0xFFFFFFFF, int(_f(v, 'D', 0)) & 0xFFFFFFFF),
    'IntPoint': lambda v: struct.pack('<2i', int(_f(v, 'X', 0)), int(_f(v, 'Y', 0))),
    'IntVector': lambda v: struct.pack('<3i', int(_f(v, 'X', 0)), int(_f(v, 'Y', 0)), int(_f(v, 'Z', 0))),
    'Box': lambda v: NATIVE['Vector'](_f(v, 'Min', {})) + NATIVE['Vector'](_f(v, 'Max', {})) + struct.pack('<B', 1 if _f(v, 'IsValid', 0) else 0),
    'Box2D': lambda v: NATIVE['Vector2D'](_f(v, 'Min', {})) + NATIVE['Vector2D'](_f(v, 'Max', {})) + struct.pack('<B', 1 if _f(v, 'bIsValid', 0) else 0),
    'TwoVectors': lambda v: NATIVE['Vector'](_f(v, 'v1', {})) + NATIVE['Vector'](_f(v, 'v2', {})),
}
PRIM = {'Int': '<i', 'Int8': '<b', 'Int16': '<h', 'Int64': '<q', 'UInt16': '<H', 'UInt32': '<I', 'UInt64': '<Q',
        'Float': '<f', 'Double': '<d'}
TYPE_NAME = {'Int': 'IntProperty', 'Int8': 'Int8Property', 'Int16': 'Int16Property', 'Int64': 'Int64Property',
             'UInt16': 'UInt16Property', 'UInt32': 'UInt32Property', 'UInt64': 'UInt64Property', 'Float': 'FloatProperty',
             'Double': 'DoubleProperty', 'Bool': 'BoolProperty', 'Byte': 'ByteProperty', 'Name': 'NameProperty',
             'Str': 'StrProperty', 'Object': 'ObjectProperty', 'Struct': 'StructProperty', 'Array': 'ArrayProperty',
             'Text': 'TextProperty', 'SoftObject': 'SoftObjectProperty', 'Class': 'ClassProperty'}


def type_name(td):
    t = td['t']
    if t == 'Enum':
        return 'ByteProperty' if td.get('u', 'Byte') == 'Byte' else 'EnumProperty'
    return TYPE_NAME[t]


class Unsupported(Exception):
    pass


class Writer(object):
    def __init__(self, schema, names, objref):
        """schema: end_fx_schema.json loaded; names: Names; objref(Obj or None) -> package index (int)"""
        self.structs = schema['structs']
        self.enums = schema.get('enums', {})
        self.names = names
        self.objref = objref
        self.notes = []
        self._fields = {}

    def fields(self, sname):
        """{lower name: (name, array dim, type)} of a struct or class and its supers"""
        if sname in self._fields:
            return self._fields[sname]
        out = {}
        n = sname
        while n:
            s = self.structs.get(n)
            if s is None:
                raise Unsupported('the End editor has no %s' % n)
            for name, dim, td in s['props']:
                out.setdefault(name.lower(), (name, dim, td))
            n = s.get('super')
        self._fields[sname] = out
        return out

    def has(self, sname):
        return sname in self.structs

    # -- values ----------------------------------------------------------------------------------------------------
    def value(self, td, v, where):
        """the bytes of one value of type td (no tag)"""
        t = td['t']
        if t in PRIM:
            if t in ('Float', 'Double'):
                return struct.pack(PRIM[t], float(v or 0.0))
            return struct.pack(PRIM[t], int(v or 0))
        if t == 'Byte':
            if isinstance(v, str):
                raise Unsupported('%s: a byte with an enum name %r' % (where, v))
            return struct.pack('<B', int(v or 0) & 0xFF)
        if t == 'Enum':
            if isinstance(v, int) and not isinstance(v, bool):
                names = self.enums.get(td['e'], [])
                v = names[v] if 0 <= v < len(names) else (names[0] if names else 'None')
            return self.names.ref(str(v) if v else (self.enums.get(td['e']) or ['None'])[0])
        if t == 'Bool':
            return struct.pack('<B', 1 if v else 0)
        if t == 'Name':
            return self.names.ref(str(v) if v else 'None')
        if t == 'Str':
            return fstring(str(v or ''))
        if t in ('Object', 'Class'):
            return struct.pack('<i', self.objref(v) if v is not None else 0)
        if t == 'Struct':
            sn = td['s']
            if sn in NATIVE:
                return NATIVE[sn](v if isinstance(v, dict) else {})
            return self.props(sn, v if isinstance(v, dict) else {}, where + '.' + sn)
        if t == 'Array':
            items = list(v or [])
            inner = td['i']
            body = struct.pack('<i', len(items))
            if inner['t'] == 'Struct':
                elems = b''.join(self.value(inner, x, '%s[%d]' % (where, k)) for k, x in enumerate(items))
                body += (self.names.ref(where.rsplit('.', 1)[-1]) + self.names.ref('StructProperty') +
                         struct.pack('<ii', len(elems), 0) + self.names.ref(inner['s']) + b'\0' * 16 + b'\0')
                return body + elems
            if inner['t'] == 'Bool':
                return body + b''.join(struct.pack('<B', 1 if x else 0) for x in items)
            return body + b''.join(self.value(inner, x, '%s[%d]' % (where, k)) for k, x in enumerate(items))
        raise Unsupported('%s: a %s' % (where, t))

    def tag(self, name, td, size, index, v):
        b = self.names.ref(name) + self.names.ref(type_name(td)) + struct.pack('<ii', size, index)
        t = td['t']
        if t == 'Struct':
            b += self.names.ref(td['s']) + b'\0' * 16
        elif t == 'Bool':
            b += struct.pack('<B', 1 if v else 0)
        elif t == 'Enum':
            b += self.names.ref(td['e'])
        elif t == 'Byte':
            b += self.names.ref('None')
        elif t == 'Array':
            b += self.names.ref(type_name(td['i']))
        return b + b'\0'                                    # no property guid

    def props(self, sname, values, where=None):
        """a tagged property stream (ending with None) of struct or class sname"""
        where = where or sname
        fields = self.fields(sname)
        out = bytearray()
        for key, v in values.items():
            f = fields.get(key.lower())
            if f is None:
                self.notes.append('%s: no %s in the End editor, left out' % (where, key))
                continue
            name, dim, td = f
            elements = v if (dim > 1 and isinstance(v, list)) else [v]
            for index, x in enumerate(elements):
                if dim > 1 and x is None:
                    continue
                try:
                    data = b'' if td['t'] == 'Bool' else self.value(td, x, '%s.%s' % (where, name))
                except Unsupported as e:
                    self.notes.append('%s: %s, left out' % (where, e))
                    continue
                out += self.tag(name, td, len(data), index, x) + data
        out += self.names.ref('None')
        return bytes(out)
