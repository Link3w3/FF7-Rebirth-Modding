# What sockets PC0010_13 and WE1021_49 have now (mesh sockets by name, and every socket name the mesh resolves: its own
# plus its skeleton's), with the packages' last-saved times. Read only.
import unreal, json, os
out = {}
proj = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir())
for path in ('/Game/Character/Player/PC0010_13_Young_Sephiroth/Model/PC0010_13', '/Game/Character/Weapon/WE1021_49_Nameless/Model/WE1021_49'):
    sm = unreal.load_asset(path)
    mesh_sockets = [str(sm.get_socket_by_index(i).get_editor_property('socket_name')) for i in range(sm.num_sockets())]
    c = unreal.new_object(unreal.SkeletalMeshComponent)
    c.set_skeletal_mesh(sm)
    bones = set(str(c.get_bone_name(i)) for i in range(c.get_num_bones()))
    every = [str(n) for n in c.get_all_socket_names()]
    skel = sm.get_editor_property('skeleton')
    files = {}
    for p in (path, skel.get_path_name().split('.')[0]):
        f = os.path.join(proj, p[len('/Game/'):] + '.uasset')
        files[p.rsplit('/', 1)[-1]] = os.path.getmtime(f) if os.path.exists(f) else None
    pkg_dirty = [p for p in (path,) if unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages() and False]
    out[path] = dict(mesh_sockets=mesh_sockets, all_sockets=sorted(n for n in every if n not in bones), saved=files)
dirty = [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
out['dirty'] = [d for d in dirty if 'PC0010_13' in d or 'WE1021_49' in d]
result = json.dumps(out, indent=1)
