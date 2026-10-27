"""Crisis Core Reunion (UE 4.27) IoStore reader: encrypted, signed, Oodle-compressed .utoc/.ucas.
The AES key comes from the CCKEY environment variable only (never written anywhere).
    cctoc.py list <utoc> [substring]
    cctoc.py extract <out dir> <substring> [<substring> ...]   (every container in the folder of the first utoc arg: CCPAKS)
"""
import os, sys, struct, ctypes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

def aes():
    k = os.environ.get('CCKEY', '').strip()
    if k.lower().startswith('0x'): k = k[2:]
    key = bytes.fromhex(k)
    assert len(key) == 32, 'CCKEY must be a 32-byte hex key'
    return Cipher(algorithms.AES(key), modes.ECB())

_lib = None
def oodle(data, us):
    global _lib
    if _lib is None:
        _lib = ctypes.CDLL(os.path.expanduser('~/tools/liblibooz.so'))
        _lib.Ooz_Decompress.restype = ctypes.c_int
        _lib.Ooz_Decompress.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_size_t, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int]
    buf = ctypes.create_string_buffer(us + 64)
    r = _lib.Ooz_Decompress(data, len(data), buf, us, 0, 0, 0, None, 0, None, None, None, 0, 0)
    assert r == us, (r, us)
    return buf.raw[:us]

class Toc:
    def __init__(self, path, cipher):
        self.path = path
        d = open(path, 'rb').read()
        assert d[:16] == b'-==--==--==--==-'
        self.version = d[16]
        (hs, n, nb, bes, nm, ml, bsz, dis, parts) = struct.unpack_from('<9I', d, 20)
        self.flags = d[80]
        self.partsize = struct.unpack_from('<Q', d, 88)[0] if self.version >= 3 else 0
        self.parts = max(parts, 1)
        o = hs
        self.ids = [d[o + i * 12:o + i * 12 + 12] for i in range(n)]; o += 12 * n
        self.offlen = []
        for i in range(n):
            b = d[o + i * 10:o + i * 10 + 10]
            self.offlen.append((int.from_bytes(b[0:5], 'big'), int.from_bytes(b[5:10], 'big')))
        o += 10 * n
        if self.version >= 4:
            raise Exception('perfect hash tocs not handled')
        self.blocks = []
        for i in range(nb):
            b = d[o + i * 12:o + i * 12 + 12]
            self.blocks.append((int.from_bytes(b[0:5], 'little'), int.from_bytes(b[5:8], 'little'), int.from_bytes(b[8:11], 'little'), b[11]))
        o += 12 * nb
        self.methods = [d[o + i * ml:o + (i + 1) * ml].rstrip(b'\0').decode() for i in range(nm)]; o += ml * nm
        if self.flags & 4:
            hsz = struct.unpack_from('<i', d, o)[0]; o += 4
            o += hsz * 2 + 20 * nb
        self.bsz = bsz
        self.cipher = cipher
        di = d[o:o + dis]; o += dis
        if self.flags & 2 and dis:
            dec = cipher.decryptor(); di = dec.update(di) + dec.finalize()
        self.files = {}
        if self.flags & 8 and dis:
            self._dirindex(di)
        self.ucas = [os.path.splitext(path)[0] + ('.ucas' if p == 0 else '_s%d.ucas' % p) for p in range(self.parts)]

    def _dirindex(self, b):
        p = [0]
        def u32():
            v = struct.unpack_from('<I', b, p[0])[0]; p[0] += 4; return v
        def fstr():
            n = struct.unpack_from('<i', b, p[0])[0]; p[0] += 4
            if n == 0: return ''
            if n < 0:
                s = b[p[0]:p[0] + (-n) * 2].decode('utf-16-le'); p[0] += (-n) * 2
            else:
                s = b[p[0]:p[0] + n].decode('latin-1'); p[0] += n
            return s.rstrip('\0')
        mount = fstr()
        nd = u32(); dirs = [struct.unpack_from('<4I', b, p[0] + i * 16) for i in range(nd)]; p[0] += 16 * nd
        nf = u32(); files = [struct.unpack_from('<3I', b, p[0] + i * 12) for i in range(nf)]; p[0] += 12 * nf
        ns = u32(); strings = [fstr() for _ in range(ns)]
        NONE = 0xffffffff
        def walk(di, prefix):
            name, child, sib, ff = dirs[di]
            path = prefix + (strings[name] + '/' if name != NONE else '')
            f = ff
            while f != NONE:
                fn, nxt, ud = files[f]; self.files[path + strings[fn]] = ud; f = nxt
            c = child
            while c != NONE:
                walk(c, path); c = dirs[c][2]
        walk(0, mount)

    def read(self, idx):
        o, l = self.offlen[idx]
        first = o // self.bsz; last = (o + l - 1) // self.bsz
        out = bytearray()
        fh = {}
        for bi in range(first, last + 1):
            bo, cs, us, m = self.blocks[bi]
            part = bo // self.partsize if self.parts > 1 else 0
            po = bo - part * self.partsize if self.parts > 1 else bo
            if part not in fh: fh[part] = open(self.ucas[part], 'rb')
            f = fh[part]; f.seek(po)
            raw = f.read((cs + 15) & ~15 if self.flags & 2 else cs)
            if self.flags & 2:
                dec = self.cipher.decryptor(); raw = dec.update(raw) + dec.finalize()
            raw = raw[:cs]
            if m == 0: out += raw[:us]
            else:
                meth = self.methods[m - 1].lower()
                assert meth == 'oodle', meth
                out += oodle(raw, us)
        for f in fh.values(): f.close()
        s = o - first * self.bsz
        return bytes(out[s:s + l])

def tocs(folder, cipher):
    out = []
    for fn in sorted(os.listdir(folder)):
        if fn.endswith('.utoc') and fn != 'global.utoc':
            out.append(Toc(os.path.join(folder, fn), cipher))
    return out

if __name__ == '__main__':
    cmd = sys.argv[1]
    c = aes()
    folder = os.environ.get('CCPAKS', os.path.expanduser('~/mnt/Paks'))
    if cmd == 'list':
        t = Toc(sys.argv[2], c)
        sub = sys.argv[3] if len(sys.argv) > 3 else ''
        for p, ud in sorted(t.files.items()):
            if sub in p: print(ud, t.offlen[ud][1], p)
    elif cmd == 'extract':
        out = sys.argv[2]; subs = sys.argv[3:]
        n = 0; total = 0
        for t in tocs(folder, c):
            for p, ud in t.files.items():
                if not any(s in p for s in subs): continue
                rel = p.split('/Content/', 1)[1] if '/Content/' in p else p.lstrip('./')
                dst = os.path.join(out, rel)
                if os.path.exists(dst): continue
                data = t.read(ud)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                open(dst, 'wb').write(data)
                n += 1; total += len(data)
        print('extracted', n, 'files,', total, 'bytes')
