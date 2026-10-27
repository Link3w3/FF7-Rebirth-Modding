"""SQEX SEAD (.sab inside an SQEXSEADSound uasset): the materials (HCA streams) of a bank."""
import struct, sys

def sab_of(data):
    s = data.find(b'sabf')
    if s < 0:
        raise ValueError('no sabf')
    return s, data[s:]

def chunks(sab):
    out = {}
    o = 0x20
    while o + 0x10 <= len(sab):
        tag = sab[o:o + 4]
        if not tag.strip(b' ').isalpha():
            break
        out[tag.decode().strip()] = struct.unpack_from('<I', sab, o + 8)[0]
        o += 0x10
        if len(out) > 8:
            break
    return out

def hca_header(hdr):
    ver, doff = struct.unpack_from('>HH', hdr, 4)
    p = 8
    info = {'version': ver, 'data_offset': doff}
    while p < doff:
        tag = bytes(b & 0x7f for b in hdr[p:p + 4])
        if tag == b'fmt\0':
            info['channels'] = hdr[p + 4]
            info['rate'] = int.from_bytes(hdr[p + 5:p + 8], 'big')
            info['blocks'], info['mute_head'], info['mute_foot'] = struct.unpack_from('>IHH', hdr, p + 8)
            p += 16
        elif tag == b'comp':
            info['block_size'] = struct.unpack_from('>H', hdr, p + 4)[0]
            p += 16
        elif tag == b'dec\0':
            info['block_size'] = struct.unpack_from('>H', hdr, p + 4)[0]
            p += 12
        elif tag == b'vbr\0':
            p += 8
        elif tag == b'ath\0':
            info['ath'] = struct.unpack_from('>H', hdr, p + 4)[0]
            p += 6
        elif tag == b'loop':
            info['loop'] = struct.unpack_from('>IIHH', hdr, p + 4)
            p += 16
        elif tag == b'ciph':
            info['ciph'] = struct.unpack_from('>H', hdr, p + 4)[0]
            p += 6
        elif tag == b'rva\0':
            info['rva'] = struct.unpack_from('>f', hdr, p + 4)[0]
            p += 8
        elif tag == b'comm':
            p += 5 + hdr[p + 4]
        elif tag == b'pad\0':
            break
        else:
            info['unknown'] = tag
            break
    return info

def materials(data):
    base, sab = sab_of(data)
    ch = chunks(sab)
    mt = ch['mtrl']
    count = struct.unpack_from('<H', sab, mt + 4)[0]
    out = []
    for i in range(count):
        eo = mt + struct.unpack_from('<I', sab, mt + 0x10 + i * 4)[0]
        channels, codec = sab[eo + 4], sab[eo + 5]
        rate, loop_start, loop_end, extra_size, stream_size = struct.unpack_from('<IIIII', sab, eo + 8)
        extra = sab[eo + 0x20:eo + 0x20 + extra_size]
        h = extra.find(b'HCA\0')
        if h < 0:
            h = extra.find(bytes([0xC8, 0xC3, 0xC1, 0x00]))
        info = hca_header(extra[h:]) if h >= 0 else {}
        hca_at = base + eo + 0x20 + h if h >= 0 else -1
        stream_at = base + eo + 0x20 + extra_size
        out.append({'index': i, 'channels': channels, 'codec': codec, 'rate': rate, 'loop': (loop_start, loop_end),
                    'extra_size': extra_size, 'stream_size': stream_size, 'hca_at': hca_at, 'stream_at': stream_at,
                    'pre_hca': extra[:h].hex() if h >= 0 else extra[:16].hex(), 'hca': info})
    return out

def sound_names(data):
    base, sab = sab_of(data)
    names = []
    i = 0
    while True:
        i = sab.find(b'?', i)
        if i < 0:
            break
        j = i + 1
        while j < len(sab) and 32 < sab[j] < 127:
            j += 1
        if j - i > 3 and sab[j] == 0:
            names.append(sab[i + 1:j].decode())
        i = j
        if len(names) > 400:
            break
    return names

if __name__ == '__main__':
    for path in sys.argv[1:]:
        d = open(path, 'rb').read()
        try:
            ms = materials(d)
        except Exception as e:
            print(path.split('__')[-1], 'ERR', e)
            continue
        print(path.split('__')[-1], 'names:', sound_names(d)[:40])
        for m in ms:
            print('   mat', m['index'], 'ch', m['channels'], 'codec', m['codec'], 'rate', m['rate'], 'stream', m['stream_size'],
                  'hca', {k: v for k, v in m['hca'].items() if k in ('blocks', 'block_size', 'ciph', 'rate', 'channels')})
