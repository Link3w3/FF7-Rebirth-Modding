"""Minimal .NET (ECMA-335) metadata reader: PE -> CLI header -> metadata streams -> tables, method bodies and an IL
disassembly with tokens resolved to names (enough to read what a managed tool does without running it).
    netmeta.py strings <dll>            user strings (#US)
    netmeta.py types <dll>              types, fields and methods
    netmeta.py il <dll> [substring]     IL of the methods whose 'Type::Method' contains the substring"""
import struct
import sys

TABLES = {
    0x00: ('Module', 'u2 S G G G'), 0x01: ('TypeRef', 'C:ResolutionScope S S'),
    0x02: ('TypeDef', 'u4 S S C:TypeDefOrRef T:Field T:MethodDef'), 0x03: ('FieldPtr', 'T:Field'),
    0x04: ('Field', 'u2 S B'), 0x05: ('MethodPtr', 'T:MethodDef'), 0x06: ('MethodDef', 'u4 u2 u2 S B T:Param'),
    0x07: ('ParamPtr', 'T:Param'), 0x08: ('Param', 'u2 u2 S'), 0x09: ('InterfaceImpl', 'T:TypeDef C:TypeDefOrRef'),
    0x0A: ('MemberRef', 'C:MemberRefParent S B'), 0x0B: ('Constant', 'u2 C:HasConstant B'),
    0x0C: ('CustomAttribute', 'C:HasCustomAttribute C:CustomAttributeType B'), 0x0D: ('FieldMarshal', 'C:HasFieldMarshal B'),
    0x0E: ('DeclSecurity', 'u2 C:HasDeclSecurity B'), 0x0F: ('ClassLayout', 'u2 u4 T:TypeDef'), 0x10: ('FieldLayout', 'u4 T:Field'),
    0x11: ('StandAloneSig', 'B'), 0x12: ('EventMap', 'T:TypeDef T:Event'), 0x13: ('EventPtr', 'T:Event'),
    0x14: ('Event', 'u2 S C:TypeDefOrRef'), 0x15: ('PropertyMap', 'T:TypeDef T:Property'), 0x16: ('PropertyPtr', 'T:Property'),
    0x17: ('Property', 'u2 S B'), 0x18: ('MethodSemantics', 'u2 T:MethodDef C:HasSemantics'),
    0x19: ('MethodImpl', 'T:TypeDef C:MethodDefOrRef C:MethodDefOrRef'), 0x1A: ('ModuleRef', 'S'), 0x1B: ('TypeSpec', 'B'),
    0x1C: ('ImplMap', 'u2 C:MemberForwarded S T:ModuleRef'), 0x1D: ('FieldRVA', 'u4 T:Field'), 0x1E: ('ENCLog', 'u4 u4'),
    0x1F: ('ENCMap', 'u4'), 0x20: ('Assembly', 'u4 u2 u2 u2 u2 u4 B S S'), 0x21: ('AssemblyProcessor', 'u4'),
    0x22: ('AssemblyOS', 'u4 u4 u4'), 0x23: ('AssemblyRef', 'u2 u2 u2 u2 u4 B S S B'), 0x24: ('AssemblyRefProcessor', 'u4 T:AssemblyRef'),
    0x25: ('AssemblyRefOS', 'u4 u4 u4 T:AssemblyRef'), 0x26: ('File', 'u4 S B'), 0x27: ('ExportedType', 'u4 u4 S S C:Implementation'),
    0x28: ('ManifestResource', 'u4 u4 S C:Implementation'), 0x29: ('NestedClass', 'T:TypeDef T:TypeDef'),
    0x2A: ('GenericParam', 'u2 u2 C:TypeOrMethodDef S'), 0x2B: ('MethodSpec', 'C:MethodDefOrRef B'),
    0x2C: ('GenericParamConstraint', 'T:GenericParam C:TypeDefOrRef'),
}
TID = {v[0]: k for k, v in TABLES.items()}
CODED = {
    'TypeDefOrRef': (2, ['TypeDef', 'TypeRef', 'TypeSpec']),
    'HasConstant': (2, ['Field', 'Param', 'Property']),
    'HasCustomAttribute': (5, ['MethodDef', 'Field', 'TypeRef', 'TypeDef', 'Param', 'InterfaceImpl', 'MemberRef', 'Module',
                               'DeclSecurity', 'Property', 'Event', 'StandAloneSig', 'ModuleRef', 'TypeSpec', 'Assembly',
                               'AssemblyRef', 'File', 'ExportedType', 'ManifestResource', 'GenericParam',
                               'GenericParamConstraint', 'MethodSpec']),
    'HasFieldMarshal': (1, ['Field', 'Param']), 'HasDeclSecurity': (2, ['TypeDef', 'MethodDef', 'Assembly']),
    'MemberRefParent': (3, ['TypeDef', 'TypeRef', 'ModuleRef', 'MethodDef', 'TypeSpec']),
    'HasSemantics': (1, ['Event', 'Property']), 'MethodDefOrRef': (1, ['MethodDef', 'MemberRef']),
    'MemberForwarded': (1, ['Field', 'MethodDef']), 'Implementation': (2, ['File', 'AssemblyRef', 'ExportedType']),
    'CustomAttributeType': (3, [None, None, 'MethodDef', 'MemberRef', None]),
    'ResolutionScope': (2, ['Module', 'ModuleRef', 'AssemblyRef', 'TypeRef']), 'TypeOrMethodDef': (1, ['TypeDef', 'MethodDef']),
}


class PE:
    def __init__(self, path):
        self.b = b = open(path, 'rb').read()
        pe = struct.unpack_from('<I', b, 0x3C)[0]
        assert b[pe:pe + 4] == b'PE\0\0'
        nsec = struct.unpack_from('<H', b, pe + 6)[0]
        opt_size = struct.unpack_from('<H', b, pe + 20)[0]
        opt = pe + 24
        magic = struct.unpack_from('<H', b, opt)[0]
        dd = opt + (96 if magic == 0x10b else 112)
        self.secs = []
        so = opt + opt_size
        for i in range(nsec):
            name, vsize, va, rsize, raw = struct.unpack_from('<8sIIII', b, so + 40 * i)
            self.secs.append((va, max(vsize, rsize), raw))
        cli_rva, _ = struct.unpack_from('<II', b, dd + 14 * 8)
        c = self.off(cli_rva)
        md_rva, md_size = struct.unpack_from('<II', b, c + 8)
        m = self.off(md_rva)
        assert b[m:m + 4] == b'BSJB'
        vlen = struct.unpack_from('<I', b, m + 12)[0]
        p = m + 16 + vlen
        nstreams = struct.unpack_from('<H', b, p + 2)[0]; p += 4
        self.streams = {}
        for _ in range(nstreams):
            off, size = struct.unpack_from('<II', b, p); p += 8
            e = b.index(b'\0', p)
            name = b[p:e].decode(); p = (e + 4) & ~3
            self.streams[name] = (m + off, size)
        self._tables()

    def off(self, rva):
        for va, size, raw in self.secs:
            if va <= rva < va + size:
                return rva - va + raw
        raise ValueError(hex(rva))

    def heap(self, name):
        o, s = self.streams[name]
        return self.b[o:o + s]

    def string(self, i):
        s = self.heap('#Strings')
        return s[i:s.index(b'\0', i)].decode('utf-8', 'replace')

    def blob(self, i):
        o, _ = self.streams['#Blob']
        n, k = self.cint(self.b, o + i)
        return self.b[o + i + k:o + i + k + n]

    def us(self, i):
        o, _ = self.streams['#US']
        n, k = self.cint(self.b, o + i)
        return self.b[o + i + k:o + i + k + n - 1].decode('utf-16-le', 'replace') if n else ''

    @staticmethod
    def cint(b, p):
        x = b[p]
        if x & 0x80 == 0:
            return x, 1
        if x & 0xC0 == 0x80:
            return ((x & 0x3F) << 8) | b[p + 1], 2
        return ((x & 0x1F) << 24) | (b[p + 1] << 16) | (b[p + 2] << 8) | b[p + 3], 4

    def _tables(self):
        o, _ = self.streams.get('#~') or self.streams['#-']
        b = self.b
        hs = b[o + 6]
        valid = struct.unpack_from('<Q', b, o + 8)[0]
        p = o + 24
        self.rows = {}
        for t in range(64):
            if valid >> t & 1:
                self.rows[t] = struct.unpack_from('<I', b, p)[0]; p += 4
        if hs & 0x20:       # extra data
            p += 4
        sidx = 4 if hs & 1 else 2; gidx = 4 if hs & 2 else 2; bidx = 4 if hs & 4 else 2

        def tsize(name):
            return 4 if self.rows.get(TID[name], 0) >= 0x10000 else 2

        def csize(kind):
            bits, tabs = CODED[kind]
            mx = max(self.rows.get(TID[t], 0) if t else 0 for t in tabs)
            return 2 if mx < (1 << (16 - bits)) else 4
        self.t = {}
        for tid in sorted(self.rows):
            name, cols = TABLES[tid]
            cols = cols.split()
            sizes = []
            for c in cols:
                if c == 'u2':
                    sizes.append(2)
                elif c == 'u4':
                    sizes.append(4)
                elif c == 'S':
                    sizes.append(sidx)
                elif c == 'G':
                    sizes.append(gidx)
                elif c == 'B':
                    sizes.append(bidx)
                elif c.startswith('T:'):
                    sizes.append(tsize(c[2:]))
                else:
                    sizes.append(csize(c[2:]))
            rows = []
            for r in range(self.rows[tid]):
                row = []
                for c, s in zip(cols, sizes):
                    v = struct.unpack_from('<H' if s == 2 else '<I', b, p)[0]; p += s
                    row.append(v)
                rows.append(row)
            self.t[name] = (cols, rows)

    def row(self, table, i):            # 1-based
        return self.t[table][1][i - 1]

    def coded(self, kind, v):
        bits, tabs = CODED[kind]
        return tabs[v & ((1 << bits) - 1)], v >> bits

    # ---- names
    def typedef_name(self, i):
        r = self.row('TypeDef', i)
        ns, n = self.string(r[2]), self.string(r[1])
        return (ns + '.' if ns else '') + n

    def typeref_name(self, i):
        r = self.row('TypeRef', i)
        ns, n = self.string(r[2]), self.string(r[1])
        return (ns + '.' if ns else '') + n

    def type_name(self, table, i):
        if table == 'TypeDef':
            return self.typedef_name(i)
        if table == 'TypeRef':
            return self.typeref_name(i)
        if table == 'TypeSpec':
            return 'spec(' + self.sig_type(self.blob(self.row('TypeSpec', i)[0]), 0)[0] + ')'
        return '%s#%d' % (table, i)

    def method_owner(self, mi):
        rows = self.t['TypeDef'][1]
        own = None
        for k, r in enumerate(rows):
            if r[5] <= mi:
                own = k + 1
        return own

    def field_owner(self, fi):
        rows = self.t['TypeDef'][1]
        own = None
        for k, r in enumerate(rows):
            if r[4] <= fi:
                own = k + 1
        return own

    def token(self, tok):
        tab, idx = tok >> 24, tok & 0xFFFFFF
        name = TABLES.get(tab, ('?',))[0]
        if tab == 0x70:
            return repr(self.us(idx))
        if name == 'MethodDef':
            return '%s::%s' % (self.typedef_name(self.method_owner(idx)), self.string(self.row('MethodDef', idx)[3]))
        if name == 'Field':
            return '%s::%s' % (self.typedef_name(self.field_owner(idx)), self.string(self.row('Field', idx)[1]))
        if name == 'MemberRef':
            r = self.row('MemberRef', idx)
            pt, pi = self.coded('MemberRefParent', r[0])
            return '%s::%s' % (self.type_name(pt, pi) if pt != 'MethodDef' else self.token((0x06 << 24) | pi), self.string(r[1]))
        if name in ('TypeDef', 'TypeRef', 'TypeSpec'):
            return self.type_name(name, idx)
        if name == 'MethodSpec':
            r = self.row('MethodSpec', idx)
            mt, mi = self.coded('MethodDefOrRef', r[0])
            return self.token((TID[mt] << 24) | mi) + '<...>'
        if name == 'StandAloneSig':
            return 'sig#%d' % idx
        return '%s#%d' % (name, idx)

    ELEM = {0x01: 'void', 0x02: 'bool', 0x03: 'char', 0x04: 'i1', 0x05: 'u1', 0x06: 'i2', 0x07: 'u2', 0x08: 'i4', 0x09: 'u4',
            0x0a: 'i8', 0x0b: 'u8', 0x0c: 'f4', 0x0d: 'f8', 0x0e: 'string', 0x18: 'native int', 0x19: 'native uint', 0x1c: 'object',
            0x16: 'typedref'}

    def sig_type(self, s, p):
        e = s[p]; p += 1
        if e in self.ELEM:
            return self.ELEM[e], p
        if e in (0x11, 0x12):
            v, k = self.cint(s, p); p += k
            t, i = self.coded('TypeDefOrRef', v)
            return self.type_name(t, i), p
        if e == 0x1d:
            t, p = self.sig_type(s, p); return t + '[]', p
        if e == 0x0f:
            t, p = self.sig_type(s, p); return t + '*', p
        if e == 0x10:
            t, p = self.sig_type(s, p); return t + '&', p
        if e == 0x15:
            t, p = self.sig_type(s, p)
            n, k = self.cint(s, p); p += k
            args = []
            for _ in range(n):
                a, p = self.sig_type(s, p); args.append(a)
            return '%s<%s>' % (t, ','.join(args)), p
        if e in (0x13, 0x1e):
            n, k = self.cint(s, p); p += k
            return ('!' if e == 0x13 else '!!') + str(n), p
        if e == 0x14:
            t, p = self.sig_type(s, p)
            rank, k = self.cint(s, p); p += k
            ns, k = self.cint(s, p); p += k
            for _ in range(ns):
                _, k = self.cint(s, p); p += k
            nl, k = self.cint(s, p); p += k
            for _ in range(nl):
                _, k = self.cint(s, p); p += k
            return t + '[' + ',' * (rank - 1) + ']', p
        if e in (0x1f, 0x20):
            v, k = self.cint(s, p); p += k
            return self.sig_type(s, p)
        if e == 0x45:
            return self.sig_type(s, p)
        if e == 0x41:
            return '...', p
        return 'elem%02x' % e, p

    def method_sig(self, blob):
        s = blob
        p = 0
        cc = s[p]; p += 1
        if cc & 0x10:
            _, k = self.cint(s, p); p += k
        n, k = self.cint(s, p); p += k
        try:
            ret, p = self.sig_type(s, p)
            args = []
            for _ in range(n):
                a, p = self.sig_type(s, p); args.append(a)
        except Exception:
            return '(?)'
        return '%s(%s)' % (ret, ', '.join(args))

    def locals_sig(self, tok):
        if not tok:
            return []
        s = self.blob(self.row('StandAloneSig', tok & 0xFFFFFF)[0])
        if s[0] != 0x07:
            return []
        n, p = self.cint(s, 1); p += 1 if n < 0x80 else (2 if n < 0x4000 else 4)
        p = 1 + (1 if n < 0x80 else (2 if n < 0x4000 else 4))
        out = []
        for _ in range(n):
            try:
                t, p = self.sig_type(s, p)
            except Exception:
                t = '?'
            out.append(t)
        return out


# ---- IL opcodes
OP1 = {}
OP2 = {}


def _ops():
    one = '''00 nop -;01 break -;02 ldarg.0 -;03 ldarg.1 -;04 ldarg.2 -;05 ldarg.3 -;06 ldloc.0 -;07 ldloc.1 -;08 ldloc.2 -;09 ldloc.3 -;
0a stloc.0 -;0b stloc.1 -;0c stloc.2 -;0d stloc.3 -;0e ldarg.s u1;0f ldarga.s u1;10 starg.s u1;11 ldloc.s u1;12 ldloca.s u1;
13 stloc.s u1;14 ldnull -;15 ldc.i4.m1 -;16 ldc.i4.0 -;17 ldc.i4.1 -;18 ldc.i4.2 -;19 ldc.i4.3 -;1a ldc.i4.4 -;1b ldc.i4.5 -;
1c ldc.i4.6 -;1d ldc.i4.7 -;1e ldc.i4.8 -;1f ldc.i4.s i1;20 ldc.i4 i4;21 ldc.i8 i8;22 ldc.r4 r4;23 ldc.r8 r8;25 dup -;26 pop -;
27 jmp tok;28 call tok;29 calli tok;2a ret -;2b br.s b1;2c brfalse.s b1;2d brtrue.s b1;2e beq.s b1;2f bge.s b1;30 bgt.s b1;
31 ble.s b1;32 blt.s b1;33 bne.un.s b1;34 bge.un.s b1;35 bgt.un.s b1;36 ble.un.s b1;37 blt.un.s b1;38 br b4;39 brfalse b4;
3a brtrue b4;3b beq b4;3c bge b4;3d bgt b4;3e ble b4;3f blt b4;40 bne.un b4;41 bge.un b4;42 bgt.un b4;43 ble.un b4;44 blt.un b4;
45 switch sw;46 ldind.i1 -;47 ldind.u1 -;48 ldind.i2 -;49 ldind.u2 -;4a ldind.i4 -;4b ldind.u4 -;4c ldind.i8 -;4d ldind.i -;
4e ldind.r4 -;4f ldind.r8 -;50 ldind.ref -;51 stind.ref -;52 stind.i1 -;53 stind.i2 -;54 stind.i4 -;55 stind.i8 -;56 stind.r4 -;
57 stind.r8 -;58 add -;59 sub -;5a mul -;5b div -;5c div.un -;5d rem -;5e rem.un -;5f and -;60 or -;61 xor -;62 shl -;63 shr -;
64 shr.un -;65 neg -;66 not -;67 conv.i1 -;68 conv.i2 -;69 conv.i4 -;6a conv.i8 -;6b conv.r4 -;6c conv.r8 -;6d conv.u4 -;
6e conv.u8 -;6f callvirt tok;70 cpobj tok;71 ldobj tok;72 ldstr tok;73 newobj tok;74 castclass tok;75 isinst tok;76 conv.r.un -;
79 unbox tok;7a throw -;7b ldfld tok;7c ldflda tok;7d stfld tok;7e ldsfld tok;7f ldsflda tok;80 stsfld tok;81 stobj tok;
82 conv.ovf.i1.un -;83 conv.ovf.i2.un -;84 conv.ovf.i4.un -;85 conv.ovf.i8.un -;86 conv.ovf.u1.un -;87 conv.ovf.u2.un -;
88 conv.ovf.u4.un -;89 conv.ovf.u8.un -;8a conv.ovf.i.un -;8b conv.ovf.u.un -;8c box tok;8d newarr tok;8e ldlen -;8f ldelema tok;
90 ldelem.i1 -;91 ldelem.u1 -;92 ldelem.i2 -;93 ldelem.u2 -;94 ldelem.i4 -;95 ldelem.u4 -;96 ldelem.i8 -;97 ldelem.i -;
98 ldelem.r4 -;99 ldelem.r8 -;9a ldelem.ref -;9b stelem.i -;9c stelem.i1 -;9d stelem.i2 -;9e stelem.i4 -;9f stelem.i8 -;
a0 stelem.r4 -;a1 stelem.r8 -;a2 stelem.ref -;a3 ldelem tok;a4 stelem tok;a5 unbox.any tok;b3 conv.ovf.i1 -;b4 conv.ovf.u1 -;
b5 conv.ovf.i2 -;b6 conv.ovf.u2 -;b7 conv.ovf.i4 -;b8 conv.ovf.u4 -;b9 conv.ovf.i8 -;ba conv.ovf.u8 -;c2 refanyval tok;
c3 ckfinite -;c6 mkrefany tok;d0 ldtoken tok;d1 conv.u2 -;d2 conv.u1 -;d3 conv.i -;d4 conv.ovf.i -;d5 conv.ovf.u -;d6 add.ovf -;
d7 add.ovf.un -;d8 mul.ovf -;d9 mul.ovf.un -;da sub.ovf -;db sub.ovf.un -;dc endfinally -;dd leave b4;de leave.s b1;
df stind.i -;e0 conv.u -'''
    two = '''00 arglist -;01 ceq -;02 cgt -;03 cgt.un -;04 clt -;05 clt.un -;06 ldftn tok;07 ldvirtftn tok;09 ldarg u2;0a ldarga u2;
0b starg u2;0c ldloc u2;0d ldloca u2;0e stloc u2;0f localloc -;11 endfilter -;12 unaligned. u1;13 volatile. -;14 tail. -;
15 initobj tok;16 constrained. tok;17 cpblk -;18 initblk -;19 no. u1;1a rethrow -;1c sizeof tok;1d refanytype -;1e readonly. -'''
    for txt, d in ((one, OP1), (two, OP2)):
        for item in txt.replace('\n', '').split(';'):
            item = item.strip()
            if item:
                c, n, a = item.split()
                d[int(c, 16)] = (n, a)


_ops()


def disasm(pe, mi):
    r = pe.row('MethodDef', mi)
    rva = r[0]
    if not rva:
        return ['  (no body)']
    o = pe.off(rva)
    b = pe.b
    h = b[o]
    if h & 3 == 2:
        size = h >> 2; code = o + 1; loc = 0
    else:
        flags = struct.unpack_from('<H', b, o)[0]
        hsz = (flags >> 12) * 4
        size = struct.unpack_from('<I', b, o + 4)[0]
        loc = struct.unpack_from('<I', b, o + 8)[0]
        code = o + hsz
    out = []
    lv = pe.locals_sig(loc)
    if lv:
        out.append('  locals: ' + ', '.join('%d:%s' % (i, t) for i, t in enumerate(lv)))
    p = code
    end = code + size
    while p < end:
        at = p - code
        op = b[p]; p += 1
        if op == 0xFE:
            op2 = b[p]; p += 1
            name, arg = OP2.get(op2, ('fe%02x' % op2, '-'))
        else:
            name, arg = OP1.get(op, ('op%02x' % op, '-'))
        s = ''
        if arg == 'u1':
            s = str(b[p]); p += 1
        elif arg == 'i1':
            s = str(struct.unpack_from('<b', b, p)[0]); p += 1
        elif arg == 'u2':
            s = str(struct.unpack_from('<H', b, p)[0]); p += 2
        elif arg == 'i4':
            v = struct.unpack_from('<i', b, p)[0]; p += 4; s = '%d (0x%X)' % (v, v & 0xFFFFFFFF)
        elif arg == 'i8':
            v = struct.unpack_from('<q', b, p)[0]; p += 8; s = '%d (0x%X)' % (v, v & 0xFFFFFFFFFFFFFFFF)
        elif arg == 'r4':
            s = repr(struct.unpack_from('<f', b, p)[0]); p += 4
        elif arg == 'r8':
            s = repr(struct.unpack_from('<d', b, p)[0]); p += 8
        elif arg == 'b1':
            v = struct.unpack_from('<b', b, p)[0]; p += 1; s = 'IL_%04x' % (p - code + v)
        elif arg == 'b4':
            v = struct.unpack_from('<i', b, p)[0]; p += 4; s = 'IL_%04x' % (p - code + v)
        elif arg == 'tok':
            t = struct.unpack_from('<I', b, p)[0]; p += 4
            try:
                s = pe.token(t)
            except Exception as e:
                s = 'tok %08x (%s)' % (t, e)
        elif arg == 'sw':
            n = struct.unpack_from('<I', b, p)[0]; p += 4
            tg = [struct.unpack_from('<i', b, p + 4 * k)[0] for k in range(n)]; p += 4 * n
            s = ' '.join('IL_%04x' % (p - code + v) for v in tg)
        out.append('  IL_%04x: %s %s' % (at, name, s))
    return out


def all_methods(pe):
    for ti, tr in enumerate(pe.t['TypeDef'][1]):
        start = tr[5]
        nxt = pe.t['TypeDef'][1][ti + 1][5] if ti + 1 < len(pe.t['TypeDef'][1]) else len(pe.t['MethodDef'][1]) + 1
        for mi in range(start, nxt):
            yield ti + 1, mi


def main():
    cmd, path = sys.argv[1], sys.argv[2]
    pe = PE(path)
    if cmd == 'strings':
        o, s = pe.streams['#US']
        i = 1
        while i < s:
            n, k = pe.cint(pe.b, o + i)
            if n == 0:
                i += 1; continue
            txt = pe.b[o + i + k:o + i + k + n - 1].decode('utf-16-le', 'replace')
            print('%06x %r' % (i, txt))
            i += k + n
    elif cmd == 'types':
        for ti, tr in enumerate(pe.t['TypeDef'][1]):
            print(pe.typedef_name(ti + 1))
            fs = tr[4]
            fe = pe.t['TypeDef'][1][ti + 1][4] if ti + 1 < len(pe.t['TypeDef'][1]) else len(pe.t.get('Field', ([], []))[1]) + 1
            for fi in range(fs, fe):
                fr = pe.row('Field', fi)
                sig = pe.blob(fr[2])
                try:
                    ft = pe.sig_type(sig, 1)[0]
                except Exception:
                    ft = '?'
                print('    field %s %s' % (ft, pe.string(fr[1])))
        for ti, mi in all_methods(pe):
            mr = pe.row('MethodDef', mi)
            print('  %s::%s %s' % (pe.typedef_name(ti), pe.string(mr[3]), pe.method_sig(pe.blob(mr[4]))))
    elif cmd == 'il':
        sub = sys.argv[3] if len(sys.argv) > 3 else ''
        for ti, mi in all_methods(pe):
            mr = pe.row('MethodDef', mi)
            full = '%s::%s' % (pe.typedef_name(ti), pe.string(mr[3]))
            if sub in full:
                print('%s %s' % (full, pe.method_sig(pe.blob(mr[4]))))
                for line in disasm(pe, mi):
                    print(line)
                print()


if __name__ == '__main__':
    main()


def attrs(pe, sub=''):
    """Custom attributes on properties/fields/types whose owner name contains sub: constructor and string arguments."""
    cols, rows = pe.t['CustomAttribute']
    prows = pe.t.get('Property', (None, []))[1]
    pmap = pe.t.get('PropertyMap', (None, []))[1]

    def prop_owner(pi):
        own = None
        for r in pmap:
            if r[1] <= pi:
                own = r[0]
        return own
    for parent, ctor, blob in rows:
        pt, pi = pe.coded('HasCustomAttribute', parent)
        if pt == 'Property':
            o = prop_owner(pi)
            name = '%s.%s' % (pe.typedef_name(o) if o else '?', pe.string(prows[pi - 1][1]))
        elif pt == 'TypeDef':
            name = pe.typedef_name(pi)
        elif pt == 'Field':
            name = pe.token((0x04 << 24) | pi)
        else:
            continue
        if sub not in name:
            continue
        ct, ci = pe.coded('CustomAttributeType', ctor)
        cname = pe.token((TID[ct] << 24) | ci)
        b = pe.blob(blob)
        # strings in the blob (SerString: compressed length + utf8; 0xFF = null)
        out = []
        p = 2
        while p < len(b):
            if b[p] == 0xFF:
                out.append(None); p += 1; continue
            try:
                n, k = pe.cint(b, p)
            except IndexError:
                break
            s = b[p + k:p + k + n]
            if n and p + k + n <= len(b) and all(32 <= c < 127 for c in s):
                out.append(s.decode()); p += k + n
            else:
                p += 1
        print('%s  [%s] %s' % (name, cname.split('::')[0].split('.')[-1], out))


if __name__ == '__main__' and sys.argv[1] == 'attrs':
    attrs(PE(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else '')
