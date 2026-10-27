"""Crisis Core Reunion animations (ccanim.py npz) onto the re-rigged Crisis Core Sephiroth model (PC0010_16: Rebirth's
bones with the Crisis Core proportions, face rig and wing), as key animations (.cacanim) for Create a Character
System's Import Key Animations.

How a bone moves: the re-rig put every Crisis Core bone c into an aligned pose (R_c, P_c, re-rig output cc_R / cc_P,
in Rebirth's frame) and gave the new bone n that c drives its own rest frame (Rn at the same joint). The mesh was posed
with those, so a vertex follows Crisis Core's skinning exactly when, at every frame,
        G_n(f) = Ra_c(f) R_c^T Rn        (Ra_c: c's animated component-space rotation, in Rebirth's frame)
  * drivers: each new bone's own source bone (bone_src), C_Hip_a by Hips, the four spine joints by the Crisis Core
    spine bone whose stretch of the torso each one sits on, the eyes by hi_eye_L / hi_eye_R;
  * a bone nobody drives (face rig, wing, weapon bones, the C_Chara* roots) keeps its rest pose under its parent;
  * translations: every bone keeps its rest offset from its parent (the model's own proportions; the Skeleton retarget
    mode), except C_Hip_a, which moves with Crisis Core's Hips (its travel included) and Trans (the root: Crisis Core's
    clips carry no root motion);
  * the sword: Crisis Core animates it on its own bone (wpn_body, under the root; both hands are constrained to its
    origin, the grip), Rebirth holds its weapons on R_Weapon_a, whose socket Attach_Weapon_Right01 (pitch 90, roll -90)
    carries a weapon mesh with the blade on +X, the grip at the origin and the edge to -Z (Rebirth's Masamune). The
    Crisis Core blade runs along wpn_body's +Z with its spine to -X, so a Rebirth weapon sits as the Crisis Core sword
    does when R_Weapon_a = wpn_body * X, X = A^-1 S^-1 (A: Crisis Core sword axes -> Rebirth weapon axes). R_Weapon_a's
    local transform is taken from the sword's place relative to Crisis Core's right hand (held: as Crisis Core holds
    it). A clip whose sword is never near the hand (the field clips park it away) keeps R_Weapon_a at rest.
    ccretarget.py <clip npz> <re-rig pose npz> <model npz> <out .cacanim> [report json]
    ccretarget.py --batch <clip folder> <re-rig pose npz> <model npz> <out folder>"""
import json
import os
import struct
import sys

import numpy as np


def q2m(q):
    q = np.asarray(q, dtype=float)
    x, y, z, w = q[..., 0], q[..., 1], q[..., 2], q[..., 3]
    m = np.empty(q.shape[:-1] + (3, 3))
    m[..., 0, 0] = 1 - 2 * (y * y + z * z); m[..., 0, 1] = 2 * (x * y - z * w); m[..., 0, 2] = 2 * (x * z + y * w)
    m[..., 1, 0] = 2 * (x * y + z * w); m[..., 1, 1] = 1 - 2 * (x * x + z * z); m[..., 1, 2] = 2 * (y * z - x * w)
    m[..., 2, 0] = 2 * (x * z - y * w); m[..., 2, 1] = 2 * (y * z + x * w); m[..., 2, 2] = 1 - 2 * (x * x + y * y)
    return m


def m2q(m):
    """rotation matrices (..., 3, 3) -> unit quaternions (..., 4) x, y, z, w"""
    m = np.asarray(m, dtype=float)
    shp = m.shape[:-2]
    m = m.reshape(-1, 3, 3)
    q = np.empty((len(m), 4))
    for k, r in enumerate(m):
        t = r[0, 0] + r[1, 1] + r[2, 2]
        if t > 0:
            s = np.sqrt(t + 1.0) * 2
            q[k] = [(r[2, 1] - r[1, 2]) / s, (r[0, 2] - r[2, 0]) / s, (r[1, 0] - r[0, 1]) / s, 0.25 * s]
        elif r[0, 0] > r[1, 1] and r[0, 0] > r[2, 2]:
            s = np.sqrt(1.0 + r[0, 0] - r[1, 1] - r[2, 2]) * 2
            q[k] = [0.25 * s, (r[0, 1] + r[1, 0]) / s, (r[0, 2] + r[2, 0]) / s, (r[2, 1] - r[1, 2]) / s]
        elif r[1, 1] > r[2, 2]:
            s = np.sqrt(1.0 + r[1, 1] - r[0, 0] - r[2, 2]) * 2
            q[k] = [(r[0, 1] + r[1, 0]) / s, 0.25 * s, (r[1, 2] + r[2, 1]) / s, (r[0, 2] - r[2, 0]) / s]
        else:
            s = np.sqrt(1.0 + r[2, 2] - r[0, 0] - r[1, 1]) * 2
            q[k] = [(r[0, 2] + r[2, 0]) / s, (r[1, 2] + r[2, 1]) / s, 0.25 * s, (r[1, 0] - r[0, 1]) / s]
    q /= np.linalg.norm(q, axis=1, keepdims=True)
    return q.reshape(shp + (4,))


def continuous(q):
    """sign-continuous over time (q and -q are the same rotation), first key with w >= 0"""
    q = q.copy()
    if q[0, 3] < 0:
        q[0] = -q[0]
    for f in range(1, len(q)):
        if np.dot(q[f], q[f - 1]) < 0:
            q[f] = -q[f]
    return q


def rotator_q(pitch, yaw, roll):
    """UE4 FRotator -> quaternion (x, y, z, w), as FRotator::Quaternion"""
    d = np.pi / 360
    sp, cp = np.sin(pitch * d), np.cos(pitch * d); sy, cy = np.sin(yaw * d), np.cos(yaw * d); sr, cr = np.sin(roll * d), np.cos(roll * d)
    return np.array([cr * sp * sy - sr * cp * cy, -cr * sp * cy - sr * cp * sy, cr * cp * sy - sr * sp * cy, cr * cp * cy + sr * sp * sy])


# Rebirth's weapon socket on R_Weapon_a (Attach_Weapon_Right01) and the Crisis Core sword -> Rebirth weapon axes:
# CC +Z (grip -> tip) -> +X, CC -X (spine) -> +Z, CC +Y -> +Y
SOCKET_R = q2m(rotator_q(90.0, 0.0, -90.0))
SWORD_A = np.array([[0.0, 0.0, 1.0], [0.0, 1.0, 0.0], [-1.0, 0.0, 0.0]])
WEAPON_X = SWORD_A.T @ SOCKET_R.T
HELD_CM = 30.0
# the game's root (Trans) in its animations: this rotation, the move's travel on component +X / +Y (root motion); the
# game does not apply the rotation to the root's children (they are in component axes in its animations)
GAME_ROOT_Q = np.array([-0.5, 0.5, -0.5, 0.5])


def order(par):
    done, out = set(), []
    while len(out) < len(par):
        for i, p in enumerate(par):
            if i not in done and (p < 0 or p in done):
                done.add(i); out.append(i)
    return out


def clip_cs(A):
    """the clip's component-space rotations and positions per frame, (F, B, 3, 3) and (F, B, 3)"""
    par = [int(p) for p in A['bone_parents']]
    R = q2m(A['q'])
    T = A['t'].astype(float)
    F, B = T.shape[:2]
    Rc = np.zeros((F, B, 3, 3)); Pc = np.zeros((F, B, 3))
    for i in order(par):
        p = par[i]
        if p < 0:
            Rc[:, i] = R[:, i]; Pc[:, i] = T[:, i]
        else:
            Rc[:, i] = Rc[:, p] @ R[:, i]
            Pc[:, i] = Pc[:, p] + np.einsum('fij,fj->fi', Rc[:, p], T[:, i])
    return Rc, Pc


class Rig:
    def __init__(self, pose_npz, model_npz):
        P = np.load(pose_npz)
        self.cc_names = [str(n) for n in P['cc_names']]
        self.cc_ix = {n: i for i, n in enumerate(self.cc_names)}
        self.cR, self.cP = P['cc_R'], P['cc_P']          # aligned pose (Rebirth frame)
        self.cR0, self.cP0 = P['cc_R0'], P['cc_P0']      # bind pose (Rebirth frame)
        self.conv = P['cc_conv']
        M = np.load(model_npz)
        self.names = [str(n) for n in M['bone_names']]
        self.par = [int(p) for p in M['bone_parents']]
        self.Rn = q2m(M['bone_cq']); self.Pn = M['bone_ct'].astype(float)
        self.src = [str(s) for s in M['bone_src']]
        ix = {n: i for i, n in enumerate(self.names)}
        self.ix = ix
        # rest locals
        self.Lr = np.zeros((len(self.names), 3, 3)); self.Lt = np.zeros((len(self.names), 3))
        for i, p in enumerate(self.par):
            if p < 0:
                self.Lr[i] = self.Rn[i]; self.Lt[i] = self.Pn[i]
            else:
                self.Lr[i] = self.Rn[p].T @ self.Rn[i]; self.Lt[i] = self.Rn[p].T @ (self.Pn[i] - self.Pn[p])
        # drivers
        drv = {}
        for i, (n, s) in enumerate(zip(self.names, self.src)):
            if s and not s.startswith('Rebirth') and s in self.cc_ix:
                drv[n] = s
        drv['C_Hip_a'] = 'Hips'
        zS, zS1 = self.cP[self.cc_ix['Spine'], 2], self.cP[self.cc_ix['Spine1'], 2]
        for n in ('C_Spine_a', 'C_Spine_b', 'C_Spine_c', 'C_Spine_d'):
            z = self.Pn[ix[n], 2]
            drv[n] = 'Hips' if z < zS else ('Spine' if z < zS1 else 'Spine1')
        for side in ('L', 'R'):
            if side + '_Eye' in ix and 'hi_eye_' + side in self.cc_ix:
                drv[side + '_Eye'] = 'hi_eye_' + side
        self.drv = drv
        self.order = order(self.par)

    def retarget(self, A, travel=False):
        """the clip on the model: local rotations (F, B, 4) and translations (F, B, 3), and a report"""
        an = [str(n) for n in A['bone_names']]
        aix = {n: i for i, n in enumerate(an)}
        Rcs, Pcs = clip_cs(A)
        F = Rcs.shape[0]
        conv = self.conv
        Ra = np.einsum('ij,fbjk->fbik', conv, Rcs)
        Pa = np.einsum('ij,fbj->fbi', conv, Pcs)
        rep = {}
        # the clip's rest (its skeleton's ref pose) against the model's bind: the same skeleton
        ref = dict(bone_names=A['bone_names'], bone_parents=A['bone_parents'], q=A['ref_q'][None], t=A['ref_t'][None])
        R0c, P0c = clip_cs(ref)
        R0c = np.einsum('ij,bjk->bik', conv, R0c[0]); P0c = np.einsum('ij,bj->bi', conv, P0c[0])
        common = [n for n in an if n in self.cc_ix]
        rep['bind_vs_ref_cm'] = round(float(max(np.linalg.norm(P0c[aix[n]] - self.cP0[self.cc_ix[n]]) for n in common)), 4)
        NB = len(self.names)
        G = np.zeros((F, NB, 3, 3)); T = np.zeros((F, NB, 3))
        for i in self.order:
            n, p = self.names[i], self.par[i]
            c = self.drv.get(n)
            if c is not None and c in aix:
                k = self.cc_ix[c]
                Gc = Ra[:, aix[c]] @ self.cR[k].T
                G[:, i] = Gc @ self.Rn[i]
            else:
                Gc = None
                G[:, i] = self.Rn[i] if p < 0 else G[:, p] @ self.Lr[i]
            if p < 0:
                T[:, i] = self.Pn[i]
            elif n == 'C_Hip_a' and Gc is not None:
                k = self.cc_ix[c]
                T[:, i] = Pa[:, aix[c]] + np.einsum('fij,j->fi', Gc, self.Pn[i] - self.cP[k])
            else:
                T[:, i] = T[:, p] + np.einsum('fij,j->fi', G[:, p], self.Lt[i])
        # the root as the game's animations have it: GAME_ROOT_Q, and (travel) the hips' way across the ground as root
        # motion (the body keeps its place under the root; the bones under Trans that nothing drives go with it)
        tr = self.ix['Trans']
        d = np.zeros((F, 3))
        if travel:
            hip = T[:, self.ix['C_Hip_a']]
            d[:, :2] = hip[:, :2] - hip[0, :2]
            # smoothed (a 0.1 s Gaussian, ends held): the travel without the hips' sway, which stays on the body
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
                # (2026-10-26) the root's children in component axes, as in the game's own animations: the game stands the
                # body under the root at rest and does not turn it by the root's GAME_ROOT_Q (given under that turn, the
                # Crisis Core moves lay on their side in game)
                Lr, Lt = G[:, i], T[:, i] - T[:, p]
            else:
                Lr = np.einsum('fji,fjk->fik', G[:, p], G[:, i])
                Lt = np.einsum('fji,fj->fi', G[:, p], T[:, i] - T[:, p])
            LQ[:, i] = continuous(m2q(Lr)); LT[:, i] = Lt
        # the sword on R_Weapon_a (relative to the right hand, see the module notes)
        rep['weapon'] = 'rest'
        if 'wpn_body' in aix and 'RightHand' in aix and 'R_Weapon_a' in self.ix:
            h, sw = aix['RightHand'], aix['wpn_body']
            KR = np.einsum('fji,fjk->fik', Ra[:, h], Ra[:, sw])
            Kt = np.einsum('fji,fj->fi', Ra[:, h], Pa[:, sw] - Pa[:, h])
            dist = np.linalg.norm(Kt, axis=1)
            rep['sword_hand_cm'] = [round(float(dist.min()), 1), round(float(np.median(dist)), 1), round(float(dist.max()), 1)]
            if dist.min() < HELD_CM:
                kh = self.cc_ix['RightHand']; nh = self.ix['R_Hand_a']
                OR = self.cR[kh].T @ self.Rn[nh]
                Ot = self.cR[kh].T @ (self.Pn[nh] - self.cP[kh])
                w = self.ix['R_Weapon_a']
                Lr = np.einsum('ji,fjk->fik', OR, KR @ WEAPON_X)
                Lt = np.einsum('ji,fj->fi', OR, Kt - Ot)
                LQ[:, w] = continuous(m2q(Lr)); LT[:, w] = Lt
                G[:, w] = G[:, nh] @ Lr
                T[:, w] = T[:, nh] + np.einsum('fij,fj->fi', G[:, nh], Lt)
                rep['weapon'] = 'from wpn_body'
                rep['weapon_held_frames'] = int((dist < HELD_CM).sum())
        rep['drivers'] = len(self.drv)
        rep['missing_drivers'] = sorted(set(c for c in self.drv.values() if c not in aix))
        rep['hip_travel_cm'] = round(float(np.linalg.norm(T[-1, self.ix['C_Hip_a'], :2] - T[0, self.ix['C_Hip_a'], :2])), 2)
        return LQ, LT, G, T, rep


def write_cacanim(path, names, LQ, LT, fps, loop=False, skip=()):
    F = LQ.shape[0]
    tracks = []
    for i, n in enumerate(names):
        if n in skip:
            continue
        Q, T = LQ[:, i], LT[:, i]
        S = np.ones_like(T)
        if np.ptp(T, 0).max() < 1e-4 and np.ptp(Q, 0).max() < 1e-6:
            Q, T, S = Q[:1], T[:1], S[:1]
        tracks.append((n, T, Q, S))
    with open(path, 'wb') as f:
        f.write(b'CACANIM1')
        f.write(struct.pack('<IfiIi', 1, float(fps), F, 1 if loop else 0, len(tracks)))
        for bone, T, Q, S in tracks:
            nb = bone.encode('ascii')
            f.write(struct.pack('<H', len(nb)) + nb)
            f.write(struct.pack('<i', len(T)))
            f.write(np.concatenate([T, Q, S], -1).astype('<f4').tobytes())
    return len(tracks)


LOOP_HINTS = ('idle', 'run', 'walk', 'stand', 'wait', '_l')


def is_loop(name):
    n = name.lower()
    return n.endswith('_l') or any(h in n for h in ('idle', 'run1', '_run', '_walk', 'stand'))


def main(argv):
    if argv[0] == '--batch':
        folder, pose, model, out = argv[1:5]
        os.makedirs(out, exist_ok=True)
        rig = Rig(pose, model)
        # --game: for Rebirth Sephiroth's own skeleton (PC0010_00): no face rig or wing tracks (the game's face and
        # wing animation stay theirs) and none for the Crisis Core hair and coat bones (that skeleton has none)
        skip = set()
        if '--game' in argv:
            skip = {n for n, s in zip(rig.names, rig.src) if s.startswith('Rebirth') or (s and s == n and n not in ('hi_hair',)) or 'CC' in n}
            skip |= {'hi_hair', 'C_FaceBase_a'}
            print('skipping %d tracks: %s ...' % (len(skip), sorted(skip)[:12]))
        manifest = []
        for f in sorted(os.listdir(folder)):
            if not f.endswith('.npz'):
                continue
            A = np.load(os.path.join(folder, f))
            if int(A['additive_type']) != 0:
                print('%-40s skipped (additive)' % f); continue
            name = f[:-4].replace('AS_sephiroth_', 'CC_')
            travel = name.startswith('CC_btm_') and not is_loop(name)
            LQ, LT, G, T, rep = rig.retarget(A, travel)
            k = write_cacanim(os.path.join(out, name + '.cacanim'), rig.names, LQ, LT, float(A['fps']), is_loop(name), skip)
            rep.update(name=name, frames=int(LQ.shape[0]), fps=float(A['fps']), tracks=k, loop=is_loop(name), travel=travel)
            manifest.append(rep)
            print('%-34s %4d frames %2d fps %3d tracks hip travel %7.1f root %s %s' % (
                name, LQ.shape[0], A['fps'], k, rep['hip_travel_cm'], rep['root_travel_cm'] if travel else '-', rep['missing_drivers'] or ''))
        json.dump(manifest, open(os.path.join(out, 'manifest.json'), 'w'), indent=1)
    else:
        clip, pose, model, out = argv[:4]
        rig = Rig(pose, model)
        A = np.load(clip)
        LQ, LT, G, T, rep = rig.retarget(A)
        rep['tracks'] = write_cacanim(out, rig.names, LQ, LT, float(A['fps']))
        print(json.dumps(rep, indent=1))
        if len(argv) > 4:
            json.dump(rep, open(argv[4], 'w'), indent=1)


if __name__ == '__main__':
    main(sys.argv[1:])
