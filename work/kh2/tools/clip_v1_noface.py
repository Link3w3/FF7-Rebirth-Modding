"""KH2 (retargeted) animation clips on Sephiroth's skeleton (PC0010_00_Skeleton), in UE space: per-frame local
translation / rotation / scale of every bone the FBX animates, plus the edits used to make his moves (time ranges,
reversal, holds, retiming, grounding the feet, root motion), and the .cacanim writer the editor importer reads."""
import os, struct, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fbxbin import Scene, props70

SKELETON = '/work/skelx/PC0010_00_Skeleton.bones'
SRC_FPS = 60.0          # the FBXs say 24 fps; KH2 plays them at 60 (run, walk and idle cycles match the game's at 60)


def load_skeleton():
    names, parents = [], []
    for line in open(SKELETON):
        n, p = line.split()
        names.append(n); parents.append(int(p))
    return names, parents


SK_NAMES, SK_PARENTS = load_skeleton()
SK_INDEX = {n: i for i, n in enumerate(SK_NAMES)}


def ref_pose():
    sys.path.append('/work/evil1013/tools')
    from zenskel import bones
    B = bones(open('/work/skelx/raw/PC0010_00_Skeleton.uasset', 'rb').read())
    T = np.array([b[2] for b in B], dtype=np.float64)
    Q = np.array([b[3] for b in B], dtype=np.float64)
    assert [b[0] for b in B] == SK_NAMES
    return T, Q


REF_T, REF_Q = ref_pose()


# ------------------------------------------------------------------ quaternion helpers (x, y, z, w), arrays (..., 4)
def qmul(a, b):
    ax, ay, az, aw = np.moveaxis(a, -1, 0)
    bx, by, bz, bw = np.moveaxis(b, -1, 0)
    return np.stack([aw * bx + ax * bw + ay * bz - az * by,
                     aw * by - ax * bz + ay * bw + az * bx,
                     aw * bz + ax * by - ay * bx + az * bw,
                     aw * bw - ax * bx - ay * by - az * bz], -1)


def qconj(q):
    return q * np.array([-1, -1, -1, 1.0])


def qrot(q, v):
    p = np.concatenate([v, np.zeros(v.shape[:-1] + (1,))], -1)
    return qmul(qmul(q, p), qconj(q))[..., :3]


def qnorm(q):
    return q / np.linalg.norm(q, axis=-1, keepdims=True)


def qslerp(a, b, t):
    d = np.sum(a * b, -1, keepdims=True)
    b = np.where(d < 0, -b, b)
    d = np.abs(d)
    t = np.asarray(t)[..., None] if np.ndim(t) else t
    lin = d > 0.9995
    th = np.arccos(np.clip(d, -1, 1))
    s = np.sin(th)
    s = np.where(s < 1e-9, 1.0, s)
    w0 = np.where(lin, 1 - t, np.sin((1 - t) * th) / s)
    w1 = np.where(lin, t, np.sin(t * th) / s)
    return qnorm(w0 * a + w1 * b)


def q_from_euler_xyz_deg(r):
    """FBX eEulerXYZ: R = Rz * Ry * Rx (X applied first). r (..., 3) degrees."""
    h = np.radians(r) / 2
    cx, sx = np.cos(h[..., 0]), np.sin(h[..., 0])
    cy, sy = np.cos(h[..., 1]), np.sin(h[..., 1])
    cz, sz = np.cos(h[..., 2]), np.sin(h[..., 2])
    z = np.zeros_like(cx)
    qx = np.stack([sx, z, z, cx], -1)
    qy = np.stack([z, sy, z, cy], -1)
    qz = np.stack([z, z, sz, cz], -1)
    return qmul(qz, qmul(qy, qx))


def q_axis_angle(axis, deg):
    axis = np.asarray(axis, dtype=np.float64)
    axis = axis / np.linalg.norm(axis)
    h = np.radians(deg) / 2
    return np.concatenate([axis * np.sin(h), [np.cos(h)]])


class Clip:
    """bones: names (skeleton bones the clip has tracks for); T, Q, S: (frames, bones, 3|4|3) local UE transforms."""

    def __init__(self, bones, T, Q, S, fps=SRC_FPS, name=''):
        self.bones, self.T, self.Q, self.S, self.fps, self.name = list(bones), T, Q, S, fps, name
        self.index = {b: i for i, b in enumerate(self.bones)}

    @property
    def frames(self):
        return self.T.shape[0]

    @property
    def seconds(self):
        return (self.frames - 1) / self.fps

    def copy(self, name=None):
        return Clip(self.bones, self.T.copy(), self.Q.copy(), self.S.copy(), self.fps, name or self.name)

    # -------------------------------------------------------------- loading
    @staticmethod
    def from_fbx(path, name=None):
        s = Scene(path)
        curves = s.curves()
        ms = s.models()
        byname = {v[1]: k for k, v in ms.items()}
        n = 0
        for c in curves.values():
            for ch in c.values():
                for comp in ch.values():
                    n = max(n, len(comp[0]))
        bones = [b for b in SK_NAMES if b in byname]
        F, B = n, len(bones)
        T = np.zeros((F, B, 3)); R = np.zeros((F, B, 3)); S = np.ones((F, B, 3))
        for j, bone in enumerate(bones):
            props = props70(ms[byname[bone]][3])
            for arr, channel, default in ((T, 'Lcl Translation', 0.0), (R, 'Lcl Rotation', 0.0), (S, 'Lcl Scaling', 1.0)):
                d = props.get(channel, [default] * 3)
                c = curves.get(bone, {}).get(channel)
                for i, axis in enumerate('XYZ'):
                    if c and ('d|' + axis) in c:
                        vals = np.asarray(c['d|' + axis][1], dtype=np.float64)
                        if len(vals) < F:
                            vals = np.concatenate([vals, np.full(F - len(vals), vals[-1])])
                        arr[:, j, i] = vals[:F]
                    else:
                        arr[:, j, i] = d[i] if i < len(d) else default
        Q = q_from_euler_xyz_deg(R)
        # FBX (right-handed) -> UE (left-handed): mirror Y (what UE's FBX importer does)
        T[..., 1] *= -1
        Q = Q * np.array([1, -1, 1, -1.0])
        Q = np.where(Q[..., 3:4] < 0, -Q, Q)
        return Clip(bones, T, Q, S, SRC_FPS, name or os.path.basename(path).split('_001_')[0].split('_remap')[0])

    # -------------------------------------------------------------- forward kinematics (component space, root = Trans)
    def world(self, wanted):
        """{bone: (pos (F,3), rot (F,4))} in component space for the wanted bones (and their ancestors)."""
        F = self.frames
        out = {}

        def local(i):
            name = SK_NAMES[i]
            if name in self.index:
                j = self.index[name]
                return self.T[:, j], self.Q[:, j]
            return np.repeat(REF_T[i][None], F, 0), np.repeat(REF_Q[i][None], F, 0)

        def get(i):
            name = SK_NAMES[i]
            if name in out:
                return out[name]
            t, q = local(i)
            p = SK_PARENTS[i]
            if p >= 0:
                pt, pq = get(p)
                t = pt + qrot(pq, t)
                q = qnorm(qmul(pq, q))
            out[name] = (t, q)
            return out[name]

        for w in wanted:
            get(SK_INDEX[w])
        return out

    # -------------------------------------------------------------- edits
    def frames_range(self, a, b=None, name=None):
        c = self.copy(name)
        sl = slice(a, b)
        c.T, c.Q, c.S = self.T[sl].copy(), self.Q[sl].copy(), self.S[sl].copy()
        return c

    def reversed(self, name=None):
        c = self.copy(name)
        c.T, c.Q, c.S = self.T[::-1].copy(), self.Q[::-1].copy(), self.S[::-1].copy()
        return c

    def hold(self, seconds, at_end=True):
        """Repeat the last (or first) frame for this long."""
        k = int(round(seconds * self.fps))
        i = -1 if at_end else 0
        T = np.repeat(self.T[i:i + 1 if i != -1 else None], k, 0)
        Q = np.repeat(self.Q[i:i + 1 if i != -1 else None], k, 0)
        S = np.repeat(self.S[i:i + 1 if i != -1 else None], k, 0)
        if at_end:
            self.T, self.Q, self.S = np.concatenate([self.T, T]), np.concatenate([self.Q, Q]), np.concatenate([self.S, S])
        else:
            self.T, self.Q, self.S = np.concatenate([T, self.T]), np.concatenate([Q, self.Q]), np.concatenate([S, self.S])
        return self

    def then(self, other, blend_frames=0, name=None):
        """This clip, then other (same bones), cross-faded over blend_frames."""
        assert self.bones == other.bones
        c = self.copy(name)
        o = other.copy()
        # the other clip's root continues from where this one ends
        o.T[:, 0] += (self.T[-1, 0] - o.T[0, 0]) * np.array([1, 1, 0.0])
        if blend_frames > 0:
            k = blend_frames
            w = np.linspace(0, 1, k + 2)[1:-1]
            a_t, b_t = c.T[-k:], o.T[:k]
            a_q, b_q = c.Q[-k:], o.Q[:k]
            T = a_t * (1 - w)[:, None, None] + b_t * w[:, None, None]
            Q = np.stack([qslerp(a_q[i], b_q[i], w[i]) for i in range(k)])
            S = c.S[-k:] * (1 - w)[:, None, None] + o.S[:k] * w[:, None, None]
            c.T = np.concatenate([c.T[:-k], T, o.T[k:]])
            c.Q = np.concatenate([c.Q[:-k], Q, o.Q[k:]])
            c.S = np.concatenate([c.S[:-k], S, o.S[k:]])
        else:
            c.T = np.concatenate([c.T, o.T[1:]])
            c.Q = np.concatenate([c.Q, o.Q[1:]])
            c.S = np.concatenate([c.S, o.S[1:]])
        return c

    def retimed(self, seconds, name=None):
        """Played in this many seconds (resampled at the same frame rate)."""
        c = self.copy(name)
        n = max(2, int(round(seconds * self.fps)) + 1)
        x = np.linspace(0, self.frames - 1, n)
        i0 = np.floor(x).astype(int); i1 = np.minimum(i0 + 1, self.frames - 1); t = (x - i0)
        c.T = self.T[i0] * (1 - t)[:, None, None] + self.T[i1] * t[:, None, None]
        c.S = self.S[i0] * (1 - t)[:, None, None] + self.S[i1] * t[:, None, None]
        c.Q = qslerp(self.Q[i0], self.Q[i1], np.repeat(t[:, None], len(self.bones), 1))
        return c

    def ground(self, max_drop=80.0, smooth=5, keep_air=False):
        """Lower the hips (C_Hip_a) so the lowest foot or toe touches the ground (the root, Trans) on every frame: the
        retarget kept the hips at standing height while the knees bend, which floats the feet."""
        w = self.world(['R_Foot_a', 'L_Foot_a', 'R_Toe_a', 'L_Toe_a', 'Trans'])
        root_z = w['Trans'][0][:, 2]
        heel = np.minimum(w['R_Foot_a'][0][:, 2], w['L_Foot_a'][0][:, 2]) - REF_T_W['R_Foot_a'][2]
        toe = np.minimum(w['R_Toe_a'][0][:, 2], w['L_Toe_a'][0][:, 2]) - REF_T_W['R_Toe_a'][2]
        lift = np.minimum(heel, toe) - root_z
        drop = np.clip(lift, 0, max_drop)
        if smooth > 1 and len(drop) > smooth:
            k = np.ones(smooth) / smooth
            pad = np.pad(drop, (smooth // 2, smooth // 2), mode='edge')
            sm = np.convolve(pad, k, mode='valid')[:len(drop)]
            drop = np.minimum(sm, np.clip(lift + 1.5, 0, max_drop))   # never push a foot more than 1.5 cm into the ground
        j = self.index['C_Hip_a']
        self.T[:, j, 2] -= drop
        self.ground_drop = drop
        return self

    def root_motion(self, velocity=None, scale=None, strip=False):
        """Trans translation: velocity (cm/s, xyz) laid on top, scaled, or stripped (kept at the first frame)."""
        j = self.index['Trans']
        t = np.arange(self.frames) / self.fps
        if strip:
            self.T[:, j] = self.T[0, j]
        if scale is not None:
            self.T[:, j] = self.T[0, j] + (self.T[:, j] - self.T[0, j]) * np.asarray(scale)
        if velocity is not None:
            self.T[:, j] += t[:, None] * np.asarray(velocity, dtype=np.float64)[None]
        return self

    def twist_lower_body(self, deg, spine=(('C_Spine_a', 0.5), ('C_Spine_b', 0.3), ('C_Spine_c', 0.2))):
        """Turn the hips (and legs) by deg about the vertical, the spine back the other way: the legs walk to one side
        while the chest keeps facing forward."""
        jh = self.index['C_Hip_a']
        qz = q_axis_angle([0, 0, 1], deg)
        # hips: rotate in the root's frame (pre-multiply)
        self.Q[:, jh] = qnorm(qmul(np.broadcast_to(qz, self.Q[:, jh].shape), self.Q[:, jh]))
        # spine: undo the turn in component space, spread over the spine bones
        w = self.world([b for b, _ in spine])
        for bone, share in spine:
            j = self.index[bone]
            pi = SK_PARENTS[SK_INDEX[bone]]
            pq = self.world([SK_NAMES[pi]])[SK_NAMES[pi]][1]
            back = q_axis_angle([0, 0, 1], -deg * share)
            # local' = parent^-1 * back * parent * local  (a turn about the component vertical, applied at this bone)
            self.Q[:, j] = qnorm(qmul(qmul(qmul(qconj(pq), np.broadcast_to(back, pq.shape)), pq), self.Q[:, j]))
        return self

    # -------------------------------------------------------------- writing
    def tracks(self, tol_pos=0.01, tol_deg=0.02):
        """[(bone, T (k,3), Q (k,4), S (k,3))] with k = 1 for constant tracks; tracks equal to the reference pose are left out."""
        out = []
        cos_tol = np.cos(np.radians(tol_deg) / 2)
        for j, bone in enumerate(self.bones):
            T, Q, S = self.T[:, j], self.Q[:, j], self.S[:, j]
            i = SK_INDEX[bone]
            const = (np.abs(T - T[0]).max() < tol_pos and np.abs(np.sum(Q * Q[0], -1)).min() > cos_tol and np.abs(S - S[0]).max() < 1e-4)
            if const:
                is_ref = (np.abs(T[0] - REF_T[i]).max() < tol_pos and abs(np.dot(Q[0], REF_Q[i])) > cos_tol and np.abs(S[0] - 1).max() < 1e-4)
                if is_ref and bone != 'Trans':
                    continue
                out.append((bone, T[:1], Q[:1], S[:1]))
            else:
                out.append((bone, T, Q, S))
        return out

    def write(self, path, loop=False):
        """.cacanim: 'CACANIM1', u32 version 1, f32 fps, i32 frames, u32 flags (1 = loop), i32 tracks, then per track
        u16 name length + name (ASCII), i32 keys (1 or frames), keys x (T xyz, Q xyzw, S xyz) float32."""
        tracks = self.tracks()
        with open(path, 'wb') as f:
            f.write(b'CACANIM1')
            f.write(struct.pack('<IfiIi', 1, self.fps, self.frames, 1 if loop else 0, len(tracks)))
            for bone, T, Q, S in tracks:
                nb = bone.encode('ascii')
                f.write(struct.pack('<H', len(nb)) + nb)
                f.write(struct.pack('<i', len(T)))
                keys = np.concatenate([T, Q, S], -1).astype('<f4')
                f.write(keys.tobytes())
        return len(tracks)


def _ref_world():
    T, Q = REF_T, REF_Q
    W = {}
    wq = {}
    for i, n in enumerate(SK_NAMES):
        p = SK_PARENTS[i]
        if p < 0:
            W[n] = T[i]; wq[n] = Q[i]
        else:
            W[n] = W[SK_NAMES[p]] + qrot(wq[SK_NAMES[p]], T[i])
            wq[n] = qnorm(qmul(wq[SK_NAMES[p]], Q[i]))
    return W


REF_T_W = _ref_world()
