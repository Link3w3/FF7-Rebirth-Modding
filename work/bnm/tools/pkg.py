"""UE 4.26 package header reader for cooked or uncooked (editor) .uasset files."""
import struct

class R:
    def __init__(self, d, p=0): self.d = d; self.p = p
    def i32(self): v = struct.unpack_from('<i', self.d, self.p)[0]; self.p += 4; return v
    def u32(self): v = struct.unpack_from('<I', self.d, self.p)[0]; self.p += 4; return v
    def i64(self): v = struct.unpack_from('<q', self.d, self.p)[0]; self.p += 8; return v
    def u16(self): v = struct.unpack_from('<H', self.d, self.p)[0]; self.p += 2; return v
    def guid(self): v = self.d[self.p:self.p + 16]; self.p += 16; return v
    def fstr(self):
        n = self.i32()
        if n == 0: return ''
        if n < 0:
            s = self.d[self.p:self.p - 2 * n].decode('utf-16-le'); self.p += -2 * n
        else:
            s = self.d[self.p:self.p + n].decode('latin-1'); self.p += n
        return s.rstrip('\0')

class Package:
    def __init__(self, uasset, uexp=b''):
        self.hdr = uasset; self.d = uasset + uexp
        r = R(uasset)
        assert r.u32() == 0x9E2A83C1
        self.legacy = r.i32()
        if self.legacy != -4: r.i32()
        self.ue4ver = r.i32(); self.licensee = r.i32()
        n = r.i32(); self.custom = [(r.guid(), r.i32()) for _ in range(n)]
        self.total_header_size = r.i32(); self.folder = r.fstr(); self.flags = r.u32()
        self.editor = not (self.flags & 0x80000000)
        self.name_count = r.i32(); self.name_offset = r.i32()
        if self.editor: self.loc_id = r.fstr()
        self.gather_count = r.i32(); self.gather_offset = r.i32()
        self.export_count = r.i32(); self.export_offset = r.i32()
        self.import_count = r.i32(); self.import_offset = r.i32()
        self.depends_offset = r.i32()
        self.softref_count = r.i32(); self.softref_offset = r.i32()
        self.searchable_offset = r.i32(); self.thumb_offset = r.i32()
        self.guid = r.guid()
        if self.editor: self.persistent_guid = r.guid()
        n = r.i32(); self.generations = [(r.i32(), r.i32()) for _ in range(n)]
        def engver(): return (r.u16(), r.u16(), r.u16(), r.u32(), r.fstr())
        self.saved_by = engver(); self.compat = engver()
        self.compression = r.u32(); assert r.i32() == 0
        self.package_source = r.u32()
        n = r.i32(); self.additional = [r.fstr() for _ in range(n)]
        if self.legacy > -7: r.i32()
        self.asset_registry_offset = r.i32(); self.bulk_start = r.i64(); self.world_tile_offset = r.i32()
        n = r.i32(); self.chunk_ids = [r.i32() for _ in range(n)]
        self.preload_count = r.i32(); self.preload_offset = r.i32()
        r.p = self.name_offset; self.names = []
        for _ in range(self.name_count):
            s = r.fstr(); r.u16(); r.u16(); self.names.append(s)
        r.p = self.import_offset; self.imports = []
        for _ in range(self.import_count):
            cp = (r.i32(), r.i32()); cn = (r.i32(), r.i32()); outer = r.i32(); on = (r.i32(), r.i32())
            pkgname = self.n((r.i32(), r.i32())) if self.editor and self.ue4ver >= 520 else None
            self.imports.append(dict(class_package=self.n(cp), class_name=self.n(cn), outer=outer, name=self.n(on), package=pkgname))
        r.p = self.export_offset; self.exports = []
        for _ in range(self.export_count):
            e = dict(cls=r.i32(), sup=r.i32(), tmpl=r.i32(), outer=r.i32(), name=self.n((r.i32(), r.i32())), flags=r.u32(),
                     size=r.i64(), offset=r.i64(), forced=r.i32(), nfc=r.i32(), nfs=r.i32(), pguid=r.guid(), pflags=r.u32(),
                     nalefg=r.i32(), isasset=r.i32(), fed=r.i32(), sbs=r.i32(), cbs=r.i32(), sbc=r.i32(), cbc=r.i32())
            self.exports.append(e)
    def n(self, t):
        i, num = t
        s = self.names[i] if 0 <= i < len(self.names) else '?%d' % i
        return s if num == 0 else '%s_%d' % (s, num - 1)
    def ref(self, idx):
        if idx < 0: return 'import:' + self.imports[-idx - 1]['name'] + '(' + self.imports[-idx - 1]['class_name'] + ')'
        if idx > 0: return 'export:' + self.exports[idx - 1]['name']
        return 'null'
    def class_of(self, e):
        return self.ref(e['cls'])
    def export_data(self, i):
        e = self.exports[i]
        return self.d[e['offset']:e['offset'] + e['size']]
