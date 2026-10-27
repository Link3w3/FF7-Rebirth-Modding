import sys, numpy as np, UnityPy
sys.path.insert(0, '/work/unityrip/scripts')
exec(open('/work/unityrip/scripts/inspect2.py').read().split("roots = ")[0])
binds = {}
for o in env.objects:
    if o.type.name == 'SkinnedMeshRenderer':
        r = o.read(); m = rd(r.m_Mesh)
        bp = [np.array([[getattr(b, 'e%d%d' % (i, j)) for j in range(4)] for i in range(4)]) for b in m.m_BindPose]
        for b, B in zip(r.m_Bones, bp):
            binds.setdefault(b.path_id, []).append((m.m_Name, np.linalg.inv(B)))
bad = []
for pid, lst in binds.items():
    Wh = world(pid)
    for mn, Wb in lst:
        e = np.abs(Wb - Wh).max()
        if e > 1e-4:
            bad.append((name_of(tr[pid]), mn, round(float(e), 4), np.round(Wb[:3, 3], 4).tolist(), np.round(Wh[:3, 3], 4).tolist()))
    if len(lst) > 1:
        e2 = max(np.abs(lst[0][1] - x[1]).max() for x in lst)
        if e2 > 1e-4:
            print('CONFLICT', name_of(tr[pid]), [x[0] for x in lst], e2)
print(len(binds), 'bound bones;', len(bad), 'differ from hierarchy')
for b in bad:
    print(b)
# full hierarchy names with depth
def walk(pid, d=0):
    t = tr[pid]
    print('  ' * d + name_of(t) + (' *' if pid in binds else ''))
    for c in t.m_Children:
        walk(c.path_id, d + 1)
if len(sys.argv) > 2:
    walk([p for p in tr if p not in parent][0])
