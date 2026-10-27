"""Minimal PE reader for the game exe: sections, VA <-> file offset, pointers, C strings."""
import struct

class PE:
    def __init__(self, path):
        self.data = data = open(path, 'rb').read()
        e = struct.unpack_from('<I', data, 0x3C)[0]
        assert data[e:e + 4] == b'PE\0\0'
        nsec = struct.unpack_from('<H', data, e + 6)[0]
        optsize = struct.unpack_from('<H', data, e + 20)[0]
        opt = e + 24
        assert struct.unpack_from('<H', data, opt)[0] == 0x20B
        self.base = struct.unpack_from('<Q', data, opt + 24)[0]
        self.sections = []
        s = opt + optsize
        for i in range(nsec):
            name = data[s:s + 8].rstrip(b'\0').decode('latin1')
            vsize, va, rsize, roff = struct.unpack_from('<IIII', data, s + 8)
            flags = struct.unpack_from('<I', data, s + 36)[0]
            self.sections.append(dict(name=name, va=self.base + va, vsize=vsize, off=roff, rsize=rsize, flags=flags,
                                      code=bool(flags & 0x20000000)))
            s += 40

    def section_of(self, va):
        for sec in self.sections:
            if sec['va'] <= va < sec['va'] + max(sec['vsize'], sec['rsize']):
                return sec
        return None

    def off(self, va):
        sec = self.section_of(va)
        if not sec:
            return None
        o = va - sec['va']
        if o >= sec['rsize']:
            return None
        return sec['off'] + o

    def va(self, off):
        for sec in self.sections:
            if sec['off'] <= off < sec['off'] + sec['rsize']:
                return sec['va'] + off - sec['off']
        return None

    def is_code(self, va):
        sec = self.section_of(va)
        return bool(sec and sec['code'])

    def is_data(self, va):
        sec = self.section_of(va)
        return bool(sec and not sec['code'])

    def u64(self, va):
        o = self.off(va)
        return None if o is None else struct.unpack_from('<Q', self.data, o)[0]

    def u32(self, va):
        o = self.off(va)
        return None if o is None else struct.unpack_from('<I', self.data, o)[0]

    def i32(self, va):
        o = self.off(va)
        return None if o is None else struct.unpack_from('<i', self.data, o)[0]

    def cstr(self, va, limit=256):
        if not va:
            return None
        o = self.off(va)
        if o is None:
            return None
        end = self.data.find(b'\0', o, o + limit)
        if end < 0:
            return None
        try:
            return self.data[o:end].decode('utf-8')
        except UnicodeDecodeError:
            return None

    def find_all(self, needle, start=0):
        out = []
        i = self.data.find(needle, start)
        while i >= 0:
            out.append(i)
            i = self.data.find(needle, i + 1)
        return out
