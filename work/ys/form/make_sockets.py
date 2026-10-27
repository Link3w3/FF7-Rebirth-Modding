"""Sephiroth's 51 mesh sockets (PC0010_00) placed on Young Sephiroth's CH049_001_Skeleton, so the game finds every socket
it attaches to by name (the Masamune, effects, damage sources, UI markers) on his model:

  * a socket on one of Sephiroth's body bones goes on CH049's matching bone (retarget_from_seph's map), turned and moved so
    that it sits on CH049 as it sits on Sephiroth whenever CH049's bone is posed as the retarget poses it (the bone's rest
    turned to point the way Sephiroth's rest bone points: MATCHED), its offset scaled down to CH049's size (hip heights);
  * a socket on L_Weapon_a (the Masamune's bone, blade +Z, edge +Y) goes on main_weapon (CH049's sword, blade +Y, edge
    -Z), with the same blade-and-edge turn the retarget gives the sword (KC), its offset along the blade kept (one sword);
  * a socket on Trans goes on CH049's root (identity at rest; Trans rests at the exporter's axis change);
  * a socket on a bone CH049 has nothing of (the weapon bones of the right hand, the helper bones for held characters,
    the wing) goes on the nearest of its ancestors that maps, with its place relative to that ancestor at rest.
    make_sockets.py <seph sockets json (probe_ys3)> <out json>"""
import json, sys
sys.path[:0] = ['/work/acl', '/work/ch049anim', '/work/ys']
import numpy as np
import retarget_from_seph as RS

SE, CH, CV = RS.SE, RS.CH, RS.CV
qmul, qinv, qrot, qnorm = CV.qmul, CV.qinv, CV.qrot, CV.qnorm
SCALE = 1.0 / RS.HIP_SCALE


def rot_quat(pitch, yaw, roll):
    """FRotator (degrees) -> quaternion [x, y, z, w] (UE's FRotator::Quaternion)."""
    dr = np.pi / 360.0
    sp, cp = np.sin(pitch * dr), np.cos(pitch * dr)
    sy, cy = np.sin(yaw * dr), np.cos(yaw * dr)
    sr, cr = np.sin(roll * dr), np.cos(roll * dr)
    return np.array([cr * sp * sy - sr * cp * cy, -cr * sp * cy - sr * cp * sy, cr * cp * sy - sr * sp * cy, cr * cp * cy + sr * sp * sy])


def quat_rot(q):
    """quaternion [x, y, z, w] -> FRotator (pitch, yaw, roll) degrees (UE's FQuat::Rotator)."""
    x, y, z, w = q
    sing = z * x - w * y
    yaw_y = 2.0 * (w * z + x * y)
    yaw_x = 1.0 - 2.0 * (y * y + z * z)
    thr = 0.4999995
    r2d = 180.0 / np.pi
    if sing < -thr:
        pitch = -90.0
        yaw = np.arctan2(yaw_y, yaw_x) * r2d
        roll = -yaw - (2.0 * np.arctan2(x, w) * r2d)
    elif sing > thr:
        pitch = 90.0
        yaw = np.arctan2(yaw_y, yaw_x) * r2d
        roll = yaw - (2.0 * np.arctan2(x, w) * r2d)
    else:
        pitch = np.arcsin(2.0 * sing) * r2d
        yaw = np.arctan2(yaw_y, yaw_x) * r2d
        roll = np.arctan2(-2.0 * (w * x + y * z), (1.0 - 2.0 * (x * x + y * y))) * r2d
    def norm(a):
        a = (a + 180.0) % 360.0 - 180.0
        return 0.0 if abs(a) < 1e-4 else float(a)
    return [norm(pitch), norm(yaw), norm(roll)]


def mapped(bone):
    """Sephiroth bone -> (CH049 bone, how) for the bones that map; None otherwise."""
    if bone == 'L_Weapon_a':
        return 'main_weapon', 'sword'
    if bone == 'Trans':
        return 'root', 'root'
    for c, s in RS.INV.items():
        if s == bone:
            return c, 'body'
    return None


def place(bone, loc, q):
    """A socket on Sephiroth's bone (local loc, local rotation q) -> (CH049 bone, local loc, local q)."""
    m = mapped(bone)
    if m is None:
        # the nearest ancestor that maps, with the socket's place relative to it at rest
        b = SE.index[bone]
        a = SE.parents[b]
        while a >= 0 and mapped(SE.names[a]) is None:
            a = SE.parents[a]
        assert a >= 0, bone
        gq_b, gt_b, gq_a, gt_a = SE.gq[b], SE.gt[b], SE.gq[a], SE.gt[a]
        comp_q = qmul(gq_b, q)
        comp_t = gt_b + qrot(gq_b, loc)
        rel_q = qmul(qinv(gq_a), comp_q)
        rel_t = qrot(qinv(gq_a), comp_t - gt_a)
        return place(SE.names[a], rel_t, rel_q)
    c, how = m
    s = SE.index[bone]
    if how == 'sword':
        # R_mw = R_LW . KC  ->  a socket at R_LW . Rs is at R_mw . KC^T . Rs
        kq = qinv(RS.KQ)
        return c, qrot(kq, loc), qnorm(qmul(kq, q))
    if how == 'root':
        # CH049's root rests at identity, Trans at its axis change: the socket's place in component space at rest
        g = SE.gq[s]
        return c, qrot(g, loc) * SCALE, qnorm(qmul(g, q))
    # a body bone: CH049's bone posed as the retarget poses it is D . MATCHED, Sephiroth's D . gq
    mq = RS.MATCHED[c]
    rel = qmul(qinv(mq), SE.gq[s])
    return c, qrot(rel, loc) * SCALE, qnorm(qmul(rel, q))


def main(probe, out):
    r = json.loads(json.load(open(probe))['result'])
    socks = []
    for name, bone, loc, rot, sc in r['seph_mesh_sockets']:
        q = rot_quat(*rot)
        c, l, qq = place(bone, np.array(loc, float), q)
        socks.append(dict(socket=name, seph_bone=bone, bone=c, location=[round(float(v), 4) for v in l],
                          rotation=[round(v, 4) for v in quat_rot(qq)], scale=sc))
    json.dump(socks, open(out, 'w'), indent=1)
    for s in socks:
        print('%-20s %-18s -> %-18s loc %-28s rot %s' % (s['socket'], s['seph_bone'], s['bone'], s['location'], s['rotation']))


if __name__ == '__main__':
    main(*sys.argv[1:3])
