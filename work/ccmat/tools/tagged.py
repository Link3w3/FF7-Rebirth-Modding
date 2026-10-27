"""Crisis Core Reunion (UE 4.27 zen packages) material assets: their tagged properties (the material packages are saved
with property tags, not unversioned), read with the package's name map; object references resolved to the export's name
or the import's package path where the package says.
    tagged.py <package.uasset> [...]     prints every export's properties as JSON"""
import json
import struct
import sys
sys.path.insert(0, '/work/ccanim/tools')
from ccanim import Zen


class R:
    def __init__(self, b, p=0):
        self.b, self.p = b, p

    def u8(self):
        v = self.b[self.p]; self.p += 1; return v

    def i32(self):
        v = struct.unpack_from('<i', self.b, self.p)[0]; self.p += 4; return v

    def u32(self):
        v = struct.unpack_from('<I', self.b, self.p)[0]; self.p += 4; return v

    def i64(self):
        v = struct.unpack_from('<q', self.b, self.p)[0]; self.p += 8; return v

    def f32(self):
        v = struct.unpack_from('<f', self.b, self.p)[0]; self.p += 4; return v

    def raw(self, n):
        v = self.b[self.p:self.p + n]; self.p += n; return v

    def fstring(self):
        n = self.i32()
        if n == 0:
            return ''
        if n < 0:
            s = self.raw(-2 * n).decode('utf-16-le')
        else:
            s = self.raw(n).decode('latin-1')
        return s.rstrip('\x00')


class Package:
    def __init__(self, path):
        self.path = path
        self.d = open(path, 'rb').read()
        self.z = Zen(self.d)

    def name(self, r):
        i, n = r.u32(), r.u32()
        s = self.z.names[i] if i < len(self.z.names) else '?%d' % i
        return s if n == 0 else '%s_%d' % (s, n - 1)

    def objref(self, v):
        """FPackageIndex: > 0 an export (its name), < 0 an import (its global id, hex), 0 none"""
        if v == 0:
            return None
        if v > 0:
            return 'export:' + self.z.exports[v - 1]['name']
        imp = self.z.imports[-v - 1]
        return 'import:%016x' % imp

    def tags(self, r, end=None):
        out = []
        while end is None or r.p < end:
            name = self.name(r)
            if name == 'None':
                break
            typ = self.name(r)
            size = r.i32()
            index = r.i32()
            extra = {}
            if typ == 'StructProperty':
                extra['struct'] = self.name(r)
                r.raw(16)
            elif typ == 'BoolProperty':
                extra['bool'] = r.u8()
            elif typ in ('ByteProperty', 'EnumProperty'):
                extra['enum'] = self.name(r)
            elif typ in ('ArrayProperty', 'SetProperty'):
                extra['inner'] = self.name(r)
            elif typ == 'MapProperty':
                extra['key'] = self.name(r); extra['value'] = self.name(r)
            if r.u8():
                r.raw(16)
            start = r.p
            value = self.value(r, typ, size, extra)
            r.p = start + size
            out.append((name if index == 0 else '%s[%d]' % (name, index), value))
        return out

    def value(self, r, typ, size, extra):
        if typ == 'BoolProperty':
            return bool(extra['bool'])
        if typ == 'FloatProperty':
            return r.f32()
        if typ == 'IntProperty':
            return r.i32()
        if typ == 'UInt32Property':
            return r.u32()
        if typ == 'NameProperty':
            return self.name(r)
        if typ == 'StrProperty':
            return r.fstring()
        if typ == 'ObjectProperty':
            return self.objref(r.i32())
        if typ == 'SoftObjectProperty':
            return [self.name(r), r.fstring()]
        if typ in ('ByteProperty', 'EnumProperty'):
            if typ == 'ByteProperty' and extra['enum'] == 'None':
                return r.u8()
            return self.name(r)
        if typ == 'StructProperty':
            return self.struct(r, extra['struct'], size)
        if typ == 'ArrayProperty':
            n = r.i32()
            inner = extra['inner']
            if inner == 'StructProperty':
                # an array of structs carries one inner tag (name, type, size, index, struct name, guid, has guid)
                self.name(r); self.name(r); r.i32(); r.i32()
                sname = self.name(r); r.raw(16)
                if r.u8():
                    r.raw(16)
                return [self.struct(r, sname, None) for _ in range(n)]
            return [self.value(r, inner, 0, {'enum': 'None', 'bool': 0}) for _ in range(n)]
        return '<%s %d bytes>' % (typ, size)

    NATIVE = {'Vector': '<3f', 'Vector4': '<4f', 'Vector2D': '<2f', 'LinearColor': '<4f', 'Rotator': '<3f', 'Quat': '<4f',
              'IntPoint': '<2i', 'Color': '<4B', 'Guid': '<4I'}

    def struct(self, r, sname, size):
        if sname in self.NATIVE:
            fmt = self.NATIVE[sname]
            v = struct.unpack_from(fmt, r.b, r.p); r.p += struct.calcsize(fmt)
            return list(v)
        return dict(self.tags(r))

    def export_props(self, i):
        b = self.z.export_bytes(i)
        r = R(b)
        props = self.tags(r)
        return dict(props), r.p, len(b)


def main(paths):
    for p in paths:
        pk = Package(p)
        out = {}
        for i, e in enumerate(pk.z.exports):
            try:
                props, used, total = pk.export_props(i)
                out[e['name']] = {'props': props, 'tagged_bytes': used, 'export_bytes': total}
            except Exception as ex:
                out[e['name']] = {'error': repr(ex)}
        print(json.dumps({p: out}, indent=1, default=str))


if __name__ == '__main__':
    main(sys.argv[1:])
