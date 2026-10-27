"""Black-box tests of the HCA format against ffmpeg's decoder: a bit writer, header and frame writers (v2.0, no ath,
no cipher, no HFR, discrete channels), and a decode helper."""
import struct, subprocess, os, tempfile
import numpy as np

def crc16(data):
    c = 0
    for b in data:
        c ^= b << 8
        for _ in range(8):
            c = ((c << 1) ^ 0x8005) & 0xFFFF if c & 0x8000 else (c << 1) & 0xFFFF
    return c

class Bits:
    def __init__(self):
        self.bits = []
    def w(self, v, n):
        for i in range(n - 1, -1, -1):
            self.bits.append((v >> i) & 1)
    def tobytes(self, size):
        assert len(self.bits) <= size * 8, (len(self.bits), size * 8)
        b = self.bits + [0] * (size * 8 - len(self.bits))
        return bytes(int(''.join(map(str, b[i:i + 8])), 2) for i in range(0, len(b), 8))

def header(channels, rate, frames, frame_size, delay=0, padding=0, min_res=1, max_res=15):
    h = bytearray(b'HCA\0') + struct.pack('>HH', 0x0200, 96)
    h += b'fmt\0' + bytes([channels]) + rate.to_bytes(3, 'big') + struct.pack('>IHH', frames, delay, padding)
    h += b'comp' + struct.pack('>H', frame_size) + bytes([min_res, max_res, 1, 1 if channels == 1 else 0, 128, 128, 0, 0, 0, 0])
    h += b'ciph' + struct.pack('>H', 0)
    h += b'pad\0'
    h += b'\0' * (94 - len(h))
    return bytes(h) + struct.pack('>H', crc16(h))

MAXBIT = [0, 2, 3, 3, 4, 4, 4, 4, 5, 6, 7, 8, 9, 10, 11, 12]
READBIT = [0]*16 + [1,1,2,2]+[0]*12 + [2,2,2,2,2,2,3,3]+[0]*8 + [2,2,3,3,3,3,3,3]+[0]*8 + [3,3,3,3,3,3,3,3,3,3,3,3,3,3,4,4] + \
          [3,3,3,3,3,3,3,3,3,3,4,4,4,4,4,4] + [3,3,3,3,3,3,4,4,4,4,4,4,4,4,4,4] + [3,3,4,4,4,4,4,4,4,4,4,4,4,4,4,4]
READVAL = [0]*16 + [0,0,1,-1]+[0]*12 + [0,0,1,1,-1,-1,2,-2]+[0]*8 + [0,0,1,-1,2,-2,3,-3]+[0]*8 + \
          [0,0,1,1,-1,-1,2,2,-2,-2,3,3,-3,-3,4,-4] + [0,0,1,1,-1,-1,2,2,-2,-2,3,-3,4,-4,5,-5] + \
          [0,0,1,1,-1,-1,2,-2,3,-3,4,-4,5,-5,6,-6] + [0,0,1,-1,2,-2,3,-3,4,-4,5,-5,6,-6,7,-7]
assert len(READBIT) == 128 and len(READVAL) == 128

def code_of(res, q):
    """(value, nbits) for quantized value q at resolution res"""
    if res == 0:
        assert q == 0
        return 0, 0
    if res > 7:
        n = MAXBIT[res]
        mag = abs(q)
        assert mag < (1 << (n - 1)), (res, q)
        if mag == 0:
            return 0, n - 1
        return (mag << 1) | (1 if q < 0 else 0), n
    mb = MAXBIT[res]
    for code in range(1 << mb):
        idx = (res << 4) + code
        if READVAL[idx] == q:
            nb = READBIT[idx]
            return code >> (mb - nb), nb
    raise ValueError((res, q))

def frame(frame_size, noise, boundary, chans):
    """chans: list of dict(delta_bits=6, sf=[128], res=[128], q=[8][128])"""
    b = Bits()
    b.w(0xFFFF, 16)
    b.w(noise, 9)
    b.w(boundary, 7)
    for ch in chans:
        db = ch.get('delta_bits', 6)
        b.w(db, 3)
        if db >= 6:
            for s in ch['sf']:
                b.w(s, 6)
        elif db > 0:
            raise NotImplementedError
    for sub in range(8):
        for ch in chans:
            for i in range(128):
                v, n = code_of(ch['res'][i], ch['q'][sub][i])
                b.w(v, n)
    body = b.tobytes(frame_size - 2)
    return body + struct.pack('>H', crc16(body))

def decode(hca_bytes, channels=1):
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, 'a.hca')
        open(p, 'wb').write(hca_bytes)
        o = os.path.join(t, 'a.raw')
        r = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', p, '-f', 'f32le', '-acodec', 'pcm_f32le', o], capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(r.stderr)
        x = np.fromfile(o, dtype='<f4')
        return x.reshape(-1, channels) if channels > 1 else x
