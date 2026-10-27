"""Bones (name, parent, ref pose) of an uncooked (editor) USkeleton / USkeletalMesh package."""
import struct, sys

def summary_names(d):
    p = 0
    def i32():
        nonlocal p; v = struct.unpack_from('<i', d, p)[0]; p += 4; return v
    def u32():
        nonlocal p; v = struct.unpack_from('<I', d, p)[0]; p += 4; return v
    def fstr():
        nonlocal p
        n = i32()
        if n == 0: return ''
        if n < 0:
            s = d[p:p - 2 * n].decode('utf-16-le'); p += -2 * n
        else:
            s = d[p:p + n].decode('latin-1'); p += n
        return s.rstrip('\0')
    assert u32() == 0x9E2A83C1
    legacy = i32()
    if legacy != -4: i32()
    ue4 = i32(); lic = i32()
    n = i32(); p += n * 20
    i32()  # total header size
    fstr()  # folder
    flags = u32()
    name_count = i32(); name_offset = i32()
    p = name_offset
    names = []
    for _ in range(name_count):
        names.append(fstr()); p += 4  # hashes
    return names, ue4

def bones(d, names, expect_min=50):
    """Scan for RawRefBoneInfo (editor layout: FName, int32 parent, FString ExportName) followed by RawRefBonePose."""
    best = None
    for off in range(0, len(d) - 8):
        n = struct.unpack_from('<i', d, off)[0]
        if n < expect_min or n > 5000:
            continue
        p = off + 4; ok = True; out = []
        for i in range(n):
            if p + 16 > len(d): ok = False; break
            ni, num, parent = struct.unpack_from('<iii', d, p); p += 12
            if not (0 <= ni < len(names)) or (i == 0 and parent != -1) or (i > 0 and not 0 <= parent < i):
                ok = False; break
            sl = struct.unpack_from('<i', d, p)[0]; p += 4
            if sl < 0: p += -2 * sl
            elif sl > 256: ok = False; break
            else: p += sl
            nm = names[ni] + ('_%d' % (num - 1) if num else '')
            out.append([nm, parent])
        if not ok:
            continue
        cnt = struct.unpack_from('<i', d, p)[0]
        if cnt != n:
            continue
        p += 4
        poses = []
        for i in range(n):
            q = struct.unpack_from('<4f', d, p); t = struct.unpack_from('<3f', d, p + 16); s = struct.unpack_from('<3f', d, p + 28)
            p += 40
            poses.append((q, t, s))
        for b, ps in zip(out, poses):
            b.extend(ps)
        best = (off, out)
        break
    return best

if __name__ == '__main__':
    d = open(sys.argv[1], 'rb').read()
    names, ue4 = summary_names(d)
    res = bones(d, names)
    print('ue4', ue4, 'names', len(names), 'bones', len(res[1]) if res else None, 'at', res[0] if res else None)

def cooked_bones(d, names, expect_min=50):
    """Cooked layout: RawRefBoneInfo (FName, int32 parent) then RawRefBonePose (FTransform x n)."""
    for off in range(0, len(d) - 8):
        n = struct.unpack_from('<i', d, off)[0]
        if n < expect_min or n > 5000 or off + 4 + 12 * n + 4 + 40 * n > len(d):
            continue
        p = off + 4; ok = True; out = []
        for i in range(n):
            ni, num, parent = struct.unpack_from('<iii', d, p); p += 12
            if not (0 <= ni < len(names)) or (i == 0 and parent != -1) or (i > 0 and not 0 <= parent < i):
                ok = False; break
            out.append([names[ni] + ('_%d' % (num - 1) if num else ''), parent])
        if not ok or struct.unpack_from('<i', d, p)[0] != n:
            continue
        p += 4
        for i in range(n):
            q = struct.unpack_from('<4f', d, p); t = struct.unpack_from('<3f', d, p + 16); s = struct.unpack_from('<3f', d, p + 28); p += 40
            out[i].extend([q, t, s])
        return off, out
    return None

def qmul(a, b):
    ax, ay, az, aw = a; bx, by, bz, bw = b
    return (aw*bx + ax*bw + ay*bz - az*by, aw*by - ax*bz + ay*bw + az*bx, aw*bz + ax*by - ay*bx + az*bw, aw*bw - ax*bx - ay*by - az*bz)

def qrot(q, v):
    x, y, z, w = q; vx, vy, vz = v
    tx = 2*(y*vz - z*vy); ty = 2*(z*vx - x*vz); tz = 2*(x*vy - y*vx)
    return (vx + w*tx + (y*tz - z*ty), vy + w*ty + (z*tx - x*tz), vz + w*tz + (x*ty - y*tx))

def component_space(bl):
    cs = []
    for nm, par, q, t, s in bl:
        if par < 0:
            cs.append((tuple(q), tuple(t)))
        else:
            pq, pt = cs[par]
            cs.append((qmul(pq, q), tuple(a + b for a, b in zip(pt, qrot(pq, t)))))
    return cs
