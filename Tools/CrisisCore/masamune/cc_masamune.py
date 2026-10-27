"""Crisis Core Reunion's Masamune for the CRISIS CORE skins, in the open End editor (Output Log, Cmd:
    py "C:/FF7R2UProj/Tools/CrisisCore/masamune/cc_masamune.py"
from what Sandalphon made of Reunion's model (Saved/ModExtract/cc16/masamune):

  1. textures  WE001021_16_C (colour, sRGB), _N (normal map), _M metal, _R roughness, _O occlusion (Rebirth's grey maps)
               into /Game/Character/Weapon/WE1021_16_CrisisCore_Masamune/Texture;
  2. material  MI_WE001021_16 on RMI_Surface_Standard_Wide (the parent of the game's own Masamune material), the textures
               on Color, Normal, Metallic, Roughness, WideOcclusion;
  3. model     WE001021_16.fbx as the skeletal mesh /Game/Character/Weapon/WE1021_16_CrisisCore_Masamune/Model/WE001021_16
               (its own skeleton with the game's Masamune bones: Trans, C_Body_a, C_Body_End, C_TrailA_a-d, C_CharaA_a;
               a physics asset), the material on its slot;
  4. skins     every data object's CRISIS CORE skins (folders CrisisCoreSephiroth, CrisisCoreSephirothSeph,
               CrisisCoreSephirothWinged) get the weapon (the blueprint in the CrisisCoreWeapon skin folder Sandalphon put in
               the game) and the sword's packages as Extra Assets, and (editor 1.21) the moves they carry (Pack Battle10,
               the CRISIS CORE form's; Sets Neutral00 -> Neutral10, Crisis Core's field idle, walk, run and dash), then each
               is built and installed again (close the game first: the skins container is made anew).

Every step saves what it made; run it again to redo what failed (made assets are kept unless CCM_FORCE=1).
Result: Saved/ModExtract/cc16/masamune/cc_masamune_result.json (and the Output Log)."""
import json
import os
import time
import traceback

import unreal

SAVED = os.path.normpath(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()))
SRC = os.path.join(SAVED, 'ModExtract', 'cc16', 'masamune')
ROOT = '/Game/Character/Weapon/WE1021_16_CrisisCore_Masamune'
NAME = 'WE001021_16'
PARENT = '/Game/Renderer/MaterialInstance/Surface/RMI_Surface_Standard_Wide'
WEAPON = ('/Game/BluePrint/Character/Weapon/WE1021_16_CrisisCore_Masamune/WE1021_10_SephirothIllusion_MasamuneCutScale.'
          'WE1021_10_SephirothIllusion_MasamuneCutScale_C')
SKIN_FOLDERS = ['CrisisCoreSephiroth', 'CrisisCoreSephirothSeph', 'CrisisCoreSephirothWinged']
PACK = 'Battle10'                        # the CRISIS CORE form's moves (editor 1.21 / game mod 3.18.0)
SETS = {'Neutral00': 'Neutral10'}        # Crisis Core's field idle, walk, run and dash
PARAMS = {'Color': '_C', 'Normal': '_N', 'Metallic': '_M', 'Roughness': '_R', 'WideOcclusion': '_O'}
FORCE = os.environ.get('CCM_FORCE') == '1'
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
RESULT = os.path.join(SRC, 'cc_masamune_result.json')
results = {}


def log(text):
    unreal.log('CC MASAMUNE: ' + text)


def save():
    with open(RESULT + '.tmp', 'w') as f:
        json.dump(results, f, indent=1)
    os.replace(RESULT + '.tmp', RESULT)


def textures():
    folder = ROOT + '/Texture'
    tasks = []
    for suffix in PARAMS.values():
        name = NAME + suffix
        if not FORCE and EAL.does_asset_exist('%s/%s' % (folder, name)):
            continue
        t = unreal.AssetImportTask()
        t.set_editor_property('filename', os.path.join(SRC, 'textures', name + '.png'))
        t.set_editor_property('destination_path', folder)
        t.set_editor_property('destination_name', name)
        t.set_editor_property('replace_existing', True)
        t.set_editor_property('automated', True)
        t.set_editor_property('save', False)
        tasks.append(t)
    if tasks:
        AT.import_asset_tasks(tasks)
    done = []
    for suffix in PARAMS.values():
        name = NAME + suffix
        tex = unreal.load_asset('%s/%s.%s' % (folder, name, name))
        if tex is None:
            raise RuntimeError('the texture %s did not import' % name)
        if suffix == '_C':
            tex.set_editor_property('srgb', True)
            tex.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_DEFAULT)
        elif suffix == '_N':
            tex.set_editor_property('srgb', False)
            tex.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP)
            tex.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_WORLD_NORMAL_MAP)
        else:
            tex.set_editor_property('srgb', False)
            tex.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_ALPHA)
        EAL.save_loaded_asset(tex)
        done.append(name)
    return done


def material():
    folder = ROOT + '/Material'
    name = 'MI_' + NAME
    path = '%s/%s' % (folder, name)
    parent = unreal.load_asset(PARENT)
    if parent is None:
        raise RuntimeError('the parent material does not load: ' + PARENT)
    mi = unreal.load_asset(path) if EAL.does_asset_exist(path) else None
    if mi is None:
        mi = AT.create_asset(name, folder, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, parent)
    ok, bad = [], []
    for param, suffix in PARAMS.items():
        tex = unreal.load_asset('%s/Texture/%s%s.%s%s' % (ROOT, NAME, suffix, NAME, suffix))
        if tex is not None:
            # (False on an instance of a game material, yet the instance holds the texture: read it back)
            MEL.set_material_instance_texture_parameter_value(mi, param, tex)
            got = MEL.get_material_instance_texture_parameter_value(mi, param)
        (ok if tex is not None and got is not None and got.get_path_name() == tex.get_path_name() else bad).append(param)
    MEL.update_material_instance(mi)
    EAL.save_loaded_asset(mi)
    return {'path': path, 'set': ok, 'not_set': bad}


def model():
    folder = ROOT + '/Model'
    path = '%s/%s' % (folder, NAME)
    if EAL.does_asset_exist(path) and not FORCE:
        sm = unreal.load_asset(path)
    else:
        if EAL.does_asset_exist(path):
            unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(unreal.load_asset(path))
        ui = unreal.FbxImportUI()
        for prop, value in (('import_mesh', True), ('import_as_skeletal', True),
                            ('mesh_type_to_import', unreal.FBXImportType.FBXIT_SKELETAL_MESH),
                            ('automated_import_should_detect_type', False), ('import_materials', False),
                            ('import_textures', False), ('import_animations', False), ('create_physics_asset', True)):
            ui.set_editor_property(prop, value)
        sd = ui.get_editor_property('skeletal_mesh_import_data')
        for prop, value in (('import_morph_targets', False),
                            ('normal_import_method', unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS),
                            ('use_t0_as_ref_pose', False), ('convert_scene', True), ('force_front_x_axis', False),
                            ('update_skeleton_reference_pose', False), ('import_meshes_in_bone_hierarchy', True)):
            sd.set_editor_property(prop, value)
        t = unreal.AssetImportTask()
        t.set_editor_property('filename', os.path.join(SRC, NAME + '.fbx'))
        t.set_editor_property('destination_path', folder)
        t.set_editor_property('destination_name', NAME)
        t.set_editor_property('replace_existing', True)
        t.set_editor_property('automated', True)
        t.set_editor_property('save', False)
        t.set_editor_property('options', ui)
        AT.import_asset_tasks([t])
        sm = unreal.load_asset('%s.%s' % (path, NAME))
    if not isinstance(sm, unreal.SkeletalMesh):
        raise RuntimeError('no skeletal mesh at ' + path + ' (see the Output Log)')
    mi = unreal.load_asset('%s/Material/MI_%s' % (ROOT, NAME))
    mats = sm.get_editor_property('materials')
    for i in range(len(mats)):
        slot = mats[i]
        slot.set_editor_property('material_interface', mi)
        mats[i] = slot
    sm.set_editor_property('materials', mats)
    EAL.save_loaded_asset(sm)
    sk = sm.get_editor_property('skeleton')
    if sk is not None:
        EAL.save_loaded_asset(sk)
    pa = sm.get_editor_property('physics_asset')
    c = unreal.SkeletalMeshComponent()
    c.set_skeletal_mesh(sm)
    bones = [str(c.get_bone_name(i)) for i in range(c.get_num_bones())]
    return {'path': path, 'skeleton': sk.get_path_name() if sk else None, 'physics_asset': pa.get_path_name() if pa else None,
            'bones': bones}


def packages():
    """the sword's project packages, for the skins' Extra Assets"""
    out = ['%s/Model/%s.%s' % (ROOT, NAME, NAME), '%s/Material/MI_%s.MI_%s' % (ROOT, NAME, NAME)]
    for suffix in PARAMS.values():
        out.append('%s/Texture/%s%s.%s%s' % (ROOT, NAME, suffix, NAME, suffix))
    sm = unreal.load_asset(out[0])
    for prop in ('skeleton', 'physics_asset'):
        a = sm.get_editor_property(prop) if sm else None
        if a is not None:
            out.append(a.get_path_name())
    return out


def skins():
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    found = []
    notes = []
    extra = packages()
    for data in reg.get_assets_by_class('EndSkeletonCompatDataObject', True):
        path = str(data.object_path)
        do = unreal.load_asset(path)
        if do is None:
            continue
        entries = list(do.get_editor_property('skins'))
        hit = [i for i, s in enumerate(entries) if str(s.get_editor_property('folder')) in SKIN_FOLDERS]
        if not hit:
            continue
        for i in hit:
            s = entries[i]
            s.set_editor_property('weapon', WEAPON)
            # (editor 1.21) the moves the skin carries: the CRISIS CORE form's pack and Crisis Core's field set (the game mod
            # 3.18.0 plays them; the field set once the forms file builds it: install_forms_1027.cmd). Only the skin on Cloud's
            # rows (the Fully Playable mods' Sephiroth): Sephiroth's own rows' skins (Seph, Winged) carry none, his own rows
            # build none of it
            if str(s.get_editor_property('folder')) == 'CrisisCoreSephiroth':
                try:
                    s.set_editor_property('pack', PACK)
                    s.set_editor_property('sets', SETS)
                except Exception:
                    notes.append('this editor has no skin Pack / Sets (editor 1.21): the CRISIS CORE skins carry no moves')
            have = [str(p.export_text()) if hasattr(p, 'export_text') else str(p) for p in s.get_editor_property('extra_assets')]
            paths = list(s.get_editor_property('extra_assets'))
            for p in extra:
                if not any(p in h for h in have):
                    paths.append(unreal.SoftObjectPath(p))
            s.set_editor_property('extra_assets', paths)
            entries[i] = s
        do.set_editor_property('skins', entries)
        EAL.save_loaded_asset(do)
        for i in hit:
            folder = str(entries[i].get_editor_property('folder'))
            started = time.time()
            try:
                r = do.build_one_skin_to(i)
            except Exception:
                found.append({'data_object': path, 'skin': folder, 'error': traceback.format_exc()[-800:]})
                continue
            # (BuildOneSkinTo(int32, FString&) -> bool: Unreal's Python gives the report alone when it returned true,
            #  None when it returned false; a tuple in some versions)
            if isinstance(r, tuple):
                ok, report = bool(r[0]), (str(r[1]) if len(r) > 1 else '')
            elif isinstance(r, str):
                ok, report = True, r
            else:
                ok, report = bool(r), ''
            found.append({'data_object': path, 'skin': folder, 'built': bool(ok), 'report': str(report)[-1500:],
                          'seconds': round(time.time() - started, 1)})
            log('skin %s: %s' % (folder, 'built' if ok else 'NOT BUILT (see the report in the result file and the Output Log)'))
    if not found:
        raise RuntimeError('no data object has the CRISIS CORE skins (%s)' % ', '.join(SKIN_FOLDERS))
    if notes:
        found.append({'notes': sorted(set(notes))})
    return found


def run(steps=('textures', 'material', 'model', 'skins')):
    results['started'] = time.strftime('%Y-%m-%d %H:%M:%S')
    for step in steps:
        log('step ' + step)
        try:
            results[step] = globals()[step]()
        except Exception:
            results[step] = {'error': traceback.format_exc()[-1500:]}
            log('step %s FAILED: %s' % (step, results[step]['error'][-300:]))
            save()
            if step != 'skins':
                break
        save()
    results['finished'] = time.strftime('%Y-%m-%d %H:%M:%S')
    save()
    log('done: ' + RESULT)
    return results


if __name__ == '__main__' or __name__ == '__rebirth_editor_link__':
    run()
