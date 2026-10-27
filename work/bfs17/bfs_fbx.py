"""The re-rigged Bahamut Fused Sephiroth (bfs_rerig.py npz) -> FBX 7.3 ASCII for the End editor's import (from ccfbx.py:
normals only, the import making MikkTSpace tangents; the UVs as the editor's own export wrote them), written the way the Remake
importer's skm_fbx.py writes (Z-up / -Y front / right-handed declared, everything mirrored in y so the import's own mirror
brings it back exactly; normals, tangents and binormals per control point; UVs per polygon vertex).
    ccfbx.py <rerig.npz> <out.fbx> <mesh name>"""
import sys, io, math
import numpy as np

def qmat(x, y, z, w):
    n = math.sqrt(x * x + y * y + z * z + w * w) or 1.0
    x, y, z, w = x / n, y / n, z / n, w / n
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])

def euler_xyz(R):
    sb = max(-1.0, min(1.0, -R[2, 0])); b = math.asin(sb)
    if abs(sb) < 0.999999:
        a = math.atan2(R[2, 1], R[2, 2]); c = math.atan2(R[1, 0], R[0, 0])
    else:
        a = math.atan2(-R[1, 2], R[1, 1]); c = 0.0
    return math.degrees(a), math.degrees(b), math.degrees(c)

def flat(a, nd=6):
    return ','.join(('%.*g' % (nd, v)) for v in np.asarray(a, dtype=np.float64).ravel().tolist())

def iflat(a):
    return ','.join(map(str, np.asarray(a).ravel().tolist()))

def fbx_matrix(M):
    return flat(M.T.ravel(), 15)

def mirror(v):
    v = np.array(v, dtype=np.float64, copy=True); v[:, 1] *= -1; return v

def write(m, out_path, name):
    names = [str(n) for n in m['bone_names']]; parents = [int(p) for p in m['bone_parents']]
    local_trs, G = [], [None] * len(names)
    for i, (q, t) in enumerate(zip(m['bone_lq'], m['bone_lt'])):
        qx, qy, qz, qw = q; tx, ty, tz = t
        R = qmat(-qx, qy, -qz, qw)
        L = np.eye(4); L[:3, :3] = R; L[:3, 3] = (tx, -ty, tz)
        assert parents[i] < i
        G[i] = L if parents[i] < 0 else G[parents[i]] @ L
        local_trs.append(((tx, -ty, tz), euler_xyz(R), (1.0, 1.0, 1.0)))
    pos = m['pos']; nrm = m['nz']
    tris = m['tri']; tmat = m['tmat']; uv = m['uv']
    slots = [str(s) for s in m['slots']]
    wb = m['wbone']; ww = m['wweight']
    ids = iter(range(1000000000, 2000000000))
    geo, mesh_model, skin = next(ids), next(ids), next(ids)
    bone_model = [next(ids) for _ in names]; bone_attr = [next(ids) for _ in names]
    mat_ids = [next(ids) for _ in slots]; pose = next(ids)
    clusters = {}
    for j in range(wb.shape[1]):
        keep = ww[:, j] > 0
        for v, bb, w_ in zip(np.nonzero(keep)[0].tolist(), wb[keep, j].tolist(), ww[keep, j].tolist()):
            clusters.setdefault(bb, ([], [])); clusters[bb][0].append(v); clusters[bb][1].append(w_)
    cl_ids = {bb: next(ids) for bb in sorted(clusters)}
    pvi = tris.copy(); pvi[:, 2] = -pvi[:, 2] - 1
    out = io.StringIO(); w = out.write
    w('; FBX 7.3.0 project file\n; written by bfs_fbx.py: Bahamut Fused Sephiroth on Rebirth Sephiroth\'s bones\n\n')
    w('FBXHeaderExtension:  {\n\tFBXHeaderVersion: 1003\n\tFBXVersion: 7300\n\tCreator: "bfs_fbx"\n}\n')
    w('GlobalSettings:  {\n\tVersion: 1000\n\tProperties70:  {\n')
    for p_, v_ in (('UpAxis', 2), ('UpAxisSign', 1), ('FrontAxis', 1), ('FrontAxisSign', -1), ('CoordAxis', 0), ('CoordAxisSign', 1),
                   ('OriginalUpAxis', 2), ('OriginalUpAxisSign', 1)):
        w('\t\tP: "%s", "int", "Integer", "",%d\n' % (p_, v_))
    w('\t\tP: "UnitScaleFactor", "double", "Number", "",1\n\t\tP: "OriginalUnitScaleFactor", "double", "Number", "",1\n\t}\n}\n')
    w('Documents:  {\n\tCount: 1\n\tDocument: 999999999, "", "Scene" {\n\t\tProperties70:  {\n\t\t\tP: "SourceObject", "object", "", ""\n'
      '\t\t\tP: "ActiveAnimStackName", "KString", "", "", ""\n\t\t}\n\t\tRootNode: 0\n\t}\n}\nReferences:  {\n}\n')
    nmodels = 1 + len(names)
    w('Definitions:  {\n\tVersion: 100\n\tCount: %d\n' % (1 + nmodels + len(names) + 1 + len(slots) + 1 + len(cl_ids) + 1))
    for t_, c_ in (('GlobalSettings', 1), ('Model', nmodels), ('NodeAttribute', len(names)), ('Geometry', 1), ('Material', len(slots)),
                   ('Deformer', 1 + len(cl_ids)), ('Pose', 1)):
        w('\tObjectType: "%s" {\n\t\tCount: %d\n\t}\n' % (t_, c_))
    w('}\nObjects:  {\n')
    P = mirror(pos); N = mirror(nrm)
    w('\tGeometry: %d, "Geometry::%s", "Mesh" {\n' % (geo, name))
    w('\t\tVertices: *%d {\n\t\t\ta: %s\n\t\t}\n' % (P.size, flat(P)))
    w('\t\tPolygonVertexIndex: *%d {\n\t\t\ta: %s\n\t\t}\n' % (pvi.size, iflat(pvi)))
    w('\t\tGeometryVersion: 124\n')
    # (per polygon vertex: the editor's skeletal mesh import reads tangents and binormals by corner index whatever the
    #  layer's mapping says, so per-control-point tangent arrays came in scrambled and split the vertices)
    corners = tris.ravel()
    for tag, arr, data in (('LayerElementNormal', 'Normals', N[corners]),):
        w('\t\t%s: 0 {\n\t\t\tVersion: 101\n\t\t\tName: ""\n\t\t\tMappingInformationType: "ByPolygonVertex"\n\t\t\tReferenceInformationType: "Direct"\n' % tag)
        w('\t\t\t%s: *%d {\n\t\t\t\ta: %s\n\t\t\t}\n\t\t}\n' % (arr, data.size, flat(data, 7)))
    for c in range(uv.shape[1]):
        u = uv[:, c, :].copy()
        w('\t\tLayerElementUV: %d {\n\t\t\tVersion: 101\n\t\t\tName: "UVChannel_%d"\n\t\t\tMappingInformationType: "ByPolygonVertex"\n\t\t\tReferenceInformationType: "IndexToDirect"\n' % (c, c + 1))
        w('\t\t\tUV: *%d {\n\t\t\t\ta: %s\n\t\t\t}\n' % (u.size, flat(u, 7)))
        w('\t\t\tUVIndex: *%d {\n\t\t\t\ta: %s\n\t\t\t}\n\t\t}\n' % (tris.size, iflat(tris)))
    w('\t\tLayerElementMaterial: 0 {\n\t\t\tVersion: 101\n\t\t\tName: ""\n\t\t\tMappingInformationType: "ByPolygon"\n\t\t\tReferenceInformationType: "IndexToDirect"\n')
    w('\t\t\tMaterials: *%d {\n\t\t\t\ta: %s\n\t\t\t}\n\t\t}\n' % (len(tmat), iflat(tmat)))
    w('\t\tLayer: 0 {\n\t\t\tVersion: 100\n')
    for t_ in ('LayerElementNormal', 'LayerElementMaterial', 'LayerElementUV'):
        w('\t\t\tLayerElement:  {\n\t\t\t\tType: "%s"\n\t\t\t\tTypedIndex: 0\n\t\t\t}\n' % t_)
    w('\t\t}\n')
    for c in range(1, uv.shape[1]):
        w('\t\tLayer: %d {\n\t\t\tVersion: 100\n\t\t\tLayerElement:  {\n\t\t\t\tType: "LayerElementUV"\n\t\t\t\tTypedIndex: %d\n\t\t\t}\n\t\t}\n' % (c, c))
    w('\t}\n')
    w('\tModel: %d, "Model::%s", "Mesh" {\n\t\tVersion: 232\n\t\tProperties70:  {\n\t\t\tP: "DefaultAttributeIndex", "int", "Integer", "",0\n\t\t}\n\t\tShading: T\n\t\tCulling: "CullingOff"\n\t}\n' % (mesh_model, name))
    for i, nm in enumerate(names):
        (t, r, s) = local_trs[i]
        w('\tNodeAttribute: %d, "NodeAttribute::%s", "LimbNode" {\n\t\tTypeFlags: "Skeleton"\n\t}\n' % (bone_attr[i], nm))
        w('\tModel: %d, "Model::%s", "LimbNode" {\n\t\tVersion: 232\n\t\tProperties70:  {\n' % (bone_model[i], nm))
        w('\t\t\tP: "Lcl Translation", "Lcl Translation", "", "A",%s\n' % flat(t, 9))
        w('\t\t\tP: "Lcl Rotation", "Lcl Rotation", "", "A",%s\n' % flat(r, 9))
        w('\t\t\tP: "Lcl Scaling", "Lcl Scaling", "", "A",%s\n' % flat(s, 9))
        w('\t\t\tP: "DefaultAttributeIndex", "int", "Integer", "",0\n\t\t}\n\t\tShading: Y\n\t\tCulling: "CullingOff"\n\t}\n')
    for mid, sname in zip(mat_ids, slots):
        w('\tMaterial: %d, "Material::%s", "" {\n\t\tVersion: 102\n\t\tShadingModel: "phong"\n\t\tMultiLayer: 0\n\t\tProperties70:  {\n\t\t\tP: "DiffuseColor", "Color", "", "A",0.8,0.8,0.8\n\t\t}\n\t}\n' % (mid, sname))
    w('\tDeformer: %d, "Deformer::%s", "Skin" {\n\t\tVersion: 101\n\t\tLink_DeformAcuracy: 50\n\t}\n' % (skin, name))
    I4 = np.eye(4)
    for bb, cid in cl_ids.items():
        vs, ws = clusters[bb]
        w('\tDeformer: %d, "SubDeformer::%s", "Cluster" {\n\t\tVersion: 100\n\t\tUserData: "", ""\n' % (cid, names[bb]))
        w('\t\tIndexes: *%d {\n\t\t\ta: %s\n\t\t}\n' % (len(vs), iflat(vs)))
        w('\t\tWeights: *%d {\n\t\t\ta: %s\n\t\t}\n' % (len(ws), flat(ws, 7)))
        # (the file's Transform is TransformLink^-1 x the mesh's bind matrix: the SDK reads it back as TransformLink x it.
        #  Writing identity here made the SDK think the mesh was bound at each bone, so the editor re-skinned every vertex.)
        w('\t\tTransform: *16 {\n\t\t\ta: %s\n\t\t}\n' % fbx_matrix(np.linalg.inv(G[bb])))
        w('\t\tTransformLink: *16 {\n\t\t\ta: %s\n\t\t}\n\t}\n' % fbx_matrix(G[bb]))
    w('\tPose: %d, "Pose::BIND_POSES", "BindPose" {\n\t\tType: "BindPose"\n\t\tVersion: 100\n\t\tNbPoseNodes: %d\n' % (pose, 1 + len(names)))
    w('\t\tPoseNode:  {\n\t\t\tNode: %d\n\t\t\tMatrix: *16 {\n\t\t\t\ta: %s\n\t\t\t}\n\t\t}\n' % (mesh_model, fbx_matrix(I4)))
    for i in range(len(names)):
        w('\t\tPoseNode:  {\n\t\t\tNode: %d\n\t\t\tMatrix: *16 {\n\t\t\t\ta: %s\n\t\t\t}\n\t\t}\n' % (bone_model[i], fbx_matrix(G[i])))
    w('\t}\n}\n')
    w('Connections:  {\n\tC: "OO",%d,0\n\tC: "OO",%d,%d\n' % (mesh_model, geo, mesh_model))
    for mid in mat_ids:
        w('\tC: "OO",%d,%d\n' % (mid, mesh_model))
    for i, par in enumerate(parents):
        w('\tC: "OO",%d,%d\n' % (bone_attr[i], bone_model[i]))
        w('\tC: "OO",%d,%d\n' % (bone_model[i], 0 if par < 0 else bone_model[par]))
    w('\tC: "OO",%d,%d\n' % (skin, geo))
    for bb, cid in cl_ids.items():
        w('\tC: "OO",%d,%d\n\tC: "OO",%d,%d\n' % (cid, skin, bone_model[bb], cid))
    w('}\n')
    open(out_path, 'w', newline='\n').write(out.getvalue())

if __name__ == '__main__':
    m = np.load(sys.argv[1])
    write(m, sys.argv[2], sys.argv[3])
    print('written', sys.argv[2])
