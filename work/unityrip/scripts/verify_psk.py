"""Import the .psk with the io_scene_psk_psa add-on (as a user would) and compare it with model.json/model.npz:
bone rest matrices, points, faces and their facing, UVs, custom normals, vertex colours and weights.

    verify_psk.py <model dir> <.psk>
"""
import json, os, sys
import numpy as np
sys.path[:0] = ['/work/unityrip/pskpy', '/work/unityrip/psk_addon']
import bpy
from mathutils import Matrix
import io_scene_psk_psa
from io_scene_psk_psa.psk.importer import import_psk, PskImportOptions
from psk_psa_py.psk.reader import read_psk_from_file


def main(model_dir, path):
    info = json.load(open(os.path.join(model_dir, 'model.json')))
    A = np.load(os.path.join(model_dir, 'model.npz'))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    io_scene_psk_psa.register()
    psk = read_psk_from_file(path)
    opts = PskImportOptions()
    opts.bone_length = 3.0
    res = import_psk(psk, bpy.context, 'check', opts)
    print('warnings', res.warnings)
    arm, me_ob = res.armature_object, res.mesh_object
    bpy.ops.object.mode_set(mode='OBJECT')
    # bones (armature space; the PSK is in centimetres)
    worst_t = worst_r = 0.0
    for b in info['bones']:
        W = Matrix(b['world'])
        M = arm.data.bones[b['name']].matrix_local
        worst_t = max(worst_t, (M.translation / 100.0 - W.translation).length)
        worst_r = max(worst_r, max(abs(M.to_3x3()[i][j] - W.to_3x3()[i][j]) for i in range(3) for j in range(3)))
    print('bones', len(info['bones']), 'max position error (m) %.2e' % worst_t, 'max rotation element error %.2e' % worst_r)
    # mesh
    me = me_ob.data
    co = np.concatenate([A[m['name'] + '/co'] for m in info['meshes']])
    no = np.concatenate([A[m['name'] + '/no'] for m in info['meshes']])
    uv = np.concatenate([A[m['name'] + '/uv0'] for m in info['meshes']])
    nt = sum(len(A[m['name'] + '/tri']) for m in info['meshes'])
    V = len(me.vertices)
    got = np.empty(V * 3, dtype=np.float32); me.vertices.foreach_get('co', got)
    got = got.reshape(-1, 3) / 100.0
    print('points', V, len(co), 'max error (m) %.2e' % np.abs(got - co).max(), 'faces', len(me.polygons), nt)
    L = len(me.loops)
    lv = np.empty(L, dtype=np.int32); me.loops.foreach_get('vertex_index', lv)
    luv = np.empty(L * 2, dtype=np.float32); me.uv_layers[0].uv.foreach_get('vector', luv)
    print('uv max error %.2e' % np.abs(luv.reshape(-1, 2) - uv[lv]).max())
    cn = np.array([tuple(x.vector) for x in me.corner_normals])
    d = (cn * no[lv]).sum(1)
    print('custom normals: min dot %.4f' % d.min())
    pn = np.empty(len(me.polygons) * 3, dtype=np.float32); me.polygons.foreach_get('normal', pn)
    pn = pn.reshape(-1, 3)
    ls = np.empty(len(me.polygons), dtype=np.int32); me.polygons.foreach_get('loop_start', ls)
    facing = np.array([(pn[i] * no[lv[ls[i]:ls[i] + 3]].mean(0)).sum() for i in range(len(pn))])
    print('faces facing along their normals: %.2f%%' % (100.0 * (facing > 0).mean()))
    # weights
    names = [b['name'] for b in info['bones']]
    want = {}
    base = 0
    for m in info['meshes']:
        k = m['name']
        for v, bi, w in zip(A[k + '/w_vert'], A[k + '/w_bone'], A[k + '/w_val']):
            want[(base + int(v), names[int(bi)])] = want.get((base + int(v), names[int(bi)]), 0.0) + float(w)
        base += len(A[k + '/co'])
    gname = {g.index: g.name for g in me_ob.vertex_groups}
    have = {}
    for v in me.vertices:
        for g in v.groups:
            have[(v.index, gname[g.group])] = g.weight
    errs = max(abs(have.get(k, 0) - want.get(k, 0)) for k in set(have) | set(want))
    print('weights', len(have), len(want), 'max error %.2e' % errs)
    ca = me.color_attributes.get('VERTEXCOLOR')
    print('vertex colours', ca is not None, 'materials', [m.name for m in me.materials])


if __name__ == '__main__':
    main(*sys.argv[1:])
