import struct, sys
class Dump:
    def __init__(self, path):
        self.d = d = open(path, 'rb').read()
        sig, ver, nstreams, rva = struct.unpack_from('<4sIII', d, 0)
        assert sig == b'MDMP'
        self.streams = {}
        for i in range(nstreams):
            t, size, r = struct.unpack_from('<III', d, rva + 12 * i)
            self.streams.setdefault(t, []).append((size, r))
        self.mem = []  # (start, size, file offset)
        for size, r in self.streams.get(5, []):
            n = struct.unpack_from('<I', d, r)[0]
            for i in range(n):
                start, dsize, drva = struct.unpack_from('<QII', d, r + 4 + 16 * i)
                self.mem.append((start, dsize, drva))
        for size, r in self.streams.get(9, []):
            n, base = struct.unpack_from('<QQ', d, r)
            off = base
            for i in range(n):
                start, dsize = struct.unpack_from('<QQ', d, r + 16 + 16 * i)
                self.mem.append((start, dsize, off)); off += dsize
        self.mem.sort()
        self.modules = []
        for size, r in self.streams.get(4, []):
            n = struct.unpack_from('<I', d, r)[0]
            for i in range(n):
                o = r + 4 + 108 * i
                base, sz = struct.unpack_from('<QI', d, o)
                name_rva = struct.unpack_from('<I', d, o + 20)[0]
                ln = struct.unpack_from('<I', d, name_rva)[0]
                name = d[name_rva + 4:name_rva + 4 + ln].decode('utf-16-le')
                self.modules.append((base, sz, name.rsplit('\\', 1)[-1]))
        self.threads = {}
        for size, r in self.streams.get(3, []):
            n = struct.unpack_from('<I', d, r)[0]
            for i in range(n):
                o = r + 4 + 48 * i
                tid, sc, pc, teb = struct.unpack_from('<IIIQ', d, o)[0], None, None, None
                tid = struct.unpack_from('<I', d, o)[0]
                stack_start, stack_size, stack_rva = struct.unpack_from('<QII', d, o + 24)
                ctx_size, ctx_rva = struct.unpack_from('<II', d, o + 40)
                self.threads[tid] = dict(stack=(stack_start, stack_size, stack_rva), ctx=(ctx_size, ctx_rva))
        self.exc = None
        for size, r in self.streams.get(6, []):
            tid = struct.unpack_from('<I', d, r)[0]
            code, flags, rec, addr, nparams = struct.unpack_from('<IIQQI', d, r + 8)
            params = struct.unpack_from('<15Q', d, r + 8 + 32 + 4)
            ctx_size, ctx_rva = struct.unpack_from('<II', d, r + 8 + 152)
            self.exc = dict(tid=tid, code=code, addr=addr, nparams=nparams, params=params[:nparams], ctx=(ctx_size, ctx_rva))
    def read(self, addr, n):
        for start, size, off in self.mem:
            if start <= addr and addr + n <= start + size:
                return self.d[off + addr - start: off + addr - start + n]
        return None
    def regs(self, ctx):
        size, rva = ctx
        names = ['Rax', 'Rcx', 'Rdx', 'Rbx', 'Rsp', 'Rbp', 'Rsi', 'Rdi', 'R8', 'R9', 'R10', 'R11', 'R12', 'R13', 'R14', 'R15', 'Rip']
        vals = struct.unpack_from('<17Q', self.d, rva + 0x78)
        return dict(zip(names, vals))
    def where(self, v):
        for base, sz, name in self.modules:
            if base <= v < base + sz:
                return '%s+%x' % (name, v - base)
        return None
