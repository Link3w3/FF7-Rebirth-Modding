"""SQEX SEAD sound banks (the "sabf" blob of an SQEXSEADSound package), read and written.

Layout (this game's voice banks):
  0x00 'sabf', u8 version, u8 ?, u16 0x10, u8 4, u8 name length + 1, u16 bank id, u32 size of the blob, name at 0x10
  (NUL, padded to 16), then a table of chunks: [tag(4) u16 0 u16 0x10 u32 offset u32 0] for 'snd ', 'seq ', 'trk ', 'mtrl'.
  Each chunk: u8 version, u8 0, u16 0x10, u16 count, ... then u32 offsets (from the chunk) of its entries, padded to 16.
  snd entry: +0x02 u16 header size (0x70: the name follows), +0x08 u32 id, +0x0C f32 volume, +0x24 f32 length (s);
             after the name (padded): 01 00 10 00, u16 index of its sequence, u16 its id.
  seq entry: ... a play command 02 04 02 0c, u16 track index, 4 bytes, u16 track id, f32 length (s); 00 04 01 00 ends.
  trk entry: 02 01 10 00, u16 index, u16 bank id, u16 material index, u16 material id, ...
  mtrl entry: 01 00 20 00, u8 channels, u8 codec (7: HCA), u16 index, u32 rate, u32 loop start, u32 loop end,
              u32 extra size, u32 stream size, u32 id, extra (a 0x10 header, then the HCA header), stream.
The banks this tool writes are a bank of the game's with some materials replaced (and some sounds silenced): the
snd / seq / trk chunks stay as they are but for the lengths and volumes, the mtrl chunk is laid out again."""
import struct


class Bank:
    def __init__(self, sab):
        assert sab[:4] == b'sabf', sab[:4]
        self.sab = bytearray(sab)
        self.size = struct.unpack_from('<I', sab, 0x0C)[0]
        self.bank_id = struct.unpack_from('<H', sab, 0x0A)[0]
        name_end = sab.index(b'\0', 0x10)
        self.name = sab[0x10:name_end].decode('latin-1')
        self.chunks = {}
        o = sab.index(b'snd ', 0x10, 0x200)
        self.table_at = o
        while sab[o:o + 4] in (b'snd ', b'seq ', b'trk ', b'mtrl', b'ins ', b'inst'):
            self.chunks[sab[o:o + 4].decode().strip()] = (o, struct.unpack_from('<I', sab, o + 8)[0])
            o += 0x10
        self.snd = self.entries('snd')
        self.seq = self.entries('seq')
        self.trk = self.entries('trk')
        self.mtrl = self.entries('mtrl')

    def entries(self, tag):
        if tag not in self.chunks:
            return []
        at = self.chunks[tag][1]
        count = struct.unpack_from('<H', self.sab, at + 4)[0]
        return [at + struct.unpack_from('<I', self.sab, at + 0x10 + 4 * i)[0] for i in range(count)]

    # ---- sounds
    def sound(self, i):
        e = self.snd[i]
        hs = struct.unpack_from('<H', self.sab, e + 2)[0]
        name_at = e + hs
        name = bytes(self.sab[name_at:self.sab.index(b'\0', name_at)]).decode('latin-1')
        after = name_at + ((len(name) + 1 + 15) // 16) * 16
        seq_index, seq_id = struct.unpack_from('<HH', self.sab, after + 4)
        return dict(at=e, id=struct.unpack_from('<I', self.sab, e + 8)[0], name=name,
                    volume=struct.unpack_from('<f', self.sab, e + 0x0C)[0], length=struct.unpack_from('<f', self.sab, e + 0x24)[0],
                    seq_index=seq_index, seq_id=seq_id)

    def set_sound(self, i, volume=None, length=None):
        e = self.snd[i]
        if volume is not None:
            struct.pack_into('<f', self.sab, e + 0x0C, volume)
        if length is not None:
            struct.pack_into('<f', self.sab, e + 0x24, length)

    # ---- sequences: the play commands
    def plays(self, i):
        e = self.seq[i]
        end = self.seq[i + 1] if i + 1 < len(self.seq) else self.chunks['trk'][1]
        out = []
        p = e
        while True:
            p = self.sab.find(b'\x02\x04\x02\x0c', p, end)
            if p < 0:
                break
            ti, tid = struct.unpack_from('<H', self.sab, p + 4)[0], struct.unpack_from('<H', self.sab, p + 10)[0]
            out.append(dict(at=p, track_index=ti, track_id=tid, length=struct.unpack_from('<f', self.sab, p + 12)[0]))
            p += 16
        return out

    def set_play_length(self, i, length):
        for c in self.plays(i):
            struct.pack_into('<f', self.sab, c['at'] + 12, length)

    # ---- tracks
    def track(self, i):
        e = self.trk[i]
        idx, bank, mi, mid = struct.unpack_from('<HHHH', self.sab, e + 4)
        return dict(at=e, index=idx, bank=bank, material_index=mi, material_id=mid)

    # ---- the material a sound plays (sound -> its sequence -> the play command's track -> the track's material id)
    def material_of_sound(self, i):
        sd = self.sound(i)
        plays = self.plays(sd['seq_index'])
        assert len(plays) == 1, (sd['name'], len(plays))
        t = self.track(plays[0]['track_index'])
        if not hasattr(self, '_by_id'):
            self._by_id = {struct.unpack_from('<I', self.sab, e + 0x1C)[0]: k for k, e in enumerate(self.mtrl)}
        return self._by_id[t['material_id']]

    # ---- materials
    def material(self, i):
        e = self.mtrl[i]
        ch, codec, idx = self.sab[e + 4], self.sab[e + 5], struct.unpack_from('<H', self.sab, e + 6)[0]
        rate, ls, le, xs, ss, mid = struct.unpack_from('<IIIIII', self.sab, e + 8)
        extra = bytes(self.sab[e + 0x20:e + 0x20 + xs])
        stream = bytes(self.sab[e + 0x20 + xs:e + 0x20 + xs + ss])
        head = bytes(self.sab[e:e + 0x20])
        return dict(at=e, channels=ch, codec=codec, index=idx, rate=rate, loop=(ls, le), extra=extra, stream=stream, id=mid,
                    head=head, length=self.hca_length(extra, rate))

    @staticmethod
    def hca_length(extra, rate):
        h = extra.find(b'HCA\0')
        if h < 0 or not rate:
            return 0.0
        hdr = extra[h:]
        p = 8
        doff = struct.unpack_from('>H', hdr, 6)[0]
        blocks = None
        mute_head = mute_foot = 0
        while p < doff:
            tag = bytes(b & 0x7f for b in hdr[p:p + 4])
            if tag == b'fmt\0':
                blocks, mute_head, mute_foot = struct.unpack_from('>IHH', hdr, p + 8)
                break
            p += 4
        if blocks is None:
            return 0.0
        return max(0.0, (blocks * 1024 - mute_head - mute_foot) / float(rate))

    def write(self, replacements):
        """The blob with materials replaced: {material index: (material dict of another bank)}; the replaced entry keeps
        this bank's index and id. Returns the new sab bytes (the size field updated)."""
        mt = self.chunks['mtrl'][1]
        count = len(self.mtrl)
        table_end = mt + 0x10 + ((4 * count + 15) // 16) * 16
        first = self.mtrl[0]
        assert first >= table_end - 0x10 and first - mt >= 0x10 + 4 * count, (hex(first), hex(table_end))
        out = bytearray(self.sab[:first])            # everything up to the first material, the mtrl offset table included
        offsets = []
        for i in range(count):
            m = self.material(i)
            r = replacements.get(i)
            if r is not None:
                head = bytearray(r['head'])
                struct.pack_into('<H', head, 6, m['index'])
                struct.pack_into('<I', head, 0x1C, m['id'])
                body = bytes(head) + r['extra'] + r['stream']
            else:
                body = m['head'] + m['extra'] + m['stream']
            while len(out) % 16:
                out.append(0)
            offsets.append(len(out) - mt)
            out += body
        while len(out) % 16:
            out.append(0)
        for i, o in enumerate(offsets):
            struct.pack_into('<I', out, mt + 0x10 + 4 * i, o)
        # what followed the last material in the original (nothing but padding in the game's banks)
        last = self.material(count - 1)
        tail_from = last['at'] + 0x20 + len(last['extra']) + len(last['stream'])
        tail = bytes(self.sab[tail_from:self.size])
        assert not tail.strip(b'\0'), ('data after the last material', len(tail))
        struct.pack_into('<I', out, 0x0C, len(out))
        return bytes(out)
