"""rig.json (Young Sephiroth on Rebirth's bones) + the transformed Sephiroth's wing: the wing's 94 bones (R_Feather*, the
root R_FeatherShoulder_a on C_Spine_d as on Sephiroth) and C_KDIRoot (the parent of its 9 KineDriver bones), with
Sephiroth's names, parents and frames, placed on Young Sephiroth's back:
  * R_FeatherShoulder_a at Sephiroth's spot on C_Spine_d (his local offset times ATTACH: Young Sephiroth's back is that much
    of Sephiroth's), in the same frame relative to C_Spine_d;
  * the rest of the wing Sephiroth's, made WING times as big around its root.
Writes the new rig (rig.json's format: component-space frames, centimetres) and the map it used ("wing": the same for the
wing's vertices).
    make_rig_wing.py <rig.json> <seph_bones.json> <out rig.json> [WING] [ATTACH]"""
import json, sys
import numpy as np

ATTACH_FROM = ('C_Spine_d', 'C_Neck_a', 'C_Hip_a')   # his back against Sephiroth's: spine_d->neck and hip->spine_d


def qm(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def mq(m):
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
    q = q / np.linalg.norm(q)
    return q if q[3] >= 0 else -q


def main(rig_path, seph_path, out, wing=0.8, attach=None):
    rig = json.load(open(rig_path))
    seph = json.load(open(seph_path))
    names = [b[0] for b in seph['bones']]
    parent = {b[0]: (names[b[1]] if b[1] >= 0 else None) for b in seph['bones']}
    cs = {n: (qm(c[0]), np.array(c[1])) for n, c in zip(names, seph['cs'])}
    ys = {b['name']: (qm(b['q']), np.array(b['t'])) for b in rig['bones']}
    assert not any('Feather' in n for n in ys), 'the rig has wing bones already'
    if attach is None:
        sp, nk, hp = ATTACH_FROM
        attach = float(np.mean([np.linalg.norm(ys[nk][1] - ys[sp][1]) / np.linalg.norm(cs[nk][1] - cs[sp][1]),
                                np.linalg.norm(ys[sp][1] - ys[hp][1]) / np.linalg.norm(cs[sp][1] - cs[hp][1])]))
    Rs, ts = cs['C_Spine_d']
    Ry, ty = ys['C_Spine_d']
    turn = Ry @ Rs.T                                         # Sephiroth's spine frame -> his
    Qr, r_s = cs['R_FeatherShoulder_a']
    r_y = ty + Ry @ (attach * (Rs.T @ (r_s - ts)))           # the root: Sephiroth's local offset on C_Spine_d, scaled
    wing_bones = [n for n in names if 'Feather' in n]
    add = []
    if 'C_KDIRoot' not in ys:
        assert parent['C_KDIRoot'] in ys, parent['C_KDIRoot']
        add.append(dict(name='C_KDIRoot', parent=parent['C_KDIRoot'], q=[round(float(x), 7) for x in mq(cs['C_KDIRoot'][0])],
                        t=[round(float(x), 5) for x in cs['C_KDIRoot'][1]], src=None))
    have = set(ys) | {'C_KDIRoot'}
    for n in wing_bones:
        assert parent[n] in have, (n, parent[n])
        Q, p = cs[n]
        add.append(dict(name=n, parent=parent[n], q=[round(float(x), 7) for x in mq(turn @ Q)],
                        t=[round(float(x), 5) for x in r_y + turn @ (wing * (p - r_s))], src=None))
        have.add(n)
    rig['bones'] = rig['bones'] + add
    rig['wing'] = dict(scale=wing, attach=attach, turn=turn.round(9).tolist(), seph_root=r_s.tolist(), root=r_y.tolist(),
                       bones=[b['name'] for b in add])
    json.dump(rig, open(out, 'w'), indent=1)
    print('added %d bones (%d wing bones, C_KDIRoot); wing x%.3f, attached at x%.3f of Sephiroth\'s offset on C_Spine_d; '
          'root %s (Sephiroth\'s %s); frames turned %.2f deg with C_Spine_d' % (
              len(add), len(wing_bones), wing, attach, r_y.round(2), r_s.round(2),
              np.degrees(np.arccos(np.clip((np.trace(turn) - 1) / 2, -1, 1)))))


if __name__ == '__main__':
    a = sys.argv[1:]
    main(a[0], a[1], a[2], *(float(x) for x in a[3:5]))
