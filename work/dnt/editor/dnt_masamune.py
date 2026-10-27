"""Dissidia NT's five Masamunes in the open End editor (task #610/#660; editor link or Output Log, Cmd:
    py "C:/FF7R2UProj/Tools/Dissidia/pipeline/dnt_masamune.py"
from what Sandalphon made of them (Saved/ModExtract/dnt/swords: make_dnt_masamunes.py, Rebirth's 2.38 m length):

  1. textures  each sword's maps (dnt_tex.py's way: _C colour sRGB, _N normal map, _R roughness, _M metal, _O occlusion,
               _E emission sRGB) into /Game/Character/Weapon/WE1021_19_DissidiaNT_Masamune/Texture/<sword>; a map whose
               file is the same as one already taken (the 2p1c sword's two materials share four) is taken once;
  2. masters   M_DNT_Uber (Phase B's) and M_DNT_Uber_Emissive (dnt_uber.py: its emission map x EmissiveIntensity on
               top of the rim) for the lit panel of the 2p1c sword (PBB-EmN);
  3. materials MI_<sword>_M0k_Uber per material slot, on M_DNT_Uber (or the emissive master), its textures on Color,
               Normal, Roughness, Metallic, WideOcclusion (Emissive): Game Materials makes them (RebirthGameMaterials_P);
  4. models    <sword>.fbx as the skeletal mesh /Game/Character/Weapon/WE1021_19_DissidiaNT_Masamune/Model/<sword> (its
               own skeleton with the game's Masamune bones: Trans, C_Body_a, C_Body_End, C_TrailA_a-d, C_CharaA_a; a
               physics asset), each slot on its instance;
  5. game      the instances made with Game Materials and RebirthGameMaterials_P installed (when the game is closed).

The skins carry the swords (dnt_import.py's _skin_assets adds them to every Dissidia NT skin's Extra Assets), and the
DissidiaNTWeapons part skin their blueprints (copies of the cut-scale Masamune's, made in the cloud).
Every step saves what it made; run it again to redo what failed (made assets are kept unless DNTM_FORCE=1).
Result: Saved/ModExtract/dnt/swords/dnt_masamune_result.json (and the Output Log)."""
import hashlib
import importlib
import json
import os
import subprocess
import sys
import time
import traceback

import unreal

SAVED = os.path.normpath(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()))
SRC = os.path.join(SAVED, 'ModExtract', 'dnt', 'swords')
ROOT = '/Game/Character/Weapon/WE1021_19_DissidiaNT_Masamune'
HERE = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else r'C:\FF7R2UProj\Tools\Dissidia\pipeline'
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import dnt_uber as U    # noqa: E402

# texture suffix -> (material parameter, kind)
PARAMS = {'_C': ('Color', 'color'), '_N': ('Normal', 'normal'), '_R': ('Roughness', 'grey'), '_M': ('Metallic', 'grey'),
          '_O': ('WideOcclusion', 'grey'), '_E': ('Emissive', 'color')}
FORCE = os.environ.get('DNTM_FORCE') == '1'
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
RESULT = os.path.join(SRC, 'dnt_masamune_result.json')
results = {}


def log(text):
    unreal.log('DNT MASAMUNE: ' + text)


def save():
    with open(RESULT + '.tmp', 'w') as f:
        json.dump(results, f, indent=1, default=str)
    os.replace(RESULT + '.tmp', RESULT)


def swords():
    return json.load(open(os.path.join(SRC, 'dnt_masamunes.json'), encoding='utf-8'))


def _md5(path):
    return hashlib.md5(open(path, 'rb').read()).hexdigest()


def texture_plan():
    """{sword: {file name: (texture asset name, its png path)}}: a file the same as one taken before is that texture"""
    plan = {}
    for s in swords():
        name = s['name']
        seen, files = {}, {}
        for slot in s['slots']:
            for suffix, fname in sorted(slot['textures'].items()):
                path = os.path.join(SRC, name, 'textures', fname)
                h = _md5(path)
                if h not in seen:
                    seen[h] = (os.path.splitext(fname)[0], path)
                files[fname] = seen[h]
        plan[name] = files
    return plan


def textures():
    done = {}
    for sword, files in texture_plan().items():
        folder = '%s/Texture/%s' % (ROOT, sword)
        unique = sorted(set(files.values()))
        tasks = []
        for asset, path in unique:
            if not FORCE and EAL.does_asset_exist('%s/%s' % (folder, asset)):
                continue
            t = unreal.AssetImportTask()
            t.set_editor_property('filename', path)
            t.set_editor_property('destination_path', folder)
            t.set_editor_property('destination_name', asset)
            t.set_editor_property('replace_existing', True)
            t.set_editor_property('automated', True)
            t.set_editor_property('save', False)
            tasks.append(t)
        if tasks:
            AT.import_asset_tasks(tasks)
        for asset, path in unique:
            tex = unreal.load_asset('%s/%s.%s' % (folder, asset, asset))
            if tex is None:
                raise RuntimeError('the texture %s did not import' % asset)
            kind = PARAMS[asset[-2:]][1]
            if kind == 'color':
                tex.set_editor_property('srgb', True)
                tex.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_DEFAULT)
            elif kind == 'normal':
                tex.set_editor_property('srgb', False)
                tex.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP)
                tex.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_WORLD_NORMAL_MAP)
            else:
                tex.set_editor_property('srgb', False)
                tex.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_ALPHA)
            EAL.save_loaded_asset(tex)
            done.setdefault(sword, []).append(asset)
    return done


def masters():
    importlib.reload(U)
    U.results.clear()
    have = {n: EAL.does_asset_exist('%s/%s' % (U.MASTERS, n)) for n in (U.OPAQUE, U.EMISSIVE)}
    make = [n for n in (U.OPAQUE, U.EMISSIVE) if FORCE or not have[n]]
    if U.OPAQUE in make and have[U.OPAQUE]:
        make.remove(U.OPAQUE)       # (Phase B's master, its cloth instances on it: left as it is)
    if make:
        U.masters(make)
    out = U.results.get('masters') or {}
    for n, r in out.items():
        if 'error' in r:
            raise RuntimeError('%s: %s' % (n, r['error'][-600:]))
    return {'existed': have, 'made': out}


def mi_name(sword, slot):
    return 'MI_%s_M%02d_Uber' % (sword, slot['material'])


def materials():
    plan = texture_plan()
    out = {}
    for s in swords():
        sword = s['name']
        folder = '%s/Material' % ROOT
        for slot in s['slots']:
            emissive = '_E' in slot['textures']
            parent = unreal.load_asset('%s/%s' % (U.MASTERS, U.EMISSIVE if emissive else U.OPAQUE))
            if parent is None:
                raise RuntimeError('no master for ' + slot['slot'])
            name = mi_name(sword, slot)
            path = '%s/%s' % (folder, name)
            mi = unreal.load_asset(path) if EAL.does_asset_exist(path) else None
            if mi is None:
                mi = AT.create_asset(name, folder, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
            MEL.set_material_instance_parent(mi, parent)
            ok, bad = [], []
            for suffix, fname in sorted(slot['textures'].items()):
                param = PARAMS[suffix][0]
                asset = plan[sword][fname][0]
                tex = unreal.load_asset('%s/Texture/%s/%s.%s' % (ROOT, sword, asset, asset))
                got = None
                if tex is not None:
                    MEL.set_material_instance_texture_parameter_value(mi, param, tex)
                    got = MEL.get_material_instance_texture_parameter_value(mi, param)
                (ok if got is not None and got.get_path_name() == tex.get_path_name() else bad).append(param)
            MEL.update_material_instance(mi)
            EAL.save_loaded_asset(mi)
            out[name] = {'parent': parent.get_name(), 'set': ok, 'not_set': bad}
            if bad:
                raise RuntimeError('%s: textures not set: %s' % (name, bad))
    return out


def models():
    out = {}
    for s in swords():
        sword = s['name']
        folder = ROOT + '/Model'
        path = '%s/%s' % (folder, sword)
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
            t.set_editor_property('filename', os.path.join(SRC, sword, sword + '.fbx'))
            t.set_editor_property('destination_path', folder)
            t.set_editor_property('destination_name', sword)
            t.set_editor_property('replace_existing', True)
            t.set_editor_property('automated', True)
            t.set_editor_property('save', False)
            t.set_editor_property('options', ui)
            AT.import_asset_tasks([t])
            sm = unreal.load_asset('%s.%s' % (path, sword))
        if not isinstance(sm, unreal.SkeletalMesh):
            raise RuntimeError('no skeletal mesh at ' + path + ' (see the Output Log)')
        by_slot = {slot['slot']: slot for slot in s['slots']}
        mats = sm.get_editor_property('materials')
        worn = []
        for i in range(len(mats)):
            m = mats[i]
            slot_name = str(m.get_editor_property('material_slot_name'))
            slot = by_slot.get(slot_name) or (s['slots'][i] if i < len(s['slots']) else None)
            if slot is None:
                raise RuntimeError('%s: slot %d (%s) is none of %s' % (sword, i, slot_name, sorted(by_slot)))
            mi = unreal.load_asset('%s/Material/%s' % (ROOT, mi_name(sword, slot)))
            m.set_editor_property('material_interface', mi)
            mats[i] = m
            worn.append((slot_name, mi.get_name() if mi else None))
        sm.set_editor_property('materials', mats)
        EAL.save_loaded_asset(sm)
        sk = sm.get_editor_property('skeleton')
        if sk is not None:
            EAL.save_loaded_asset(sk)
        pa = sm.get_editor_property('physics_asset')
        if pa is not None:
            EAL.save_loaded_asset(pa)
        c = unreal.SkeletalMeshComponent()
        c.set_skeletal_mesh(sm)
        out[sword] = {'path': path, 'skeleton': sk.get_path_name() if sk else None,
                      'physics_asset': pa.get_path_name() if pa else None, 'slots': worn,
                      'bones': [str(c.get_bone_name(i)) for i in range(c.get_num_bones())]}
    return out


def instances():
    return ['%s/Material/%s.%s' % (ROOT, mi_name(s['name'], slot), mi_name(s['name'], slot)) for s in swords() for slot in s['slots']]


def packages():
    """the swords' packages the skins cook (Extra Assets): each model, its skeleton and physics asset (their instances and
    textures go into the game with Game Materials)"""
    out = []
    for s in swords():
        p = '%s/Model/%s.%s' % (ROOT, s['name'], s['name'])
        sm = unreal.load_asset(p)
        if sm is None:
            continue
        out.append(p)
        for prop in ('skeleton', 'physics_asset'):
            a = sm.get_editor_property(prop)
            if a is not None:
                out.append(a.get_path_name())
    return out


def game_running():
    return [e for e in ('ff7rebirth_.exe', 'ff7rebirth.exe')
            if e in subprocess.run(['tasklist', '/FI', 'IMAGENAME eq ' + e, '/NH'], capture_output=True, text=True,
                                   creationflags=0x08000000).stdout.lower()]


def game():
    import rebirth_fx.gamematerials as gm
    running = game_running()
    rep = gm.make(instances(), install=not running, quiet=True) or {}
    if rep.get('failed'):
        raise RuntimeError('Game Materials: %s' % rep['failed'])
    return {'running': running, 'made': rep.get('made'), 'installed': rep.get('installed'), 'error': rep.get('error')}


def run(steps=('textures', 'masters', 'materials', 'models', 'game')):
    results['started'] = time.strftime('%Y-%m-%d %H:%M:%S')
    for step in steps:
        log('step ' + step)
        try:
            results[step] = globals()[step]()
        except Exception:
            results[step] = {'error': traceback.format_exc()[-1500:]}
            log('step %s FAILED: %s' % (step, results[step]['error'][-300:]))
            save()
            break
        save()
    results['finished'] = time.strftime('%Y-%m-%d %H:%M:%S')
    save()
    log('done: ' + RESULT)
    return results


if __name__ == '__main__':
    run()
