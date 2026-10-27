# Reference-pose transforms (rotation, translation, scale) of every bone of PC0010_13 and WE1021_49, with the methods this
# editor offers; and each mesh's imported bounds. Read only.
import unreal, json
out = {}
for path in ('/Game/Character/Player/PC0010_13_Young_Sephiroth/Model/PC0010_13', '/Game/Character/Weapon/WE1021_49_Nameless/Model/WE1021_49',
             '/Game/Character/Weapon/WE1021_00_SephirothIllusion_Masamune/Model/WE1021_00'):
    sm = unreal.load_asset(path)
    c = unreal.new_object(unreal.SkeletalMeshComponent)
    c.set_skeletal_mesh(sm)
    info = {'methods': [m for m in ('get_ref_pose_transform', 'get_ref_pose_position', 'get_bone_transform', 'get_socket_transform') if hasattr(c, m)]}
    bones = []
    n = c.get_num_bones()
    for i in range(min(n, 12) if 'PC0010_13' in path else n):
        name = str(c.get_bone_name(i))
        row = [name]
        if hasattr(c, 'get_ref_pose_transform'):
            try:
                t = c.get_ref_pose_transform(i)
                row += [[round(t.translation.x, 4), round(t.translation.y, 4), round(t.translation.z, 4)],
                        [round(t.rotation.x, 5), round(t.rotation.y, 5), round(t.rotation.z, 5), round(t.rotation.w, 5)],
                        [round(t.scale3d.x, 5), round(t.scale3d.y, 5), round(t.scale3d.z, 5)]]
            except Exception as e:
                row.append('ERR ' + str(e)[:80])
        bones.append(row)
    info['bones'] = bones
    b = sm.get_bounds()
    info['bounds'] = dict(origin=[round(b.origin.x, 2), round(b.origin.y, 2), round(b.origin.z, 2)],
                          extent=[round(b.box_extent.x, 2), round(b.box_extent.y, 2), round(b.box_extent.z, 2)])
    try:
        ib = sm.get_imported_bounds()
        info['imported_bounds'] = dict(origin=[round(ib.origin.x, 2), round(ib.origin.y, 2), round(ib.origin.z, 2)],
                                       extent=[round(ib.box_extent.x, 2), round(ib.box_extent.y, 2), round(ib.box_extent.z, 2)])
    except Exception as e:
        info['imported_bounds'] = 'ERR ' + str(e)[:60]
    out[path] = info
result = json.dumps(out, indent=0)
