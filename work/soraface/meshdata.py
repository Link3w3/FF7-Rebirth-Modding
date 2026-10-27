"""Sora's skinned mesh from the editor's FBX export, in UE component space (FBX y = -UE y)."""
import numpy as np
import fbxbin


def load(path='sora_mesh.fbx'):
    root, ver = fbxbin.read(path)
    objs = root.find('Objects')
    by_id = {k.props[0]: k for k in objs.kids}
    conn = [(c.props[1], c.props[2]) for c in root.find('Connections').kids if c.props[0] == 'OO']
    parents = {}
    children = {}
    for ch, pa in conn:
        parents.setdefault(ch, []).append(pa)
        children.setdefault(pa, []).append(ch)
    geo = next(k for k in objs.kids if k.name == 'Geometry')
    V = geo.find('Vertices').props[0].reshape(-1, 3).astype(np.float64)
    V[:, 1] *= -1.0
    pvi = geo.find('PolygonVertexIndex').props[0]
    # polygons (all triangles from UE's exporter)
    ends = np.nonzero(pvi < 0)[0]
    idx = pvi.copy(); idx[ends] = -idx[ends] - 1
    starts = np.concatenate([[0], ends[:-1] + 1])
    assert np.all(ends - starts == 2), 'not all triangles'
    T = np.stack([idx[starts], idx[starts + 1], idx[starts + 2]], 1)
    T = T[:, ::-1].copy()     # the y flip mirrors: keep the winding outward
    lm = geo.find('LayerElementMaterial')
    mats = lm.find('Materials').props[0]
    if len(mats) == 1:
        mats = np.repeat(mats, len(T))
    # material names in the order the mesh model links them
    mesh_model = next(p for p in parents[geo.props[0]] if by_id.get(p) is not None and by_id[p].name == 'Model')
    mat_ids = [c for c in children.get(mesh_model, []) if by_id.get(c) is not None and by_id[c].name == 'Material']
    mat_names = [by_id[m].props[1].split('\x00')[0] for m in mat_ids]
    # skin weights
    nv = len(V)
    W = {}
    skin = next(k for k in objs.kids if k.name == 'Deformer' and k.props[2] == 'Skin')
    for cid in children.get(skin.props[0], []):
        cl = by_id[cid]
        if cl.name != 'Deformer':
            continue
        bones = [by_id[c] for c in children.get(cid, []) if by_id.get(c) is not None and by_id[c].name == 'Model']
        if not bones or cl.find('Indexes') is None:
            continue
        bname = bones[0].props[1].split('\x00')[0]
        W[bname] = (cl.find('Indexes').props[0].astype(np.int64), cl.find('Weights').props[0].astype(np.float64))
    return dict(V=V, T=T, mat=mats, mat_names=mat_names, W=W)


if __name__ == '__main__':
    m = load()
    print(len(m['V']), len(m['T']), m['mat_names'], np.bincount(m['mat']))
    print(len(m['W']), sorted(m['W'], key=lambda b: -len(m['W'][b][0]))[:20])
    tot = np.zeros(len(m['V']))
    for b, (i, w) in m['W'].items():
        np.add.at(tot, i, w)
    print('weight sums', tot.min(), tot.max())
    print('bbox', m['V'].min(0), m['V'].max(0))
