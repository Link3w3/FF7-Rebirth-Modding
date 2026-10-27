"""Dissidia NT Sephiroth's motions (G2A, tools/g2a.py) onto the re-rigged Dissidia NT model (PC0010_19_DNT_1p1c:
Rebirth's bones in the Dissidia NT proportions), as key animations (.cacanim) for Create a Character System's Import
Key Animations, on Rebirth Sephiroth's skeleton (PC0010_00) like the CRISIS CORE form's (ccanim/tools/ccretarget.py):

  * every Dissidia NT joint j has an aligned pose (dnt_R / dnt_P: the re-rig put the mesh in it, in Unreal's frame) and
    the new bone n it drives its rest (Rn), so the mesh follows Dissidia NT's skinning when G_n(f) = Ra_j(f) R_j^T Rn;
  * drivers: each bone's source joint (bone_src 'b<global id>'), the four spine joints by the Dissidia NT spine joint
    whose stretch of the torso each sits on (b2 hips, b9, b10);
  * translations: each bone keeps its rest offset (the model's proportions), but C_Hip_a moves with the hips (b2, with
    b1's travel); with travel, the hips' smoothed way across the ground goes on Trans as root motion (GAME_ROOT_Q);
  * the Masamune: Dissidia NT holds it on b22 (under the right hand b20; its blade on the joint's +X, the edge to +Z).
    Rebirth's R_Weapon_a carries its weapon on the socket Attach_Weapon_Right01 (blade +X, edge -Z), so R_Weapon_a's
    world rotation is Ra_22 M D S^T (M: Dissidia NT -> Unreal axes, a mirror; D = diag(1, 1, -1): the edge to -Z, which
    with M's mirror makes a proper rotation; S: the socket's rotation), placed at b22's origin (the grip), relative to
    the right hand as Dissidia NT has it;
  * --game (PC0010_00): no face, eye or Dissidia NT-only bone tracks (the game's face animation stays).
    dnt_anim.py <motion folder> <model face npz> <base g1m> <out folder> [--names a,b,...]"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '/work/ccanim/tools')
import g1m          # noqa: E402
import g2a          # noqa: E402
from ccretarget import q2m, m2q, continuous, rotator_q, order, write_cacanim, GAME_ROOT_Q   # noqa: E402

M = np.array([[0.0, 0.0, 1.0], [-1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
SOCKET_R = q2m(rotator_q(90.0, 0.0, -90.0))
D_EDGE = np.diag([1.0, 1.0, -1.0])      # (M is a mirror: det(M D) = +1)
WEAPON_X = M @ D_EDGE @ SOCKET_R.T
assert abs(np.linalg.det(WEAPON_X) - 1.0) < 1e-9
WEAPON_JOINT, HAND_JOINT = 'b22', 'b20'


class DntSkeleton:
    """The base skeleton's rest locals by joint (global id), in the order of the model's dnt_names (base joints)."""

    def __init__(self, base_g1m):
        b = open(base_g1m, 'rb').read()
        sk = g1m.Skeleton(g1m.chunk(b, 'G1MS')[0])
        self.names = ['b%d' % sk.global_of_local.get(i, 1000 + i) for i in range(sk.count)]
        self.par = [-1 if p == 0xFFFFFFFF else int(p) for p in sk.parent_raw]
        self.lq = sk.quat.copy()
        self.lp = sk.pos.copy()
        self.gid = [sk.global_of_local.get(i, -1) for i in range(sk.count)]
        self.order = order(self.par)

    def world(self, mot):
        """(F, J, 3, 3), (F, J, 3): the clip's world rotations / positions in Dissidia NT's axes"""
        F, J = mot.frames, len(self.names)
        LQ = np.repeat(self.lq[None], F, 0)
        LP = np.repeat(self.lp[None], F, 0)
        for li, g in enumerate(self.gid):
            tr = mot.tracks.get(g)
            if tr is None:
                continue
            if 'rot' in tr:
                LQ[:, li] = tr['rot']
            if 'pos' in tr:
                LP[:, li] = tr['pos']
        LR = q2m(LQ)
        WR = np.zeros((F, J, 3, 3)); WP = np.zeros((F, J, 3))
        for i in self.order:
            p = self.par[i]
            if p < 0:
                WR[:, i] = LR[:, i]; WP[:, i] = LP[:, i]
            else:
                WR[:, i] = WR[:, p] @ LR[:, i]
                WP[:, i] = WP[:, p] + np.einsum('fij,fj->fi', WR[:, p], LP[:, i])
        return WR, WP


class Rig:
    def __init__(self, model_npz, skel):
        m = np.load(model_npz)
        self.skel = skel
        dn = [str(n) for n in m['dnt_names']]
        self.dix = {n: i for i, n in enumerate(dn)}
        self.dR, self.dP = m['dnt_R'], m['dnt_P']           # aligned (Unreal frame)
        self.names = [str(n) for n in m['bone_names']]
        self.par = [int(p) for p in m['bone_parents']]
        self.src = [str(s) for s in m['bone_src']]
        self.Rn = q2m(m['bone_cq']); self.Pn = m['bone_ct'].astype(float)
        self.ix = {n: i for i, n in enumerate(self.names)}
        NB = len(self.names)
        self.Lr = np.zeros((NB, 3, 3)); self.Lt = np.zeros((NB, 3))
        for i, p in enumerate(self.par):
            if p < 0:
                self.Lr[i] = self.Rn[i]; self.Lt[i] = self.Pn[i]
            else:
                self.Lr[i] = self.Rn[p].T @ self.Rn[i]; self.Lt[i] = self.Rn[p].T @ (self.Pn[i] - self.Pn[p])
        sidx = {n: i for i, n in enumerate(skel.names)}
        drv = {}
        for n, s in zip(self.names, self.src):
            if s.startswith('b') and s in sidx and s in self.dix:
                drv[n] = s
        z9, z10 = self.dP[self.dix['b9'], 2], self.dP[self.dix['b10'], 2]
        for n in ('C_Spine_a', 'C_Spine_b', 'C_Spine_c', 'C_Spine_d'):
            z = self.Pn[self.ix[n], 2]
            drv[n] = 'b2' if z < z9 else ('b9' if z < z10 else 'b10')
        drv['C_Hip_a'] = 'b2'
        self.drv = drv
        self.sidx = sidx
        self.order = order(self.par)

    def retarget(self, mot, travel=False, travel_limit=None):
        """travel_limit (cm): the hips' way across the ground scaled down to at most this far from where they start
        (Dissidia NT dashes metres into its attacks); None keeps it as it is"""
        WR, WP = self.skel.world(mot)
        F = WR.shape[0]
        Ra = np.einsum('ij,fbjk,lk->fbil', M, WR, M)
        Pa = np.einsum('ij,fbj->fbi', M, WP)
        NB = len(self.names)
        G = np.zeros((F, NB, 3, 3)); T = np.zeros((F, NB, 3))
        rep = {}
        for i in self.order:
            n, p = self.names[i], self.par[i]
            c = self.drv.get(n)
            Gc = None
            if c is not None:
                k, s = self.dix[c], self.sidx[c]
                Gc = Ra[:, s] @ self.dR[k].T
                G[:, i] = Gc @ self.Rn[i]
            else:
                G[:, i] = self.Rn[i] if p < 0 else G[:, p] @ self.Lr[i]
            if p < 0:
                T[:, i] = self.Pn[i]
            elif n == 'C_Hip_a':
                k, s = self.dix[c], self.sidx[c]
                T[:, i] = Pa[:, s] + np.einsum('fij,j->fi', Gc, self.Pn[i] - self.dP[k])
                if travel_limit:
                    way = T[:, i, :2] - T[0, i, :2]
                    far = float(np.linalg.norm(way, axis=1).max())
                    if far > travel_limit:
                        T[:, i, :2] = T[0, i, :2] + way * (travel_limit / far)
                        rep['travel_scaled'] = round(travel_limit / far, 3)
            else:
                T[:, i] = T[:, p] + np.einsum('fij,j->fi', G[:, p], self.Lt[i])
        tr = self.ix['Trans']
        d = np.zeros((F, 3))
        if travel:
            hip = T[:, self.ix['C_Hip_a']]
            d[:, :2] = hip[:, :2] - hip[0, :2]
            k = np.exp(-0.5 * (np.arange(-9, 10) / 3.0) ** 2); k /= k.sum()
            for a in range(2):
                pad = np.r_[np.full(9, d[0, a]), d[:, a], np.full(9, d[-1, a])]
                d[:, a] = np.convolve(pad, k, mode='valid')
            d[:, :2] -= d[0, :2]
        G[:, tr] = q2m(GAME_ROOT_Q)
        T[:, tr] = d
        for i, p in enumerate(self.par):
            if p == tr and self.names[i] not in self.drv:
                T[:, i] = self.Pn[i] + d
        rep['root_travel_cm'] = [round(float(v), 1) for v in d[-1, :2]]
        LQ = np.zeros((F, NB, 4)); LT = np.zeros((F, NB, 3))
        for i in range(NB):
            p = self.par[i]
            if p < 0:
                Lr, Lt = G[:, i], T[:, i]
            elif p == tr:
                Lr, Lt = G[:, i], T[:, i] - T[:, p]
            else:
                Lr = np.einsum('fji,fjk->fik', G[:, p], G[:, i])
                Lt = np.einsum('fji,fj->fi', G[:, p], T[:, i] - T[:, p])
            LQ[:, i] = continuous(m2q(Lr)); LT[:, i] = Lt
        # the Masamune on R_Weapon_a, relative to the right hand as Dissidia NT holds it on b22
        h, w = self.sidx[HAND_JOINT], self.sidx[WEAPON_JOINT]
        kh = self.dix[HAND_JOINT]
        nh, nw = self.ix['R_Hand_a'], self.ix['R_Weapon_a']
        KR = np.einsum('fji,fjk->fik', Ra[:, h], Ra[:, w])
        Kt = np.einsum('fji,fj->fi', Ra[:, h], Pa[:, w] - Pa[:, h])
        OR = self.dR[kh].T @ self.Rn[nh]
        Ot = self.dR[kh].T @ (self.Pn[nh] - self.dP[kh])
        Lr = np.einsum('ji,fjk->fik', OR, KR @ WEAPON_X)
        Lt = np.einsum('ji,fj->fi', OR, Kt - Ot)
        LQ[:, nw] = continuous(m2q(Lr)); LT[:, nw] = Lt
        G[:, nw] = G[:, nh] @ Lr
        T[:, nw] = T[:, nh] + np.einsum('fij,fj->fi', G[:, nh], Lt)
        rep['grip_from_hand_cm'] = [round(float(x), 1) for x in np.percentile(np.linalg.norm(Kt, axis=1), [0, 50, 100])]
        rep['hip_travel_cm'] = round(float(np.linalg.norm(T[-1, self.ix['C_Hip_a'], :2] - T[0, self.ix['C_Hip_a'], :2])), 2)
        rep['hip_height_cm'] = [round(float(T[:, self.ix['C_Hip_a'], 2].min()), 1), round(float(T[:, self.ix['C_Hip_a'], 2].max()), 1)]
        return LQ, LT, G, T, rep

    def game_skip(self):
        """bones left out for Rebirth Sephiroth's own skeleton (PC0010_00): the face rig, the eyes, the Dissidia NT-only
        bones (hair, coat, belt, tassel, feather and wing chains: PC0010_00 has none of them)"""
        skip = {n for n, s in zip(self.names, self.src) if s.startswith('Rebirth') or 'DNT' in n}
        skip |= {'C_FaceBase_a', 'L_Eye', 'R_Eye'}
        return skip


def main(argv):
    folder, model, base, out = argv[:4]
    pick = None
    if '--names' in argv:
        pick = set(argv[argv.index('--names') + 1].split(','))
    loops = set()
    if '--loops' in argv:
        loops = set(argv[argv.index('--loops') + 1].split(','))
    os.makedirs(out, exist_ok=True)
    skel = DntSkeleton(base)
    rig = Rig(model, skel)
    skip = rig.game_skip()
    manifest = []
    for f in sorted(os.listdir(folder)):
        if not f.endswith('.g1a'):
            continue
        clip = f[:-4]
        if pick and clip not in pick:
            continue
        mot = g2a.read(os.path.join(folder, f))
        loop = clip in loops
        LQ, LT, G, T, rep = rig.retarget(mot, travel=not loop)
        name = 'DNT_' + clip
        k = write_cacanim(os.path.join(out, name + '.cacanim'), rig.names, LQ, LT, float(mot.fps), loop, skip)
        rep.update(name=name, frames=int(LQ.shape[0]), fps=float(mot.fps), tracks=k, loop=loop)
        manifest.append(rep)
        print('%-16s %4d frames %2.0f fps %3d tracks hip travel %7.1f root %-16s hips %s grip %s' % (
            name, LQ.shape[0], mot.fps, k, rep['hip_travel_cm'], rep['root_travel_cm'], rep['hip_height_cm'],
            rep['grip_from_hand_cm']), flush=True)
    json.dump(manifest, open(os.path.join(out, 'manifest.json'), 'w'), indent=1)


if __name__ == '__main__':
    main(sys.argv[1:])
