"""FF7 Rebirth cooked skeletal mesh (zen .uasset + .ubulk, as Square Enix's cooker writes it) -> body npz for the
Kawaii checks: LOD0's vertices (the .ubulk starts with LOD0's raw positions), its skin weights (8 bone indices + 8
weights a vertex, section-local through each render section's bone map) and its render sections.
The format of ysskirt/body.npz: pos, w_bone, w_vert, w_weight, bones, vmat, mats.
    cooked_mesh.py <mesh.uasset> <mesh.ubulk> <out.npz>"""
import struct, sys
import numpy as np
sys.path[:0] = ['/work/cs', '/work/kawaii_preset/tools']
from zen import Zen
from mesh_bones import find_ref_skeleton


def sections_at(x, p, NB):
    """The render sections of the list whose count is at p: [(mat, base, ntri, nb bonemap, nv, maxinf)] or None."""
    n = struct.unpack_from('<i', x, p)[0]
    q = p + 4
    out = []
    expect_base = 0
    for k in range(n):
        strip, mat, base, ntri = struct.unpack_from('<HHII', x, q)
        if base != expect_base or ntri <= 0 or ntri > 5_000_000:
            return None
        found = None
        for r in range(q + 21, q + 64):
            nb = struct.unpack_from('<I', x, r)[0]
            if not (1 <= nb <= 2048):
                continue
            e = r + 4 + 2 * nb
            if e + 10 > len(x):
                continue
            bm = struct.unpack_from('<%dH' % nb, x, r + 4)
            if max(bm) >= NB:
                continue
            nv, mi, cloth = struct.unpack_from('<IIh', x, e)
            if 1 <= nv <= 2_000_000 and 1 <= mi <= 12 and cloth == -1:
                found = (r, list(bm), nv, mi)
                break
        if not found:
            return None
        r, bm, nv, mi = found
        out.append(dict(mat=mat, base=base, ntri=ntri, bonemap=bm, nverts=nv, maxinf=mi))
        expect_base = base + 3 * ntri
        if k + 1 < n:
            # the next section: its strip flags + material + base index
            nxt = None
            for s in range(r + 4 + 2 * len(bm) + 10, r + 4 + 2 * len(bm) + 4000):
                st, m2, b2 = struct.unpack_from('<HHI', x, s)
                if b2 == expect_base and m2 < 256 and st in (0x0101, 0x0000, 0x0001, 0x0100):
                    nxt = s
                    break
            if nxt is None:
                return None
            q = nxt
    return out


def find_lod0(x, NB):
    best = None
    for p in range(0, len(x) - 24):
        n = struct.unpack_from('<i', x, p)[0]
        if not (1 <= n <= 64):
            continue
        strip, mat, base, ntri = struct.unpack_from('<HHII', x, p + 4)
        if base != 0 or ntri == 0 or strip not in (0x0101, 0x0000, 0x0001, 0x0100):
            continue
        s = sections_at(x, p, NB)
        if s:
            nv = sum(t['nverts'] for t in s)
            if best is None or nv > best[2]:
                best = (p, s, nv)
            break   # LOD0 is the first list
    return best


def main(uasset, ubulk, out):
    d = open(uasset, 'rb').read()
    z = Zen(d)
    i = max(range(len(z.exports)), key=lambda k: z.exports[k]['serial_size'])
    x = z.export_bytes(i)
    at, bones = find_ref_skeleton(z, x)
    NB = len(bones)
    lod = find_lod0(x, NB)
    assert lod, 'no LOD0 sections found'
    p, secs, NV = lod
    b = open(ubulk, 'rb').read()
    pos = np.frombuffer(b[:NV * 12], dtype=np.float32).reshape(NV, 3).astype(np.float64)
    # the skin weights: 8 indices + 8 weights a vertex (all weights summing to 255), at a multiple of NV bytes
    W = None
    for k in range(12, 80):
        o = k * NV
        if o + NV * 16 > len(b):
            break
        r = np.frombuffer(b[o:o + NV * 16], dtype=np.uint8).reshape(NV, 16)
        if (r[:, 8:].astype(np.int32).sum(1) == 255).all():
            W = (o, r)
            break
    assert W is not None, 'no skin weights found'
    o, r = W
    vmat = np.zeros(NV, dtype=np.int32)
    w_bone, w_vert, w_weight = [], [], []
    vb = 0
    for si, s in enumerate(secs):
        vmat[vb:vb + s['nverts']] = si
        bm = np.array(s['bonemap'], dtype=np.int64)
        idx = r[vb:vb + s['nverts'], :8].astype(np.int64)
        wt = r[vb:vb + s['nverts'], 8:].astype(np.float64) / 255.0
        for j in range(8):
            m = wt[:, j] > 0
            w_vert.append(np.nonzero(m)[0] + vb)
            w_bone.append(bm[np.minimum(idx[m, j], len(bm) - 1)])
            w_weight.append(wt[m, j])
        vb += s['nverts']
    assert vb == NV
    names = [bn[0] for bn in bones]
    mats = ['mat%d' % s['mat'] for s in secs]
    np.savez(out, pos=pos, w_bone=np.concatenate(w_bone), w_vert=np.concatenate(w_vert), w_weight=np.concatenate(w_weight),
             bones=np.array(names), vmat=vmat, mats=np.array(mats))
    print('%s: %d bones, LOD0 %d vertices in %d sections (%s), weights at bulk %d' % (uasset.split('/')[-1], NB, NV, len(secs),
          ', '.join('%s:%d/%d' % (m, s['nverts'], s['maxinf']) for m, s in zip(mats, secs)), o))


if __name__ == '__main__':
    main(*sys.argv[1:4])
