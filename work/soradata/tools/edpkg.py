"""Names, imports and exports of an editor (uncooked, versioned) UE 4.26 .uasset."""
import struct
import sys


class R:
    def __init__(self, d, p=0):
        self.d, self.p = d, p

    def i32(self):
        v, = struct.unpack_from('<i', self.d, self.p); self.p += 4; return v

    def u32(self):
        v, = struct.unpack_from('<I', self.d, self.p); self.p += 4; return v

    def i64(self):
        v, = struct.unpack_from('<q', self.d, self.p); self.p += 8; return v

    def fstr(self):
        n = self.i32()
        if n == 0:
            return ''
        if n < 0:
            s = self.d[self.p:self.p - 2 * n].decode('utf-16-le'); self.p -= 2 * n
        else:
            s = self.d[self.p:self.p + n].decode('latin-1'); self.p += n
        return s.rstrip('\0')


class EditorPackage:
    def __init__(self, d):
        r = R(d)
        assert r.u32() == 0x9E2A83C1
        self.legacy = r.i32()
        if self.legacy != -4:
            r.i32()
        self.ue4 = r.i32(); self.licensee = r.i32()
        n = r.i32(); r.p += 20 * n
        self.total_header_size = r.i32()
        self.folder = r.fstr()
        self.flags = r.u32()
        self.name_count, self.name_offset = r.i32(), r.i32()
        if not (self.flags & 0x80000000):
            r.fstr()
        r.i32(); r.i32()
        self.export_count, self.export_offset = r.i32(), r.i32()
        self.import_count, self.import_offset = r.i32(), r.i32()
        r.p = self.name_offset
        self.names = []
        for _ in range(self.name_count):
            self.names.append(r.fstr()); r.p += 4
        r.p = self.import_offset
        self.imports = []
        for _ in range(self.import_count):
            cp = self.name(r); cn = self.name(r); outer = r.i32(); on = self.name(r)
            if self.ue4 >= 520 and not (self.flags & 0x80000000):   # (VER_UE4_NON_OUTER_PACKAGE_IMPORT: editor packages)
                pkg = self.name(r)
            self.imports.append((cp, cn, outer, on))
        self.exports = []
        r.p = self.export_offset
        for _ in range(self.export_count):
            cls, sup, tmpl, outer = r.i32(), r.i32(), r.i32(), r.i32()
            on = self.name(r)
            flags = r.u32()
            size, off = r.i64(), r.i64()
            r.p += 4 * 3 + 16 + 4 + 4 + 4 + 4 * 5   # forced export / not for client / server, guid, package flags, not-always-loaded, is asset, dependencies
            self.exports.append(dict(cls=cls, outer=outer, name=on, size=size, offset=off))

    def name(self, r):
        i, n = r.i32(), r.i32()
        s = self.names[i]
        return s if n == 0 else '%s_%d' % (s, n - 1)

    def obj(self, index):
        if index < 0:
            cp, cn, outer, on = self.imports[-index - 1]
            return (self.obj(outer) + '.' if outer else '') + on
        if index > 0:
            e = self.exports[index - 1]
            return (self.obj(e['outer']) + '.' if e['outer'] else '') + e['name']
        return ''


if __name__ == '__main__':
    p = EditorPackage(open(sys.argv[1], 'rb').read())
    print('ue4', p.ue4, 'flags %08x' % p.flags, 'names', p.name_count, 'imports', p.import_count, 'exports', p.export_count)
    for i, (cp, cn, outer, on) in enumerate(p.imports):
        print('  import %3d %-20s %s' % (-i - 1, cn, p.obj(-i - 1)))
    for i, e in enumerate(p.exports):
        print('  export %3d %-26s %s' % (i + 1, p.obj(e['cls']).rsplit('.', 1)[-1], p.obj(i + 1)))
