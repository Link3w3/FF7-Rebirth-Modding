"""SQEXSEADSoundAliasNameSetting (a voice bank's aliases): RandomSettings, a map alias -> {RandomProperties: [(SoundName,
RandomWeights)], SilentRatio, bIgnorePreviousSelectedSound}, unversioned properties.
    read(pkg bytes) -> (names, list of (alias, sounds [(name, number, weight)], silent, ignore_prev, (start, end) in export))"""
import struct, sys
sys.path[:0] = ['/work/cs']
from zen import Zen


def header(e, o):
    """FUnversionedHeader at o -> (fragments [(skip, values, has_zeroes)], zero mask bits list, new offset)."""
    frags = []
    while True:
        v = struct.unpack_from('<H', e, o)[0]; o += 2
        skip, zeroes, last, num = v & 0x7f, (v >> 7) & 1, (v >> 8) & 1, v >> 9
        frags.append((skip, num, zeroes))
        if last:
            break
    total_zero_bits = sum(n for s, n, z in frags if z)
    mask = []
    if total_zero_bits:
        if total_zero_bits <= 8:
            b = e[o]; o += 1; mask = [(b >> i) & 1 for i in range(total_zero_bits)]
        elif total_zero_bits <= 16:
            b = struct.unpack_from('<H', e, o)[0]; o += 2; mask = [(b >> i) & 1 for i in range(total_zero_bits)]
        else:
            words = (total_zero_bits + 31) // 32
            for w in range(words):
                b = struct.unpack_from('<I', e, o)[0]; o += 4
                mask += [(b >> i) & 1 for i in range(32)]
            mask = mask[:total_zero_bits]
    return frags, mask, o


def present(frags, mask):
    """Property indices serialized (not zero), in order."""
    out = []
    idx = 0
    zi = 0
    for skip, num, zeroes in frags:
        idx += skip
        for k in range(num):
            if zeroes:
                is_zero = mask[zi]; zi += 1
            else:
                is_zero = 0
            if not is_zero:
                out.append(idx)
            idx += 1
    return out


def read(d):
    z = Zen(d)
    e = z.export_data(0)
    names = z.names
    frags, mask, o = header(e, 0)
    props = present(frags, mask)
    assert props == [2], props            # RandomSettings only
    removed, count = struct.unpack_from('<ii', e, o); o += 8
    assert removed == 0
    out = []
    for _ in range(count):
        start = o
        ki, kn = struct.unpack_from('<II', e, o); o += 8
        f2, m2, o = header(e, o)
        p2 = present(f2, m2)
        sounds, silent, ignore = [], 0.0, False
        for p in p2:
            if p == 0:
                n = struct.unpack_from('<i', e, o)[0]; o += 4
                for _ in range(n):
                    f3, m3, o = header(e, o)
                    p3 = present(f3, m3)
                    nm, num, w = None, 0, 0
                    for q in p3:
                        if q == 0:
                            nm, num = struct.unpack_from('<II', e, o); o += 8
                        elif q == 1:
                            w = struct.unpack_from('<i', e, o)[0]; o += 4
                        else:
                            raise ValueError('element prop %d' % q)
                    sounds.append((names[nm] if nm is not None else None, num, w))
            elif p == 1:
                silent = struct.unpack_from('<f', e, o)[0]; o += 4
            elif p == 2:
                ignore = bool(e[o]); o += 1
            else:
                raise ValueError('value prop %d' % p)
        out.append((names[ki] + ('_%d' % (kn - 1) if kn else ''), sounds, silent, ignore, (start, o)))
    return names, out, o, len(e)


if __name__ == '__main__':
    d = open(sys.argv[1], 'rb').read()
    names, rows, end, size = read(d)
    print(len(rows), 'aliases; end', end, 'of', size)
    for a, s, sil, ig, _ in rows:
        print('%-40s silent %.2f ignore %d  %s' % (a, sil, ig, ', '.join('%s_%d(%d)' % (n, num - 1, w) if num else '%s(%d)' % (n, w) for n, num, w in s)))
