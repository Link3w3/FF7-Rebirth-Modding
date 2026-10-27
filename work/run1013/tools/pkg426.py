"""UE4.26 legacy package reader for both cooked (unversioned, FilterEditorOnly) and editor-saved packages."""
import struct
class R:
    def __init__(self, d, p=0): self.d = d; self.p = p
    def i32(self): v = struct.unpack_from('<i', self.d, self.p)[0]; self.p += 4; return v
    def u32(self): v = struct.unpack_from('<I', self.d, self.p)[0]; self.p += 4; return v
    def i64(self): v = struct.unpack_from('<q', self.d, self.p)[0]; self.p += 8; return v
    def u16(self): v = struct.unpack_from('<H', self.d, self.p)[0]; self.p += 2; return v
    def guid(self): v = self.d[self.p:self.p+16]; self.p += 16; return v
    def fstr(self):
        n = self.i32()
        if n == 0: return ''
        if n < 0:
            s = self.d[self.p:self.p + (-n) * 2].decode('utf-16-le'); self.p += (-n) * 2
        else:
            s = self.d[self.p:self.p + n].decode('latin-1'); self.p += n
        return s.rstrip('\0')
class Pkg:
    def __init__(self, uasset, uexp=b''):
        self.d = uasset + uexp
        r = R(uasset)
        assert r.u32() == 0x9E2A83C1
        self.legacy = r.i32()
        if self.legacy != -4: r.i32()
        self.ue4 = r.i32(); self.lic = r.i32()
        n = r.i32(); self.custom = [(r.guid(), r.i32()) for _ in range(n)]
        self.total_header = r.i32(); self.folder = r.fstr(); self.flags = r.u32()
        self.editor = not (self.flags & 0x80000000)
        name_count, name_off = r.i32(), r.i32()
        if self.editor: self.loc_id = r.fstr()
        r.i32(); r.i32()
        exp_count, exp_off, imp_count, imp_off = r.i32(), r.i32(), r.i32(), r.i32()
        self.names = []
        q = R(uasset, name_off)
        for _ in range(name_count):
            self.names.append(q.fstr()); q.p += 4
        q = R(uasset, imp_off)
        self.imports = []
        for _ in range(imp_count):
            cp = self.n(q.i32(), q.i32()); cn = self.n(q.i32(), q.i32()); outer = q.i32(); on = self.n(q.i32(), q.i32())
            if self.editor: q.p += 8
            self.imports.append((cp, cn, outer, on))
        q = R(uasset, exp_off)
        self.exports = []
        for _ in range(exp_count):
            e = dict(cls=q.i32(), sup=q.i32(), tmpl=q.i32(), outer=q.i32(), name=self.n(q.i32(), q.i32()), flags=q.u32(), size=q.i64(), offset=q.i64())
            q.p += 12 + 16 + 4 + 4 + 4 + 20
            self.exports.append(e)
    def n(self, i, num):
        s = self.names[i] if 0 <= i < len(self.names) else '?%d' % i
        return s if num == 0 else '%s_%d' % (s, num - 1)
    def import_path(self, index):  # index < 0
        im = self.imports[-index - 1]
        chain = [im[3]]; outer = im[2]
        while outer < 0:
            o = self.imports[-outer - 1]; chain.append(o[3]); outer = o[2]
        chain.reverse()
        return chain[0] + ('.' + '.'.join(chain[1:]) if len(chain) > 1 else '')

def read_props(P, data, p, end, depth=0, out=None):
    """Tagged properties (versioned editor packages, UE4.26). Returns list of (name, type, extra, value-ish)."""
    import struct as st
    out = [] if out is None else out
    while p < end:
        name = P.n(*st.unpack_from('<ii', data, p)); p += 8
        if name == 'None': break
        typ = P.n(*st.unpack_from('<ii', data, p)); p += 8
        size, aidx = st.unpack_from('<ii', data, p); p += 8
        extra = None
        if typ == 'StructProperty': extra = P.n(*st.unpack_from('<ii', data, p)); p += 8 + 16
        elif typ == 'BoolProperty': extra = data[p]; p += 1
        elif typ in ('ByteProperty', 'EnumProperty', 'ArrayProperty', 'SetProperty'): extra = P.n(*st.unpack_from('<ii', data, p)); p += 8
        elif typ == 'MapProperty': extra = (P.n(*st.unpack_from('<ii', data, p)), P.n(*st.unpack_from('<ii', data, p + 8))); p += 16
        hg = data[p]; p += 1
        if hg: p += 16
        out.append((depth, name, typ, extra, aidx, p, size))
        if typ == 'ArrayProperty' and extra == 'StructProperty':
            count = st.unpack_from('<i', data, p)[0]
            # inner tag
            q = p + 4
            iname = P.n(*st.unpack_from('<ii', data, q)); q += 8
            ityp = P.n(*st.unpack_from('<ii', data, q)); q += 8
            isize = st.unpack_from('<q', data, q)[0]; q += 8
            istruct = P.n(*st.unpack_from('<ii', data, q)); q += 8 + 16 + 1
            out.append((depth + 1, '[%d x %s]' % (count, istruct), 'inner', None, 0, q, isize))
            for k in range(count):
                q = read_props(P, data, q, p + size, depth + 2, out)
        p += size
    return p
