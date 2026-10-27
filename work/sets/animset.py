"""Decode UEndAnimSet exports (unversioned property serialization, UE 4.26)."""
import sys, os, struct
sys.path.insert(0,'/work/cs'); sys.path.insert(0,'/work/gunmoves')
from tagged import Zen, export_layout, export_bytes

SCHEMA = [('DisplayName','name'),('AnimationAssets','map'),('ResidentBlendSequenceName','name'),('ResidentBlendBoneName','name'),
          ('ResidentBlendBoneNames','namearray'),('bDisableLookAt','bool'),('bComponentSpaceLookAt','bool'),('BaseLookAtWeight','float'),
          ('BodyLookAtWeight','float'),('HeadLookAtWeight','float'),('HandConstraintRate','float'),('bUseAim','bool'),('AimOffset','vector'),
          ('bCanBeInCluster','bool')]

def decode(z, data):
    p = 0
    frags = []
    while True:
        v, = struct.unpack_from('<H', data, p); p += 2
        skip = v & 0x7f; zero = bool(v & 0x80); last = bool(v & 0x100); num = v >> 9
        frags.append((skip, zero, num, last))
        if last: break
    zcount = sum(n for s, zf, n, l in frags if zf)
    zbits = []
    if zcount:
        if zcount <= 8: w, = struct.unpack_from('<B', data, p); p += 1; nb = 8
        elif zcount <= 16: w, = struct.unpack_from('<H', data, p); p += 2; nb = 16
        else:
            words = (zcount + 31) // 32; w = 0
            for k in range(words):
                x, = struct.unpack_from('<I', data, p); p += 4; w |= x << (32 * k)
            nb = 32 * words
        zbits = [(w >> i) & 1 for i in range(zcount)]
    idx = 0; zi = 0; out = {}
    def name():
        nonlocal p
        i, n = struct.unpack_from('<II', data, p); p += 8
        s = z.names[i] if i < len(z.names) else '?%d' % i
        return s if n == 0 else '%s_%d' % (s, n - 1)
    for skip, zf, num, last in frags:
        idx += skip
        for k in range(num):
            fname, ftype = SCHEMA[idx]
            isz = zf and zbits[zi] == 1
            if zf: zi += 1
            if isz:
                out[fname] = '(zero)'
            elif ftype == 'name': out[fname] = name()
            elif ftype == 'bool': out[fname] = data[p] != 0; p += 1
            elif ftype == 'float': out[fname], = struct.unpack_from('<f', data, p); p += 4
            elif ftype == 'vector': out[fname] = struct.unpack_from('<fff', data, p); p += 12
            elif ftype == 'namearray':
                n, = struct.unpack_from('<i', data, p); p += 4
                out[fname] = [name() for _ in range(n)]
            elif ftype == 'map':
                rem, n = struct.unpack_from('<ii', data, p); p += 8
                m = []
                for _ in range(n):
                    key = name(); obj, = struct.unpack_from('<i', data, p); p += 4
                    m.append((key, obj))
                out[fname] = m
            idx += 1
    return out, p

if __name__ == '__main__':
    for n in sys.argv[1:]:
        d = open(n, 'rb').read(); z = Zen(d); L = export_layout(z)
        for i, e in enumerate(z.exports):
            x = export_bytes(z, i, L)
            try:
                props, end = decode(z, x)
            except Exception as ex:
                print('==', os.path.basename(n), e['name'], 'ERROR', ex); continue
            m = props.pop('AnimationAssets', [])
            print('==', os.path.basename(n).replace('Motion__','').replace('.uasset',''), e['name'], 'animations:', len(m) if isinstance(m, list) else m, 'end', end, '/', len(x))
            for k, v in props.items(): print('     %-26s %s' % (k, v))
