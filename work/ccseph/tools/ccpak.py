"""Crisis Core Reunion (UE 4.27) .pak reader: pak version 11, encrypted index (AES-256-ECB), path hash and full
directory index, encoded entries, Oodle-compressed (and possibly encrypted) blocks.
The AES key comes from the CCKEY environment variable only (never written anywhere).
    ccpak.py list <pak> [substring]
    ccpak.py extract <pak> <out dir> <substring> [<substring> ...]"""
import os
import struct
import sys
import ctypes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

MAGIC = 0x5A6F12E1


def aes():
    k = os.environ.get('CCKEY', '').strip()
    if k.lower().startswith('0x'):
        k = k[2:]
    key = bytes.fromhex(k)
    assert len(key) == 32, 'CCKEY must be a 32-byte hex key'
    return Cipher(algorithms.AES(key), modes.ECB())


_lib = None


def oodle(data, us):
    global _lib
    if _lib is None:
        _lib = ctypes.CDLL(os.path.expanduser('~/tools/liblibooz.so'))
        _lib.Ooz_Decompress.restype = ctypes.c_int
        _lib.Ooz_Decompress.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_size_t, ctypes.c_int, ctypes.c_int,
                                        ctypes.c_int, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_void_p,
                                        ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int]
    buf = ctypes.create_string_buffer(us + 64)
    r = _lib.Ooz_Decompress(data, len(data), buf, us, 0, 0, 0, None, 0, None, None, None, 0, 0)
    assert r == us, (r, us)
    return buf.raw[:us]


class Rd:
    def __init__(self, b, p=0):
        self.b, self.p = b, p

    def i32(self):
        v = struct.unpack_from('<i', self.b, self.p)[0]; self.p += 4; return v

    def u32(self):
        v = struct.unpack_from('<I', self.b, self.p)[0]; self.p += 4; return v

    def i64(self):
        v = struct.unpack_from('<q', self.b, self.p)[0]; self.p += 8; return v

    def u64(self):
        v = struct.unpack_from('<Q', self.b, self.p)[0]; self.p += 8; return v

    def raw(self, n):
        v = self.b[self.p:self.p + n]; self.p += n; return v

    def fstring(self):
        n = self.i32()
        if n == 0:
            return ''
        if n < 0:
            s = self.raw(-2 * n).decode('utf-16-le')
        else:
            s = self.raw(n).decode('utf-8', 'replace')
        return s.rstrip('\x00')


class Pak:
    def __init__(self, path):
        self.path = path
        self.f = open(path, 'rb')
        size = os.path.getsize(path)
        self.f.seek(size - 221)
        t = self.f.read(221)
        self.guid = t[0:16]
        self.encrypted_index = t[16] != 0
        magic, self.version = struct.unpack_from('<Ii', t, 17)
        assert magic == MAGIC, hex(magic)
        self.index_offset, self.index_size = struct.unpack_from('<qq', t, 25)
        self.methods = [t[61 + 32 * i:61 + 32 * (i + 1)].split(b'\x00')[0].decode() for i in range(5)]
        self.cipher = aes()
        idx = self._read(self.index_offset, self.index_size, self.encrypted_index)
        r = Rd(idx)
        self.mount = r.fstring()
        self.num_entries = r.i32()
        self.seed = r.u64()
        if r.i32():
            r.i64(); r.i64(); r.raw(20)
        has_full = r.i32()
        if has_full:
            fdi_off = r.i64(); fdi_size = r.i64(); r.raw(20)
        n = r.i32()
        self.encoded = r.raw(n)
        nfiles = r.i32()
        self.files = [self._entry_legacy(r) for _ in range(nfiles)]
        self.entries = {}
        if has_full:
            d = Rd(self._read(fdi_off, fdi_size, self.encrypted_index))
            for _ in range(d.i32()):
                dname = d.fstring()
                for _ in range(d.i32()):
                    fname = d.fstring()
                    loc = d.i32()
                    self.entries[(dname + fname).lstrip('/')] = loc

    def _read(self, off, size, encrypted):
        self.f.seek(off)
        b = self.f.read(size)
        if encrypted:
            dec = self.cipher.decryptor()
            b = dec.update(b + b'\x00' * ((-len(b)) % 16)) + dec.finalize()
            b = b[:size]
        return b

    def _entry_legacy(self, r):
        e = dict(offset=r.i64(), size=r.i64(), usize=r.i64(), method=r.u32())
        r.raw(20)
        blocks = []
        if e['method']:
            for _ in range(r.i32()):
                blocks.append((r.i64(), r.i64()))
        flags = r.raw(1)[0]
        e['encrypted'] = bool(flags & 1)
        e['block_size'] = r.u32()
        e['blocks'] = blocks
        e['relative'] = True
        return e

    def decode(self, loc):
        if loc < 0:
            return self.files[-loc - 1]
        b, p = self.encoded, loc
        v = struct.unpack_from('<I', b, p)[0]; p += 4
        if (v & 0x3f) == 0x3f:
            block_size = struct.unpack_from('<I', b, p)[0]; p += 4
        else:
            block_size = (v & 0x3f) << 11
        method = (v >> 23) & 0x3f
        if v & (1 << 31):
            offset = struct.unpack_from('<I', b, p)[0]; p += 4
        else:
            offset = struct.unpack_from('<q', b, p)[0]; p += 8
        if v & (1 << 30):
            usize = struct.unpack_from('<I', b, p)[0]; p += 4
        else:
            usize = struct.unpack_from('<q', b, p)[0]; p += 8
        if method:
            if v & (1 << 29):
                size = struct.unpack_from('<I', b, p)[0]; p += 4
            else:
                size = struct.unpack_from('<q', b, p)[0]; p += 8
        else:
            size = usize
        encrypted = bool(v & (1 << 22))
        nblocks = (v >> 6) & 0xffff
        header = 8 + 8 + 8 + 4 + 20 + 1 + 4 + ((4 + 16 * nblocks) if method else 0)
        blocks = []
        if nblocks:
            if nblocks == 1 and not encrypted:
                blocks.append((header, header + size))
            else:
                cur = header
                for _ in range(nblocks):
                    cs = struct.unpack_from('<I', b, p)[0]; p += 4
                    blocks.append((cur, cur + cs))
                    cur += (cs + 15) // 16 * 16 if encrypted else cs
        return dict(offset=offset, size=size, usize=usize, method=method, encrypted=encrypted, block_size=block_size,
                    blocks=blocks, header=header, relative=True)

    def read(self, name):
        e = self.decode(self.entries[name])
        if not e['method']:
            start = e['offset'] + e['header']
            return self._read(start, e['size'] if not e['encrypted'] else (e['size'] + 15) // 16 * 16, e['encrypted'])[:e['size']]
        method = self.methods[e['method'] - 1].lower()
        assert method.startswith('oodle') or method.startswith('zlib'), method
        if method.startswith('zlib'):
            import zlib
        out = []
        left = e['usize']
        for a, z in e['blocks']:
            n = z - a
            raw = self._read(e['offset'] + a, (n + 15) // 16 * 16 if e['encrypted'] else n, e['encrypted'])[:n]
            us = min(e['block_size'], left)
            if method.startswith('zlib'):
                out.append(zlib.decompress(raw))
            else:
                out.append(oodle(raw, us) if n < us else raw[:us])
            left -= us
        return b''.join(out)


def main():
    cmd = sys.argv[1]
    if cmd == 'list':
        p = Pak(sys.argv[2])
        sub = sys.argv[3] if len(sys.argv) > 3 else ''
        print('mount', p.mount, 'version', p.version, 'entries', p.num_entries, 'methods', [m for m in p.methods if m])
        for n in sorted(p.entries):
            if sub.lower() in n.lower():
                e = p.decode(p.entries[n])
                print('%12d %12d %s' % (e['usize'], e['size'], n))
    elif cmd == 'extract':
        p = Pak(sys.argv[2])
        out = sys.argv[3]
        subs = [s.lower() for s in sys.argv[4:]]
        for n in sorted(p.entries):
            if any(s in n.lower() for s in subs):
                data = p.read(n)
                dst = os.path.join(out, n.replace('../', '').lstrip('/'))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                open(dst, 'wb').write(data)
                print('%10d %s' % (len(data), n))


if __name__ == '__main__':
    main()
