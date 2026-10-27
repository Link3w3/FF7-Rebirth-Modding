"""The bone hierarchy of a cooked Control Rig (the CDO's Hierarchy.BoneHierarchy.Bones), read from its unversioned
properties. FRigBone's properties are in the order the game serializes them: its own, then FRigElement's (Name, Index).

    python3 righier.py <rig .uasset>
"""
import struct
import sys
import numpy as np
sys.path[:0] = ['/work/iostore', '/work/cs']
from zen import Zen


class R:
    def __init__(self, z, d, p=0):
        self.z, self.d, self.p = z, d, p

    def u8(self):
        v = self.d[self.p]; self.p += 1; return v

    def u16(self):
        v, = struct.unpack_from('<H', self.d, self.p); self.p += 2; return v

    def i32(self):
        v, = struct.unpack_from('<i', self.d, self.p); self.p += 4; return v

    def f32(self, n):
        v = struct.unpack_from('<%df' % n, self.d, self.p); self.p += 4 * n; return v

    def name(self):
        i, n = struct.unpack_from('<II', self.d, self.p); self.p += 8
        s = self.z.names[i]
        return s if n == 0 else '%s_%d' % (s, n - 1)

    def header(self, count):
        """unversioned header -> list of (property index, is_zero) for the values present"""
        frags = []
        while True:
            f = self.u16()
            skip, zeros, last, num = f & 0x7f, bool(f & 0x80), bool(f & 0x100), f >> 9
            frags.append((skip, zeros, num))
            if last:
                break
        nz = sum(num for skip, zeros, num in frags if zeros)
        mask = 0
        if nz:
            if nz <= 8:
                mask = self.u8()
            elif nz <= 16:
                mask = self.u16()
            else:
                words = (nz + 31) // 32
                for w in range(words):
                    mask |= (self.i32() & 0xffffffff) << (32 * w)
        out, idx, zi = [], 0, 0
        for skip, zeros, num in frags:
            idx += skip
            for _ in range(num):
                z = False
                if zeros:
                    z = bool(mask >> zi & 1); zi += 1
                out.append((idx, z)); idx += 1
        assert idx <= count, (idx, count)
        return out

    def transform(self):
        q, t, s = (0.0, 0.0, 0.0, 1.0), (0.0, 0.0, 0.0), (1.0, 1.0, 1.0)
        for i, z in self.header(3):
            if z:
                q, t, s = [((0, 0, 0, 0), t, s), (q, (0, 0, 0), s), (q, t, (0, 0, 0))][i]
                continue
            if i == 0:
                q = self.f32(4)
            elif i == 1:
                t = self.f32(3)
            else:
                s = self.f32(3)
        return np.array(q), np.array(t), np.array(s)


BONE = ['ParentName', 'ParentIndex', 'InitialTransform', 'GlobalTransform', 'LocalTransform', 'Dependents', 'Type', 'Name', 'Index']


def bone(r):
    v = dict(ParentName=None, ParentIndex=0, Dependents=[], Type=0, Name=None, Index=0)
    for i, z in r.header(len(BONE)):
        k = BONE[i]
        if z:
            if 'Transform' in k:
                v[k] = (np.zeros(4), np.zeros(3), np.zeros(3))
            continue
        if k in ('ParentName', 'Name'):
            v[k] = r.name()
        elif k in ('ParentIndex', 'Index'):
            v[k] = r.i32()
        elif 'Transform' in k:
            v[k] = r.transform()
        elif k == 'Dependents':
            n = r.i32(); v[k] = [r.i32() for _ in range(n)]
        elif k == 'Type':
            v[k] = r.u8()
    return v


def read(path):
    data = open(path, 'rb').read()
    z = Zen(data)
    cdo = [i for i, e in enumerate(z.exports) if e['name'].startswith('Default__')]
    assert len(cdo) == 1
    d = z.export_bytes(cdo[0])
    r = R(z, d)
    top = r.header(13)
    assert [i for i, zz in top][:2] == [1, 2], top
    r.i32()                                  # VM (export index)
    hc = r.header(5)                         # RigHierarchyContainer
    assert hc[0] == (0, False), hc
    bh = r.header(3)                         # RigBoneHierarchy
    assert bh[0] == (0, False), bh
    n = r.i32()
    bones = [bone(r) for _ in range(n)]
    return z, bones, r.p, len(d)


if __name__ == '__main__':
    z, bones, at, size = read(sys.argv[1])
    print(len(bones), 'bones; read to', at, 'of', size)
    for b in bones:
        q, t, s = b['InitialTransform']
        print('%3d %-16s parent %-14s type %d  init t (%.3f %.3f %.3f) q (%.4f %.4f %.4f %.4f)' % (
            b['Index'], b['Name'], b['ParentName'], b['Type'], *t, *q))
