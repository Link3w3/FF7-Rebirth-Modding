"""Find FReferenceSkeleton (RawRefBoneInfo + RawRefBonePose) in a cooked zen USkeleton / USkeletalMesh export."""
import sys, struct
sys.path.insert(0,'/work/cs'); sys.path.insert(0,'.')
from zen import Zen
from tagged import export_layout, export_bytes

def find_refskel(z, e):
    names = z.names
    best = None
    for p in range(0, len(e) - 16, 4) if False else range(0, len(e) - 16):
        n = struct.unpack_from('<i', e, p)[0]
        if n < 20 or n > 4000: continue
        q = p + 4
        if q + n * 12 > len(e): continue
        ok = True
        for i in range(n):
            ni, num, parent = struct.unpack_from('<IIi', e, q + i * 12)
            if ni >= len(names) or num > 64 or parent >= i or parent < -1 or (i == 0) != (parent == -1):
                ok = False; break
        if not ok: continue
        bones = []
        for i in range(n):
            ni, num, parent = struct.unpack_from('<IIi', e, q + i * 12)
            bones.append((names[ni] + ('' if num == 0 else '_%d' % (num - 1)), parent))
        r = q + n * 12
        pose = None
        m = struct.unpack_from('<i', e, r)[0] if r + 4 <= len(e) else -1
        if m == n:
            pose = []
            for i in range(n):
                vals = struct.unpack_from('<10f', e, r + 4 + i * 40)
                pose.append((vals[0:4], vals[4:7], vals[7:10]))  # quat, translation, scale
        cand = (n, p, bones, pose)
        if best is None or n > best[0]: best = cand
    return best

def load(path):
    z = Zen(open(path, 'rb').read()); L = export_layout(z)
    out = None
    for i, ex in enumerate(z.exports):
        e = export_bytes(z, i, L)
        if len(e) < 1000: continue
        r = find_refskel(z, e)
        if r and (out is None or r[0] > out[0]): out = r
    return out

if __name__ == '__main__':
    for p in sys.argv[1:]:
        r = load(p)
        if not r: print(p, 'no ref skeleton'); continue
        n, off, bones, pose = r
        print(p.split('__')[-1], n, 'bones at', off, 'pose' if pose else 'no pose')
