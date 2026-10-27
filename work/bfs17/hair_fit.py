"""Bahamut Fused Sephiroth: PC0010_10's hair fitted to the helmet, as Blender's Grab + Smooth brushes would do it.

  * the strands that frame his face (and the long ones down his chest) are hidden above the helmet's brow and hang over
    his face below it, brought out in front of the mask, the cheek guards and his armour where they would go into them;
    the short centre bangs (over his nose and mouth) are dropped, the pieces at his ears go under the cheek guards;
  * the cap and the long hair are tucked where they poke through the helmet's shell by a little (so the long hair comes
    out of the helmet's back opening and from under its back plate), and pushed back out of the collar / back armour where
    they sink into it;
  * the moves are spread along the strands (a smooth falloff over the hair's own surface), so the strands bend under the
    edges instead of kinking;
  * what the helmet covers is held to the head (C_HairBase_a, as Rebirth's scalp is), blending to the strand's own bones
    where the strand comes out, so the physics swings only what is out of the helmet.

    hair_fit.py <rerig.npz> <pc10.npz> <out hair.npz> [renders prefix]
The output: pos, normals, uv (V,4,2), tri, slot (per triangle: 0 hair, 1 hair core), slot_names, slot_materials,
bones (names used), wbone/wweight (V,4, indices into bones), hidden (0..1), moved (cm)."""
import re
import sys
import numpy as np
sys.path.insert(0, '/work/bfs17')
from radial_hits import hits
from rayhits import ray_hits

MARGIN = 0.35          # how far under the helmet's surface a tucked vertex goes (cm)
T_FRONT = 6.0          # the front strands above his brow: tucked when up to this far out over the helmet
Z_BROW = 191.5         # the helmet's brow: the front strands are hidden above it and hang over his face below it
T_CAP = 2.5            # the cap: tucked when poking out by up to this
T_BACK = 1.5           # the long hair: only its slight pokes through the shell
R_HEAD = 17.0          # the helmet's reach from the head centre (beyond it nothing is tucked or held)
SMOOTH_ITERS = 40
FRONT = re.compile(r'^(C_HairA|C_HairB|[LR]_HairA)$')   # the strands that frame his face and the long ones down his chest
SIDE = re.compile(r'^[LR]_HairF$')                      # the short pieces at his ears: under the cheek guards
BANGS = re.compile(r'^C_Hair[C-K]$')     # the short centre bangs: they would hang over his nose and mouth
BACK = re.compile(r'^(C_HairL|C_HairM|[LR]_HairC|[LR]_HairD|[LR]_HairE)$')


def chain_of(n):
    m = re.match(r'(.*?)_([a-z])_Phy$', n)
    return m.group(1) if m else n


def main(rerig_path, pc10_path, out_path, render_prefix=None):
    r = np.load(rerig_path, allow_pickle=True)
    d = np.load(pc10_path, allow_pickle=True)
    names_b = list(r['bone_names'])
    slots_b = [str(s) for s in r['slots']]
    pos_b, tri_b, tm_b = r['pos'], r['tri'], r['tmat']
    face = np.array([s.startswith('PC0010_00') or s == 'Common_Mouth' for s in slots_b])
    wb_b, ww_b = r['wbone'], r['wweight']
    dom_b = np.array(names_b)[wb_b[np.arange(len(wb_b)), ww_b.argmax(1)]]
    head_bones = {'C_Head_a', 'C_FaceBase_a'}
    is_head = np.array([n in head_bones for n in dom_b])
    helm = (~face[tm_b]) & is_head[tri_b].all(1)
    def grp(n):
        return 'wing' if 'Wing' in n else 'mantle' if 'Mant' in n else 'tail' if 'Tail' in n else 'body'
    g_b = np.array([grp(n) for n in dom_b])
    body = (~face[tm_b]) & (g_b[tri_b[:, 0]] == 'body') & ~helm
    centre = r['bone_ct'][names_b.index('C_Head_a')] + np.array([0, 0, 7.0])

    # ---- the hair (PC0010_10's two hair slots), its own vertex numbering
    mn = [str(s) for s in d['mat_names']]
    hair_slots = [k for k, n in enumerate(mn) if 'Hair' in n]
    tmask = np.isin(d['mat'], hair_slots)
    tri_src = d['tri'][tmask]
    slot_src = np.array([hair_slots.index(m) for m in d['mat'][tmask]])
    used = np.unique(tri_src)
    remap = -np.ones(len(d['pos']), dtype=np.int64); remap[used] = np.arange(len(used))
    tri = remap[tri_src]
    P0 = d['pos'][used].copy()
    N0 = d['normals'][used].copy()
    UV = np.stack([d['uv%d' % k][used] for k in range(4)], 1)
    names_h = list(d['names'])
    wb, ww = d['wb'][used][:, :4], d['ww'][used][:, :4].astype(np.float64)
    V = len(P0)
    dom = wb[np.arange(V), ww.argmax(1)]
    chain = np.array([chain_of(names_h[b]) for b in dom])
    is_front = np.array([bool(FRONT.match(c)) for c in chain])
    is_back = np.array([bool(BACK.match(c)) for c in chain])
    is_cap = chain == 'C_HairBase_a'
    is_bangs = np.array([bool(BANGS.match(c)) for c in chain])
    print('hair: %d verts, %d tris; front %d, back %d, cap %d' % (V, len(tri), is_front.sum(), is_back.sum(), is_cap.sum()))

    # welded graph (UV seams split vertices at one place: they must move together)
    key = np.round(P0 / 1e-3).astype(np.int64)
    _, weld = np.unique(key, axis=0, return_inverse=True)
    weld = weld.ravel()
    NW = weld.max() + 1
    e = np.concatenate([tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]])
    e = weld[e]
    e = e[e[:, 0] != e[:, 1]]
    e = np.unique(np.sort(e, 1), axis=0)
    deg = np.bincount(e.ravel(), minlength=NW).astype(np.float64)
    W0 = np.zeros((NW, 3)); np.add.at(W0, weld, P0); cnt = np.bincount(weld, minlength=NW)[:, None]; W0 /= cnt

    def wmean(X):                                   # per-welded-vertex mean of a per-vertex field
        S = np.zeros((NW,) + X.shape[1:]); np.add.at(S, weld, X)
        return S / cnt.reshape((-1,) + (1,) * (X.ndim - 1))

    def smooth_w(X):                                # one Laplacian step on the welded graph
        S = np.zeros_like(X); np.add.at(S, e[:, 0], X[e[:, 1]]); np.add.at(S, e[:, 1], X[e[:, 0]])
        nb = S / np.maximum(deg, 1).reshape((-1,) + (1,) * (X.ndim - 1))
        return np.where((deg > 0).reshape((-1,) + (1,) * (X.ndim - 1)), 0.5 * X + 0.5 * nb, X)

    # ---- the helmet: every hit along the ray from the head centre through each (welded) vertex
    H = hits(centre, W0, pos_b[tri_b[helm]])
    Rv = np.linalg.norm(W0 - centre, axis=1)
    U = (W0 - centre) / Rv[:, None]
    fw = wmean(is_front.astype(float)) > 0.5
    cw = wmean(is_cap.astype(float)) > 0.5
    T_out = np.where(fw, T_FRONT, np.where(cw, T_CAP, T_BACK))
    target_r = np.full(NW, np.nan)                 # tucked: this radius
    covered = np.zeros(NW, bool)                   # a helmet layer over it (seen from the head centre)
    depth_under = np.zeros(NW)                     # how far under that layer
    below_brow = fw & (W0[:, 2] <= Z_BROW)
    for i in range(NW):
        h = H[i]
        if len(h) == 0 or Rv[i] > R_HEAD + T_FRONT or below_brow[i]:
            continue
        above = h[h >= Rv[i] - MARGIN]
        below = h[h < Rv[i] - MARGIN]
        if len(above) and above[0] <= R_HEAD + 2:
            covered[i] = True
            depth_under[i] = above[0] - Rv[i]
            if above[0] - Rv[i] < MARGIN:
                target_r[i] = above[0] - MARGIN
        elif len(below) and Rv[i] - below[-1] < T_out[i] and below[-1] <= R_HEAD:
            target_r[i] = below[-1] - MARGIN
            covered[i] = True
            depth_under[i] = MARGIN
    D0 = np.zeros((NW, 3))
    t = ~np.isnan(target_r)
    D0[t] = (target_r[t] - Rv[t])[:, None] * U[t]
    # hair over the face that shows through the helmet's openings (its eye slits, the gaps over the brow and at the
    # temples) goes under the face itself (the head, eyes and mouth of Rebirth's face hide it); the back opening keeps its hair
    skin_slots = [k for k, n in enumerate(slots_b) if n in ('PC0010_00_Head', 'PC0010_00_Eye', 'Common_Mouth')]
    Hs = hits(centre, W0, pos_b[tri_b[np.isin(tm_b, skin_slots)]])
    bangs_w = wmean(is_bangs.astype(float)) > 0.5
    exposed_fix = 0
    side_w = wmean(np.array([bool(SIDE.match(c)) for c in chain]).astype(float)) > 0.5
    for i in range(NW):
        if bangs_w[i] or below_brow[i] or Rv[i] > R_HEAD or not len(Hs[i]):
            continue
        # the cap over his brow and temples and the short pieces at his ears: all of it under the mask and the cheek
        # guards, so it goes under the face's own surface, whatever the helmet's layers there (its slits and gaps show it)
        brow_cap = cw[i] and W0[i, 0] > centre[0] - 2 and W0[i, 2] > 178
        ear_piece = side_w[i] and W0[i, 0] > centre[0] - 6 and W0[i, 2] > 172
        opening = (not covered[i]) and W0[i, 0] > centre[0] - 4 and W0[i, 2] > 172 and (fw[i] or cw[i])
        if not (brow_cap or ear_piece or opening):
            continue
        hs_ = Hs[i]
        near_ = hs_[np.argmin(np.abs(hs_ - Rv[i]))]
        if near_ > Rv[i] + 3.0:
            continue
        want = near_ - 0.5
        if Rv[i] > want:
            target_r[i] = want if np.isnan(target_r[i]) else min(target_r[i], want)
            covered[i] = True
            depth_under[i] = max(depth_under[i], 0.5)
            exposed_fix += 1
    D0 = np.zeros((NW, 3))
    t = ~np.isnan(target_r)
    D0[t] = (target_r[t] - Rv[t])[:, None] * U[t]
    print('face openings: %d welded verts put under the face' % exposed_fix)
    print('helmet: %d welded verts tucked (front %d, cap %d, back %d), %d covered' % (t.sum(), (t & fw).sum(), (t & cw).sum(), (t & ~fw & ~cw).sum(), covered.sum()))

    # ---- the collar / back armour: the long hair and the cap pushed back out of it (rays backward, -X)
    bw = ~fw
    cand = np.nonzero(bw & ~t & (W0[:, 2] > 140) & (W0[:, 2] < 186))[0]
    Vbody = pos_b[tri_b[body]]
    nb = np.cross(Vbody[:, 1] - Vbody[:, 0], Vbody[:, 2] - Vbody[:, 0]); nb /= np.linalg.norm(nb, axis=1, keepdims=True) + 1e-12
    near = np.linalg.norm(Vbody.mean(1)[:, None, :2] - np.array([[-10.0, 0.0]]), axis=2).ravel() < 60
    Vbody, nb = Vbody[near], nb[near]
    pushed = 0
    back_dir = np.array([-1.0, 0, 0])
    for i in cand:
        tt, idx = ray_hits(W0[i], back_dir, Vbody)
        if len(tt):
            j = np.argmin(tt)
            if nb[idx[j]] @ back_dir > 0 and tt[j] < 12:
                D0[i] = back_dir * (tt[j] + 0.6)
                t[i] = True
                pushed += 1
    print('back armour: %d welded verts pushed out (of %d checked)' % (pushed, len(cand)))
    # the front strands from the brow down: out in front of the mask, the cheek guards, his collar and chest armour where
    # they go into them (rays forward, +X), so they hang over his face and down his chest
    Vfront = np.concatenate([pos_b[tri_b[helm]], Vbody])
    nf = np.cross(Vfront[:, 1] - Vfront[:, 0], Vfront[:, 2] - Vfront[:, 0]); nf /= np.linalg.norm(nf, axis=1, keepdims=True) + 1e-12
    fr = np.nonzero(below_brow & ~t & (W0[:, 2] > 120))[0]
    fwd = np.array([1.0, 0, 0])
    pushed_f = 0
    for i in fr:
        tt, idx = ray_hits(W0[i], fwd, Vfront)
        if len(tt):
            j = np.argmin(tt)
            if nf[idx[j]] @ fwd > 0 and tt[j] < 15:
                D0[i] = fwd * (tt[j] + 0.6)
                t[i] = True
                pushed_f += 1
    print('front: %d welded verts of the front strands brought out over the mask and armour (of %d checked)' % (pushed_f, len(fr)))

    # ---- the falloff along the hair (Grab with Smooth): constrained verts keep their move, the rest relax toward them
    D = D0.copy()
    for _ in range(SMOOTH_ITERS):
        D = smooth_w(D)
        D[t] = D0[t]
    W1 = W0 + D
    # keep the tucked ones under the helmet after the relax (a relaxed neighbour may have come up through it)
    R1 = np.linalg.norm(W1 - centre, axis=1)
    moved = np.linalg.norm(D, axis=1)
    print('moved: %d welded verts by > 0.2 cm, max %.1f cm' % ((moved > 0.2).sum(), moved.max()))

    # ---- held to the head where the helmet covers it (blending out along the strand)
    s = (covered | (t & (Rv < R_HEAD))).astype(float)
    for _ in range(12):
        s = np.maximum(smooth_w(s), np.where(covered, 1.0, 0.0))
    s = np.clip(s, 0, 1)
    sv = s[weld]
    base = names_h.index('C_HairBase_a')
    # new weights: (1 - s) * own + s * C_HairBase_a
    bones_used = sorted(set(wb[ww > 0].tolist()) | {base})
    WB = np.concatenate([wb, np.full((V, 1), base)], 1)
    WW = np.concatenate([ww * (1 - sv)[:, None], sv[:, None]], 1)
    # merge duplicates and keep the 4 largest
    out_b = np.zeros((V, 4), np.int64); out_w = np.zeros((V, 4))
    for i in range(V):
        acc = {}
        for b, w in zip(WB[i], WW[i]):
            if w > 1e-6:
                acc[int(b)] = acc.get(int(b), 0.0) + float(w)
        top = sorted(acc.items(), key=lambda x: -x[1])[:4]
        tot = sum(w for _, w in top)
        for k, (b, w) in enumerate(top):
            out_b[i, k] = b; out_w[i, k] = w / tot
    # the centre bangs are dropped (triangles all of whose corners are theirs)
    drop = is_bangs[tri].all(1)
    tri2 = tri[~drop]; slot2 = slot_src[~drop]
    usedv = np.unique(tri2)
    rm = -np.ones(V, np.int64); rm[usedv] = np.arange(len(usedv))
    print('dropped the centre bangs: %d triangles' % drop.sum())
    P1 = W1[weld]
    names_out = [names_h[b] for b in sorted(set(out_b[usedv][out_w[usedv] > 0].tolist()))]
    bidx = {names_h.index(n): k for k, n in enumerate(names_out)}
    wbo = np.vectorize(lambda b: bidx.get(int(b), 0))(out_b[usedv])
    wwo = out_w[usedv]
    np.savez_compressed(out_path, pos=P1[usedv], normals=N0[usedv], uv=UV[usedv], tri=rm[tri2], slot=slot2, chain=chain[usedv],
                        slot_names=np.array(['PC0010_00_Hair', 'PC0010_00_HairCore']),
                        slot_materials=np.array(['/Game/Character/Player/PC0010_01_Sephiroth_StandardWet/Material/PC0010_01_Hair.PC0010_01_Hair',
                                                 '/Game/Character/Player/PC0010_01_Sephiroth_StandardWet/Material/PC0010_01_HairCore.PC0010_01_HairCore']),
                        bones=np.array(names_out), wbone=wbo, wweight=wwo, hidden=sv[usedv], moved=moved[weld][usedv])
    print('wrote %s: %d verts, %d tris, %d bones' % (out_path, len(usedv), len(tri2), len(names_out)))


if __name__ == '__main__':
    main(*sys.argv[1:5])
