# Nameless (WE1021_49) next to the Masamune (WE1021_00): bones (parents, rest places), sockets, size, materials and their
# textures, Asset User Data. Read only.
import unreal, json
EAL = unreal.EditorAssetLibrary
out = {}


def vec(v):
    return [round(v.x, 3), round(v.y, 3), round(v.z, 3)]


def rot(r):
    return [round(r.roll, 2), round(r.pitch, 2), round(r.yaw, 2)]


for key, folder in (('nameless', '/Game/Character/Weapon/WE1021_49_Nameless'),
                    ('masamune', '/Game/Character/Weapon/WE1021_00_SephirothIllusion_Masamune')):
    info = {'assets': [str(a) for a in EAL.list_assets(folder, recursive=True, include_folder=False)]}
    meshes = [a for a in info['assets'] if '/Model/' in a]
    for a in meshes:
        obj = unreal.load_asset(a.split('.')[0])
        if not isinstance(obj, unreal.SkeletalMesh):
            info.setdefault('other', []).append((a, obj.get_class().get_name() if obj else None))
            continue
        c = unreal.new_object(unreal.SkeletalMeshComponent)
        c.set_skeletal_mesh(obj)
        n = c.get_num_bones()
        bones = []
        for i in range(n):
            nm = str(c.get_bone_name(i))
            bones.append([nm, str(c.get_parent_bone(nm)), vec(c.get_ref_pose_position(i))])
        sockets = []
        for i in range(obj.num_sockets()):
            s = obj.get_socket_by_index(i)
            sockets.append([str(s.get_editor_property('socket_name')), str(s.get_editor_property('bone_name')),
                            vec(s.get_editor_property('relative_location')), rot(s.get_editor_property('relative_rotation')),
                            vec(s.get_editor_property('relative_scale'))])
        b = obj.get_bounds()
        mats = []
        for m in obj.get_editor_property('materials'):
            mi = m.get_editor_property('material_interface')
            entry = [str(m.get_editor_property('material_slot_name')), mi.get_path_name() if mi else None]
            if mi is not None and isinstance(mi, unreal.MaterialInstance):
                p = mi.get_editor_property('parent')
                entry.append(p.get_path_name() if p else None)
                entry.append({str(tp.get_editor_property('parameter_info').get_editor_property('name')):
                              (tp.get_editor_property('parameter_value').get_name() if tp.get_editor_property('parameter_value') else None)
                              for tp in mi.get_editor_property('texture_parameter_values')})
            mats.append(entry)
        aud = []
        for d in (obj.get_editor_property('asset_user_data') or []):
            if d is None:
                continue
            e = {'class': d.get_class().get_name()}
            try:
                e['bonamik'] = [x.get_path_name() if x else None for x in d.get_editor_property('BonamikDataList')]
            except Exception:
                pass
            aud.append(e)
        skel = obj.get_editor_property('skeleton')
        info[a] = dict(bones=bones, sockets=sockets, origin=vec(b.origin), extent=vec(b.box_extent),
                       skeleton=skel.get_path_name() if skel else None, materials=mats, user_data=aud,
                       lods=obj.get_editor_property('lod_info').__len__() if hasattr(obj.get_editor_property('lod_info'), '__len__') else None)
    out[key] = info
result = json.dumps(out, indent=0)
