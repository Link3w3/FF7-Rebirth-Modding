"""Dissidia NT Sephiroth into the End project, in the open editor (Output Log, Cmd: py "C:/FF7R2UProj/Tools/Dissidia/pipeline/dnt_import.py"),
from what Sandalphon made of the game's files (Saved/ModExtract/dnt):

  1. textures  every outfit's textures (textures/<outfit>/*.png, made by dnt_tex.py from its G1T) into
               /Game/Character/Player/PC0010_19_DissidiaNT_Sephiroth/Texture/<outfit>: _C colour (sRGB), _N normal map,
               _R roughness, _M metal, _O occlusion, _A alpha as Rebirth's grey maps (TC_Alpha, BC4, not sRGB);
  2. materials one material instance per material slot (models/<model>_mats.json): on Rebirth Sephiroth's own
               (PC0010_00_BodyA cloth, BodyB cloth with cut-outs, Hair, Head, Skin, Eye), his textures on its parameters;
  3. models    the nine outfits (models/<model>.fbx: his model on Rebirth Sephiroth's bones and face rig) as skeletal
               meshes in .../Model, one skeleton per body (1p, 2p, 3p), their slots' materials, PC0010_10's physics asset;
  4. skins     DO_DissidiaNTSkins (/Game/RebirthSkelCompat/DissidiaNT): eighteen skins, each outfit twice (Cloud's rows
               for the Fully Playable mods, and Sephiroth's own rows), on the PC0010_00 family; Build Skins builds them
               and puts them in the game (close the game first) - its SKINS page lists them;
  5. kawaii    DissidiaNTSephirothKawaii.json (their KawaiiPhysics) into the game's compat folder (the old one, if there
               is one, into the game's _mod_backups\\ue4ss first).

Every step saves what it made; run it again to redo what failed (made textures and assets are kept unless DNT_FORCE=1).
Result: Saved/ModExtract/dnt/dnt_import_result.json (and the Output Log). Steps one by one from Python:
    import dnt_import as d; d.run(steps=['textures'])     (steps: textures, materials, models, skins, kawaii)"""
import json
import os
import shutil
import sys
import time
import traceback

import unreal

SAVED = os.path.normpath(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()))
SRC = os.path.join(SAVED, 'ModExtract', 'dnt')
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = '/Game/Character/Player/PC0010_19_DissidiaNT_Sephiroth'
DO_PATH = '/Game/RebirthSkelCompat/DissidiaNT'
DO_NAME = 'DO_DissidiaNTSkins'
GAME = r'C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY VII REBIRTH'
COMPAT = os.path.join(GAME, 'End', 'Binaries', 'Win64', 'ue4ss', 'Mods', 'RebirthSkelCompat', 'compat')
PHYSICS = '/Game/Character/Player/PC0010_10_Sephiroth_Transform/Model/PC0010_10_PhysicsAsset.PC0010_10_PhysicsAsset'
FAMILY = '/Game/Character/Player/PC0010_00_Sephiroth_Standard/Model/PC0010_00_Skeleton.PC0010_00_Skeleton'
BODY_A = '/Game/Character/Player/PC0010_00_Sephiroth_Standard/Material/PC0010_00_BodyA'
CLOUD_ROWS = ['PC0000_00_Cloud_Standard', 'PC0000_08_Cloud_SoldierNoHelmet', 'PC0000_09_Cloud_CostaClothing',
              'PC0000_10_Cloud_CostaClothing2', 'PC0000_04_Cloud_ZackCostume', 'PC0000_12_Cloud_ZackCostumeDirty',
              'PC0000_18_Cloud_ZackCostumeAge21', 'PC0000_19_Cloud_ZackCostumeDirtyAge21', 'PC0000_23_Cloud_ZackCostumeWet']
SEPH_ROWS = ['PC0010_00_Sephiroth_Standard', 'PC0010_10_Sephiroth_Transform']
OUTFITS = ['1p1c', '1p2c', '1p3c', '2p1c', '2p2c', '2p3c', '3p1c', '3p2c', '3p3c']
NAMES = {'1p': 'Dissidia NT Sephiroth', '2p': 'Dissidia NT One-Winged Angel', '3p': 'Dissidia NT Safer Sephiroth'}
COLOURS = {'1c': '', '2c': ' (colour 2)', '3c': ' (colour 3)'}
DESCRIPTION = {
    '1p': 'DISSIDIA FINAL FANTASY NT\'s Sephiroth (his default appearance) from the game\'s own files: his model on Rebirth Sephiroth\'s bones (the PC0010_00 family) with Rebirth\'s face rig, KawaiiPhysics hair, coat, belts and tassel.',
    '2p': 'DISSIDIA FINAL FANTASY NT\'s Sephiroth, his One-Winged Angel appearance (the black wing, the torn coat) from the game\'s own files: on Rebirth Sephiroth\'s bones (the PC0010_00 family) with Rebirth\'s face rig, KawaiiPhysics hair, coat and feathers.',
    '3p': 'DISSIDIA FINAL FANTASY NT\'s Safer Sephiroth appearance from the game\'s own files: on Rebirth Sephiroth\'s bones (the PC0010_00 family) with Rebirth\'s face rig, KawaiiPhysics hair, coat and wings.',
}
# cloth materials whose albedo alpha cuts holes where the mesh uses it (the rest of the cloth is opaque)
MASKED_CLOTH = {'2p': [3]}
# the moves the skins on Cloud's rows carry: the DISSIDIA NT form's pack (Battle12), from the moment the character comes in
# wearing one (game mod 3.18.2: 3.18.0 - 3.18.1 played the character's own moves until another form was picked)
PACK = 'Battle12'
FORCE = os.environ.get('DNT_FORCE') == '1'
# the textures to import: textures_v2 (dnt_tex_v2.py, 10-27: Unreal's normal frame, roughness from Dissidia NT's gloss,
# metal colour) when it is there, else the first conversion's textures (DNT_TEXTURES names another folder)
TEXTURES = os.environ.get('DNT_TEXTURES') or ('textures_v2' if os.path.isdir(os.path.join(SRC, 'textures_v2')) else 'textures')

EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
RESULT = os.path.join(SRC, 'dnt_import_result.json')
results = {}


def log(text):
    unreal.log('DNT IMPORT ' + text)


def save():
    tmp = RESULT + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=1, default=str)
    os.replace(tmp, RESULT)


def model_name(o):
    return 'PC0010_19_DNT_' + o


def spec_of(o):
    return json.load(open(os.path.join(SRC, 'models', model_name(o) + '_mats.json'), encoding='utf-8'))


# ---------------------------------------------------------------------------------------------------------------------
def textures(outfits=OUTFITS):
    out = results.setdefault('textures', {})
    for o in outfits:
        folder = '%s/Texture/%s' % (ROOT, o)
        src = os.path.join(SRC, TEXTURES, o)
        files = sorted(f for f in os.listdir(src) if f.lower().endswith('.png')) if os.path.isdir(src) else []
        if not files:
            out[o] = {'error': 'no textures in ' + src + ' (run the texture step of the .cmd first)'}
            continue
        tasks = []
        for f in files:
            name = f[:-4]
            if not FORCE and EAL.does_asset_exist('%s/%s' % (folder, name)):
                continue
            t = unreal.AssetImportTask()
            t.set_editor_property('filename', os.path.join(src, f))
            t.set_editor_property('destination_path', folder)
            t.set_editor_property('destination_name', name)
            t.set_editor_property('replace_existing', True)
            t.set_editor_property('automated', True)
            t.set_editor_property('save', False)
            tasks.append(t)
        if tasks:
            AT.import_asset_tasks(tasks)
        done, failed = 0, []
        for f in files:
            name = f[:-4]
            tex = unreal.load_asset('%s/%s.%s' % (folder, name, name))
            if tex is None:
                failed.append(name)
                continue
            suffix = name.rsplit('_', 1)[-1]
            try:
                if suffix == 'C':
                    tex.set_editor_property('srgb', True)
                    tex.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_DEFAULT)
                elif suffix == 'N':
                    tex.set_editor_property('srgb', False)
                    tex.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP)
                    tex.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_WORLD_NORMAL_MAP)
                else:
                    tex.set_editor_property('srgb', False)
                    tex.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_ALPHA)
                EAL.save_loaded_asset(tex)
                done += 1
            except Exception:
                failed.append(name + ': ' + traceback.format_exc()[-300:])
        out[o] = {'textures': done, 'failed': failed}
        log('textures %s: %d (%d failed)' % (o, done, len(failed)))
        save()


# ---------------------------------------------------------------------------------------------------------------------
def materials(outfits=OUTFITS):
    out = results.setdefault('materials', {})
    factory = unreal.MaterialInstanceConstantFactoryNew()
    for o in outfits:
        spec = spec_of(o)
        folder = '%s/Material/%s' % (ROOT, o)
        made = {}
        for s in spec['slots']:
            name = 'MI_PC0010_19_%s_%s' % (o, s['slot'])
            path = '%s/%s' % (folder, name)
            try:
                masked = s['role'] == 'Cloth' and s['material'] in MASKED_CLOTH.get(o[:2], [])
                parent_path = s['parent'] if (s['role'] != 'Cloth' or masked) else BODY_A
                parent = unreal.load_asset(parent_path)
                if parent is None:
                    made[s['slot']] = {'error': 'no parent ' + parent_path}
                    continue
                mi = unreal.load_asset(path) if EAL.does_asset_exist(path) else None
                if mi is None:
                    mi = AT.create_asset(name, folder, unreal.MaterialInstanceConstant, factory)
                MEL.set_material_instance_parent(mi, parent)
                set_ok, set_failed = [], []
                for param, tex_name in s['textures'].items():
                    if param == 'Coverage' and s['role'] == 'Cloth' and not masked:
                        continue
                    tex = unreal.load_asset('%s/Texture/%s/%s.%s' % (ROOT, o, tex_name, tex_name))
                    if tex is None:
                        set_failed.append('%s (no texture %s)' % (param, tex_name))
                        continue
                    MEL.set_material_instance_texture_parameter_value(mi, param, tex)
                    # (the call says False on an instance of a game material, whose parameters the editor's stand-in
                    # does not list, yet the instance holds the texture: what it holds is what counts)
                    got = MEL.get_material_instance_texture_parameter_value(mi, param)
                    ok = got is not None and got.get_path_name() == tex.get_path_name()
                    (set_ok if ok else set_failed).append(param)
                MEL.update_material_instance(mi)
                EAL.save_loaded_asset(mi)
                made[s['slot']] = {'path': path, 'parent': parent_path.rsplit('/', 1)[1], 'set': set_ok,
                                   'not_set': set_failed}
            except Exception:
                made[s['slot']] = {'error': traceback.format_exc()[-600:]}
        out[o] = made
        log('materials %s: %d' % (o, len(made)))
        save()


# ---------------------------------------------------------------------------------------------------------------------
def _mesh_options(skeleton):
    ui = unreal.FbxImportUI()
    for prop, value in (('import_mesh', True), ('import_as_skeletal', True),
                        ('mesh_type_to_import', unreal.FBXImportType.FBXIT_SKELETAL_MESH),
                        ('automated_import_should_detect_type', False), ('import_materials', False),
                        ('import_textures', False), ('import_animations', False), ('create_physics_asset', False)):
        ui.set_editor_property(prop, value)
    if skeleton is not None:
        ui.set_editor_property('skeleton', skeleton)
    sd = ui.get_editor_property('skeletal_mesh_import_data')
    for prop, value in (('import_morph_targets', False),
                        ('normal_import_method', unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS),
                        ('use_t0_as_ref_pose', False), ('convert_scene', True), ('force_front_x_axis', False),
                        ('update_skeleton_reference_pose', False), ('import_meshes_in_bone_hierarchy', True)):
        sd.set_editor_property(prop, value)
    return ui


def models(outfits=OUTFITS):
    out = results.setdefault('models', {})
    sub = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
    folder = '%s/Model' % ROOT
    skeletons = {}
    for o in outfits:
        name = model_name(o)
        path = '%s/%s' % (folder, name)
        try:
            body = o[:2]
            if body not in skeletons:
                first = model_name(body + '1c')
                sk_path = '%s/%s_Skeleton' % (folder, first)
                skeletons[body] = unreal.load_asset(sk_path) if EAL.does_asset_exist(sk_path) else None
            if EAL.does_asset_exist(path):
                if not FORCE:
                    out[o] = {'path': path, 'kept': 'there already (DNT_FORCE=1 imports it again)'}
                    sm = unreal.load_asset(path)
                    if skeletons.get(o[:2]) is None and sm is not None:
                        skeletons[o[:2]] = sm.get_editor_property('skeleton')
                    continue
                sub.close_all_editors_for_asset(unreal.load_asset(path))
            fbx = os.path.join(SRC, 'models', name + '.fbx')
            t = unreal.AssetImportTask()
            t.set_editor_property('filename', fbx)
            t.set_editor_property('destination_path', folder)
            t.set_editor_property('destination_name', name)
            t.set_editor_property('replace_existing', True)
            t.set_editor_property('automated', True)
            t.set_editor_property('save', False)
            t.set_editor_property('options', _mesh_options(skeletons.get(body)))
            started = time.time()
            AT.import_asset_tasks([t])
            sm = unreal.load_asset('%s.%s' % (path, name))
            if not isinstance(sm, unreal.SkeletalMesh):
                raise RuntimeError('the import made no skeletal mesh at %s (see the Output Log)' % path)
            sk = sm.get_editor_property('skeleton')
            if skeletons.get(body) is None:
                skeletons[body] = sk
            mats = sm.get_editor_property('materials')
            assigned, missing = [], []
            for i in range(len(mats)):
                slot = mats[i]
                sname = str(slot.get_editor_property('material_slot_name'))
                mpath = '%s/Material/%s/MI_PC0010_19_%s_%s' % (ROOT, o, o, sname)
                mi = unreal.load_asset(mpath) if EAL.does_asset_exist(mpath) else None
                if mi is None:
                    missing.append(sname)
                    continue
                slot.set_editor_property('material_interface', mi)
                mats[i] = slot
                assigned.append(sname)
            sm.set_editor_property('materials', mats)
            pa = unreal.load_asset(PHYSICS)
            if pa is not None:
                sm.set_editor_property('physics_asset', pa)
            EAL.save_loaded_asset(sm)
            if sk is not None:
                EAL.save_loaded_asset(sk)
            c = unreal.SkeletalMeshComponent()
            c.set_skeletal_mesh(sm)
            out[o] = {'path': path, 'skeleton': sk.get_path_name() if sk else None, 'bones': c.get_num_bones(),
                      'materials': assigned, 'materials_missing': missing, 'seconds': round(time.time() - started, 1)}
        except Exception:
            out[o] = {'error': traceback.format_exc()[-1500:]}
        log('model %s: %s' % (o, json.dumps(out[o])[:300]))
        save()


# ---------------------------------------------------------------------------------------------------------------------
def build_result(r):
    """(ok, report) of BuildSkinsTo / BuildOneSkinTo (bool with an FString& out): Unreal's Python gives the report
    alone when the call returned true and None when it returned false (a tuple in some versions)"""
    if isinstance(r, tuple):
        return bool(r[0]), str(r[1]) if len(r) > 1 else ''
    if isinstance(r, str):
        return True, r
    return bool(r), ''


def _data_object():
    path = '%s/%s' % (DO_PATH, DO_NAME)
    if EAL.does_asset_exist(path):
        return unreal.load_asset(path)
    factory = unreal.DataAssetFactory()
    factory.set_editor_property('data_asset_class', unreal.EndSkeletonCompatDataObject)
    return AT.create_asset(DO_NAME, DO_PATH, unreal.EndSkeletonCompatDataObject, factory)


# (10-27, the Masamunes) Dissidia NT's swords (dnt_masamune.py): every Dissidia NT skin carries them (Cloud's weapon
# packs in the Fully Playable Young Sephiroth's data name their blueprints, the DissidiaNTWeapons part skin's), so they
# are in the game with the skins; their instances and textures come from Game Materials
SWORDS_ROOT = '/Game/Character/Weapon/WE1021_19_DissidiaNT_Masamune'
SWORDS = ['WE001021_19_00', 'WE001021_19_02', 'WE001021_19_03', 'WE001021_19_04', 'WE001021_19_05']


def _sword_assets():
    out = []
    for n in SWORDS:
        p = '%s/Model/%s' % (SWORDS_ROOT, n)
        if not EAL.does_asset_exist(p):
            continue
        sm = unreal.load_asset(p)
        if sm is None:
            continue
        out.append(sm.get_path_name())
        for prop in ('skeleton', 'physics_asset'):
            a = sm.get_editor_property(prop)
            if a is not None:
                out.append(a.get_path_name())
    return out


def _skin_assets(sm):
    """the model's material instances of this project and their textures: the skin's Extra Assets (the skin build cooks
    only the model, its skeleton and physics asset and what Extra Assets lists: 10-27, the skins went in with no
    materials or textures without them); and Dissidia NT's swords (_sword_assets)"""
    paths = []
    for slot in sm.get_editor_property('materials'):
        mi = slot.get_editor_property('material_interface')
        if mi is None or not mi.get_path_name().startswith(ROOT + '/'):
            continue
        # (dnt_uber.py's _Uber instances come from Game Materials, RebirthGameMaterials_P, with their textures: not the
        #  skin's)
        if mi.get_name().endswith('_Uber'):
            continue
        if mi.get_path_name() not in paths:
            paths.append(mi.get_path_name())
        for tpv in mi.get_editor_property('texture_parameter_values'):
            t = tpv.get_editor_property('parameter_value')
            if t is not None and t.get_path_name().startswith(ROOT + '/') and t.get_path_name() not in paths:
                paths.append(t.get_path_name())
    return paths + [p for p in _sword_assets() if p not in paths]


def skins(outfits=OUTFITS, build=True):
    out = results['skins'] = {}   # (made anew every run: all eighteen skins are set and built again)
    try:
        do = _data_object()
        family = unreal.load_asset(FAMILY)
        entries = []
        for o in outfits:
            sm = unreal.load_asset('%s/Model/%s' % (ROOT, model_name(o)))
            if sm is None:
                out[o] = {'error': 'no model (the models step)'}
                continue
            assets = _skin_assets(sm)
            out[o] = {'extra_assets': len(assets)}
            for rows, tag, extra in ((CLOUD_ROWS, '', 'Cloud\'s rows (the Fully Playable mods\' Sephiroth)'),
                                     (SEPH_ROWS, 'Seph', 'Sephiroth\'s own rows')):
                s = unreal.EndCharacterSkin()
                s.set_editor_property('enabled', True)
                s.set_editor_property('name', NAMES[o[:2]] + COLOURS[o[2:]])
                s.set_editor_property('folder', 'DissidiaNT%s%s' % (o, tag))
                s.set_editor_property('model', sm)
                s.set_editor_property('characters', rows)
                s.set_editor_property('family', family)
                s.set_editor_property('keep_proportions', False)
                s.set_editor_property('voice', 'own' if not tag else '')
                s.set_editor_property('worn_at_once', False)
                s.set_editor_property('author', '')
                s.set_editor_property('description', DESCRIPTION[o[:2]] + ' (' + extra + ')')
                s.set_editor_property('extra_assets', [unreal.SoftObjectPath(p) for p in assets])
                if not tag:
                    # (editor 1.21) the moves the skin carries in the normal form and each form with no pack of its own: PACK
                    try:
                        s.set_editor_property('pack', PACK)
                    except Exception:
                        out.setdefault('notes', []).append('this editor has no skin Pack (editor 1.21): the skins carry no moves')
                entries.append(s)
        do.set_editor_property('skins', entries)
        do.set_editor_property('install_skins', True)
        gd = unreal.DirectoryPath()
        gd.set_editor_property('path', GAME)
        do.set_editor_property('game_directory', gd)
        EAL.save_loaded_asset(do)
        out['data_object'] = do.get_path_name()
        out['entries'] = len(entries)
        save()
        # (the registry up to date with what the steps before made)
        reg = unreal.AssetRegistryHelpers.get_asset_registry()
        reg.scan_paths_synchronous([ROOT], True)
        if build:
            started = time.time()
            r = do.build_skins_to()
            ok, report = build_result(r)
            out['built'] = {'ok': bool(ok), 'seconds': round(time.time() - started, 1), 'report': str(report)[-6000:]}
            # each built skin's packages: a skin with no material instance went in without its materials
            thin = []
            for o in outfits:
                for tag in ('', 'Seph'):
                    sj = os.path.join(COMPAT, '..', 'skins', 'DissidiaNT%s%s' % (o, tag), 'skin.json')
                    try:
                        pk = json.load(open(sj, encoding='utf-8')).get('packages', [])
                        names = [p if isinstance(p, str) else p.get('file', '') for p in pk]
                        if not any('/Material/' in n for n in names):
                            thin.append('DissidiaNT%s%s (%d packages)' % (o, tag, len(names)))
                    except Exception as e:
                        thin.append('DissidiaNT%s%s: %s' % (o, tag, e))
            if thin:
                out['built']['ok'] = False
                out['built']['no_materials'] = thin
            save()
            log('skins built: %s' % ('ok' if out['built']['ok'] else 'FAILED (see the result file)'))
    except Exception:
        out['error'] = traceback.format_exc()[-1500:]
    save()


# ---------------------------------------------------------------------------------------------------------------------
def kawaii():
    out = results['kawaii'] = {}
    try:
        src = os.path.join(SRC, 'DissidiaNTSephirothKawaii.json')
        dst = os.path.join(COMPAT, 'DissidiaNTSephirothKawaii.json')
        if not os.path.isdir(COMPAT):
            out['error'] = 'no compat folder ' + COMPAT
            return
        if os.path.isfile(dst):
            b = os.path.join(GAME, '_mod_backups', 'ue4ss', 'DissidiaNTKawaii_' + time.strftime('%Y%m%d_%H%M%S'))
            os.makedirs(b, exist_ok=True)
            shutil.copy2(dst, b)
            out['backup'] = b
        shutil.copyfile(src, dst + '.tmp')
        os.replace(dst + '.tmp', dst)
        out['installed'] = dst
    except Exception:
        out['error'] = traceback.format_exc()[-800:]
    save()


STEPS = ['textures', 'materials', 'models', 'skins', 'kawaii']


def run(steps=None):
    global results
    try:
        results = json.load(open(RESULT, encoding='utf-8'))
    except Exception:
        results = {}
    results['started'] = time.strftime('%Y-%m-%d %H:%M:%S')
    results['errors'] = []   # (this run's: what earlier runs made stays in the steps' own records)
    for step in steps or STEPS:
        log('step ' + step)
        try:
            globals()[step]()
        except Exception:
            results.setdefault('errors', []).append('%s: %s' % (step, traceback.format_exc()[-800:]))
        save()
    results['finished'] = time.strftime('%Y-%m-%d %H:%M:%S')
    save()
    log('done: ' + RESULT)
    return results


if __name__ == '__main__' or __name__ == '__rebirth_editor_link__':
    run()
