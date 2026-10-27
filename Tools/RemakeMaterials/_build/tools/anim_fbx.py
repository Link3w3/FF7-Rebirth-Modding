"""FF7 Remake (UE 4.18 SQEX) cooked AnimSequence -> FBX 7.3 ASCII (its skeleton + one animation stack), for the End
editor's FBX animation import onto a skeleton made from skm_fbx.py's meshes.

The same conventions as skm_fbx.py, so the frames fit the imported skeleton:
  - declared Z-up / -Y front / right-handed (what the editor's import converts to, so nothing is converted); the
    import mirrors y, so everything goes out mirrored in y and comes back as the game has it:
    positions (x, -y, z), rotations (-x, y, -z, w), scales as they are
  - the root bone rests flat (skm_fbx.skeleton(flat_root=True)): with C the root's rest turn, every frame the root's
    transform is the game's times C^-1 and the root's children take C into theirs (root' = root C^-1,
    child' = C child), so every bone stays exactly where the game puts it, the root rests flat and the root's motion
    stays as authored (a turn about the up axis stays a turn about the up axis)
Each bone with a track in the clip gets linear keys for its local translation, rotation (Euler XYZ degrees, kept
continuous from frame to frame) and scale at every frame of the clip's sample rate (frame i at i / rate seconds; a
channel that never changes gets its first and last key only). The file holds those bones and their ancestors (the
ancestors without a track at the skeleton's reference pose, no curves); the import removes the ancestors' tracks
again (write() returns the tracked bones), so every bone without a track in the game falls back to the mesh's own
reference pose, as in the game.
The bones go out with the FBX default inherit type (RrSs: a parent's scale is applied along the child's axes),
which is how UE composes FTransforms, so scaled bones come back with the game's local values.

Additive clips (AAT_LocalSpaceBase) are written as full poses: their deltas put on their base pose (RefPoseSeq at
RefFrameIndex, ABPT_AnimFrame; or the skeleton's reference pose, ABPT_RefPose), as UE does when it plays them
(rotation delta * base, base + translation delta, base scale * (1 + scale delta)). Setting the imported sequence
additive against the same base again gives back the game's deltas.

    write(anim_path, skel, out_path, bones=None) -> info dict
    python3 anim_fbx.py <AnimSequence.uasset> <Skeleton.uasset> <out.fbx> [bones.json (a list of bone names)]"""
import sys, os, io, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import anim, pkg418

FBX_SECOND = 46186158000          # FBX time units a second
TIME_MODES = {120: 1, 100: 2, 60: 3, 50: 4, 48: 5, 30: 6, 24: 11, 1000: 12, 96: 15, 72: 16}


# ---- quaternion / matrix helpers (x, y, z, w; arrays [..., 4]) --------------------------------------------------
def qmul(a, b):
    ax, ay, az, aw = np.moveaxis(np.asarray(a, np.float64), -1, 0)
    bx, by, bz, bw = np.moveaxis(np.asarray(b, np.float64), -1, 0)
    return np.stack([aw * bx + ax * bw + ay * bz - az * by,
                     aw * by - ax * bz + ay * bw + az * bx,
                     aw * bz + ax * by - ay * bx + az * bw,
                     aw * bw - ax * bx - ay * by - az * bz], -1)


def qconj(q):
    return np.asarray(q, np.float64) * np.array([-1.0, -1.0, -1.0, 1.0])


def qnorm(q):
    q = np.asarray(q, np.float64)
    return q / np.maximum(np.linalg.norm(q, axis=-1, keepdims=True), 1e-12)


def qrot(q, v):
    """rotate vectors v [..., 3] by unit quaternions q [..., 4]"""
    q = np.asarray(q, np.float64); v = np.asarray(v, np.float64)
    u, w = q[..., :3], q[..., 3:4]
    t = 2.0 * np.cross(u, v)
    return v + w * t + np.cross(u, t)


def qmats(q):
    q = qnorm(q)
    x, y, z, w = np.moveaxis(q, -1, 0)
    R = np.empty(q.shape[:-1] + (3, 3))
    R[..., 0, 0] = 1 - 2 * (y * y + z * z); R[..., 0, 1] = 2 * (x * y - z * w); R[..., 0, 2] = 2 * (x * z + y * w)
    R[..., 1, 0] = 2 * (x * y + z * w); R[..., 1, 1] = 1 - 2 * (x * x + z * z); R[..., 1, 2] = 2 * (y * z - x * w)
    R[..., 2, 0] = 2 * (x * z - y * w); R[..., 2, 1] = 2 * (y * z + x * w); R[..., 2, 2] = 1 - 2 * (x * x + y * y)
    return R


def euler_xyz(R):
    """R = Rz(c) Ry(b) Rx(a) -> (a, b, c) degrees (FBX eEulerXYZ, the order skm_fbx.euler_xyz uses), for arrays
    [..., 3, 3]. b from atan2(sin b, cos b), so a bone a hair off the gimbal lock (b near +-90) keeps its exact turn;
    only at the lock itself (cos b ~ 0) c is 0 and a takes the whole turn"""
    cb = np.hypot(R[..., 0, 0], R[..., 1, 0])
    b = np.arctan2(-R[..., 2, 0], cb)
    regular = cb > 1e-9
    a = np.where(regular, np.arctan2(R[..., 2, 1], R[..., 2, 2]), np.arctan2(-R[..., 1, 2], R[..., 1, 1]))
    c = np.where(regular, np.arctan2(R[..., 1, 0], R[..., 0, 0]), 0.0)
    return np.degrees(np.stack([a, b, c], -1))


def euler_filter(E):
    """E [bones, frames, 3] degrees -> the same rotations, each frame the equivalent angles nearest the frame before
    ((a, b, c) == (a + 180, 180 - b, c + 180), each angle modulo 360), so the curves have no 360 degree jumps"""
    E = np.array(E, np.float64, copy=True)
    for i in range(1, E.shape[1]):
        prev = E[:, i - 1]
        a, b, c = E[:, i, 0], E[:, i, 1], E[:, i, 2]
        best, bestd = None, None
        for alt in (E[:, i], np.stack([a + 180.0, 180.0 - b, c + 180.0], -1)):
            cand = alt + 360.0 * np.round((prev - alt) / 360.0)
            d = np.abs(cand - prev).sum(-1)
            if best is None:
                best, bestd = cand, d
            else:
                pick = d < bestd - 1e-9
                best = np.where(pick[:, None], cand, best); bestd = np.where(pick, d, bestd)
        E[:, i] = best
    return E


# ---- the game's data --------------------------------------------------------------------------------------------
def game_root_of(path):
    """the extracted game folder that holds 'GameContents' (the /Game/ of the game's package paths)"""
    p = os.path.abspath(path).replace('\\', '/')
    k = p.rfind('/GameContents/')
    if k < 0:
        raise ValueError('%s is not under a GameContents folder' % path)
    return p[:k]


def package_file(game_root, object_path):
    """'/Game/GameContents/X/Y.Y' -> <game_root>/GameContents/X/Y.uasset"""
    pkg = object_path.split('.')[0]
    if not pkg.startswith('/Game/'):
        raise ValueError('not a /Game/ package: %s' % object_path)
    return os.path.join(game_root, pkg[len('/Game/'):] + '.uasset')


def clip(path):
    """an AnimSequence package -> its props, track map, curves and its decoded tracks
    rot [T, N, 4], trans [T, N, 3], scale [T, N, 3] (ones without scale tracks); T tracks, N frames"""
    a = anim.read(path)
    c = anim.acl_decode(a['acl'])
    if c['num_bones'] != len(a['track_map']):
        raise ValueError('%s: %d ACL tracks, %d in the track map' % (path, c['num_bones'], len(a['track_map'])))
    scale = c['scale']
    additive = str(a['props'].get('AdditiveAnimType') or 'AAT_None')
    if scale is None:
        scale = np.full(c['trans'].shape, 0.0 if additive != 'AAT_None' else 1.0)
    pkg = pkg418.Package(path)
    ref = a['props'].get('RefPoseSeq')
    a['ref_pose_seq_path'] = pkg.import_path(ref) if isinstance(ref, int) and ref < 0 else None
    a.update(rot=c['rot'], trans=c['trans'], scale=scale, num_samples=c['num_samples'], sample_rate=c['sample_rate'],
             has_scale=c['has_scale'], kinds=c['kinds'], additive=additive)
    return a


def ref_pose(skel):
    P = np.array(skel['poses'], np.float64)
    return qnorm(P[:, 0:4]), P[:, 4:7], P[:, 7:10]


def pose_at(C, frame, skel):
    """the full local pose (q, t, s per skeleton bone) of a (non additive) clip at a frame; the reference pose for
    bones without a track"""
    q, t, s = (x.copy() for x in ref_pose(skel))
    f = min(max(int(frame), 0), C['num_samples'] - 1)
    for k, b in enumerate(C['track_map']):
        q[b], t[b], s[b] = C['rot'][k, f], C['trans'][k, f], C['scale'][k, f]
    return q, t, s


def full_tracks(C, skel, game_root=None):
    """the clip's tracks as full local poses [T, N, ...]: additive clips get their deltas put on their base pose, and
    keep tracks for the bones their base animates too. Returns (track bones, q, t, s, base info)"""
    bones = list(C['track_map'])
    q, t, s = C['rot'], C['trans'], C['scale']
    if C['additive'] == 'AAT_None':
        return bones, q, t, s, None
    if C['additive'] != 'AAT_LocalSpaceBase':
        raise NotImplementedError('additive type %s' % C['additive'])
    rp = str(C['props'].get('RefPoseType') or 'ABPT_None')
    base = dict(type=rp)
    if rp == 'ABPT_AnimFrame':
        if not C['ref_pose_seq_path']:
            raise ValueError('additive clip without its base sequence')
        frame = int(C['props'].get('RefFrameIndex') or 0)
        bpath = package_file(game_root, C['ref_pose_seq_path'])
        B = clip(bpath)
        if B['additive'] != 'AAT_None':
            raise NotImplementedError('the base sequence is additive itself')
        bq, bt, bs = pose_at(B, frame, skel)
        base.update(sequence=C['ref_pose_seq_path'], frame=frame, file=bpath, base_tracks=list(B['track_map']))
        extra = [b for b in B['track_map'] if b not in bones]
    elif rp == 'ABPT_RefPose':
        bq, bt, bs = ref_pose(skel)
        extra = []
    else:
        raise NotImplementedError('additive base pose type %s' % rp)
    n = q.shape[1]
    allb = bones + extra
    Q = np.empty((len(allb), n, 4)); T = np.empty((len(allb), n, 3)); S = np.empty((len(allb), n, 3))
    for k, b in enumerate(allb):
        if k < len(bones):
            # (FTransform::BlendFromIdentityAndAccumulate at full weight)
            Q[k] = qnorm(qmul(q[k], bq[b][None, :]))
            T[k] = bt[b][None, :] + t[k]
            S[k] = bs[b][None, :] * (1.0 + s[k])
        else:
            Q[k], T[k], S[k] = bq[b], bt[b], bs[b]
    return allb, Q, T, S, base


# ---- conversion to the FBX's space ------------------------------------------------------------------------------
def mirror_q(q):
    return np.asarray(q, np.float64) * np.array([-1.0, 1.0, -1.0, 1.0])


def mirror_v(v):
    return np.asarray(v, np.float64) * np.array([1.0, -1.0, 1.0])


def to_fbx(names, parents, q, t, s, root_rest_q):
    """game-space local transforms of the written bones ([B, N, ...], parents indexing the written bones) -> the
    FBX's local (t, q, s): mirrored in y, the root flat (root C^-1, root's children C child)"""
    qm, tm = mirror_q(q), mirror_v(t)
    s = np.array(s, np.float64, copy=True)
    qc = qnorm(mirror_q(root_rest_q))
    for i, p in enumerate(parents):
        if p < 0:
            qm[i] = qnorm(qmul(qm[i], qconj(qc)[None, :]))
        elif parents[p] < 0:
            qm[i] = qnorm(qmul(qc[None, :], qm[i]))
            tm[i] = qrot(np.broadcast_to(qc, qm[i].shape), tm[i])
    return tm, qm, s


def fmt(a, nd=9):
    a = np.asarray(a, np.float64).ravel()
    return ','.join(('%.*g' % (nd, v)) for v in a.tolist())


def write(anim_path, skel, out_path, bones=None, game_root=None, name=None, every_bone=False):
    """anim_path: the game's AnimSequence package; skel: anim.skeleton() of the USkeleton its track map indexes;
    bones: the bone names the target skeleton has (default all the skeleton's; a track for another bone is an error);
    the file holds the tracked bones and their ancestors (every_bone: all of `bones`), in skeleton order;
    out_path: the FBX. Returns what the import needs (tracked bones, curves, additive base, flags)."""
    game_root = game_root or game_root_of(anim_path)
    name = name or os.path.basename(anim_path)[:-7]
    C = clip(anim_path)
    if C['sample_rate'] <= 0:
        raise ValueError('sample rate %r' % C['sample_rate'])
    sk_names, sk_par = skel['names'], skel['parents']
    sk_index = {nm: i for i, nm in enumerate(sk_names)}
    want = set(range(len(sk_names))) if bones is None else {sk_index[nm] for nm in bones}
    tb, Q, T, S, base = full_tracks(C, skel, game_root)
    missing = [sk_names[b] for b in tb if b not in want]
    if missing:
        raise ValueError('%s: tracks for bones not written: %s' % (name, ', '.join(missing[:10])))
    want = set(want) if every_bone else set(tb)
    for b in list(want):                    # (every ancestor of a written bone)
        p = sk_par[b]
        while p >= 0 and p not in want:
            want.add(p); p = sk_par[p]
    order = sorted(want)
    pos = {b: i for i, b in enumerate(order)}
    parents = [pos[sk_par[b]] if sk_par[b] >= 0 else -1 for b in order]
    if sum(1 for p in parents if p < 0) != 1 or parents[0] != -1:
        raise ValueError('the written bones need one root, first')
    n = C['num_samples']
    rq, rt, rs = ref_pose(skel)
    # every written bone, every frame (untracked bones hold their reference pose)
    q = np.repeat(rq[order][:, None, :], n, 1); t = np.repeat(rt[order][:, None, :], n, 1); s = np.repeat(rs[order][:, None, :], n, 1)
    tracked = np.zeros(len(order), bool)
    for k, b in enumerate(tb):
        q[pos[b]], t[pos[b]], s[pos[b]] = Q[k], T[k], S[k]
        tracked[pos[b]] = True
    root_scale = s[0]
    if np.abs(root_scale - root_scale[:, :1]).max() > 1e-5:
        raise NotImplementedError('the root scales non-uniformly')
    if np.abs(rs[order[0]] - 1.0).max() > 1e-6:
        raise NotImplementedError('the root rests scaled')
    T3, Q4, S3 = to_fbx([sk_names[b] for b in order], parents, q, t, s, rq[order[0]])
    E = euler_filter(euler_xyz(qmats(Q4)))
    rate = int(C['sample_rate'])
    times = [(i * FBX_SECOND) // rate for i in range(n)]
    stop = times[-1]
    names = [sk_names[b] for b in order]
    # ---- FBX text
    ids = iter(range(1000000000, 2000000000))
    bone_model = [next(ids) for _ in names]; bone_attr = [next(ids) for _ in names]
    stack, layer = next(ids), next(ids)
    out = io.StringIO(); w = out.write
    w('; FBX 7.3.0 project file\n; written by anim_fbx.py from FINAL FANTASY VII REMAKE cooked animation %s\n\n' % name)
    w('FBXHeaderExtension:  {\n\tFBXHeaderVersion: 1003\n\tFBXVersion: 7300\n\tCreator: "anim_fbx"\n}\n')
    w('GlobalSettings:  {\n\tVersion: 1000\n\tProperties70:  {\n')
    for k, v in (('UpAxis', 2), ('UpAxisSign', 1), ('FrontAxis', 1), ('FrontAxisSign', -1), ('CoordAxis', 0), ('CoordAxisSign', 1),
                 ('OriginalUpAxis', 2), ('OriginalUpAxisSign', 1)):
        w('\t\tP: "%s", "int", "Integer", "",%d\n' % (k, v))
    w('\t\tP: "UnitScaleFactor", "double", "Number", "",1\n\t\tP: "OriginalUnitScaleFactor", "double", "Number", "",1\n')
    w('\t\tP: "TimeMode", "enum", "", "",%d\n' % TIME_MODES.get(rate, 14))
    w('\t\tP: "TimeSpanStart", "KTime", "Time", "",0\n\t\tP: "TimeSpanStop", "KTime", "Time", "",%d\n' % stop)
    w('\t\tP: "CustomFrameRate", "double", "Number", "",%d\n\t}\n}\n' % rate)
    w('Documents:  {\n\tCount: 1\n\tDocument: 999999999, "", "Scene" {\n\t\tProperties70:  {\n\t\t\tP: "SourceObject", "object", "", ""\n')
    w('\t\t\tP: "ActiveAnimStackName", "KString", "", "", "%s"\n\t\t}\n\t\tRootNode: 0\n\t}\n}\nReferences:  {\n}\n' % name)
    channels = []        # (bone index, property, letter, values)
    for i in range(len(names)):
        if not tracked[i]:
            continue
        for prop, letter, vals in (('Lcl Translation', 'T', T3[i]), ('Lcl Rotation', 'R', E[i]), ('Lcl Scaling', 'S', S3[i])):
            channels.append((i, prop, letter, vals))
    w('Definitions:  {\n\tVersion: 100\n\tCount: %d\n' % (1 + 2 * len(names) + 2 + len(channels) * 4))
    for typ, cnt in (('GlobalSettings', 1), ('Model', len(names)), ('NodeAttribute', len(names)), ('AnimationStack', 1),
                     ('AnimationLayer', 1), ('AnimationCurveNode', len(channels)), ('AnimationCurve', len(channels) * 3)):
        w('\tObjectType: "%s" {\n\t\tCount: %d\n\t}\n' % (typ, cnt))
    w('}\nObjects:  {\n')
    for i, nm in enumerate(names):
        w('\tNodeAttribute: %d, "NodeAttribute::%s", "LimbNode" {\n\t\tTypeFlags: "Skeleton"\n\t}\n' % (bone_attr[i], nm))
        w('\tModel: %d, "Model::%s", "LimbNode" {\n\t\tVersion: 232\n\t\tProperties70:  {\n' % (bone_model[i], nm))
        w('\t\t\tP: "InheritType", "enum", "", "",0\n')
        w('\t\t\tP: "Lcl Translation", "Lcl Translation", "", "A",%s\n' % fmt(T3[i, 0]))
        w('\t\t\tP: "Lcl Rotation", "Lcl Rotation", "", "A",%s\n' % fmt(E[i, 0]))
        w('\t\t\tP: "Lcl Scaling", "Lcl Scaling", "", "A",%s\n' % fmt(S3[i, 0]))
        w('\t\t\tP: "DefaultAttributeIndex", "int", "Integer", "",0\n\t\t}\n\t\tShading: Y\n\t\tCulling: "CullingOff"\n\t}\n')
    w('\tAnimationStack: %d, "AnimStack::%s", "" {\n\t\tProperties70:  {\n' % (stack, name))
    for k in ('LocalStart', 'LocalStop', 'ReferenceStart', 'ReferenceStop'):
        w('\t\t\tP: "%s", "KTime", "Time", "",%d\n' % (k, 0 if k.endswith('Start') else stop))
    w('\t\t}\n\t}\n')
    w('\tAnimationLayer: %d, "AnimLayer::BaseLayer", "" {\n\t}\n' % layer)
    ktimes = ','.join(str(x) for x in times)
    ktimes_ends = '%d,%d' % (times[0], times[-1])
    conns = []
    for (i, prop, letter, vals) in channels:
        cn = next(ids)
        w('\tAnimationCurveNode: %d, "AnimCurveNode::%s", "" {\n\t\tProperties70:  {\n' % (cn, letter))
        for ax, comp in zip('XYZ', vals[0]):
            w('\t\t\tP: "d|%s", "Number", "", "A",%s\n' % (ax, fmt([comp])))
        w('\t\t}\n\t}\n')
        conns.append('\tC: "OO",%d,%d\n' % (cn, layer))
        conns.append('\tC: "OP",%d,%d, "%s"\n' % (cn, bone_model[i], prop))
        for a, ax in enumerate('XYZ'):
            cv = next(ids)
            v = vals[:, a]
            if n > 2 and np.all(v == v[0]):
                kt, kv = ktimes_ends, v[[0, -1]]          # (a channel that never changes: its first and last key)
            else:
                kt, kv = ktimes, v
            w('\tAnimationCurve: %d, "AnimCurve::", "" {\n\t\tDefault: %s\n\t\tKeyVer: 4009\n' % (cv, fmt([v[0]])))
            w('\t\tKeyTime: *%d {\n\t\t\ta: %s\n\t\t}\n' % (len(kv), kt))
            w('\t\tKeyValueFloat: *%d {\n\t\t\ta: %s\n\t\t}\n' % (len(kv), fmt(kv)))
            # (one attribute for every key: linear interpolation)
            w('\t\tKeyAttrFlags: *1 {\n\t\t\ta: 24836\n\t\t}\n\t\tKeyAttrDataFloat: *4 {\n\t\t\ta: 0,0,255790911,0\n\t\t}\n')
            w('\t\tKeyAttrRefCount: *1 {\n\t\t\ta: %d\n\t\t}\n\t}\n' % len(kv))
            conns.append('\tC: "OP",%d,%d, "d|%s"\n' % (cv, cn, ax))
    w('}\nConnections:  {\n')
    for i, par in enumerate(parents):
        w('\tC: "OO",%d,%d\n' % (bone_attr[i], bone_model[i]))
        w('\tC: "OO",%d,%d\n' % (bone_model[i], 0 if par < 0 else bone_model[par]))
    w('\tC: "OO",%d,%d\n' % (layer, stack))
    w(''.join(conns))
    w('}\nTakes:  {\n\tCurrent: "%s"\n\tTake: "%s" {\n\t\tFileName: "%s.tak"\n\t\tLocalTime: 0,%d\n\t\tReferenceTime: 0,%d\n\t}\n}\n'
      % (name, name, name, stop, stop))
    tmp = out_path + '.tmp'
    with open(tmp, 'w', newline='\n') as f:
        f.write(out.getvalue())
    os.replace(tmp, out_path)
    P = C['props']
    curves = []
    for cv in C['curves']:
        fc = cv.get('FloatCurve') or {}
        curves.append(dict(name=cv.get('Name'), flags=cv.get('CurveTypeFlags'),
                           keys=[[k['Time'], k['Value'], k['InterpMode']] for k in (fc.get('Keys') or [])]))
    return dict(name=name, frames=int(P.get('NumFrames') or n), samples=n, rate=rate,
                length=float(P.get('SequenceLength') or (n - 1) / float(rate)),
                tracks=[sk_names[b] for b in tb], game_tracks=[sk_names[b] for b in C['track_map']],
                bones_written=len(names), written=names, has_scale=bool(C['has_scale']),
                additive=C['additive'], ref_pose_type=str(P.get('RefPoseType') or 'ABPT_None'), base=(
                    None if base is None else {k: v for k, v in base.items() if k in ('type', 'sequence', 'frame')}),
                enable_root_motion=(P['bEnableRootMotion'] if 'bEnableRootMotion' in P else None),
                force_root_lock=(P['bForceRootLock'] if 'bForceRootLock' in P else None),
                rate_scale=P.get('RateScale'), curves=curves, notifies=len(P.get('Notifies') or []))


if __name__ == '__main__':
    src, skel_path, out_path = sys.argv[1:4]
    bones = json.load(open(sys.argv[4])) if len(sys.argv) > 4 else None
    info = write(src, anim.skeleton(skel_path), out_path, bones)
    print(json.dumps({k: (v if k not in ('tracks', 'game_tracks', 'curves') else len(v)) for k, v in info.items()}, default=str))
    print(os.path.getsize(out_path), 'bytes')
