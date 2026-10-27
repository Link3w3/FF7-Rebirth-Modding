"""A skeletal mesh cooked by the End project's editor (the Skin Maker's build: a zen package whose LOD0 data is in the
package itself, no .ubulk) -> body npz for the Kawaii checks, as tools/cooked_mesh.py makes from the game's own meshes:
LOD0's positions (found by FPositionVertexBuffer's header: stride 12, the vertex count twice), its render sections (their
bone maps, cooked_mesh.find_lod0) and its skin weights (8 bone indices + 8 weights a vertex, the weights of each vertex
summing to 255, or 4 + 4; section-local through each section's bone map).
    cooked_mesh_inline.py <mesh.uasset> <out.npz>"""
import re
import struct
import sys
import numpy as np
sys.path[:0] = ['/work/cs', '/work/kawaii_preset/tools']
from zen import Zen
from mesh_bones import find_ref_skeleton


def find_sections(x, NB, NV):
    """LOD0's render sections in an editor-cooked mesh: each section's bone map (int32 count, uint16 bones < NB) followed
    by its vertex count, its most bone influences (1 - 12) and its cloth asset index (-1), at any byte (the editor's
    sections are not aligned), in order; the first ones whose vertex counts add up to NV."""
    L = len(x)
    found = []
    for a in range(4):
        v = np.frombuffer(x[a:a + (L - a) // 4 * 4], dtype='<i4')
        for k in np.nonzero((v >= 1) & (v <= NB))[0]:
            p = a + 4 * int(k)
            nb = int(v[k]); e = p + 4 + 2 * nb
            if e + 10 > L:
                continue
            nv, mi, cl = struct.unpack_from('<IIh', x, e)
            if not (1 <= nv <= 2_000_000 and 1 <= mi <= 12 and cl == -1):
                continue
            bm = np.frombuffer(x, dtype='<u2', count=nb, offset=p + 4)
            if int(bm.max()) >= NB:
                continue
            found.append((p, [int(b) for b in bm], nv, mi))
    found.sort()
    out, tot = [], 0
    for k, (p, bm, nv, mi) in enumerate(found):
        out.append(dict(mat=k, bonemap=bm, nverts=nv, maxinf=mi))
        tot += nv
        if tot == NV:
            return out
    return None


def find_positions(x, nv):
    key = struct.pack('<IIii', 12, nv, 12, nv)
    p = x.find(key)
    return p + 16 if p >= 0 else None


def find_weights(x, nv, start):
    """The first place after `start` where nv records of 8 + 8 (or 4 + 4) bytes have weights summing to 255 each."""
    for rec, half in ((16, 8), (8, 4)):
        p = start
        end = len(x) - nv * rec
        while p <= end:
            r = np.frombuffer(x, dtype=np.uint8, count=64 * rec, offset=p).reshape(64, rec)
            if (r[:, half:].astype(np.int32).sum(1) == 255).all():
                full = np.frombuffer(x, dtype=np.uint8, count=nv * rec, offset=p).reshape(nv, rec)
                if (full[:, half:].astype(np.int32).sum(1) == 255).all():
                    return p, full, half
            p += 4
    return None


def main(uasset, out):
    d = open(uasset, 'rb').read()
    z = Zen(d)
    i = max(range(len(z.exports)), key=lambda k: z.exports[k]['serial_size'])
    x = z.export_bytes(i)
    at, bones = find_ref_skeleton(z, x)
    NB = len(bones)
    pb = []
    for m in re.finditer(re.escape(struct.pack('<I', 12)), x):
        q = m.start()
        if q + 16 > len(x):
            break
        st, n, es, c = struct.unpack_from('<IIii', x, q)
        if st == 12 and es == 12 and n == c and 100 <= n <= 2_000_000:
            pb.append((q, n))
    assert pb, 'no position buffer'
    NV = pb[0][1]
    pp = pb[0][0] + 16
    secs = find_sections(x, NB, NV)
    assert secs, 'no LOD0 sections adding up to %d vertices' % NV
    pos = np.frombuffer(x, dtype=np.float32, count=NV * 3, offset=pp).reshape(NV, 3).astype(np.float64)
    W = find_weights(x, NV, pp + NV * 12)
    assert W is not None, 'no skin weights found'
    o, r, half = W
    vmat = np.zeros(NV, dtype=np.int32)
    w_bone, w_vert, w_weight = [], [], []
    vb = 0
    for si, s in enumerate(secs):
        vmat[vb:vb + s['nverts']] = si
        bm = np.array(s['bonemap'], dtype=np.int64)
        idx = r[vb:vb + s['nverts'], :half].astype(np.int64)
        wt = r[vb:vb + s['nverts'], half:].astype(np.float64) / 255.0
        for j in range(half):
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
    print('%s: %d bones, LOD0 %d vertices in %d sections, positions at %d, weights (%d a vertex) at %d' % (
        uasset.split('/')[-1], NB, NV, len(secs), pp, half, o))


if __name__ == '__main__':
    main(*sys.argv[1:3])
