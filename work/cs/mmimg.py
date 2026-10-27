import struct
class MMAsset:
    """UMemoryMappedAsset export payload (after UObject properties)."""
    def __init__(self, e, names, prop_end):
        self.e = e; self.names = names
        p = prop_end
        self.prefix = e[:p]
        self.frozen_size, self.size, self.idk, self.padding = struct.unpack_from('<IIHH', e, p); p += 12
        self.pad_bytes = e[p:p+self.padding]; p += self.padding
        self.content_off = p
        self.content = e[p:p+self.frozen_size]; p += self.frozen_size
        self.nvt, self.nsn, self.nmn = struct.unpack_from('<III', e, p); p += 12
        self.vtables = []
        for _ in range(self.nvt):
            h, n = struct.unpack_from('<QI', e, p); p += 12
            pts = [struct.unpack_from('<II', e, p + 8*i) for i in range(n)]; p += 8*n
            self.vtables.append((h, pts))
        self.script_names = []
        for _ in range(self.nsn):
            ni, num, n = struct.unpack_from('<iiI', e, p); p += 12
            offs = list(struct.unpack_from('<%dI' % n, e, p)); p += 4*n
            self.script_names.append(((ni, num), offs))
        self.minimal_names = []
        for _ in range(self.nmn):
            ni, num, n = struct.unpack_from('<iiI', e, p); p += 12
            offs = list(struct.unpack_from('<%dI' % n, e, p)); p += 4*n
            self.minimal_names.append(((ni, num), offs))
        self.end = p
        self.trailer = e[p:]
        # offset -> name string
        self.name_at = {}
        for (ni, num), offs in self.minimal_names:
            s = names[ni] if num == 0 else '%s_%d' % (names[ni], num - 1)
            for o in offs:
                self.name_at[o] = s
    def u32(self, o): return struct.unpack_from('<I', self.content, o)[0]
    def i32(self, o): return struct.unpack_from('<i', self.content, o)[0]
    def ptr(self, o):
        v = struct.unpack_from('<q', self.content, o)[0]
        if v == 0: return None
        assert v & 1, (o, v)
        return o + (v >> 1)
    def arr(self, o):
        return self.ptr(o), self.i32(o+8), self.i32(o+12)
