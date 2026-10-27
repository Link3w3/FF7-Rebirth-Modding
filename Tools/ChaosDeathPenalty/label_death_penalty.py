# Chaos's gun, the Death Penalty (WE0011_10), made cookable (the editor's part of run_death_penalty.cmd; End editor
# closed: it runs in an editor commandlet). Everything in Content\Character\Weapon\WE011_10_Chaos_DeathPenialty goes
# under a Primary Asset Label of its own for pakchunk56 (no other label or data object of the project uses 56; the label
# is saved before anything is loaded). Its material instance was made on the game's cooked copy of the Quicksilver's
# material in Content\Character\Weapon (which this editor cannot load: it reads it wrong and stops), so it is put on
# that material's own parent, RMI_Surface_Standard_Wide (the Quicksilver's material is that with its textures; the
# Death Penalty's give their own), with the DirectX normal map the import made (it had the OpenGL one, whose green
# channel is the other way up in this engine). The model's effect mesh (EffectAppendixMesh: the Quicksilver's cooked
# WE0011_00_vfx, which it was cloned with) is cleared, and the model is saved and loaded as the cook will load it.
# run_death_penalty.cmd puts the two cooked Quicksilver files aside while this runs (and back after), so nothing loads
# them. The folder was Content\Character\Weapons when these were made (the game's is Weapon): the project's
# PackageRedirects (DefaultEngine.ini) take their old references to the new place, and each is saved with the new ones.
# Result: Saved\ChaosDeathPenalty\label_result.json
import json, os, traceback
import unreal

FOLDER = '/Game/Character/Weapon/WE011_10_Chaos_DeathPenialty'
LABEL = FOLDER + '/PAL_DeathPenalty_Chunk56'
CHUNK = 56
MESH = FOLDER + '/Model/WE0011_10'
PARENT = '/Game/Renderer/MaterialInstance/Surface/RMI_Surface_Standard_Wide'
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(SAVED, 'ChaosDeathPenalty')
os.makedirs(OUT, exist_ok=True)
RESULT = os.path.join(OUT, 'label_result.json')
results = {'steps': []}


def write_json(path, value):
    temp = path + '.tmp'
    with open(temp, 'w') as f:
        json.dump(value, f, indent=1)
    os.replace(temp, path)


def log(key, value):
    results[key] = value
    results['steps'].append(key)
    unreal.log('DEATH PENALTY %s: %s' % (key, str(value)[:2000]))
    write_json(RESULT, results)


def setp(obj, names, value):
    last = None
    for name in names if isinstance(names, (list, tuple)) else [names]:
        try:
            obj.set_editor_property(name, value)
            return
        except Exception as ex:
            last = ex
    raise last


def getp(obj, names):
    last = None
    for name in names if isinstance(names, (list, tuple)) else [names]:
        try:
            return obj.get_editor_property(name)
        except Exception as ex:
            last = ex
    raise last


def new_label(folder, name):
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    made = None
    try:
        factory = unreal.DataAssetFactory()
        factory.set_editor_property('data_asset_class', unreal.PrimaryAssetLabel)
        made = tools.create_asset(name, folder, unreal.PrimaryAssetLabel, factory)
    except Exception:
        made = None
    if made is None:
        made = tools.create_asset(name, folder, unreal.PrimaryAssetLabel, None)
    return made


def chunk_users(registry):
    """Labels and data objects of the project that put assets in CHUNK (other than this label)."""
    users = []
    for class_name in ('PrimaryAssetLabel', 'EndSkeletonCompatDataObject'):
        try:
            found = registry.get_assets_by_class(class_name, True)
        except Exception:
            found = []
        for data in found:
            path = str(data.object_path)
            if path.split('.')[0] == LABEL:
                continue
            obj = unreal.EditorAssetLibrary.load_asset(path)
            if obj is None:
                continue
            try:
                chunk = int(getp(getp(obj, 'rules'), 'chunk_id')) if class_name == 'PrimaryAssetLabel' else int(getp(obj, 'build_chunk'))
            except Exception:
                continue
            if chunk == CHUNK:
                users.append(path)
    return users


def mesh_report(mesh):
    out = {}
    skeleton = getp(mesh, 'skeleton')
    out['skeleton'] = skeleton.get_path_name() if skeleton else None
    try:
        out['materials'] = ['%s: %s' % (getp(m, 'material_slot_name'), (getp(m, 'material_interface').get_path_name() if getp(m, 'material_interface') else None))
                            for m in getp(mesh, 'materials')]
    except Exception as ex:
        out['materials'] = 'not read (%s)' % ex
    try:
        b = mesh.get_bounds()
        out['bounds_cm'] = [round(b.box_extent.x * 2, 1), round(b.box_extent.y * 2, 1), round(b.box_extent.z * 2, 1)]
        out['bounds_origin'] = [round(b.origin.x, 1), round(b.origin.y, 1), round(b.origin.z, 1)]
    except Exception as ex:
        out['bounds_cm'] = 'not read (%s)' % ex
    try:
        lods = unreal.EditorSkeletalMeshLibrary.get_lod_count(mesh)
        out['lods'] = lods
        out['vertices'] = [unreal.EditorSkeletalMeshLibrary.get_num_verts(mesh, k) for k in range(lods)]
    except Exception as ex:
        out['lods'] = 'not read (%s)' % ex
    sockets = []
    for owner in (mesh, skeleton):
        if owner is None:
            continue
        try:
            for s in getp(owner, 'sockets') or []:
                loc, rot = getp(s, 'relative_location'), getp(s, 'relative_rotation')
                sockets.append('%s on %s at (%.1f, %.1f, %.1f) rot (%.0f, %.0f, %.0f) [%s]' % (
                    getp(s, 'socket_name'), getp(s, 'bone_name'), loc.x, loc.y, loc.z, rot.pitch, rot.yaw, rot.roll,
                    'mesh' if owner is mesh else 'skeleton'))
        except Exception as ex:
            sockets.append('%s sockets not read (%s)' % ('mesh' if owner is mesh else 'skeleton', ex))
    out['sockets'] = sockets
    return out


def fix_normal_map(mi):
    """The DirectX normal map in place of the OpenGL one (same name, _N_DirectX for _N_OpenGL), if it is there."""
    changed = []
    values = list(getp(mi, 'texture_parameter_values') or [])
    for v in values:
        tex = getp(v, 'parameter_value')
        if tex is None:
            continue
        path = tex.get_path_name()
        if '_N_OpenGL' not in path:
            continue
        other = path.replace('_N_OpenGL', '_N_DirectX')
        if not unreal.EditorAssetLibrary.does_asset_exist(other.split('.')[0]):
            continue
        new = unreal.EditorAssetLibrary.load_asset(other.split('.')[0])
        info = getp(v, 'parameter_info')
        name = getp(info, 'name')
        try:
            unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(mi, name, new)
        except Exception:
            setp(v, 'parameter_value', new)
            setp(mi, 'texture_parameter_values', values)
        changed.append('%s: %s -> %s' % (name, path.rsplit('/', 1)[1], other.rsplit('/', 1)[1]))
    if changed:
        try:
            unreal.MaterialEditingLibrary.update_material_instance(mi)
        except Exception:
            pass
        if not unreal.EditorAssetLibrary.save_loaded_asset(mi, False):
            raise RuntimeError('the material instance %s could not be saved' % mi.get_path_name())
    return changed


try:
    if os.path.exists(RESULT):
        os.replace(RESULT, RESULT + '.previous')
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    registry.scan_paths_synchronous([FOLDER], True)
    found = [a for a in registry.get_assets_by_path(FOLDER, True) if str(a.asset_class) not in ('PrimaryAssetLabel',)]
    if not found:
        raise RuntimeError('nothing in ' + FOLDER)
    log('found', ['%s (%s)' % (str(a.asset_name), str(a.asset_class)) for a in found])

    # 1. The label first, without loading anything (it labels the folder's assets, subfolders included)
    users = chunk_users(registry)
    if users:
        raise RuntimeError('pakchunk%d is used by %s too: tell Sandalphon' % (CHUNK, ', '.join(users)))
    log('chunk', 'pakchunk%d: no other label or data object uses it' % CHUNK)
    label = unreal.EditorAssetLibrary.load_asset(LABEL) if unreal.EditorAssetLibrary.does_asset_exist(LABEL) else None
    if label is None:
        label = new_label(FOLDER, LABEL.rsplit('/', 1)[1])
    if label is None:
        raise RuntimeError('the label %s could not be made' % LABEL)
    rules = label.get_editor_property('rules')
    setp(rules, 'chunk_id', CHUNK)
    setp(rules, 'priority', max(1, int(getp(rules, 'priority'))))
    setp(rules, 'cook_rule', unreal.PrimaryAssetCookRule.ALWAYS_COOK)
    setp(rules, ['apply_recursively', 'b_apply_recursively'], False)
    setp(label, 'rules', rules)
    setp(label, ['label_assets_in_my_directory', 'b_label_assets_in_my_directory'], True)
    setp(label, 'explicit_assets', [])
    if not unreal.EditorAssetLibrary.save_loaded_asset(label, False):
        raise RuntimeError('the label %s could not be saved' % LABEL)
    log('label', '%s: chunk %d, the %d asset(s) of its folder' % (LABEL, CHUNK, len(found)))

    # 2. Its material: on RMI_Surface_Standard_Wide, the DirectX normal map
    parent_new = unreal.EditorAssetLibrary.load_asset(PARENT)
    if parent_new is None:
        raise RuntimeError('the parent material does not load: ' + PARENT)
    changed = []
    for a in found:
        if str(a.asset_class) != 'MaterialInstanceConstant':
            continue
        mi = unreal.EditorAssetLibrary.load_asset(str(a.object_path))
        before = getp(mi, 'parent')
        before_text = before.get_path_name() if before else 'none (the cooked copy is aside)'
        if before is not parent_new:
            try:
                unreal.MaterialEditingLibrary.set_material_instance_parent(mi, parent_new)
            except Exception:
                setp(mi, 'parent', parent_new)
        after = getp(mi, 'parent')
        if after is not parent_new:
            raise RuntimeError('the parent of %s could not be set' % str(a.asset_name))
        changed.append('%s: parent %s -> %s' % (str(a.asset_name), before_text, after.get_path_name()))
        changed += fix_normal_map(mi)
        try:
            unreal.MaterialEditingLibrary.update_material_instance(mi)
        except Exception:
            pass
        if not unreal.EditorAssetLibrary.save_loaded_asset(mi, False):
            raise RuntimeError('the material instance %s could not be saved' % mi.get_path_name())
        changed.append('%s: textures %s' % (str(a.asset_name), ', '.join(
            '%s=%s' % (getp(getp(v, 'parameter_info'), 'name'), getp(v, 'parameter_value').get_name() if getp(v, 'parameter_value') else None)
            for v in (getp(mi, 'texture_parameter_values') or []))))
    log('materials', changed)

    # 3. The model: no effect mesh, saved, loaded as the cook will load it
    mesh = unreal.EditorAssetLibrary.load_asset(MESH)
    if mesh is None:
        raise RuntimeError('the mesh does not load: ' + MESH)
    appendix = 'not a property here'
    for name in ('effect_appendix_mesh', 'EffectAppendixMesh'):
        try:
            value = mesh.get_editor_property(name)
            mesh.set_editor_property(name, None)
            appendix = 'was %s, cleared' % (value.get_path_name() if value else 'none (the cooked copy is aside)')
            break
        except Exception as ex:
            appendix = 'not set (%s)' % ex
    if not unreal.EditorAssetLibrary.save_loaded_asset(mesh, False):
        raise RuntimeError('the mesh could not be saved')
    report = mesh_report(mesh)
    report['effect_appendix_mesh'] = appendix
    log('mesh', report)

    # 4. Its skeleton and physics asset saved with their references at the new place too
    saved = []
    for a in found:
        if str(a.asset_class) in ('Skeleton', 'PhysicsAsset'):
            obj = unreal.EditorAssetLibrary.load_asset(str(a.object_path))
            if obj is None:
                raise RuntimeError('%s does not load' % str(a.object_path))
            if not unreal.EditorAssetLibrary.save_loaded_asset(obj, False):
                raise RuntimeError('%s could not be saved' % str(a.object_path))
            saved.append(str(a.asset_name))
    log('resaved', saved)
    log('done', True)
except Exception:
    results['error'] = traceback.format_exc()
    unreal.log_error('DEATH PENALTY ERROR: ' + results['error'])
    write_json(RESULT, results)
