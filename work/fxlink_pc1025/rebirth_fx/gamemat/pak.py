"""Reads a legacy .pak file of UE 4.26 (version 11, path hash + full directory index, not encrypted): its files by path
and their data. The game keeps a few files outside its IoStore containers in pakchunk0 (the shader libraries)."""
import struct
import zlib

ENTRY_HEADER_UNCOMPRESSED = 53     # FPakEntry as serialized in front of an uncompressed file's data (v11)


class PakError(Exception):
    pass


def _fstring(b, p):
    n = struct.unpack_from('<i', b, p)[0]
    p += 4
    if n == 0:
        return '', p
    if n > 0:
        return b[p:p + n - 1].decode('latin-1'), p + n
    n = -n
    return b[p:p + 2 * n - 2].decode('utf-16-le'), p + 2 * n


class Entry(object):
    __slots__ = ('path', 'offset', 'size', 'usize', 'method', 'blocks', 'block_size', 'encrypted')

    def __init__(self, path, offset, size, usize, method, blocks, block_size, encrypted):
        self.path, self.offset, self.size, self.usize = path, offset, size, usize
        self.method, self.blocks, self.block_size, self.encrypted = method, blocks, block_size, encrypted

    def __repr__(self):
        return 'Entry(%s @%d size %d usize %d method %d)' % (self.path, self.offset, self.size, self.usize, self.method)


class Pak(object):
    def __init__(self, path):
        self.path = path
        with open(path, 'rb') as f:
            f.seek(0, 2)
            total = f.tell()
            f.seek(max(0, total - 512))
            tail = f.read()
        at = tail.rfind(struct.pack('<I', 0x5A6F12E1))
        if at < 0:
            raise PakError('%s: no pak footer' % path)
        self.version = struct.unpack_from('<i', tail, at + 4)[0]
        self.index_offset, self.index_size = struct.unpack_from('<qq', tail, at + 8)
        encrypted = tail[at - 1] if at >= 1 else 0
        if self.version < 10:
            raise PakError('%s: pak version %d (this reader takes 10 and 11)' % (path, self.version))
        if encrypted:
            raise PakError('%s: the index is encrypted' % path)
        # compression method names (5 x 32 bytes after the index hash and the frozen flag)
        names = []
        q = at + 8 + 16 + 20
        if self.version >= 9:
            q += 1 if self.version == 9 else 0
        for k in range(5):
            raw = tail[q + 32 * k:q + 32 * (k + 1)]
            if len(raw) < 32:
                break
            names.append(raw.split(b'\0', 1)[0].decode('latin-1'))
        self.methods = [''] + [n for n in names]
        with open(path, 'rb') as f:
            f.seek(self.index_offset)
            idx = f.read(self.index_size)
            self.mount, p = _fstring(idx, 0)
            self.count, self.seed = struct.unpack_from('<iQ', idx, p)
            p += 12
            has_hash = struct.unpack_from('<I', idx, p)[0]
            p += 4
            if has_hash:
                p += 16 + 20
            has_full = struct.unpack_from('<I', idx, p)[0]
            p += 4
            if not has_full:
                raise PakError('%s: no full directory index' % path)
            full_off, full_size = struct.unpack_from('<qq', idx, p)
            p += 16 + 20
            n = struct.unpack_from('<i', idx, p)[0]
            p += 4
            self.encoded = idx[p:p + n]
            p += n
            nfiles = struct.unpack_from('<i', idx, p)[0]
            p += 4
            self.files = []
            for _ in range(nfiles):
                e, p = self._legacy_entry(idx, p)
                self.files.append(e)
            f.seek(full_off)
            fdi = f.read(full_size)
        self.entries = {}
        p = 0
        ndirs = struct.unpack_from('<i', fdi, p)[0]
        p += 4
        for _ in range(ndirs):
            d, p = _fstring(fdi, p)
            nf = struct.unpack_from('<i', fdi, p)[0]
            p += 4
            for _ in range(nf):
                name, p = _fstring(fdi, p)
                loc = struct.unpack_from('<i', fdi, p)[0]
                p += 4
                self.entries[(d + name).lstrip('/')] = loc

    def _legacy_entry(self, b, p):
        offset, size, usize, method = struct.unpack_from('<qqqI', b, p)
        p += 28 + 20
        blocks = []
        if method:
            n = struct.unpack_from('<i', b, p)[0]
            p += 4
            for _ in range(n):
                blocks.append(struct.unpack_from('<qq', b, p))
                p += 16
        flags, block_size = struct.unpack_from('<BI', b, p)
        p += 5
        return (offset, size, usize, method, blocks, block_size, bool(flags & 1)), p

    def _decode(self, loc):
        if loc < 0:
            return self.files[-loc - 1]
        b = self.encoded
        p = loc
        v = struct.unpack_from('<I', b, p)[0]
        p += 4
        if (v & 0x3f) == 0x3f:
            block_size = struct.unpack_from('<I', b, p)[0]
            p += 4
        else:
            block_size = (v & 0x3f) << 11
        method = (v >> 23) & 0x3f
        if v & (1 << 31):
            offset = struct.unpack_from('<I', b, p)[0]
            p += 4
        else:
            offset = struct.unpack_from('<Q', b, p)[0]
            p += 8
        if v & (1 << 30):
            usize = struct.unpack_from('<I', b, p)[0]
            p += 4
        else:
            usize = struct.unpack_from('<Q', b, p)[0]
            p += 8
        if method:
            if v & (1 << 29):
                size = struct.unpack_from('<I', b, p)[0]
                p += 4
            else:
                size = struct.unpack_from('<Q', b, p)[0]
                p += 8
        else:
            size = usize
        encrypted = bool(v & (1 << 22))
        nblocks = (v >> 6) & 0xffff
        blocks = []
        if nblocks:
            # block ranges relative to the entry's offset: they follow its serialized header
            header = ENTRY_HEADER_UNCOMPRESSED + 4 + 16 * nblocks
            if nblocks == 1 and not encrypted:
                blocks.append((header, header + size))
            else:
                start = header
                for _ in range(nblocks):
                    bs = struct.unpack_from('<I', b, p)[0]
                    p += 4
                    blocks.append((start, start + bs))
                    start += (bs + 15) & ~15 if encrypted else bs
        return (offset, size, usize, method, blocks, block_size, encrypted)

    def entry(self, path):
        path = path.lstrip('/')
        if path.startswith(self.mount.lstrip('/')):
            path = path[len(self.mount.lstrip('/')):]
        loc = self.entries.get(path)
        if loc is None:
            raise KeyError('%s is not in %s' % (path, self.path))
        offset, size, usize, method, blocks, block_size, encrypted = self._decode(loc)
        return Entry(path, offset, size, usize, method, blocks, block_size, encrypted)

    def find(self, suffix):
        """Paths ending with suffix (case-insensitive)."""
        s = suffix.lower()
        return sorted(p for p in self.entries if p.lower().endswith(s))

    def data_start(self, e):
        """Where an uncompressed, unencrypted file's bytes start (after its FPakEntry header)."""
        if e.method or e.encrypted:
            raise PakError('%s is compressed or encrypted' % e.path)
        return e.offset + ENTRY_HEADER_UNCOMPRESSED

    def read(self, e, start=0, size=None):
        with open(self.path, 'rb') as f:
            if not e.method and not e.encrypted:
                f.seek(self.data_start(e) + start)
                return f.read(e.usize - start if size is None else size)
            if e.encrypted:
                raise PakError('%s is encrypted' % e.path)
            name = self.methods[e.method] if e.method < len(self.methods) else '?'
            if name.lower() != 'zlib':
                raise PakError('%s: compression %s (this reader takes zlib)' % (e.path, name))
            out = bytearray()
            for a, b in e.blocks:
                f.seek(e.offset + a)
                out += zlib.decompress(f.read(b - a))
            data = bytes(out)
            return data[start:] if size is None else data[start:start + size]
