"""Along the left thigh (tenths from the hip joint): the leg mesh's farthest reach from the thigh's axis toward its
front, side (out) and back (cm, the height map clip_check uses), the node's thigh capsule radius there, and how far
the front coat panels' bones (L_SkirtA, C_SkirtA, L_SkirtB) and cloth sit from the axis in the reference pose.
    leg_profile_cmp.py body.npz rig.json entry.json"""
import json, re, sys, math
import numpy as np
exec(open('/work/kawaii_preset/tests/clip_check.py').read().split("maps = {(s, p)")[0].replace('body_path, rig_path, frames_path = sys.argv[1:4]', 'body_path, rig_path, entry_path = sys.argv[1:4]; frames_path = None'))
entry = json.load(open(entry_path))['kawaii'][0]
bi, length, ax, e1, e2, m = height_map('L', 'thigh')
bq = refq[bi]; bt = reft[bi]
def side_dir(v):
    d = qrot(qinv(bq), np.array(v, float)); d -= (d @ ax) * ax; return d / np.linalg.norm(d)
dirs = {'front': side_dir([1, 0, 0]), 'out': side_dir([0, -1, 0]), 'back': side_dir([-1, 0, 0]), 'in': side_dir([0, 1, 0])}
def reach(t, d):
    a = math.atan2(d @ e2, d @ e1); ai = int((a + math.pi) / (2 * math.pi) * m.shape[1]) % m.shape[1]
    return m[min(m.shape[0] - 1, int(t * m.shape[0])), ai]
node = [n for n in entry['nodes'] if n['root_bone'] == 'L_SkirtA_a_Phy'][0]
cap = [c for c in node['tapered_capsules'] if c['bone'] == 'L_UpperLeg_a'][0]
# the capsule along the bone's axis: its centre offset, half length, radius1 at its -Z end (toward the hip)
off = np.array(cap['offset']); half = cap['length'] / 2
def from_rotator(p, y, r):
    h = math.pi / 360.0; sp, cp, sy, cy, sr, cr = math.sin(p*h), math.cos(p*h), math.sin(y*h), math.cos(y*h), math.sin(r*h), math.cos(r*h)
    return np.array([cr*sp*sy - sr*cp*cy, -cr*sp*cy - sr*cp*sy, cr*cp*sy - sr*sp*cy, cr*cp*cy + sr*sp*sy])
cax = qrot(from_rotator(*cap['rotation']), np.array([0, 0, 1.0]))
print('thigh %.1f cm; capsule from %.1f to %.1f cm along it, radius %.1f -> %.1f (tapered)' % (length, (off @ ax) - half, (off @ ax) + half, cap['radius1'], cap['radius0']))
def cap_r(s):   # the capsule's surface distance from the thigh axis at s cm along the thigh (round ends included)
    u = s - (off @ ax); 
    if abs(u) <= half:
        return cap['radius1'] + (cap['radius0'] - cap['radius1']) * (u + half) / (2 * half)
    rr = cap['radius1'] if u < 0 else cap['radius0']; e = abs(u) - half
    return math.sqrt(max(0.0, rr * rr - e * e))
chains = {}
for root in ('L_SkirtA', 'C_SkirtA', 'L_SkirtB'):
    pts = [reft[index[n]] for n in names if re.match(r'^%s_[a-h]_Phy$' % root, n)]
    chains[root] = pts
print(' tenth | leg reach front / out / back / in | capsule | front panels: bone distance from the thigh axis at this height (L_SkirtA, C_SkirtA, L_SkirtB)')
for k in range(10):
    t = (k + 0.5) / 10; s = t * length
    p = bt + qrot(bq, ax * s)   # the axis point in component space
    row = ['%.1f' % reach(t, dirs[d]) for d in ('front', 'out', 'back', 'in')]
    cd = []
    for root, pts in chains.items():
        # the chain's polyline point at the height of p (component Z), its distance from the axis line
        best = None
        for a, b in zip(pts, pts[1:]):
            if (a[2] - p[2]) * (b[2] - p[2]) <= 0 and abs(a[2] - b[2]) > 1e-6:
                w = (p[2] - a[2]) / (b[2] - a[2]); q = a + (b - a) * w
                L = qrot(qinv(bq), q - bt); rad = L - (L @ ax) * ax
                best = np.linalg.norm(rad)
        cd.append('%.1f' % best if best is not None else '-')
    print('  %d/10 | %s | %.1f | %s' % (k, ' / '.join(row), cap_r(s), ', '.join(cd)))
