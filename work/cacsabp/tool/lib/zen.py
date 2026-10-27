import struct
class Zen:
    def __init__(self, d):
        self.d = d
        (self.name_mapped, self.srcname_mapped, self.flags, self.cooked_header_size, self.nm_off, self.nm_size, self.nh_off, self.nh_size,
         self.imp_off, self.exp_off, self.eb_off, self.graph_off, self.graph_size, self.pad) = struct.unpack_from('<QQIIiiiiiiiiii', d, 0)
        self.names = []
        p = self.nm_off; end = self.nm_off + self.nm_size
        while p < end:
            h0, h1 = d[p], d[p+1]; p += 2
            wide = h0 & 0x80; ln = ((h0 & 0x7f) << 8) | h1
            if wide:
                if p & 1: p += 1
                s = d[p:p+ln*2].decode('utf-16-le'); p += ln*2
            else:
                s = d[p:p+ln].decode('latin-1'); p += ln
            self.names.append(s)
        self.hash_version = struct.unpack_from('<Q', d, self.nh_off)[0]
        self.hashes = list(struct.unpack_from('<%dQ' % ((self.nh_size-8)//8), d, self.nh_off+8))
        self.imports = list(struct.unpack_from('<%dQ' % ((self.exp_off - self.imp_off)//8), d, self.imp_off))
        n_exp = (self.eb_off - self.exp_off) // 72
        self.exports = []
        for i in range(n_exp):
            o = self.exp_off + i*72
            so, ss, objname, outer, cls, sup, tmpl, gimp, oflags, fflags = struct.unpack_from('<QQQQQQQQIB', d, o)
            self.exports.append(dict(serial_offset=so, serial_size=ss, name=self.mapped(objname), outer=outer, cls=cls, super=sup, template=tmpl, global_import=gimp, oflags=oflags, fflags=fflags))
        self.header_end = self.graph_off + self.graph_size
    def mapped(self, v):
        idx = v & 0xffffffff; num = v >> 32
        # FMappedName: index in low 30 bits, type in top 2 bits
        typ = idx >> 30; idx &= 0x3fffffff
        s = self.names[idx] if idx < len(self.names) else '?%d' % idx
        return s if num == 0 else '%s_%d' % (s, num - 1)
    def export_data(self, i=0):
        # exports laid out in bundle order after header; single export case
        e = self.exports[i]
        so = e['serial_offset']
        # retail packages count serial offsets from the cooked header size; some mod tools count from 0
        start = self.header_end + (so - self.cooked_header_size if so >= self.cooked_header_size else so)
        return self.d[start:start + e['serial_size']]

    def bundle_positions(self):
        """{export index: (start, size)} from the export bundles (the data follows the header in bundle order)."""
        import struct as _s
        if getattr(self, '_pos', None) is not None:
            return self._pos
        total = 2 * len(self.exports)
        heads, seen, p = [], 0, self.eb_off
        while seen < total:
            first, count = _s.unpack_from('<II', self.d, p); p += 8
            heads.append((first, count)); seen += count
        ents = [_s.unpack_from('<II', self.d, p + 8 * k) for k in range(total)]
        pos, at = {}, self.header_end
        for first, count in heads:
            for idx, cmd in ents[first:first + count]:
                if cmd == 1:
                    size = self.exports[idx]['serial_size']
                    pos[idx] = (at, size); at += size
        self._pos = pos
        return pos
    def export_bytes(self, i):
        start, size = self.bundle_positions()[i]
        return self.d[start:start + size]
