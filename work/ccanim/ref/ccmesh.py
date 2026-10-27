"""Crisis Core Reunion (UE 4.27, cooked, unversioned) skeletal mesh: its materials, reference skeleton and LOD0 render
data (sections, indices, positions, tangents, UVs, skin weights) from the zen package, into an npz.
    ccmesh.py <SK_*.uasset> <out.npz>"""
import os, sys, struct
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.expanduser('~/mnt/FF7R2UProj/Tools/CrisisCore/tools')]
from zen import Zen
from mesh_bones import find_ref_skeleton
import ccnames

class R:
    def __init__(self, b, p=0): self.b = b; self.p = p
    def u8(self): v = self.b[self.p]; self.p += 1; return v
    def u16(self): v = struct.unpack_from('<H', self.b, self.p)[0]; self.p += 2; return v
    def i16(self): v = struct.unpack_from('<h', self.b, self.p)[0]; self.p += 2; return v
    def u32(self): v = struct.unpack_from('<I', self.b, self.p)[0]; self.p += 4; return v
    def i32(self): v = struct.unpack_from('<i', self.b, self.p)[0]; self.p += 4; return v
    def f32(self): v = struct.unpack_from('<f', self.b, self.p)[0]; self.p += 4; return v
    def raw(self, n): v = self.b[self.p:self.p + n]; self.p += n; return v
    def boolean(self):
        v = self.u32(); assert v in (0, 1), ('bool', v, self.p - 4); return bool(v)
    def bulk(self):
        es = self.i32(); n = self.i32(); assert es > 0 and 0 <= n < 50_000_000, ('bulk', es, n, self.p); return es, n, self.raw(es * n)

def section(r, NB):
    s = {}
    s['strip'] = r.u16()
    s['mat'] = r.u16(); s['base'] = r.u32(); s['ntri'] = r.u32()
    s['recompute'] = r.boolean()
    s['mask'] = r.u8()
    s['shadow'] = r.boolean()
    s['basevert'] = r.u32()
    ncm = r.i32(); assert 0 <= ncm < 1_000_000, ncm
    r.raw(ncm * 64)   # FMeshToMeshVertData (4.27: 64 bytes)
    nbm = r.i32(); assert 0 < nbm <= 65535, ('bonemap', nbm, r.p)
    s['bonemap'] = list(struct.unpack_from('<%dH' % nbm, r.b, r.p)); r.p += 2 * nbm
    assert max(s['bonemap']) < NB
    s['nverts'] = r.u32(); s['maxinf'] = r.u32()
    s['cloth'] = r.i16()
    r.raw(16); r.i32()   # FSectionClothingData: guid + lod
    # FDuplicatedVerticesBuffer: DupVertData (uint32 array), DupVertIndexData (FIndexLengthPair array)
    n = r.i32(); assert 0 <= n < 5_000_000, ('dupvert', n, r.p); r.p += 4 * n
    n = r.i32(); assert 0 <= n < 5_000_000, ('dupindex', n, r.p); r.p += 8 * n
    s['disabled'] = r.boolean()
    return s

def parse(path):
    d = open(path, 'rb').read()
    z = Zen(d)
    x = z.export_bytes(0)
    at, bones = find_ref_skeleton(z, x)
    NB = len(bones)
    # the materials before the reference skeleton: count + 40 bytes each
    mats = None
    for n in range(1, 64):
        p = at - 4 - 40 * n
        if p >= 0 and struct.unpack_from('<i', x, p)[0] == n:
            mats = []
            for k in range(n):
                idx, ni, num, extra = struct.unpack_from('<iiii', x, p + 4 + 40 * k)
                slot = z.names[ni] if num == 0 else '%s_%d' % (z.names[ni], num - 1)
                mi = ccnames.imp(z.imports[-idx - 1]) if idx < 0 else None
                mats.append((slot, mi))
            break
    assert mats, 'materials not found'
    r = R(x, at + 4 + 12 * NB)
    r.p += 4 + 40 * NB
    nm = r.i32(); r.p += 12 * nm
    cooked = r.boolean(); assert cooked
    nlod = r.i32(); assert 1 <= nlod <= 8
    # LOD0
    strip = r.u16(); cooked_out = r.boolean(); inlined = r.boolean(); assert inlined and not cooked_out
    nreq = r.i32(); req = struct.unpack_from('<%dH' % nreq, x, r.p); r.p += 2 * nreq
    nsec = r.i32(); assert 1 <= nsec <= 256, nsec
    secs = [section(r, NB) for _ in range(nsec)]
    nab = r.i32(); r.p += 2 * nab          # ActiveBoneIndices
    buffers_size = r.u32()                 # (4.27) the size of the buffers below
    istrip = r.u16()
    dts = r.u8(); assert dts in (2, 4), dts
    es, ni, ib = r.bulk(); assert es == dts
    idx = np.frombuffer(ib, dtype=np.uint16 if dts == 2 else np.uint32).astype(np.int64)
    stride = r.u32(); nv = r.u32(); es, n, pb = r.bulk(); assert es == 12 and n == nv and stride == 12
    pos = np.frombuffer(pb, dtype=np.float32).reshape(nv, 3).astype(np.float64)
    strip3 = r.u16()
    ntc = r.u32(); nv2 = r.u32(); fullprec = r.boolean(); hiprec = r.boolean(); assert nv2 == nv
    es, n, tb = r.bulk(); assert n == nv and es == (16 if hiprec else 8), (es, n)
    if hiprec:
        t = np.frombuffer(tb, dtype=np.int16).reshape(nv, 2, 4).astype(np.float64) / 32767.0
    else:
        # (UE 4.20+ packs tangents as signed bytes: value / 127, and w = +127 or -127 for the binormal sign)
        t = np.frombuffer(tb, dtype=np.int8).reshape(nv, 2, 4).astype(np.float64) / 127.0
    tangx, tangz = t[:, 0, :], t[:, 1, :]   # TangentX, TangentZ (normal; w = binormal sign)
    es, n, ub = r.bulk(); assert n == nv * ntc and es == (8 if fullprec else 4), (es, n, ntc)
    uv = (np.frombuffer(ub, dtype=np.float32) if fullprec else np.frombuffer(ub, dtype=np.float16).astype(np.float32)).reshape(nv, ntc, 2).astype(np.float64)
    strip4 = r.u16()
    var = r.boolean(); maxinf = r.u32(); numbones = r.u32(); nv3 = r.u32(); b16 = r.boolean(); assert nv3 == nv, (nv3, nv)
    es, n, wb = r.bulk(); assert es == 1
    per = maxinf * (2 if b16 else 1) + maxinf
    assert not var and n == nv * per, (var, n, nv, per)
    w = np.frombuffer(wb, dtype=np.uint8).reshape(nv, per)
    if b16:
        wi = w[:, :2 * maxinf].copy().view(np.uint16).reshape(nv, maxinf).astype(np.int64)
    else:
        wi = w[:, :maxinf].astype(np.int64)
    ww = w[:, -maxinf:].astype(np.float64) / 255.0
    # section-local bone indices -> skeleton bones
    vbone = np.zeros_like(wi); vmat = np.zeros(nv, dtype=np.int64)
    for k, s in enumerate(secs):
        a, b = s['basevert'], s['basevert'] + s['nverts']
        bm = np.array(s['bonemap'], dtype=np.int64)
        vbone[a:b] = bm[np.minimum(wi[a:b], len(bm) - 1)]
        vmat[a:b] = s['mat']
    tri = idx.reshape(-1, 3)
    tmat = np.zeros(len(tri), dtype=np.int64)
    for s in secs:
        tmat[s['base'] // 3: s['base'] // 3 + s['ntri']] = s['mat']
    info = dict(nb=NB, nv=nv, ntri=len(tri), nsec=nsec, ntc=ntc, maxinf=maxinf, b16=b16, hiprec=hiprec, fullprec=fullprec, nlod=nlod,
                sections=[(s['mat'], s['base'], s['ntri'], s['basevert'], s['nverts'], s['maxinf'], len(s['bonemap'])) for s in secs],
                after_weights=r.p, export=len(x))
    return dict(pos=pos, tangx=tangx, tangz=tangz, uv=uv, tri=tri, tmat=tmat, vmat=vmat, wbone=vbone, wweight=ww,
                bones=bones, mats=mats, info=info)

if __name__ == '__main__':
    m = parse(sys.argv[1])
    print(m['info'])
    print('materials', m['mats'])
    if len(sys.argv) > 2:
        b = m['bones']
        np.savez(sys.argv[2], pos=m['pos'], tangx=m['tangx'], tangz=m['tangz'], uv=m['uv'], tri=m['tri'], tmat=m['tmat'], vmat=m['vmat'],
                 wbone=m['wbone'], wweight=m['wweight'], bone_names=np.array([x[0] for x in b]), bone_parents=np.array([x[1] for x in b]),
                 bone_q=np.array([x[2] for x in b]), bone_t=np.array([x[3] for x in b]), bone_s=np.array([x[4] for x in b]),
                 mat_slots=np.array([s for s, _ in m['mats']]), mat_paths=np.array([str(p) for _, p in m['mats']]))
