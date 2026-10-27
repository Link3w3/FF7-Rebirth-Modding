import struct
class B:
    """little-endian reader over bytes with a names table"""
    def __init__(self, d, p=0, names=None, end=None):
        self.d, self.p, self.names = d, p, names
        self.end = len(d) if end is None else end
    def raw(self, n):
        if self.p + n > self.end: raise EOFError('read %d at %d past %d' % (n, self.p, self.end))
        v = self.d[self.p:self.p + n]; self.p += n; return v
    def un(self, f):
        n = struct.calcsize(f)
        if self.p + n > self.end: raise EOFError('read %d at %d past %d' % (n, self.p, self.end))
        v = struct.unpack_from(f, self.d, self.p); self.p += n; return v
    def u8(self): return self.un('<B')[0]
    def u16(self): return self.un('<H')[0]
    def i16(self): return self.un('<h')[0]
    def u32(self): return self.un('<I')[0]
    def i32(self): return self.un('<i')[0]
    def i64(self): return self.un('<q')[0]
    def f32(self): return self.un('<f')[0]
    def b32(self):
        v = self.u32()
        if v > 1: raise ValueError('bool32 %d at %d' % (v, self.p - 4))
        return bool(v)
    def name(self):
        i, n = self.un('<ii')
        if self.names is None: return (i, n)
        if not 0 <= i < len(self.names): raise ValueError('bad name %d at %d' % (i, self.p - 8))
        s = self.names[i]
        return s if n == 0 else '%s_%d' % (s, n - 1)
    def fstr(self):
        n = self.i32()
        if n == 0: return ''
        if n < 0: return self.raw(-2 * n).decode('utf-16-le').rstrip('\0')
        if n > 1 << 16: raise ValueError('bad fstring len %d at %d' % (n, self.p - 4))
        return self.raw(n).decode('latin-1').rstrip('\0')
    def arr(self, fn, maxn=1 << 24):
        n = self.i32()
        if not 0 <= n <= maxn: raise ValueError('bad array count %d at %d' % (n, self.p - 4))
        return [fn() for _ in range(n)]
    def bulk_array(self, elem_size=None):
        """TArray::BulkSerialize: int32 element size, int32 count, data"""
        es = self.i32(); n = self.i32()
        if elem_size is not None and es != elem_size: raise ValueError('bulk elem size %d != %d at %d' % (es, elem_size, self.p - 8))
        if not (0 < es <= 256 and 0 <= n < 1 << 26): raise ValueError('bad bulk array %d x %d at %d' % (n, es, self.p - 8))
        return es, n, self.raw(es * n)
    def peek(self, n=64):
        return self.d[self.p:self.p + n].hex(' ')
