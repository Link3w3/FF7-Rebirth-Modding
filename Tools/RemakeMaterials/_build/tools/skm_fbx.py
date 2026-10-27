"""Remake cooked SkeletalMesh -> FBX 7.3 ASCII (one LOD), for the End editor's FBX import.
The file is declared Z-up / -Y front / right-handed, the axis system the editor's import converts to, so nothing is
converted; the import then mirrors y (left-handed UE), so everything goes out mirrored in y and comes back as it was:
positions and vectors (x, -y, z), rotations (-x, y, -z, w)."""
import sys, os, math, io, contextlib
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pkg418, uprops, skm

def qmat(x, y, z, w):
    n = math.sqrt(x * x + y * y + z * z + w * w) or 1.0
    x, y, z, w = x / n, y / n, z / n, w / n
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])

def euler_xyz(R):
    """R = Rz(c) Ry(b) Rx(a) -> (a, b, c) degrees (FBX eEulerXYZ)"""
    sb = -R[2, 0]
    sb = max(-1.0, min(1.0, sb))
    b = math.asin(sb)
    if abs(sb) < 0.999999:
        a = math.atan2(R[2, 1], R[2, 2]); c = math.atan2(R[1, 0], R[0, 0])
    else:
        a = math.atan2(-R[1, 2], R[1, 1]); c = 0.0
    return math.degrees(a), math.degrees(b), math.degrees(c)

def flat(a, nd=6):
    a = np.asarray(a, dtype=np.float64).ravel()
    return ','.join(('%.*g' % (nd, v)) for v in a.tolist())

def iflat(a):
    return ','.join(map(str, np.asarray(a).ravel().tolist()))

def fbx_matrix(M):
    """4x4 (column vectors, translation in the last column) -> FBX's 16 values (translation at 12..14)"""
    return flat(M.T.ravel(), 10)

def skeleton(ref, flat_root=True):
    """Each bone's local (translation, euler XYZ, scale) and global matrix. flat_root: the root rests with no turn and a
    scale of 1, as the game's skeletons rest theirs (Remake's Trans rests turned 120 degrees about (1,-1,1)); its children
    take its old rest into their own, so every bone and vertex stays exactly where it was."""
    bones, poses = ref['bones'], ref['poses']
    n = len(bones)
    local_trs, G = [], [None] * n
    for i, ((name, parent), (qx, qy, qz, qw, tx, ty, tz, sx, sy, sz)) in enumerate(zip(bones, poses)):
        R = qmat(-qx, qy, -qz, qw)
        L = np.eye(4); L[:3, :3] = R * np.array([sx, sy, sz])[None, :]; L[:3, 3] = (tx, -ty, tz)
        G[i] = L if parent < 0 else G[parent] @ L
        if parent >= i: raise ValueError('bone %d parent %d after it' % (i, parent))
        local_trs.append(((tx, -ty, tz), euler_xyz(R), (sx, sy, sz)))
    if flat_root and n and bones[0][1] < 0:
        root = np.eye(4); root[:3, 3] = G[0][:3, 3]
        inv_root = np.linalg.inv(root)
        for i, (name, parent) in enumerate(bones):
            if parent != 0:
                continue
            L = inv_root @ G[i]
            scale = np.linalg.norm(L[:3, :3], axis=0)
            R = L[:3, :3] / np.where(scale > 1e-12, scale, 1.0)[None, :]
            local_trs[i] = (tuple(L[:3, 3].tolist()), euler_xyz(R), tuple(scale.tolist()))
        local_trs[0] = (tuple(G[0][:3, 3].tolist()), (0.0, 0.0, 0.0), (1.0, 1.0, 1.0))
        G[0] = root
    return local_trs, G

def lod_arrays(M, k=0):
    L = M['lods'][k]
    vb = L['vertices']
    stride, nv, nuv = vb['stride'], vb['count'], vb['num_texcoords']
    raw = np.frombuffer(vb['data'], np.uint8).reshape(nv, stride)
    tx = raw[:, 0:4].astype(np.float64) / 127.5 - 1.0
    tz = raw[:, 4:8].astype(np.float64) / 127.5 - 1.0
    pos = raw[:, 8:20].copy().view(np.float32).reshape(nv, 3).astype(np.float64)
    if vb['full_uvs']:
        uv = raw[:, 20:20 + 8 * nuv].copy().view(np.float32).reshape(nv, nuv, 2).astype(np.float64)
    else:
        uv = raw[:, 20:20 + 4 * nuv].copy().view(np.float16).reshape(nv, nuv, 2).astype(np.float64)
    nrm = tz[:, :3]; nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-8)
    tan = tx[:, :3]; tan /= np.maximum(np.linalg.norm(tan, axis=1, keepdims=True), 1e-8)
    sign = np.where(raw[:, 7] >= 128, 1.0, -1.0)
    bin_ = np.cross(nrm, tan) * sign[:, None]
    sw = L['weights']
    nw = sw['stride'] // 2
    wraw = np.frombuffer(sw['data'], np.uint8).reshape(nv, sw['stride'])
    widx, wval = wraw[:, :nw].astype(np.int64), wraw[:, nw:].astype(np.float64) / 255.0
    gidx = np.zeros_like(widx)
    sec_of_vertex = np.zeros(nv, np.int64)
    for si, s in enumerate(L['sections']):
        a, b = s['base_vertex'], s['base_vertex'] + s['num_vertices']
        bm = np.array(s['bone_map'], np.int64)
        gidx[a:b] = bm[np.minimum(widx[a:b], len(bm) - 1)]
        sec_of_vertex[a:b] = si
    isz = L['indices']['size']
    idx = np.frombuffer(L['indices']['data'], np.uint32 if isz == 4 else np.uint16).astype(np.int64).reshape(-1, 3)
    tri_mat = np.zeros(len(idx), np.int64)
    for s in L['sections']:
        t0 = s['base_index'] // 3
        tri_mat[t0:t0 + s['num_triangles']] = s['material']
    return dict(pos=pos, nrm=nrm, tan=tan, bin=bin_, uv=uv, gidx=gidx, wval=wval, tris=idx, tri_mat=tri_mat, sections=L['sections'])

def mirror(v):
    v = np.array(v, dtype=np.float64, copy=True); v[:, 1] *= -1; return v

def write(M, pkg, name, out_path, lod=0):
    names = [b[0] for b in M['ref']['bones']]
    parents = [b[1] for b in M['ref']['bones']]
    local_trs, G = skeleton(M['ref'])
    A = lod_arrays(M, lod)
    slots = [m_['slot'] for m_ in M['materials']]
    nv = len(A['pos'])
    ids = iter(range(1000000000, 2000000000))
    geo, mesh_model, skin = next(ids), next(ids), next(ids)
    bone_model = [next(ids) for _ in names]
    bone_attr = [next(ids) for _ in names]
    mat_ids = [next(ids) for _ in slots]
    pose = next(ids)
    # skin clusters
    clusters = {}
    for j in range(A['gidx'].shape[1]):
        w = A['wval'][:, j]; b = A['gidx'][:, j]
        keep = w > 0
        for v, bb, ww in zip(np.nonzero(keep)[0].tolist(), b[keep].tolist(), w[keep].tolist()):
            clusters.setdefault(bb, ([], []))
            clusters[bb][0].append(v); clusters[bb][1].append(ww)
    cl_ids = {bb: next(ids) for bb in sorted(clusters)}
    pvi = A['tris'].copy(); pvi[:, 2] = -pvi[:, 2] - 1
    out = io.StringIO(); w = out.write
    w('; FBX 7.3.0 project file\n; written by skm_fbx.py from FINAL FANTASY VII REMAKE cooked skeletal mesh %s\n\n' % name)
    w('''FBXHeaderExtension:  {
	FBXHeaderVersion: 1003
	FBXVersion: 7300
	Creator: "skm_fbx"
}
GlobalSettings:  {
	Version: 1000
	Properties70:  {
		P: "UpAxis", "int", "Integer", "",2
		P: "UpAxisSign", "int", "Integer", "",1
		P: "FrontAxis", "int", "Integer", "",1
		P: "FrontAxisSign", "int", "Integer", "",-1
		P: "CoordAxis", "int", "Integer", "",0
		P: "CoordAxisSign", "int", "Integer", "",1
		P: "OriginalUpAxis", "int", "Integer", "",2
		P: "OriginalUpAxisSign", "int", "Integer", "",1
		P: "UnitScaleFactor", "double", "Number", "",1
		P: "OriginalUnitScaleFactor", "double", "Number", "",1
	}
}
Documents:  {
	Count: 1
	Document: 999999999, "", "Scene" {
		Properties70:  {
			P: "SourceObject", "object", "", ""
			P: "ActiveAnimStackName", "KString", "", "", ""
		}
		RootNode: 0
	}
}
References:  {
}
''')
    nmodels = 1 + len(names)
    w('''Definitions:  {
	Version: 100
	Count: %d
	ObjectType: "GlobalSettings" {
		Count: 1
	}
	ObjectType: "Model" {
		Count: %d
	}
	ObjectType: "NodeAttribute" {
		Count: %d
	}
	ObjectType: "Geometry" {
		Count: 1
	}
	ObjectType: "Material" {
		Count: %d
	}
	ObjectType: "Deformer" {
		Count: %d
	}
	ObjectType: "Pose" {
		Count: 1
	}
}
Objects:  {
''' % (1 + nmodels + len(names) + 1 + len(slots) + 1 + len(cl_ids) + 1, nmodels, len(names), len(slots), 1 + len(cl_ids)))
    # geometry
    # (the editor's import reads the binormal as -TangentY, as its FBX export writes it)
    P = mirror(A['pos']); N = mirror(A['nrm']); T = mirror(A['tan']); Bn = -mirror(A['bin'])
    w('\tGeometry: %d, "Geometry::%s", "Mesh" {\n' % (geo, name))
    w('\t\tVertices: *%d {\n\t\t\ta: %s\n\t\t}\n' % (P.size, flat(P)))
    w('\t\tPolygonVertexIndex: *%d {\n\t\t\ta: %s\n\t\t}\n' % (pvi.size, iflat(pvi)))
    w('\t\tGeometryVersion: 124\n')
    for tag, arrname, data in (('LayerElementNormal', 'Normals', N), ('LayerElementTangent', 'Tangents', T), ('LayerElementBinormal', 'Binormals', Bn)):
        # (FBX spells per-control-point mapping "ByVertice"; an unknown word is read as no mapping at all)
        w('\t\t%s: 0 {\n\t\t\tVersion: 101\n\t\t\tName: ""\n\t\t\tMappingInformationType: "ByVertice"\n\t\t\tReferenceInformationType: "Direct"\n' % tag)
        w('\t\t\t%s: *%d {\n\t\t\t\ta: %s\n\t\t\t}\n\t\t}\n' % (arrname, data.size, flat(data, 7)))
    for c in range(A['uv'].shape[1]):
        uv = A['uv'][:, c, :].copy(); uv[:, 1] = 1.0 - uv[:, 1]
        # (per polygon vertex through an index, as the editor's own FBX export writes UVs)
        w('\t\tLayerElementUV: %d {\n\t\t\tVersion: 101\n\t\t\tName: "UVChannel_%d"\n\t\t\tMappingInformationType: "ByPolygonVertex"\n\t\t\tReferenceInformationType: "IndexToDirect"\n' % (c, c + 1))
        w('\t\t\tUV: *%d {\n\t\t\t\ta: %s\n\t\t\t}\n' % (uv.size, flat(uv, 7)))
        w('\t\t\tUVIndex: *%d {\n\t\t\t\ta: %s\n\t\t\t}\n\t\t}\n' % (A['tris'].size, iflat(A['tris'])))
    w('\t\tLayerElementMaterial: 0 {\n\t\t\tVersion: 101\n\t\t\tName: ""\n\t\t\tMappingInformationType: "ByPolygon"\n\t\t\tReferenceInformationType: "IndexToDirect"\n')
    w('\t\t\tMaterials: *%d {\n\t\t\t\ta: %s\n\t\t\t}\n\t\t}\n' % (len(A['tri_mat']), iflat(A['tri_mat'])))
    w('\t\tLayer: 0 {\n\t\t\tVersion: 100\n')
    for t in ('LayerElementNormal', 'LayerElementTangent', 'LayerElementBinormal', 'LayerElementMaterial', 'LayerElementUV'):
        w('\t\t\tLayerElement:  {\n\t\t\t\tType: "%s"\n\t\t\t\tTypedIndex: 0\n\t\t\t}\n' % t)
    w('\t\t}\n')
    for c in range(1, A['uv'].shape[1]):
        w('\t\tLayer: %d {\n\t\t\tVersion: 100\n\t\t\tLayerElement:  {\n\t\t\t\tType: "LayerElementUV"\n\t\t\t\tTypedIndex: %d\n\t\t\t}\n\t\t}\n' % (c, c))
    w('\t}\n')
    # mesh model
    w('\tModel: %d, "Model::%s", "Mesh" {\n\t\tVersion: 232\n\t\tProperties70:  {\n\t\t\tP: "DefaultAttributeIndex", "int", "Integer", "",0\n\t\t}\n\t\tShading: T\n\t\tCulling: "CullingOff"\n\t}\n' % (mesh_model, name))
    # bones
    for i, nm in enumerate(names):
        (t, r, s) = local_trs[i]
        w('\tNodeAttribute: %d, "NodeAttribute::%s", "LimbNode" {\n\t\tTypeFlags: "Skeleton"\n\t}\n' % (bone_attr[i], nm))
        w('\tModel: %d, "Model::%s", "LimbNode" {\n\t\tVersion: 232\n\t\tProperties70:  {\n' % (bone_model[i], nm))
        w('\t\t\tP: "Lcl Translation", "Lcl Translation", "", "A",%s\n' % flat(t, 9))
        w('\t\t\tP: "Lcl Rotation", "Lcl Rotation", "", "A",%s\n' % flat(r, 9))
        w('\t\t\tP: "Lcl Scaling", "Lcl Scaling", "", "A",%s\n' % flat(s, 9))
        w('\t\t\tP: "DefaultAttributeIndex", "int", "Integer", "",0\n\t\t}\n\t\tShading: Y\n\t\tCulling: "CullingOff"\n\t}\n')
    # materials
    for mid, sname in zip(mat_ids, slots):
        w('\tMaterial: %d, "Material::%s", "" {\n\t\tVersion: 102\n\t\tShadingModel: "phong"\n\t\tMultiLayer: 0\n\t\tProperties70:  {\n\t\t\tP: "DiffuseColor", "Color", "", "A",0.8,0.8,0.8\n\t\t}\n\t}\n' % (mid, sname))
    # skin
    w('\tDeformer: %d, "Deformer::%s", "Skin" {\n\t\tVersion: 101\n\t\tLink_DeformAcuracy: 50\n\t}\n' % (skin, name))
    I4 = np.eye(4)
    for bb, cid in cl_ids.items():
        vs, ws = clusters[bb]
        w('\tDeformer: %d, "SubDeformer::%s", "Cluster" {\n\t\tVersion: 100\n\t\tUserData: "", ""\n' % (cid, names[bb]))
        w('\t\tIndexes: *%d {\n\t\t\ta: %s\n\t\t}\n' % (len(vs), iflat(vs)))
        w('\t\tWeights: *%d {\n\t\t\ta: %s\n\t\t}\n' % (len(ws), flat(ws, 7)))
        w('\t\tTransform: *16 {\n\t\t\ta: %s\n\t\t}\n' % fbx_matrix(I4))
        w('\t\tTransformLink: *16 {\n\t\t\ta: %s\n\t\t}\n\t}\n' % fbx_matrix(G[bb]))
    # bind pose
    w('\tPose: %d, "Pose::BIND_POSES", "BindPose" {\n\t\tType: "BindPose"\n\t\tVersion: 100\n\t\tNbPoseNodes: %d\n' % (pose, 1 + len(names)))
    w('\t\tPoseNode:  {\n\t\t\tNode: %d\n\t\t\tMatrix: *16 {\n\t\t\t\ta: %s\n\t\t\t}\n\t\t}\n' % (mesh_model, fbx_matrix(I4)))
    for i in range(len(names)):
        w('\t\tPoseNode:  {\n\t\t\tNode: %d\n\t\t\tMatrix: *16 {\n\t\t\t\ta: %s\n\t\t\t}\n\t\t}\n' % (bone_model[i], fbx_matrix(G[i])))
    w('\t}\n}\n')
    # connections
    w('Connections:  {\n')
    w('\tC: "OO",%d,0\n' % mesh_model)
    w('\tC: "OO",%d,%d\n' % (geo, mesh_model))
    for mid in mat_ids:
        w('\tC: "OO",%d,%d\n' % (mid, mesh_model))
    for i, par in enumerate(parents):
        w('\tC: "OO",%d,%d\n' % (bone_attr[i], bone_model[i]))
        w('\tC: "OO",%d,%d\n' % (bone_model[i], 0 if par < 0 else bone_model[par]))
    w('\tC: "OO",%d,%d\n' % (skin, geo))
    for bb, cid in cl_ids.items():
        w('\tC: "OO",%d,%d\n' % (cid, skin))
        w('\tC: "OO",%d,%d\n' % (bone_model[bb], cid))
    w('}\n')
    open(out_path, 'w', newline='\n').write(out.getvalue())
    return dict(vertices=nv, triangles=len(A['tris']), bones=len(names), clusters=len(cl_ids), slots=slots,
                max_influences=int((A['wval'] > 0).sum(1).max()))

if __name__ == '__main__':
    from schema import Schema
    S = Schema()
    src, out_path = sys.argv[1], sys.argv[2]
    p = pkg418.Package(src)
    cls, v, end = uprops.read_export(S, p, 0)
    with contextlib.redirect_stdout(io.StringIO()):
        M, r = skm.read(p, 0, end)
    info = write(M, p, os.path.basename(src)[:-7], out_path)
    print(info, os.path.getsize(out_path))
