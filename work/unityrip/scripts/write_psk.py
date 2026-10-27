"""model.json/model.npz (extract_unity.py) -> .psk (ActorX, with VTXNORMS and VERTEXCOLOR), in the conventions of the
io_scene_psk_psa add-on (the Blender PSK importer): points in Blender's axes, Unreal units (x100: centimetres),
faces wound as that add-on writes them, V flipped, the root bone's rotation as is and every other bone's local rotation
conjugated, locations relative to the parent in the parent's frame.

    write_psk.py <model dir> <out .psk> [scale (default 100)]
"""
import json, os, sys
import numpy as np
sys.path.insert(0, '/work/unityrip/pskpy')
import bpy  # (provides mathutils)
from mathutils import Matrix
from psk_psa_py.psk.data import Psk
from psk_psa_py.psk.writer import write_psk_to_path
from psk_psa_py.shared.data import PsxBone, Vector3, Color


def v3(x, y, z):
    v = Vector3()
    v.x, v.y, v.z = float(x), float(y), float(z)
    return v


def main(model_dir, out, scale='100'):
    scale = float(scale)
    info = json.load(open(os.path.join(model_dir, 'model.json')))
    A = np.load(os.path.join(model_dir, 'model.npz'))
    psk = Psk()
    bones = info['bones']
    W = [Matrix(b['world']) for b in bones]
    for i, b in enumerate(bones):
        pb = PsxBone()
        pb.name = b['name'].encode('cp1252')
        p = b['parent']
        assert p < i, 'parents first'
        if p < 0:
            assert i == 0, 'one root'
            q = W[i].to_quaternion()
            loc = W[i].translation * scale
            pb.parent_index = 0
        else:
            Rp = W[p].to_3x3()
            q = (Rp.inverted() @ W[i].to_3x3()).to_quaternion().conjugated()
            loc = Rp.inverted() @ (W[i].translation - W[p].translation) * scale
            pb.parent_index = p
        pb.rotation.x, pb.rotation.y, pb.rotation.z, pb.rotation.w = q.x, q.y, q.z, q.w
        pb.location = v3(*loc)
        psk.bones.append(pb)
    for i, b in enumerate(bones):
        if b['parent'] >= 0:
            psk.bones[b['parent']].children_count += 1
    mat_names = []
    for m in info['meshes']:
        for n in m['materials']:
            if n not in mat_names:
                mat_names.append(n)
    for i, n in enumerate(mat_names):
        pm = Psk.Material()
        pm.name = n.encode('cp1252')
        pm.texture_index = i
        psk.materials.append(pm)
    base = 0
    for m in info['meshes']:
        k = m['name']
        co, no, uv, tri, tmat = A[k + '/co'], A[k + '/no'], A[k + '/uv0'], A[k + '/tri'], A[k + '/tri_mat']
        mats = [mat_names.index(n) for n in m['materials']]
        vmat = np.zeros(len(co), dtype=np.int64)
        vmat[tri.ravel()] = np.repeat(np.array(mats)[tmat], 3)
        fm = np.array(mats)[tmat]
        for j in range(3):                                 # (one material per vertex: each mesh has one here)
            assert (vmat[tri[:, j]] == fm).all(), (k, 'a vertex shared by two materials')
        col = A[k + '/col'] if k + '/col' in A else np.ones((len(co), 4), dtype=np.float32)
        for i in range(len(co)):
            psk.points.append(v3(*(co[i] * scale)))
            psk.vertex_normals.append(v3(*no[i]))
            psk.wedges.append(Psk.Wedge(base + i, float(uv[i, 0]), float(1.0 - uv[i, 1]), int(vmat[i])))
            c = Color()
            c.r, c.g, c.b, c.a = [int(round(float(x) * 255)) for x in col[i]]
            psk.vertex_colors.append(c)
        for t, mi in zip(tri, tmat):
            # Blender face (a, c, b) -> the add-on's wedge order is reversed
            psk.faces.append(Psk.Face((base + int(t[2]), base + int(t[1]), base + int(t[0])), mats[mi], 0, 1))
        for v, bi, w in zip(A[k + '/w_vert'], A[k + '/w_bone'], A[k + '/w_val']):
            pw = Psk.Weight()
            pw.weight, pw.point_index, pw.bone_index = float(w), base + int(v), int(bi)
            psk.weights.append(pw)
        base += len(co)
    psk.sort_and_normalize_weights()
    write_psk_to_path(psk, os.path.abspath(out), is_extended_format=True)
    print('psk', out, os.path.getsize(out), 'bones', len(psk.bones), 'points', len(psk.points), 'faces', len(psk.faces),
          'materials', mat_names)


if __name__ == '__main__':
    main(*sys.argv[1:])
