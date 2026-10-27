"""PC0010_13_BNM's spec: ch049_001's Bonamik (ch049_bnm_spec.json) on the re-rigged skeleton: every body under the bone
its bone became (rig.json's rename), each body exactly where and as it was (its component-space place and frame kept:
under a bone whose rest frame changed it takes the local place and rotation that keep it so). Everything else as is.
    make_bnm_spec.py <rig.json> <ch049_bnm_spec.json> <out spec.json>"""
import json, sys
import numpy as np
sys.path[:0] = ['/work/ch049bnm']
import make_ch049_bnm_spec as MS
sys.path[:0] = ['/work/ys/rig']
from build_rig_fbx import quat_matrix   # noqa (bpy-free part)


def mat_quat(R):
    """rotation matrix -> quaternion [x, y, z, w]"""
    m = R
    tr = m[0, 0] + m[1, 1] + m[2, 2]
    if tr > 0:
        s = np.sqrt(tr + 1.0) * 2
        w, x, y, z = 0.25 * s, (m[2, 1] - m[1, 2]) / s, (m[0, 2] - m[2, 0]) / s, (m[1, 0] - m[0, 1]) / s
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = np.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2
        w, x, y, z = (m[2, 1] - m[1, 2]) / s, 0.25 * s, (m[0, 1] + m[1, 0]) / s, (m[0, 2] + m[2, 0]) / s
    elif m[1, 1] > m[2, 2]:
        s = np.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2
        w, x, y, z = (m[0, 2] - m[2, 0]) / s, (m[0, 1] + m[1, 0]) / s, 0.25 * s, (m[1, 2] + m[2, 1]) / s
    else:
        s = np.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2
        w, x, y, z = (m[1, 0] - m[0, 1]) / s, (m[0, 2] + m[2, 0]) / s, (m[1, 2] + m[2, 1]) / s, 0.25 * s
    q = np.array([x, y, z, w])
    return q / np.linalg.norm(q)


def main(rig_path, spec_path, out_path):
    rig = json.load(open(rig_path))
    spec = json.load(open(spec_path))
    S = MS.Skel('/work/unityrip/out/model')
    new = {b['name']: (quat_matrix(b['q']), np.array(b['t'])) for b in rig['bones']}
    rename = rig['rename']
    moved = 0
    for b in spec['mBodies']:
        old = b['mParentName']
        nn = rename[old]
        R0, t0 = S.R[old], S.t[old]
        R1, t1 = new[nn]
        assert np.abs(t1 - t0).max() < 1e-3, (old, nn, t0, t1)      # the bone stays where it was
        p = t0 + R0 @ np.array(b['m_LocalTransform'])
        Rb = R0 @ quat_matrix(b['m_LocalRotation'])
        b['mParentName'] = nn
        b['m_LocalTransform'] = [round(float(x), 4) for x in R1.T @ (p - t1)]
        q = mat_quat(R1.T @ Rb)
        if np.abs(q - np.array([0, 0, 0, 1.0])).max() < 1e-6:
            q = np.array([0, 0, 0, 1.0])
        else:
            moved += 1
        b['m_LocalRotation'] = [round(float(x), 6) for x in q]
    json.dump(spec, open(out_path, 'w'), indent=1)
    print('%d bodies, %d under a bone whose frame changed (kept in place)' % (len(spec['mBodies']), moved))
    print(sorted({b['mParentName'] for b in spec['mBodies']})[:200])


if __name__ == '__main__':
    main(*sys.argv[1:4])
