import sys, numpy as np, UnityPy
env = UnityPy.load(sys.argv[1])
objs = {o.path_id: o for o in env.objects}
def rd(pptr):
    return pptr.deref_parse_as_object() if hasattr(pptr, 'deref_parse_as_object') else pptr.read()
tr = {}
for o in env.objects:
    if o.type.name == 'Transform':
        t = o.read(); tr[o.path_id] = t
def name_of(t):
    return rd(t.m_GameObject).m_Name
def local(t):
    p = t.m_LocalPosition; q = t.m_LocalRotation; s = t.m_LocalScale
    x, y, z, w = q.x, q.y, q.z, q.w
    R = np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                  [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                  [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])
    M = np.eye(4); M[:3, :3] = R * np.array([s.x, s.y, s.z]); M[:3, 3] = [p.x, p.y, p.z]
    return M
parent = {}
for pid, t in tr.items():
    for c in t.m_Children:
        parent[c.path_id] = pid
def world(pid):
    M = local(tr[pid])
    while pid in parent:
        pid = parent[pid]; M = local(tr[pid]) @ M
    return M
roots = [pid for pid in tr if pid not in parent]
print('roots', [name_of(tr[r]) for r in roots])
for o in env.objects:
    if o.type.name == 'SkinnedMeshRenderer':
        r = o.read()
        m = rd(r.m_Mesh)
        go = rd(r.m_GameObject)
        bones = [b.path_id for b in r.m_Bones]
        mats = [rd(x).m_Name for x in r.m_Materials]
        bp = [np.array([[getattr(b, 'e%d%d' % (i, j)) for j in range(4)] for i in range(4)]) for b in m.m_BindPose]
        rt = r.m_RootBone.path_id
        mesh_t = [pid for pid, t in tr.items() if rd(t.m_GameObject).m_Name == go.m_Name][0]
        Wm = world(mesh_t)
        err = 0
        for b, B in zip(bones, bp):
            # bindpose = bone.worldToLocal * mesh.localToWorld  -> bone world = mesh world * inv(bindpose)
            Wb = Wm @ np.linalg.inv(B)
            err = max(err, np.abs(Wb - world(b)).max())
        print(go.m_Name, m.m_Name, 'bones', len(bones), 'root', name_of(tr[rt]) if rt in tr else rt, 'mats', mats,
              'mesh world identity?', np.allclose(Wm, np.eye(4), atol=1e-5), 'max bind vs hierarchy err %.2e' % err,
              'shapes', len(m.m_Shapes.channels) if m.m_Shapes else 0, 'submeshes', len(m.m_SubMeshes))
