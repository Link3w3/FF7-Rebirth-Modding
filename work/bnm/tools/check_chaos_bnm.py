"""Offline checks of make_chaos_vincent_wing_bonamik.py against Sephiroth's PC0010_10_BNM and Chaos's skeleton."""
import importlib.util, json, sys
import numpy as np
sys.path.insert(0, '/work/bnm/tools')
from load import load

SCRIPT = sys.argv[1] if len(sys.argv) > 1 else '/work/bnm/ChaosVincentBonamik/make_chaos_vincent_wing_bonamik.py'
spec_ = importlib.util.spec_from_file_location('chaos_bnm', SCRIPT)
M = importlib.util.module_from_spec(spec_); spec_.loader.exec_module(M)

fails = []
def check(ok, what):
    if not ok: fails.append(what)

# --- Sephiroth's data in the script's representation
L, objs = load('PC0010_10_Sephiroth_Transform/Model/PC0010_10_BNM')
S = objs[1]
ENUMS = {e.entry: e for e in (M.SPHERE, M.CAPSULE, M.NO_CONSTRAINT, M.LATERAL, M.PARENT_CHILD, M.BENDING, M.LOCAL_FORCE)}
def conv(d):
    """A parsed tagged struct in the script's representation; enum entries the script does not name get value -1."""
    out = {}
    for k, v in d.items():
        if k == '__order__' or '[' in k: continue
        if k == 'm_ColId':
            v = [d['m_ColId']] + [d['m_ColId[%d]' % i] for i in range(1, 8)]
        elif k in ('m_Gravity', 'm_LocalTransform', 'm_LocalScale'):
            v = M.Vec(v)
        elif k == 'm_LocalRotation':
            v = M.Quat(v)
        elif isinstance(v, str) and v.startswith('ESQEX_'):
            v = ENUMS.get(v) or M.Enum(v.split('_v2_')[0] + '_v2', -1, v)
        out[k] = v
    return out
SB = [conv(b) for b in S['m_Bodies']]
SL = [conv(l) for l in S['m_Links']]

# 1. the totals formulas reproduce Sephiroth's stored counts
tot, scene = M.compute_totals(SB, SL)
for k, v in tot.items():
    if k in ('m_TotalCollisions',): continue
    check(S.get(k, 0) == v, 'formula %s: %s vs stored %s' % (k, v, S.get(k, 0)))
sm = S['m_SceneManager']
arr = lambda name: [sm.get(name if i == 0 else '%s[%d]' % (name, i), 0) for i in range(15)]
check(scene['m_TotalLinksInBatch'] == arr('m_TotalLinksInBatch'), 'formula links per batch')
check(scene['m_TotalLinkBatches'] == sm['m_TotalLinkBatches'], 'formula link batches')
check(scene['m_TotalConesInBatch'] == arr('m_TotalConesInBatch'), 'formula cones per batch')
check(scene['m_TotalConeBatches'] == sm['m_TotalConeBatches'], 'formula cone batches')
check(len(S['m_Solvers']) == sm['m_TotalGroup'], 'formula total group')
print('formulas vs PC0010_10_BNM:', 'OK' if not fails else fails)

# 2. our asset
V = M.build_spec()
B, K = V['m_Bodies'], V['m_Links']
f32 = lambda x: np.float32(x)
def eq(a, b):
    if isinstance(a, M.Enum) or isinstance(b, M.Enum): return a.entry == b.entry
    if isinstance(a, (list, tuple)): return len(a) == len(b) and all(eq(x, y) for x, y in zip(a, b))
    if isinstance(a, float) or isinstance(b, float): return f32(a) == f32(b) and np.signbit(f32(a)) == np.signbit(f32(b))
    return a == b
wing = [b for b in SB if b['m_GroupId'] == 1]
seph_root = next(b for b in wing if b['m_IsKinematic']); seph_swing = next(b for b in wing if not b['m_IsKinematic'])
seph_link = SL[0]
OWN_B = {'m_Index', 'm_JointName', 'm_ParentBodyName', 'm_ChildBodyName', 'm_ParentId', 'm_ChildId', 'm_GroupId', 'm_ColId', 'm_CollisionBatchNo'}
OWN_L = {'m_ParentBodyName', 'm_ChildBodyName', 'm_ParentId', 'm_ChildId', 'm_ConeInnerStr', 'm_ConeBatchNo', 'm_LimitY', 'm_LimitZ'}
for b in B:
    t = seph_root if b['m_IsKinematic'] else seph_swing
    check(set(b) == set(t), 'body fields differ from Sephiroth: %s' % (set(b) ^ set(t)))
    for k in t:
        if k not in OWN_B: check(eq(b[k], t[k]), 'body %s %s: %r vs Sephiroth %r' % (b['m_JointName'], k, b[k], t[k]))
for l in K:
    check(set(l) == set(seph_link), 'link fields differ: %s' % (set(l) ^ set(seph_link)))
    for k in seph_link:
        if k not in OWN_L: check(eq(l[k], seph_link[k]), 'link %s-%s %s: %r vs %r' % (l['m_ParentBodyName'], l['m_ChildBodyName'], k, l[k], seph_link[k]))
seph_solvers = [conv(s) for s in S['m_Solvers'][:2]]
for ours, theirs in zip(V['m_Solvers'], seph_solvers):
    check(set(ours) == set(theirs), 'solver fields differ')
    for k in theirs: check(eq(ours[k], theirs[k]), 'solver %s %s' % (theirs['m_GroupName'], k))
ssm = conv(sm)
for k in ('m_IsEnable', 'm_SubStep', 'm_LSScoeff_tran', 'm_LSScoeff_rot', 'm_RootName', 'm_Gravity', 'm_FastMotionHandlingMode', 'm_EnableGroundCollision'):
    check(eq(V['m_SceneManager'][k], ssm[k]), 'scene %s' % k)
inner = sorted({round(float(f32(l['m_ConeInnerStr'])), 6) for l in K})
seph_inner = sorted({round(float(f32(l['m_ConeInnerStr'])), 6) for l in SL if l['m_LinkType'].entry.endswith('ParentChild')})
check(set(inner) <= set(seph_inner), 'cone inner strengths %s not among Sephiroth\'s %s' % (inner, seph_inner))

# 3. bones
chaos = json.load(open('/work/bnm/chaos_bones.json'))['bones']
names = [b[0] for b in chaos]; parent = {b[0]: (names[b[1]] if b[1] >= 0 else None) for b in chaos}
kids = {}
for n in names: kids.setdefault(parent[n], []).append(n)
for b in B: check(b['m_JointName'] in parent, 'bone %s missing in PC0011_10_Skeleton' % b['m_JointName'])
for chain in M.CHAINS:
    for a, c in zip(chain, chain[1:]): check(parent[c] == a, '%s is not under %s' % (c, a))
    check(kids.get(chain[0]) == [chain[1]], 'root %s has children %s' % (chain[0], kids.get(chain[0])))
check(all(n in names for n in M.WING_BONES), 'numbered bones missing')
attach = [l.strip() for l in open('/tmp/scratch', encoding='utf-8', errors='replace') if l.strip()]
numbered = [n for n in attach if n and all(ch in '0123456789ABCDEF' for ch in n)]
check(numbered == M.WING_BONES, 'numbered bones in the attachment: %s' % numbered)
check(all(b['m_JointName'] in numbered for b in B), 'a body is not on a numbered bone')

# 4. summary
print('bodies %d (roots %d), links %d' % (len(B), sum(b['m_IsKinematic'] for b in B), len(K)))
print('totals', {k: v for k, v in V.items() if k.startswith('m_Total')})
sc = V['m_SceneManager']
print('scene', {k: sc[k] for k in ('m_TotalGroup', 'm_TotalLinkBatches', 'm_TotalConeBatches', 'm_TotalCollisionBatches')}, 'cones/batch', sc['m_TotalConesInBatch'][:3])
for chain in M.CHAINS:
    ls = [l for l in K if l['m_ParentBodyName'] in chain]
    print('  chain %-14s inner %s batches %s' % ('-'.join(chain), [round(float(f32(l['m_ConeInnerStr'])), 3) for l in ls], [l['m_ConeBatchNo'] for l in ls]))
print('FAILS:' if fails else 'ALL CHECKS PASSED', fails[:20])
sys.exit(1 if fails else 0)
