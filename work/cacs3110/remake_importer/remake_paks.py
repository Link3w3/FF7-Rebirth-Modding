"""FINAL FANTASY VII REMAKE's pak files (UE 4.18, pak version 4): AES-256 (ECB) encrypted indexes, Oodle (Kraken) and
zlib compressed blocks. No third-party modules are needed for the pak format itself:

  AES     Windows CNG (bcrypt.dll, through ctypes); else the `cryptography` package if it is installed; else a numpy
          implementation (numpy is installed by the importer anyway). Each one is self-tested before it is used.
  Oodle   ooz.dll (built once by build_ooz.cmd from the ooz source next to it), or an oo2core_*_win64.dll put next to
          this file; on Linux libooz.so. Remake ships no Oodle DLL of its own.

The AES key is handed in by the caller as bytes and kept in memory only: it is never written, logged or printed here,
and no error message contains it.
"""
import ctypes
import glob
import os
import struct
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
PAK_MAGIC = 0x5A6F12E1
FOOTER = 45                 # (4.18, pak v4) encrypted-index flag, magic, version, index offset, index size, index hash


class PakError(Exception):
    pass


class KeyError_(PakError):
    """The key is malformed or does not open the game's paks."""


# ---------------------------------------------------------------------------------------------------------------------
# AES-256 ECB (decryption only)
# ---------------------------------------------------------------------------------------------------------------------

# FIPS-197 appendix C.3 (AES-256): every backend has to give this back before it is used
_TEST_KEY = bytes(range(32))
_TEST_PT = bytes.fromhex('00112233445566778899aabbccddeeff')
_TEST_CT = bytes.fromhex('8ea2b7ca516745bfeafc49904b496089')


def parse_key(text):
    """The user's key text (hex, 64 digits, an optional 0x, spaces allowed) -> 32 bytes. The message of a bad key never
    repeats it."""
    s = ''.join(str(text).split())
    if s[:2] in ('0x', '0X'):
        s = s[2:]
    if not s:
        raise KeyError_('no key was typed')
    if any(c not in '0123456789abcdefABCDEF' for c in s):
        raise KeyError_('the key has characters that are not hex digits (0-9, a-f)')
    if len(s) != 64:
        raise KeyError_('the key has %d hex digits; an AES-256 key has 64' % len(s))
    return bytes.fromhex(s)


class _CngAes(object):
    """AES-256 ECB through Windows CNG (bcrypt.dll)."""
    name = 'Windows CNG'

    def __init__(self, key):
        from ctypes import wintypes
        b = ctypes.WinDLL('bcrypt.dll')
        H, UL = ctypes.c_void_p, wintypes.ULONG
        b.BCryptOpenAlgorithmProvider.argtypes = [ctypes.POINTER(H), ctypes.c_wchar_p, ctypes.c_wchar_p, UL]
        b.BCryptSetProperty.argtypes = [H, ctypes.c_wchar_p, ctypes.c_void_p, UL, UL]
        b.BCryptGenerateSymmetricKey.argtypes = [H, ctypes.POINTER(H), ctypes.c_void_p, UL, ctypes.c_void_p, UL, UL]
        b.BCryptDecrypt.argtypes = [H, ctypes.c_void_p, UL, ctypes.c_void_p, ctypes.c_void_p, UL, ctypes.c_void_p, UL,
                                    ctypes.POINTER(UL), UL]
        b.BCryptDestroyKey.argtypes = [H]
        b.BCryptCloseAlgorithmProvider.argtypes = [H, UL]
        for fn in (b.BCryptOpenAlgorithmProvider, b.BCryptSetProperty, b.BCryptGenerateSymmetricKey, b.BCryptDecrypt,
                   b.BCryptDestroyKey, b.BCryptCloseAlgorithmProvider):
            fn.restype = ctypes.c_long          # NTSTATUS
        self._b, self._ulong = b, UL
        self._alg, self._key = H(), H()
        self._check(b.BCryptOpenAlgorithmProvider(ctypes.byref(self._alg), 'AES', None, 0), 'BCryptOpenAlgorithmProvider')
        mode = ctypes.create_unicode_buffer('ChainingModeECB')
        self._check(b.BCryptSetProperty(self._alg, 'ChainingMode', mode, ctypes.sizeof(mode), 0), 'BCryptSetProperty')
        secret = ctypes.create_string_buffer(bytes(key), len(key))
        try:
            self._check(b.BCryptGenerateSymmetricKey(self._alg, ctypes.byref(self._key), None, 0, secret, len(key), 0),
                        'BCryptGenerateSymmetricKey')
        finally:
            ctypes.memset(secret, 0, len(key))

    @staticmethod
    def _check(status, what):
        if status != 0:
            raise OSError('%s failed (NTSTATUS 0x%08X)' % (what, status & 0xFFFFFFFF))

    def decrypt(self, data):
        n = len(data)
        if n % 16:
            raise ValueError('AES data of %d bytes (not whole blocks)' % n)
        if not n:
            return b''
        src = ctypes.create_string_buffer(bytes(data), n)
        dst = ctypes.create_string_buffer(n)
        got = self._ulong(0)
        self._check(self._b.BCryptDecrypt(self._key, src, n, None, None, 0, dst, n, ctypes.byref(got), 0), 'BCryptDecrypt')
        return dst.raw[:got.value]

    def close(self):
        try:
            if self._key:
                self._b.BCryptDestroyKey(self._key)
            if self._alg:
                self._b.BCryptCloseAlgorithmProvider(self._alg, 0)
        except Exception:
            pass
        self._key = self._alg = None


class _CryptographyAes(object):
    name = 'cryptography'

    def __init__(self, key):
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        self._cipher = Cipher(algorithms.AES(bytes(key)), modes.ECB())

    def decrypt(self, data):
        d = self._cipher.decryptor()
        return d.update(bytes(data)) + d.finalize()

    def close(self):
        self._cipher = None


def _gmul(a, b):
    p = 0
    while b:
        if b & 1:
            p ^= a
        a = ((a << 1) ^ 0x1B) & 0xFF if a & 0x80 else a << 1
        b >>= 1
    return p


def _aes_tables():
    sbox = [0] * 256
    p = q = 1
    while True:                                     # 3 generates the field: p runs over it, q = 1/p
        p = p ^ ((p << 1) & 0xFF) ^ (0x1B if p & 0x80 else 0)
        q ^= (q << 1) & 0xFF
        q ^= (q << 2) & 0xFF
        q ^= (q << 4) & 0xFF
        if q & 0x80:
            q ^= 0x09
        x = q
        for k in (1, 2, 3, 4):
            x ^= ((q << k) | (q >> (8 - k))) & 0xFF
        sbox[p] = x ^ 0x63
        if p == 1:
            break
    sbox[0] = 0x63
    inv = [0] * 256
    for i, v in enumerate(sbox):
        inv[v] = i
    td0 = [(_gmul(inv[x], 14) << 24) | (_gmul(inv[x], 9) << 16) | (_gmul(inv[x], 13) << 8) | _gmul(inv[x], 11) for x in range(256)]
    return sbox, inv, td0


class _NumpyAes(object):
    """AES-256 ECB decryption with numpy (table lookups over every block at once)."""
    name = 'numpy'

    def __init__(self, key):
        import numpy as np
        self.np = np
        key = bytes(key)
        if len(key) != 32:
            raise ValueError('AES-256 needs a 32-byte key')
        sbox, inv, td0 = _aes_tables()
        ror = lambda v, n: ((v >> n) | (v << (32 - n))) & 0xFFFFFFFF
        self.td = [np.array([ror(v, 8 * k) for v in td0], np.uint32) for k in range(4)]
        self.inv = np.array(inv, np.uint32)
        # the encryption key schedule (Nk 8, Nr 14) ...
        w = list(struct.unpack('>8I', key))
        rcon = 1
        for i in range(8, 60):
            t = w[i - 1]
            if i % 8 == 0:
                t = ((t << 8) | (t >> 24)) & 0xFFFFFFFF
                t = (sbox[t >> 24] << 24) | (sbox[(t >> 16) & 255] << 16) | (sbox[(t >> 8) & 255] << 8) | sbox[t & 255]
                t ^= rcon << 24
                rcon = _gmul(rcon, 2)
            elif i % 8 == 4:
                t = (sbox[t >> 24] << 24) | (sbox[(t >> 16) & 255] << 16) | (sbox[(t >> 8) & 255] << 8) | sbox[t & 255]
            w.append(w[i - 8] ^ t)
        # ... and the equivalent inverse cipher's: rounds in reverse, InvMixColumns on the inner ones
        rounds = [w[4 * r:4 * r + 4] for r in range(15)][::-1]
        for r in range(1, 14):
            rounds[r] = [int(self.td[0][sbox[v >> 24]] ^ self.td[1][sbox[(v >> 16) & 255]] ^ self.td[2][sbox[(v >> 8) & 255]]
                             ^ self.td[3][sbox[v & 255]]) for v in rounds[r]]
        self.rk = [[np.uint32(v) for v in rr] for rr in rounds]
        del w, key

    def decrypt(self, data):
        np = self.np
        n = len(data)
        if n % 16:
            raise ValueError('AES data of %d bytes (not whole blocks)' % n)
        out = bytearray()
        T0, T1, T2, T3 = self.td
        IS, rk = self.inv, self.rk
        step = 1 << 22                              # 4 MB at a time
        for at in range(0, n, step):
            blk = np.frombuffer(bytes(data[at:at + step]), dtype='>u4').astype(np.uint32).reshape(-1, 4)
            s0, s1, s2, s3 = (blk[:, k] ^ rk[0][k] for k in range(4))
            for r in range(1, 14):
                k = rk[r]
                t0 = T0[s0 >> 24] ^ T1[(s3 >> 16) & 255] ^ T2[(s2 >> 8) & 255] ^ T3[s1 & 255] ^ k[0]
                t1 = T0[s1 >> 24] ^ T1[(s0 >> 16) & 255] ^ T2[(s3 >> 8) & 255] ^ T3[s2 & 255] ^ k[1]
                t2 = T0[s2 >> 24] ^ T1[(s1 >> 16) & 255] ^ T2[(s0 >> 8) & 255] ^ T3[s3 & 255] ^ k[2]
                t3 = T0[s3 >> 24] ^ T1[(s2 >> 16) & 255] ^ T2[(s1 >> 8) & 255] ^ T3[s0 & 255] ^ k[3]
                s0, s1, s2, s3 = t0, t1, t2, t3
            k = rk[14]
            o0 = (IS[s0 >> 24] << 24) ^ (IS[(s3 >> 16) & 255] << 16) ^ (IS[(s2 >> 8) & 255] << 8) ^ IS[s1 & 255] ^ k[0]
            o1 = (IS[s1 >> 24] << 24) ^ (IS[(s0 >> 16) & 255] << 16) ^ (IS[(s3 >> 8) & 255] << 8) ^ IS[s2 & 255] ^ k[1]
            o2 = (IS[s2 >> 24] << 24) ^ (IS[(s1 >> 16) & 255] << 16) ^ (IS[(s0 >> 8) & 255] << 8) ^ IS[s3 & 255] ^ k[2]
            o3 = (IS[s3 >> 24] << 24) ^ (IS[(s2 >> 16) & 255] << 16) ^ (IS[(s1 >> 8) & 255] << 8) ^ IS[s0 & 255] ^ k[3]
            out += np.stack([o0, o1, o2, o3], 1).astype('>u4').tobytes()
        return bytes(out)

    def close(self):
        self.rk = None


def aes_backends():
    return ([_CngAes] if os.name == 'nt' else []) + [_CryptographyAes, _NumpyAes]


def make_aes(key, backends=None, notes=None):
    """An AES-256 ECB decryptor for `key` (32 bytes) from the first backend that passes the FIPS-197 self-test."""
    failed = []
    for cls in backends or aes_backends():
        try:
            probe = cls(_TEST_KEY)
            ok = probe.decrypt(_TEST_CT) == _TEST_PT
            probe.close()
            if not ok:
                raise RuntimeError('wrong result in its self-test')
            return cls(key)
        except Exception as ex:                    # (messages never hold the key: only the test key went in)
            failed.append('%s: %s' % (cls.name, str(ex).splitlines()[0] if str(ex) else type(ex).__name__))
    raise PakError('no AES decryption works here (%s)' % '; '.join(failed))


# ---------------------------------------------------------------------------------------------------------------------
# Oodle
# ---------------------------------------------------------------------------------------------------------------------

def oodle_candidates():
    if os.name == 'nt':
        names = ['ooz.dll', 'oo2core_9_win64.dll', 'oo2core_8_win64.dll', 'oo2core_7_win64.dll', 'oo2core_6_win64.dll']
    else:
        names = ['libooz.so', 'liboo2corelinux64.so.9', 'liboo2corelinux64.so']
    out = []
    for d in (HERE, os.path.join(HERE, 'ooz')):
        for n in names:
            out.append(os.path.join(d, n))
    return out


# a Kraken stream made for the self-test (of the text below, by Oodle's own compressor): every decompressor found has to
# give the text back before it is used
_OODLE_TEST = bytes.fromhex(
    '8c060000bc8000ba52656d616b652049300230005e00011b0b0211090052d706f5fdf4b90ff35301bbc4ca03bcd5ad004835f041452f43f7'
    'b8fd52fe0205bdfb4f16aefbfeff500db1f756fbfdfbec1116b5440df5bfa9f7f7f7f7f7f701010100000000000000000c10aeaeaeaeaeb112'
    '0001300100001e003dcfff3e3e3e3e3e3d3d3d3d3d3d3d3d3d3e3d3d3d0e109e9e9e9e9d0100000207053001040020003b33070c3a3a3a3a3a'
    '3b3b3b3b3b3b3b3b3b3a3b3b3b160f109e9e9e9e8c0110a0')
_OODLE_TEXT = b''.join(b'Remake Importer self-test %04d: the quick brown fox jumps over the lazy dog. ' % i for i in range(64))


class Oodle(object):
    """Oodle (Kraken) decompression through ooz (Ooz_Decompress) or Oodle's own oo2core (OodleLZ_Decompress): the
    same arguments."""

    def __init__(self, path=None):
        tried = [path] if path else oodle_candidates()
        found = [p for p in tried if p and os.path.isfile(p)]
        if not found:
            raise PakError('no Oodle decompressor: ooz.dll is not built yet (run build_ooz.cmd once, in %s)' % HERE)
        self.path = found[0]
        try:
            lib = ctypes.CDLL(self.path)
        except OSError as ex:
            raise PakError('%s does not load (%s)' % (self.path, ex))
        fn = None
        for symbol in ('Ooz_Decompress', 'OodleLZ_Decompress'):
            fn = getattr(lib, symbol, None)
            if fn is not None:
                self.symbol = symbol
                break
        if fn is None:
            raise PakError('%s has neither Ooz_Decompress nor OodleLZ_Decompress' % self.path)
        c = ctypes
        fn.argtypes = [c.c_char_p, c.c_ssize_t, c.c_void_p, c.c_ssize_t, c.c_int, c.c_int, c.c_int, c.c_void_p, c.c_ssize_t,
                       c.c_void_p, c.c_void_p, c.c_void_p, c.c_ssize_t, c.c_int]
        fn.restype = c.c_int
        self._lib, self._fn = lib, fn
        try:
            ok = self.decompress(_OODLE_TEST, len(_OODLE_TEXT)) == _OODLE_TEXT
        except PakError:
            ok = False
        if not ok:
            raise PakError('%s loads but does not decompress its self-test correctly (rebuild it with build_ooz.cmd)' % self.path)

    def decompress(self, src, n):
        dst = ctypes.create_string_buffer(n + 64)          # (the decoder may write a little past the end)
        got = self._fn(bytes(src), len(src), dst, n, 0, 0, 0, None, 0, None, None, None, 0, 3)
        if got != n:
            raise PakError('Oodle gave %d of %d bytes (%s)' % (got, n, os.path.basename(self.path)))
        return dst.raw[:n]


# ---------------------------------------------------------------------------------------------------------------------
# pak files
# ---------------------------------------------------------------------------------------------------------------------

class Pak(object):
    """One pak file: its decrypted index, and its entries read on demand."""

    def __init__(self, path, aes):
        self.path = path
        with open(path, 'rb') as f:
            f.seek(0, 2)
            size = f.tell()
            if size < FOOTER:
                raise PakError('%s is too small to be a pak file' % os.path.basename(path))
            f.seek(size - FOOTER)
            foot = f.read(FOOTER)
            magic, self.version, ioff, isize = struct.unpack_from('<IIqq', foot, 1)
            if magic != PAK_MAGIC:
                raise PakError('%s is not a pak file this reader knows (UE 4.18, version 4)' % os.path.basename(path))
            if not (0 < isize < size and 0 <= ioff <= size - isize):
                raise PakError('%s: its index is outside the file' % os.path.basename(path))
            self.encrypted_index = bool(foot[0])
            f.seek(ioff)
            data = f.read(isize)
        if self.encrypted_index:
            if aes is None:
                raise KeyError_('the paks are encrypted: the AES key is needed')
            data = aes.decrypt(data[:len(data) & ~15])
        self.data = data
        n = struct.unpack_from('<i', data, 0)[0]
        mount = data[4:4 + n - 1] if 0 < n < 1024 else b''
        if not mount.startswith(b'../') or not all(32 <= ch < 127 for ch in mount):
            raise KeyError_('the key does not open %s (its index does not decrypt to a file list): check the key' % os.path.basename(path))
        self.mount = mount.decode('ascii')
        self.count = struct.unpack_from('<i', data, 4 + n)[0]
        self._first = 8 + n

    def names(self):
        """(name, record position) of every entry; the name has the mount point in front."""
        d, ver, mount = self.data, self.version, self.mount
        unpack = struct.unpack_from
        p = self._first
        for _ in range(self.count):
            ln = unpack('<i', d, p)[0]
            p += 4
            if ln >= 0:
                name = d[p:p + ln].decode('latin-1').rstrip('\0')
                p += ln
            else:
                name = d[p:p - 2 * ln].decode('utf-16-le').rstrip('\0')
                p += -2 * ln
            rec = p
            comp = unpack('<i', d, p + 24)[0]
            p += 48
            if ver >= 3:
                if comp:
                    p += 4 + 16 * unpack('<i', d, p)[0]
                p += 5
            yield mount + name, rec

    def entry(self, rec):
        d = self.data
        off, size, usize, comp = struct.unpack_from('<qqqi', d, rec)
        p = rec + 48
        blocks, enc, bsize = [], 0, 0
        if self.version >= 3:
            if comp:
                nb = struct.unpack_from('<i', d, p)[0]
                p += 4
                blocks = [struct.unpack_from('<qq', d, p + 16 * k) for k in range(nb)]
                p += 16 * nb
            enc = d[p]
            bsize = struct.unpack_from('<I', d, p + 1)[0]
        return dict(offset=off, size=size, usize=usize, comp=comp, enc=enc, bsize=bsize, blocks=blocks)

    def read(self, rec, aes, oodle):
        e = self.entry(rec)
        hsize = 48
        if self.version >= 3:
            if e['comp']:
                hsize += 4 + 16 * len(e['blocks'])
            hsize += 5
        with open(self.path, 'rb') as f:
            if e['comp'] == 0:
                f.seek(e['offset'] + hsize)
                n = (e['size'] + 15) & ~15 if e['enc'] else e['size']
                d = f.read(n)
                if e['enc']:
                    d = aes.decrypt(d)
                return d[:e['size']]
            out, done = [], 0
            for a, b in e['blocks']:
                start = a if self.version < 5 else e['offset'] + a      # (4.18: block offsets are absolute)
                ln = b - a
                f.seek(start)
                d = f.read((ln + 15) & ~15 if e['enc'] else ln)
                if e['enc']:
                    d = aes.decrypt(d)[:ln]
                if e['comp'] == 1:
                    piece = zlib.decompress(d)
                elif e['comp'] == 4:
                    if oodle is None:
                        raise PakError('this file is Oodle-compressed: ooz.dll is needed (run build_ooz.cmd once)')
                    piece = oodle.decompress(d, min(e['bsize'], e['usize'] - done))
                else:
                    raise PakError('compression method %d is not known here' % e['comp'])
                out.append(piece)
                done += len(piece)
        data = b''.join(out)
        if len(data) != e['usize']:
            raise PakError('a file came out with %d of its %d bytes' % (len(data), e['usize']))
        return data


def paks_folder(game_dir):
    """The game's End/Content/Paks folder, from the install folder (or that folder itself)."""
    game_dir = os.path.abspath(os.path.expanduser(game_dir))
    for cand in (os.path.join(game_dir, 'End', 'Content', 'Paks'), os.path.join(game_dir, 'Content', 'Paks'), game_dir):
        if glob.glob(os.path.join(cand, '*.pak')):
            return cand
    raise PakError('no .pak files under %s (pick the FINAL FANTASY VII REMAKE install folder, the one with ff7remake.exe)'
                   % game_dir)


class GameIndex(object):
    """Every file of every pak: name (End/Content/..., no mount prefix) -> where it is."""

    def __init__(self, game_dir, aes, oodle=None, log=None):
        self.folder = paks_folder(game_dir)
        self.aes, self.oodle = aes, oodle
        self.paks, self.files = [], {}
        self.duplicates = 0
        for path in sorted(glob.glob(os.path.join(self.folder, '*.pak'))):
            pak = Pak(path, aes)
            k = len(self.paks)
            self.paks.append(pak)
            files = self.files
            for name, rec in pak.names():
                while name.startswith('../'):
                    name = name[3:]
                if name in files:
                    self.duplicates += 1
                files[name] = (k << 40) | rec
            if log:
                log('  %s: %d files' % (os.path.basename(path), pak.count))
        self.count = len(self.files)

    def has(self, name):
        return name in self.files

    def read(self, name):
        v = self.files[name]
        return self.paks[v >> 40].read(v & ((1 << 40) - 1), self.aes, self.oodle)

    def size(self, name):
        v = self.files[name]
        return self.paks[v >> 40].entry(v & ((1 << 40) - 1))['usize']


def game_to_file(game_path):
    """'/Game/GameContents/X/Y' (a package path, an optional .Object after it) -> 'End/Content/GameContents/X/Y'."""
    p = game_path.split('.')[0] if '.' in game_path.rsplit('/', 1)[-1] else game_path
    if p.startswith('/Game/'):
        return 'End/Content/' + p[6:]
    if p.startswith('/Engine/'):
        return 'Engine/Content/' + p[8:]
    return None


def file_to_game(name):
    if name.startswith('End/Content/'):
        return '/Game/' + os.path.splitext(name[12:])[0]
    if name.startswith('Engine/Content/'):
        return '/Engine/' + os.path.splitext(name[15:])[0]
    return None
