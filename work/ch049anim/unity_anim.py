"""Unity Mecanim clips (AnimationClip m_MuscleClip: streamed Hermite curves, dense samples, constants) -> local
transform tracks for every transform of a rig, sampled at the clip's rate.

  rig = load_rig(character bundle, root object name)    the prefab hierarchy: paths, parents, local TRS at rest
  for clip in clips(motion bundle): tracks = decode(clip, rig)   -> dict(fps, times, T [f,n,3], Q [f,n,4], S [f,n,3], loop)

Streamed data: frames of (time, key count, keys (curve index, 4 cubic coefficients)); a key's curve runs
c0 x^3 + c1 x^2 + c2 x + c3 from its time until the curve's next key (x = t - key time). Curve indices run over the
streamed curves, then the dense ones, then the constants; the clip's generic bindings take 3 curves for a position,
scale or euler, 4 for a rotation and 1 for anything else, in order; their paths are CRC32s of the transform paths.
"""
import struct, zlib
import numpy as np
import UnityPy


def rd(p):
    return p.deref_parse_as_object() if hasattr(p, 'deref_parse_as_object') else p.read()


class Rig:
    pass


def load_rig(bundle, root_name='skin_ch049_001'):
    env = UnityPy.load(bundle)
    tr, go = {}, {}
    for o in env.objects:
        if o.type.name == 'Transform':
            t = o.read()
            tr[o.path_id] = t
            go[o.path_id] = rd(t.m_GameObject).m_Name
    root = [p for p, n in go.items() if n == root_name]
    assert len(root) == 1, root_name
    rig = Rig()
    rig.names, rig.parents, rig.paths = [], [], []
    rig.T, rig.Q, rig.S = [], [], []

    def walk(pid, parent, path):
        i = len(rig.names)
        t = tr[pid]
        rig.names.append(go[pid])
        rig.parents.append(parent)
        rig.paths.append(path)
        p, q, s = t.m_LocalPosition, t.m_LocalRotation, t.m_LocalScale
        rig.T.append([p.x, p.y, p.z])
        rig.Q.append([q.x, q.y, q.z, q.w])
        rig.S.append([s.x, s.y, s.z])
        for c in t.m_Children:
            walk(c.path_id, i, (path + '/' if path else '') + go[c.path_id])
    walk(root[0], -1, '')
    rig.T, rig.Q, rig.S = np.array(rig.T), np.array(rig.Q), np.array(rig.S)
    rig.index = {n: i for i, n in enumerate(rig.names)}
    rig.by_hash = {zlib.crc32(p.encode('utf-8')) & 0xffffffff: i for i, p in enumerate(rig.paths)}
    return rig


def clips(bundle, skip_cam=True):
    env = UnityPy.load(bundle)
    out = []
    for o in env.objects:
        if o.type.name == 'AnimationClip':
            a = o.read()
            if skip_cam and a.m_Name.endswith('_cam'):
                continue
            out.append(a)
    return sorted(out, key=lambda a: a.m_Name)


def _streamed(sc):
    raw = np.asarray(sc.data, dtype=np.uint32).tobytes()
    keys = {}
    pos = 0
    while pos < len(raw):
        t, n = struct.unpack_from('<fi', raw, pos)
        pos += 8
        for _ in range(n):
            idx = struct.unpack_from('<i', raw, pos)[0]
            c = struct.unpack_from('<4f', raw, pos + 4)
            pos += 20
            keys.setdefault(idx, []).append((t, c))
    return keys


def _eval_streamed(keylist, times):
    kt = np.array([k[0] for k in keylist], dtype=np.float64)
    kc = np.array([k[1] for k in keylist], dtype=np.float64)
    ok = np.isfinite(kt) & (np.abs(kt) < 1e30)
    if ok.any():
        first = np.argmax(ok)
        kt, kc = kt[first:], kc[first:]
        ok = np.isfinite(kt) & (np.abs(kt) < 1e30)
        kt, kc = kt[ok], kc[ok]
    else:
        return np.full(len(times), kc[0][3])
    j = np.clip(np.searchsorted(kt, times + 1e-6, side='right') - 1, 0, len(kt) - 1)
    x = np.maximum(times - kt[j], 0.0)
    c = kc[j]
    return ((c[:, 0] * x + c[:, 1]) * x + c[:, 2]) * x + c[:, 3]


def _binding_curves(bindings):
    """[(binding, first curve, dimension)]"""
    out = []
    n = 0
    for b in bindings:
        if b.typeID == 4:
            d = 4 if b.attribute == 2 else (3 if b.attribute in (1, 3, 4) else 1)
        else:
            d = 1
        out.append((b, n, d))
        n += d
    return out, n


def euler_zxy_to_quat(e):
    """Unity euler (degrees, applied Z then X then Y) -> quaternion xyzw"""
    x, y, z = np.radians(e[..., 0]) / 2, np.radians(e[..., 1]) / 2, np.radians(e[..., 2]) / 2
    cx, sx, cy, sy, cz, sz = np.cos(x), np.sin(x), np.cos(y), np.sin(y), np.cos(z), np.sin(z)
    # q = qy * qx * qz
    qw = cy * cx * cz + sy * sx * sz
    qx = cy * sx * cz + sy * cx * sz
    qy = sy * cx * cz - cy * sx * sz
    qz = cy * cx * sz - sy * sx * cz
    return np.stack([qx, qy, qz, qw], -1)


def decode(a, rig):
    mc = a.m_MuscleClip
    cl = mc.m_Clip.data if hasattr(mc.m_Clip, 'data') else mc.m_Clip
    fps = float(a.m_SampleRate)
    start, stop = float(mc.m_StartTime), float(mc.m_StopTime)
    nf = int(round((stop - start) * fps)) + 1
    times = start + np.arange(nf) / fps
    sc, dc, cc = cl.m_StreamedClip, cl.m_DenseClip, cl.m_ConstantClip
    ns, nd = int(sc.curveCount), int(dc.m_CurveCount)
    values = {}
    for idx, kl in _streamed(sc).items():
        values[idx] = _eval_streamed(kl, times)
    if nd:
        arr = np.asarray(dc.m_SampleArray, dtype=np.float64).reshape(int(dc.m_FrameCount), nd)
        dt = float(dc.m_BeginTime) + np.arange(arr.shape[0]) / float(dc.m_SampleRate)
        for j in range(nd):
            values[ns + j] = np.interp(times, dt, arr[:, j])
    for j, v in enumerate(cc.data):
        values[ns + nd + j] = np.full(nf, float(v))
    n = len(rig.names)
    T = np.repeat(rig.T[None], nf, 0).copy()
    Q = np.repeat(rig.Q[None], nf, 0).copy()
    S = np.repeat(rig.S[None], nf, 0).copy()
    binds, total = _binding_curves(a.m_ClipBindingConstant.genericBindings)
    animated, unknown, missing = set(), set(), 0
    for b, first, d in binds:
        if b.typeID != 4:
            continue
        i = rig.by_hash.get(b.path)
        if i is None:
            unknown.add(b.path)
            continue
        cols = [values.get(first + k) for k in range(d)]
        if any(c is None for c in cols):
            missing += 1
            continue
        v = np.stack(cols, -1)
        if b.attribute == 1:
            T[:, i] = v
        elif b.attribute == 2:
            Q[:, i] = v / np.linalg.norm(v, axis=-1, keepdims=True)
        elif b.attribute == 3:
            S[:, i] = v
        elif b.attribute == 4:
            Q[:, i] = euler_zxy_to_quat(v)
        animated.add(i)
    for i in range(n):           # one hemisphere per track
        q = Q[:, i]
        for f in range(1, nf):
            if np.dot(q[f], q[f - 1]) < 0:
                q[f] = -q[f]
    loop = bool(getattr(mc, 'm_LoopTime', False))
    return dict(name=a.m_Name, fps=fps, times=times, T=T, Q=Q, S=S, loop=loop, animated=sorted(animated),
                unknown_paths=len(unknown), missing_curves=missing, curves=total, have=len(values))


def qmat(q):
    x, y, z, w = np.moveaxis(q, -1, 0)
    R = np.stack([1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w),
                  2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w),
                  2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)], -1)
    return R.reshape(q.shape[:-1] + (3, 3))


def world(T, Q, S, parents):
    """[f, n, 4, 4] world matrices of local tracks"""
    f, n = T.shape[:2]
    L = np.zeros((f, n, 4, 4))
    L[..., :3, :3] = qmat(Q) * S[..., None, :]
    L[..., :3, 3] = T
    L[..., 3, 3] = 1
    W = np.zeros_like(L)
    for i, p in enumerate(parents):
        W[:, i] = L[:, i] if p < 0 else W[:, p] @ L[:, i]
    return W
