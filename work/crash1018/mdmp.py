"""A small minidump reader: exception, modules, the crashing thread's context and a return-address scan of its stack."""
import struct, sys

def u16s(d, rva):
    n = struct.unpack_from('<I', d, rva)[0]
    return d[rva + 4:rva + 4 + n].decode('utf-16-le', 'replace')

class Dump:
    def __init__(self, path):
        self.d = d = open(path, 'rb').read()
        sig, ver, nstreams, dir_rva = struct.unpack_from('<4sIII', d, 0)
        assert sig == b'MDMP', sig
        self.streams = {}
        for i in range(nstreams):
            t, size, rva = struct.unpack_from('<III', d, dir_rva + 12 * i)
            self.streams.setdefault(t, []).append((size, rva))
        self.modules = []
        for size, rva in self.streams.get(4, []):
            n = struct.unpack_from('<I', d, rva)[0]
            for k in range(n):
                o = rva + 4 + 108 * k
                base, sz, cs, ts, name_rva = struct.unpack_from('<QIIII', d, o)
                self.modules.append((base, sz, u16s(d, name_rva)))
        self.memory = []          # (start, size, file offset)
        for size, rva in self.streams.get(9, []):
            n, base_rva = struct.unpack_from('<QQ', d, rva)
            off = base_rva
            for k in range(n):
                start, sz = struct.unpack_from('<QQ', d, rva + 16 + 16 * k)
                self.memory.append((start, sz, off)); off += sz
        for size, rva in self.streams.get(5, []):
            n = struct.unpack_from('<I', d, rva)[0]
            for k in range(n):
                start, sz, mrva = struct.unpack_from('<QII', d, rva + 4 + 16 * k)
                self.memory.append((start, sz, mrva))
        self.threads = {}
        for size, rva in self.streams.get(3, []):
            n = struct.unpack_from('<I', d, rva)[0]
            for k in range(n):
                o = rva + 4 + 48 * k
                tid, susp, pclass, prio, teb, st_start, st_size, st_rva, ctx_size, ctx_rva = struct.unpack_from('<IIIIQQIIII', d, o)
                self.threads[tid] = dict(teb=teb, stack=(st_start, st_size, st_rva), ctx=(ctx_size, ctx_rva))

    def module_of(self, addr):
        for base, sz, name in self.modules:
            if base <= addr < base + sz:
                return name.rsplit('\\', 1)[-1], addr - base
        return None, None

    def read(self, addr, n):
        for start, sz, off in self.memory:
            if start <= addr and addr + n <= start + sz:
                return self.d[off + addr - start: off + addr - start + n]
        return None

    def exception(self):
        for size, rva in self.streams.get(6, []):
            tid = struct.unpack_from('<I', self.d, rva)[0]
            code, flags, rec, addr, nparams = struct.unpack_from('<IIQQI', self.d, rva + 8)
            params = struct.unpack_from('<15Q', self.d, rva + 8 + 32)
            ctx_size, ctx_rva = struct.unpack_from('<II', self.d, rva + 8 + 32 + 120)
            return dict(tid=tid, code=code, flags=flags, addr=addr, params=params[:nparams], ctx=(ctx_size, ctx_rva))
        return None

    def context(self, ctx):
        size, rva = ctx
        # x64 CONTEXT: P1Home..P6Home (48), ContextFlags, MxCsr (8), segs (12) + EFlags (4), Dr0-7 (48), then Rax..R15, Rip
        names = ['Rax', 'Rcx', 'Rdx', 'Rbx', 'Rsp', 'Rbp', 'Rsi', 'Rdi', 'R8', 'R9', 'R10', 'R11', 'R12', 'R13', 'R14', 'R15', 'Rip']
        vals = struct.unpack_from('<17Q', self.d, rva + 0x78)
        return dict(zip(names, vals))

if __name__ == '__main__':
    dm = Dump(sys.argv[1])
    ex = dm.exception()
    print('exception code 0x%08x flags %d at 0x%x params %s thread %d' % (ex['code'], ex['flags'], ex['addr'], [hex(p) for p in ex['params']], ex['tid']))
    print('  in', dm.module_of(ex['addr']))
    ctx = dm.context(ex['ctx'])
    print('  ', ', '.join('%s=%x' % kv for kv in ctx.items()))
    print('modules:', len(dm.modules))
    for base, sz, name in dm.modules[:6]: print('   %x %x %s' % (base, sz, name))
    # return addresses on the crashing thread's stack
    rsp = ctx['Rsp']
    st = dm.threads.get(ex['tid'])
    print('stack scan from rsp %x' % rsp)
    shown = 0
    for k in range(0, 0x6000, 8):
        b = dm.read(rsp + k, 8)
        if not b: break
        v = struct.unpack('<Q', b)[0]
        m, off = dm.module_of(v)
        if m:
            print('   [rsp+%04x] %s+0x%x' % (k, m, off)); shown += 1
            if shown > 60: break
