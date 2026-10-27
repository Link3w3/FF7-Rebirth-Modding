"""Transform math for FBX -> UE bone data (numpy-free core, quats as (x, y, z, w))."""
import math


def quat_from_euler_xyz_deg(rx, ry, rz):
    """FBX eEulerXYZ (the default): R = Rz * Ry * Rx applied to column vectors (X first)."""
    hx, hy, hz = math.radians(rx) / 2, math.radians(ry) / 2, math.radians(rz) / 2
    cx, sx, cy, sy, cz, sz = math.cos(hx), math.sin(hx), math.cos(hy), math.sin(hy), math.cos(hz), math.sin(hz)
    qx = (sx, 0.0, 0.0, cx)
    qy = (0.0, sy, 0.0, cy)
    qz = (0.0, 0.0, sz, cz)
    return qmul(qz, qmul(qy, qx))


def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz)


def qconj(q):
    return (-q[0], -q[1], -q[2], q[3])


def qrot(q, v):
    x, y, z = v
    p = qmul(qmul(q, (x, y, z, 0.0)), qconj(q))
    return (p[0], p[1], p[2])


def qnorm(q):
    n = math.sqrt(sum(c * c for c in q))
    return tuple(c / n for c in q)


def qangle(a, b):
    """angle between two rotations, degrees"""
    d = abs(sum(x * y for x, y in zip(a, b)))
    return math.degrees(2 * math.acos(min(1.0, d)))


def to_ue(t, q):
    """FBX (right-handed) local transform -> UE (left-handed): mirror Y."""
    return (t[0], -t[1], t[2]), (q[0], -q[1], q[2], -q[3])
