# FF7 Remake characters and weapons in the End editor, from a job file (remake_<who>_job.json) made from the game's own files:
#   textures   the character's textures (PNG made from the game's), at the game's paths, with the game's texture settings
#   instances  its material instances on the rebuilt Remake masters' renderer instances (import_remake_mis.py made those)
#   models     its models (FBX made by skm_fbx.py: LOD 0, the root resting flat), its instances on their slots, and the
#              sockets of the game's skeleton (on the imported skeleton) and of the model (on it): a weapon's
#              Attach_Chara01, Body_Center01, ... (needs the Create a Character System editor plugin 1.16:
#              RebirthRemakeImportLibrary.AddSockets; without it the result says the sockets were not added)
#   bonamik    its Bonamik (the game's file) converted to Rebirth's and put on its model's Bonamik Data List
# Safe in the open editor (each step saves what it makes). From the Output Log (Cmd):
#   py "C:/FF7R2UProj/Tools/RemakeMaterials/remake_character.py" "C:/FF7R2UProj/Tools/RemakeMaterials/remake_cloud_job.json"
# or step by step from Python: import remake_character as rc; rc.run(job_path, steps=['textures'])
# Results: Saved\RemakeMaterials\<job name>_result.json
import importlib
import json
import os
import sys
import time
import traceback
import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(SAVED, 'RemakeMaterials')
MODELS = os.path.join(HERE, '_build', 'remake_models')
BONAMIK = os.path.join(SAVED, 'RemakeBonamik')
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
STEPS = ['textures', 'instances', 'models', 'bonamik']


def _enum(cls_name, name):
    import re
    cls = getattr(unreal, cls_name)
    name = name.split('::')[-1]
    for cand in (name, re.sub(r'(?<=[a-z0-9])(?=[A-Z])', '_', name).upper(), name.upper()):
        if hasattr(cls, cand):
            return getattr(cls, cand)
    flat = name.replace('_', '').upper()
    for k in dir(cls):
        if k.replace('_', '').upper() == flat:
            return getattr(cls, k)
    raise KeyError('%s.%s' % (cls_name, name))


class Job(object):
    def __init__(self, path):
        self.path = path
        self.spec = json.load(open(path))
        self.name = self.spec['name']
        mis = self.spec.get('mis')
        self.mis = json.load(open(os.path.join(HERE, mis))) if mis else {'textures': [], 'character': []}
        os.makedirs(OUT, exist_ok=True)
        self.result_path = os.path.join(OUT, self.name.replace(' ', '_') + '_result.json')
        try:
            self.results = json.load(open(self.result_path))
        except Exception:
            self.results = {}
        self.results.setdefault('warnings', [])

    def save(self):
        json.dump(self.results, open(self.result_path, 'w'), indent=1)

    def warn(self, text):
        self.results['warnings'].append(text)
        unreal.log_warning('REMAKECHAR ' + text)

    def setp(self, obj, prop, value):
        try:
            obj.set_editor_property(prop, value)
            return True
        except Exception as ex:
            self.warn('could not set %s.%s: %s' % (obj.get_name(), prop, ex))
            return False


def _import_file(path, folder, name, options=None):
    task = unreal.AssetImportTask()
    task.set_editor_property('filename', path)
    task.set_editor_property('destination_path', folder)
    task.set_editor_property('destination_name', name)
    task.set_editor_property('replace_existing', True)
    task.set_editor_property('automated', True)
    task.set_editor_property('save', False)
    if options is not None:
        task.set_editor_property('options', options)
    AT.import_asset_tasks([task])
    return unreal.load_asset('%s/%s.%s' % (folder, name, name))


def textures(job, start=0, count=None):
    done = job.results.setdefault('textures', {})
    items = job.mis['textures'][start:None if count is None else start + count]
    for t in items:
        try:
            if not os.path.exists(t['png']):
                raise RuntimeError('missing ' + t['png'])
            tex = _import_file(t['png'], t['folder'], t['name'])
            if tex is None:
                raise RuntimeError('did not import')
            job.setp(tex, 'srgb', bool(t['srgb']))
            for key, prop, enum in (('compression', 'compression_settings', 'TextureCompressionSettings'), ('lod_group', 'lod_group', 'TextureGroup'),
                                    ('filter', 'filter', 'TextureFilter'), ('address_x', 'address_x', 'TextureAddress'),
                                    ('address_y', 'address_y', 'TextureAddress')):
                if t.get(key):
                    try:
                        job.setp(tex, prop, _enum(enum, t[key]))
                    except KeyError:
                        job.warn('%s: this engine has no %s %s' % (t['name'], enum, t[key]))
            EAL.save_loaded_asset(tex)
            done[t['name']] = '%s %dx%d' % (t['format'], t['size'][0], t['size'][1])
        except Exception:
            done[t['name']] = 'FAILED: ' + traceback.format_exc()[-600:]
        job.save()
    return '%d of %d textures imported' % (sum(1 for v in done.values() if not v.startswith('FAILED')), len(job.mis['textures']))


def _diagnose(material):
    lib = getattr(unreal, 'RebirthMaterialDiagnosticsLibrary', None)
    if lib is None:
        return {'ok': None, 'errors': ['no RebirthMaterialDiagnosticsLibrary']}
    try:
        d = json.loads(lib.get_material_diagnostics(material, True))
    except Exception as ex:
        return {'ok': False, 'errors': [str(ex)]}
    errors, ok = [], True
    for key in ('resources', 'material_resources'):
        for r in d.get(key, []) or []:
            errors += r.get('compile_errors', []) or []
            if r.get('has_shader_map') and not r.get('compiled_successfully', True):
                ok = False
    return {'ok': ok and not errors, 'errors': sorted(set(errors))[:12]}


def instances(job, compile_check=True):
    done = job.results.setdefault('instances', {})
    for p in sorted(set(i['parent'] for i in job.mis['character'])):
        if not EAL.does_asset_exist(p):
            raise RuntimeError('no %s: import the Remake renderer instances first (run_import_remake_mis.cmd)' % p)
    for item in job.mis['character']:
        try:
            parent = unreal.load_asset(item['parent'])
            folder, name = item['path'].rsplit('/', 1)
            new = not EAL.does_asset_exist(item['path'])
            mi = AT.create_asset(name, folder, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew()) if new else unreal.load_asset(item['path'])
            if not isinstance(mi, unreal.MaterialInstanceConstant):
                raise RuntimeError('%s is not a material instance' % item['path'])
            if not new:
                MEL.clear_all_material_instance_parameters(mi)
            MEL.set_material_instance_parent(mi, parent)
            notes = []
            for n, v in item['scalars']:
                MEL.set_material_instance_scalar_parameter_value(mi, n, float(v))
            for n, v in item['vectors']:
                MEL.set_material_instance_vector_parameter_value(mi, n, unreal.LinearColor(*v))
            for n, p in item['textures']:
                t = unreal.load_asset(p) if EAL.does_asset_exist(p) else None
                if t is None:
                    notes.append('texture %s: no %s' % (n, p))
                    continue
                MEL.set_material_instance_texture_parameter_value(mi, n, t)
                got = MEL.get_material_instance_texture_parameter_value(mi, n)
                if got is None or got.get_path_name() != t.get_path_name():
                    notes.append('texture %s: the instance holds %s' % (n, got.get_path_name() if got else None))
            MEL.update_material_instance(mi)
            EAL.save_loaded_asset(mi)
            out = {'made': 'made' if new else 'remade'}
            if notes:
                out['notes'] = notes
            if compile_check:
                out['compile'] = _diagnose(mi)
            done[item['name']] = out
        except Exception:
            done[item['name']] = {'made': 'FAILED', 'error': traceback.format_exc()[-1200:]}
        job.save()
    return '%d of %d instances made, %d compile without errors' % (
        sum(1 for v in done.values() if v.get('made') != 'FAILED'), len(job.mis['character']),
        sum(1 for v in done.values() if (v.get('compile') or {}).get('ok')))


def _mesh_options(job, m):
    ui = unreal.FbxImportUI()
    for prop, value in (('import_mesh', True), ('import_as_skeletal', True), ('mesh_type_to_import', unreal.FBXImportType.FBXIT_SKELETAL_MESH),
                        ('automated_import_should_detect_type', False), ('import_materials', False), ('import_textures', False),
                        ('import_animations', False), ('create_physics_asset', False)):
        job.setp(ui, prop, value)
    if m.get('skeleton'):
        sk = unreal.load_asset(m['skeleton'])
        if sk is None:
            raise RuntimeError('no skeleton ' + m['skeleton'])
        job.setp(ui, 'skeleton', sk)
    sd = ui.get_editor_property('skeletal_mesh_import_data')
    for prop, value in (('import_morph_targets', False), ('normal_import_method', unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS),
                        ('use_t0_as_ref_pose', False), ('convert_scene', True), ('force_front_x_axis', False),
                        ('update_skeleton_reference_pose', False), ('import_meshes_in_bone_hierarchy', True)):
        job.setp(sd, prop, value)
    return ui


def _sockets(job, m, sm, sk):
    """The job's sockets for model m: on='skeleton' ones on its skeleton sk, on='mesh' ones on the mesh sm, each made anew
    when one of that name is there (RebirthRemakeImportLibrary.AddSockets, editor plugin 1.16). Saves what it changed."""
    wanted = m.get('sockets') or []
    if not wanted:
        return None
    lib = getattr(unreal, 'RebirthRemakeImportLibrary', None)
    if lib is None or not hasattr(lib, 'add_sockets'):
        return ('not added (%d): they need the Create a Character System editor plugin 1.16 (close the editor, run '
                'Tools\\RebirthSkelCompat\\run_build_plugin.cmd, then import again)' % len(wanted))
    out = {}
    for on, target in (('skeleton', sk), ('mesh', sm)):
        part = [x for x in wanted if x.get('on', 'skeleton') == on]
        if not part:
            continue
        if target is None:
            out[on] = {'error': 'no %s to put them on' % on}
            continue
        try:
            out[on] = json.loads(lib.add_sockets(target, json.dumps(part)))
        except Exception:
            out[on] = {'error': traceback.format_exc()[-600:]}
            continue
        if out[on].get('added') or out[on].get('replaced'):
            EAL.save_loaded_asset(target)
    return out


def models(job):
    done = job.results.setdefault('models', {})
    sub = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
    for m in job.spec.get('models', []):
        path = '%s/%s' % (m['folder'], m['name'])
        try:
            if EAL.does_asset_exist(path):   # (replacing a mesh under its own open editor tab can take the editor down)
                sub.close_all_editors_for_asset(unreal.load_asset(path))
            sm = _import_file(os.path.join(MODELS, m['fbx']), m['folder'], m['name'], _mesh_options(job, m))
            if not isinstance(sm, unreal.SkeletalMesh):
                raise RuntimeError('the import made no skeletal mesh at %s (see the editor log)' % path)
            mats = sm.get_editor_property('materials')
            assigned, missing = [], []
            for i in range(len(mats)):
                slot = mats[i]                        # a copy: change it, then put it back
                name = str(slot.get_editor_property('material_slot_name'))
                mpath = '%s/%s' % (m['materials'], name)
                mi = unreal.load_asset(mpath) if EAL.does_asset_exist(mpath) else None
                if mi is None:
                    missing.append(name)
                    continue
                slot.set_editor_property('material_interface', mi)
                mats[i] = slot
                assigned.append(name)
            sm.set_editor_property('materials', mats)
            EAL.save_loaded_asset(sm)
            sk = sm.get_editor_property('skeleton')
            if sk is not None:
                EAL.save_loaded_asset(sk)
            c = unreal.SkeletalMeshComponent()
            c.set_skeletal_mesh(sm)
            done[m['name']] = {'path': path, 'skeleton': sk.get_path_name() if sk else None, 'bones': c.get_num_bones(),
                               'materials': assigned, 'materials_missing': missing}
            socks = _sockets(job, m, sm, sk)
            if socks is not None:
                done[m['name']]['sockets'] = socks
        except Exception:
            done[m['name']] = {'error': traceback.format_exc()[-1500:]}
        job.save()
    return '%d of %d models imported' % (sum(1 for v in done.values() if 'error' not in v), len(job.spec.get('models', [])))


def bonamik(job):
    sys.path.insert(0, os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()), 'Python'))
    import rebirth_fx.kh3bonamik as k
    importlib.reload(k)
    done = job.results.setdefault('bonamik', {})
    for b in job.spec.get('bonamik', []):
        rep = k.convert_file(os.path.join(BONAMIK, b['file']), mesh=b['mesh'], save=True)
        done[b['file']] = {x: rep.get(x) for x in ('ok', 'error', 'asset', 'mesh', 'counts', 'warnings', 'saved', 'mesh_action', 'missing_bones')}
        job.save()
    return '%d of %d Bonamik converted' % (sum(1 for v in done.values() if v.get('ok')), len(job.spec.get('bonamik', [])))


def run(job_path, steps=None, **kw):
    job = Job(job_path)
    said = {}
    for step in steps or STEPS:
        t0 = time.time()
        try:
            said[step] = globals()[step](job, **kw.get(step, {}))
        except Exception:
            said[step] = 'FAILED: ' + traceback.format_exc()[-1500:]
        job.results.setdefault('steps', {})[step] = said[step]
        job.results['steps'][step + '_seconds'] = round(time.time() - t0, 1)
        job.save()
        unreal.log('REMAKECHAR %s %s: %s' % (job.name, step, said[step]))
    return said


if __name__ == '__main__' and len(sys.argv) > 1:
    print(run(sys.argv[1]))
