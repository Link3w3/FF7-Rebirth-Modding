"""Minimal reader for uncooked UE4.26 .uasset summaries: names, imports, exports."""
import struct, sys
def fstr(b, o):
    n = struct.unpack_from('<i', b, o)[0]; o += 4
    if n == 0: return '', o
    if n > 0: return b[o:o + n - 1].decode('latin1'), o + n
    n = -n; return b[o:o + 2 * n - 2].decode('utf-16le'), o + 2 * n
class Asset:
    def __init__(self, data):
        self.d = d = data
        o = 0
        tag, legacy = struct.unpack_from('<Ii', d, o); o += 8
        assert tag == 0x9E2A83C1, hex(tag)
        if legacy != -4: o += 4  # legacy ue3 version
        self.ue4ver, self.licver = struct.unpack_from('<ii', d, o); o += 8
        ncv = struct.unpack_from('<i', d, o)[0]; o += 4
        o += ncv * 20
        self.total_header, = struct.unpack_from('<i', d, o); o += 4
        self.folder, o = fstr(d, o)
        self.flags, = struct.unpack_from('<I', d, o); o += 4
        self.name_count, self.name_off = struct.unpack_from('<ii', d, o); o += 8
        if self.ue4ver >= 516:  # localization id
            self.loc_id, o = fstr(d, o)
        self.gather_count, self.gather_off = struct.unpack_from('<ii', d, o); o += 8
        self.export_count, self.export_off = struct.unpack_from('<ii', d, o); o += 8
        self.import_count, self.import_off = struct.unpack_from('<ii', d, o); o += 8
        self.dep_off, = struct.unpack_from('<i', d, o); o += 4
        # names
        self.names = []
        p = self.name_off
        for i in range(self.name_count):
            s, p = fstr(d, p); p += 4  # hashes
            self.names.append(s)
        self.imports = []
        p = self.import_off
        for i in range(self.import_count):
            cp, cpn, cn, cnn, outer, on, onn = struct.unpack_from('<iiiiiii', d, p); p += 28
            self.imports.append((self.names[cp], self.names[cn], outer, self.names[on] + ('' if not onn else '_%d' % (onn - 1))))
    def name(self, i): return self.names[i]
if __name__ == '__main__':
    a = Asset(open(sys.argv[1], 'rb').read())
    print('ue4', a.ue4ver, 'lic', a.licver, 'names', a.name_count, 'imports', a.import_count, 'exports', a.export_count)
    for i, imp in enumerate(a.imports): print('  imp', -i - 1, imp)
    print([n for n in a.names][:200])
