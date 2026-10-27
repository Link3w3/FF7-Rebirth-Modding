mkdir -p $HOME/animcheck && cat > $HOME/animcheck/pkg426.py <<'PYEOF'
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

PYEOF
cat > $HOME/animcheck/sqex.py <<'PYEOF'
import sys, struct
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from pkg426 import Pkg, read_props
def analyze(path, verbose=True):
    d = open(path, 'rb').read()
    P = Pkg(d)
    out = {}
    for e in P.exports:
        cls = P.import_path(e['cls']) if e['cls'] < 0 else ''
        if not cls.endswith('AnimSequence'): continue
        off, size = e['offset'], e['size']
        props = []
        p = read_props(P, d, off, off + size, 0, props)
        q = p
        hasguid = struct.unpack_from('<i', d, q)[0]; q += 4
        if hasguid: q += 16
        skelguid = d[q:q+16]; q += 16
        PM_START = off
        fcs, sz, idk, pad = struct.unpack_from('<IIHH', d, q); q += 12
        q += pad
        PM_POINTER1 = q
        off1, num, mx = struct.unpack_from('<Qii', d, q); q += 16
        PM_POINTER2 = q
        off2, num2, mx2 = struct.unpack_from('<Qii', d, q); q += 16
        ddc = d[q:q+8]; q += 8; sig = d[q:q+8]; q += 8
        data = q
        # ACL clip header, if present
        acl = None
        if d[data+8:data+12] == b'\x10\xac\x10\xac':
            acl = struct.unpack_from('<I', d, data)[0]
        # frozen content size says where the stream ends (relative to PM_POINTER1)
        stream_end = PM_POINTER1 + fcs
        # after stream: unk1..3 then strip flags (2 bytes) then RawAnimationData count
        r = stream_end
        unk = struct.unpack_from('<iii', d, r); r += 12
        strip = d[r:r+2]; r += 2
        ntracks = struct.unpack_from('<i', d, r)[0]
        out = dict(name=e['name'], flags=P.flags, frozen=fcs, size=sz, idk=idk, pad=pad, off1=off1, num=num, max=mx, off2=off2, num2=num2,
                   sig=sig, acl_size=acl, data_rel=data - PM_POINTER1, unk=unk, strip=strip.hex(), ntracks=ntracks, export_size=size)
        if verbose:
            print(path.split('/')[-1], out)
    return out
if __name__ == '__main__':
    for f in sys.argv[1:]:
        analyze(f)

PYEOF
cat > $HOME/animcheck/check.py <<'PYEOF'

import sys, glob, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sqex import analyze
bad, good, other = [], [], []
for root in sys.argv[1:]:
    for f in sorted(glob.glob(os.path.join(root, '**', '*.uasset'), recursive=True)):
        try:
            o = analyze(f, False)
        except Exception as ex:
            other.append((f, 'ERR %s' % ex)); continue
        if not o:
            other.append((f, 'no AnimSequence')); continue
        n = o['num']; acl = o['acl_size']; data = o['frozen'] - 48
        pad = lambda x: (16 - x % 16) % 16
        consistent = (n == 0 and data == 0) or (n > 0 and data == n + pad(n))
        (good if consistent else bad).append((os.path.relpath(f, root), n, acl, o['frozen']))
print('good', len(good), 'bad', len(bad), 'other', len(other))
for b in bad: print('BAD', b)
for o in other[:20]: print('OTHER', o)

PYEOF
md5sum $HOME/animcheck/*.py
