"""Offline checks of make_safer_bonamik.py: Safer's skeleton, and the fields the game's own regular Bonamik carries.
    python3 check_safer_bnm.py [script]"""
import importlib.util, json, math, sys

SCRIPT = sys.argv[1] if len(sys.argv) > 1 else '/work/saferbnm/make_safer_bonamik.py'
SKEL = '/tmp/scratch/look365/safer_PC0010_999_Skeleton.json'
SEPH = '/tmp/scratch/seph_bnm3.json'
spec_ = importlib.util.spec_from_file_location('safer_bnm', SCRIPT)
M = importlib.util.module_from_spec(spec_); spec_.loader.exec_module(M)

fails = []
def check(ok, what):
    if not ok:
        fails.append(what)

skel = json.load(open(SKEL))
names = [b['name'] for b in skel]
parent = dict((b['name'], names[b['parent']] if b['parent'] is not None and b['parent'] >= 0 else None) for b in skel)
cs = dict((b['name'], b['cs']) for b in skel)
S = M.build_spec()

# 1. bones: every bone used exists, chains are parent/child, hair hangs on the head
for bone in M.bones_used():
    check(bone in parent, 'no bone ' + bone)
for _g, bones in M.HAIR_LOCKS + M.FEATHER_CHAINS:
    for a, b in zip(bones, bones[1:]):
        check(parent.get(b) == a, '%s is not under %s' % (b, a))
for _g, bones in M.HAIR_LOCKS:
    check(parent.get(bones[0]) == M.HAIR_PARENT, bones[0] + ' not on the head')
phy = sorted(n for n in names if n.endswith('_Phy'))
covered = set()
for _g, bones in M.HAIR_LOCKS + M.FEATHER_CHAINS:
    covered |= set(bones)
check(sorted(covered) == phy, 'physics bones not covered: %s; extra: %s' % (sorted(set(phy) - covered), sorted(covered - set(phy))))

# 2. the fields of the game's regular Bonamik data (Sephiroth's) are all set, and nothing else
seph = json.load(open(SEPH))
def fieldset(items):
    out = set()
    for it in items:
        out |= set(k for k in it if k != '__order__')
    return out
for key in ('mGroups', 'mBodies', 'mShapes'):
    want = fieldset(seph[key]); got = fieldset(S[key])
    check(want == got, '%s fields: missing %s, extra %s' % (key, sorted(want - got), sorted(got - want)))
want = fieldset(seph['mCones']); got = fieldset(S['mCones'])
check(want == got, 'mCones fields: missing %s, extra %s' % (sorted(want - got), sorted(got - want)))
want = fieldset(seph['mLinks']); got = fieldset(S['mLinks'])
check(want == got, 'mLinks fields: missing %s, extra %s' % (sorted(want - got), sorted(got - want)))
want = set(k for k in seph['mSceneManager'] if k != '__order__'); got = set(S['mSceneManager'])
check(want == got, 'scene fields: missing %s, extra %s' % (sorted(want - got), sorted(got - want)))
check(fieldset(seph['mGroups'][0]['mFpsCorrection']) == set(M.FPS_CORRECTION), 'fps correction fields')

# 3. the values copied are Sephiroth's
B = dict((b['mName'], b) for b in seph['mBodies'])
def same_body(mine, his, skip):
    for k in M.BODY_KEYS:
        if k in skip:
            continue
        a, b = mine[k], his[k]
        if isinstance(a, float) or isinstance(b, float):
            check(abs(a - b) < 1e-3, 'value %s: %r vs his %r' % (k, a, b))
        else:
            check(a == b, 'value %s: %r vs his %r' % (k, a, b))
same_body(M.HAIR_ROOT, B['Bdy_L_HairLongA_a_Phy_0_1'], ())
for k, c in enumerate('bcdefgh'):
    same_body(M.HAIR_SWING[k], B['Bdy_L_HairLongA_%s_Phy_0_1' % c], ())
same_body(M.FEATHER_ROOT, B['Bdy_Sta_L_CollarA_a_Phy_0_1'], ())
same_body(M.FEATHER_SWING, B['Bdy_Sta_L_CollarA_b_Phy_0_1'], ())
same_body(M.COLLIDER, B['Bdy_Sta_C_Spine_b_0_1'], ('m_Radius',))   # (each collider has its own radius)
hg = [g for g in seph['mGroups'] if g['m_GroupName'] == 'HairLA'][0]
for k, v in M.GROUP.items():
    if k == 'mFpsCorrection':
        continue
    check(abs(float(hg[k]) - float(v)) < 1e-4, 'group %s: %r vs his %r' % (k, v, hg[k]))
his_cones = [c for c in seph['mCones'] if c['mA'].startswith('Bdy_L_HairLongA_')]
for (ly, lz, inner), c in zip(M.HAIR_CONE_STEPS, his_cones):
    check((ly, lz) == (c['mLimitY'], c['mLimitZ']) and abs(inner - c['mInnerConeStr']) < 1e-4, 'hair cone steps')
for k in ('mOuterConeStr', 'mConeParentStr', 'mStretchedStrength', 'mCompressedStrength', 'mLinkParentStrength'):
    check(abs(M.HAIR_CONE[k] - his_cones[0][k]) < 1e-4, 'hair cone ' + k)

# 4. geometry: the skull sphere, the hair's first bodies clear of it, capsules sized
def dist(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))
head = cs['C_Head_a']
skull = [head[0], head[1] + M.SKULL_OFFSET[1], head[2] + M.SKULL_OFFSET[0]]   # head X is up, Y forward (from the skeleton)
for _g, bones in M.HAIR_LOCKS:
    d = dist(cs[bones[1]], skull)
    check(d > M.SKULL_RADIUS + M.HAIR_RADIUS, '%s starts inside the skull sphere (%.1f)' % (bones[1], d))
    print('  %-14s first swinging body %.0f from the skull middle (sphere %.0f + hair %.0f)' % (bones[1], d, M.SKULL_RADIUS, M.HAIR_RADIUS))
for g, a, b in M.CAPSULES:
    d = dist(cs[a], cs[b])
    print('  capsule %-8s %-13s %-13s length %5.1f radii %.0f/%.0f' % (g, a, b, d, M.COLLIDER_RADIUS[a], M.COLLIDER_RADIUS[b]))
    for _g, bones in M.HAIR_LOCKS:
        for bone in bones[1:]:
            # distance from the hair body to the capsule's segment
            p, q, x = cs[a], cs[b], cs[bone]
            pq = [q[i] - p[i] for i in range(3)]; px = [x[i] - p[i] for i in range(3)]
            L2 = sum(v * v for v in pq) or 1.0
            t = max(0.0, min(1.0, sum(pq[i] * px[i] for i in range(3)) / L2))
            c = [p[i] + t * pq[i] for i in range(3)]
            r = M.COLLIDER_RADIUS[a] + t * (M.COLLIDER_RADIUS[b] - M.COLLIDER_RADIUS[a])
            check(dist(c, x) > r + M.HAIR_RADIUS, '%s starts inside capsule %s-%s' % (bone, a, b))

print('bodies %d (swinging %d), cones %d, links %d, shapes %d, groups %d' % (
    len(S['mBodies']), sum(1 for b in S['mBodies'] if not b['m_IsKinematic']), len(S['mCones']), len(S['mLinks']),
    len(S['mShapes']), len(S['mGroups'])))
print('OK' if not fails else 'FAILS:\n  ' + '\n  '.join(fails))
sys.exit(1 if fails else 0)
