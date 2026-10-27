"""Per-animation motion summary of the retargeted KH2 FBXs (UE space: FBX local transforms with Y mirrored)."""
import sys, os, json, math, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fbxbin import Scene, props70
from xform import quat_from_euler_xyz_deg, qmul, qrot, to_ue, qangle
import numpy as np

BODY = ['C_Hip_a', 'C_Spine_a', 'C_Spine_b', 'C_Spine_c', 'C_Spine_d', 'C_Head_a', 'R_Shoulder_a', 'L_Shoulder_a',
        'R_Arm_a', 'L_Arm_a', 'R_Elbow_a', 'L_Elbow_a', 'R_Hand_a', 'L_Hand_a', 'R_Leg_a', 'L_Leg_a', 'R_Knee_a', 'L_Knee_a',
        'R_Foot_a', 'L_Foot_a']


def analyze(path):
    s = Scene(path)
    curves = s.curves()
    fps = s.settings.get('CustomFrameRate', [30.0])[0]
    n = 1
    for c in curves.values():
        for ch in c.values():
            for comp in ch.values():
                n = max(n, len(comp[0]))
    ms = s.models()
    byname = {v[1]: k for k, v in ms.items()}
    parent = {}
    for k, v in ms.items():
        p = s.parent.get(k)
        parent[v[1]] = ms[p][1] if p and p in ms else None
    defaults = {name: props70(ms[k][3]) for name, k in byname.items()}

    def chan(bone, channel):
        out = np.zeros((n, 3))
        c = curves.get(bone, {}).get(channel)
        d = defaults[bone].get(channel, [0.0, 0.0, 0.0])
        for i, a in enumerate('XYZ'):
            if c and ('d|' + a) in c:
                vals = list(c['d|' + a][1])
                vals = vals + [vals[-1]] * max(0, n - len(vals))
                out[:, i] = vals[:n]
            else:
                out[:, i] = d[i] if i < len(d) else 0.0
        return out

    cache = {}

    def local(bone):
        T, R = chan(bone, 'Lcl Translation'), chan(bone, 'Lcl Rotation')
        return [to_ue(tuple(T[f]), quat_from_euler_xyz_deg(*R[f])) for f in range(n)]

    def world(bone):
        if bone in cache:
            return cache[bone]
        loc = local(bone)
        p = parent.get(bone)
        if p is None or p == 'Armature':
            res = loc
        else:
            res = []
            for (pt, pq), (lt, lq) in zip(world(p), loc):
                t = qrot(pq, lt)
                res.append(((pt[0] + t[0], pt[1] + t[1], pt[2] + t[2]), qmul(pq, lq)))
        cache[bone] = res
        return res

    P = lambda b: np.array([t for t, q in world(b)])
    info = dict(file=os.path.basename(path).replace('_001_remap_remap.fbx', '').replace('_remap_remap.fbx', ''), frames=n, fps=fps,
                seconds=round((n - 1) / fps, 2))
    tr, hip = P('Trans'), P('C_Hip_a')
    info['root_move'] = [round(float(x)) for x in (tr[-1] - tr[0])]
    info['hip_move'] = [round(float(x)) for x in (hip[-1] - hip[0])]
    info['hip_z'] = [round(float(hip[:, 2].min())), round(float(hip[:, 2].max()))]
    info['hip_path'] = round(float(np.sum(np.linalg.norm(np.diff(hip, axis=0), axis=1))))
    rf, lf = P('R_Foot_a'), P('L_Foot_a')
    info['feet_z'] = round(float(max(rf[:, 2].max(), lf[:, 2].max())))
    info['feet_swing'] = round(float(np.ptp(rf[:, 0] - lf[:, 0]) + np.ptp(rf[:, 1] - lf[:, 1])))
    rh, lh = P('R_Hand_a'), P('L_Hand_a')
    info['hands_path'] = round(float(np.sum(np.linalg.norm(np.diff(rh, axis=0), axis=1)) + np.sum(np.linalg.norm(np.diff(lh, axis=0), axis=1))))
    info['hand_z_max'] = [round(float(rh[:, 2].max())), round(float(lh[:, 2].max()))]
    head = P('C_Head_a')
    info['head_z'] = [round(float(head[:, 2].min())), round(float(head[:, 2].max()))]
    diffs = [qangle(local(b)[0][1], local(b)[-1][1]) for b in BODY if b in byname]
    info['loop_deg'] = round(float(np.mean(diffs)), 1)
    return info


if __name__ == '__main__':
    files = sorted(glob.glob(sys.argv[1] + '/*.fbx'))
    import multiprocessing as mp
    out = []
    with mp.Pool(int(sys.argv[3])) as pool:
        for info in pool.imap(analyze, files):
            print(json.dumps(info), flush=True)
            out.append(info)
    json.dump(out, open(sys.argv[2], 'w'), indent=1)
