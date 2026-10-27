"""One FINAL FANTASY VII REMAKE character, from the game's paks to a job for remake_character.py (Tools/RemakeMaterials).

    extracted   the character folder's packages (Model, Material, Texture, ...) and every package its meshes and
                material instances use from elsewhere: <project>/Saved/RemakeImporter/<folder>/extracted/End/Content/...
    textures    each texture its material instances use (mip 0) as PNG (EXR for the HDR BC6H ones), at the game's path
                under Tools/RemakeMaterials/_build/remake_textures (where Remake Cloud's are), with the game's settings
    instances   its material instances, in remake_<who>_mis.json (the format of remake_cloud_mis.json)
    models      each skeletal mesh of its Model folder as FBX (LOD 0, written by skm_fbx.py: the root resting flat) in
                Tools/RemakeMaterials/_build/remake_models
    bonamik     each mesh's Bonamik (the game's <name>_BNM.uasset/.uexp) in Saved/RemakeBonamik, where the job's
                bonamik step reads it
    job         remake_<who>_job.json next to the extracted files (Saved/RemakeImporter/<folder>)

Needs numpy (the texture decoders and the FBX writer). The pak access (and the key) comes in as a GameIndex.
"""
import contextlib
import importlib.util
import io
import json
import os
import re
import shutil
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
RK418 = os.path.join(HERE, 'rk418')
if RK418 not in sys.path:
    sys.path.insert(0, RK418)

import remake_paks as rp

CATEGORIES = ('Player', 'Enemy')
CHAR_ROOT = 'End/Content/GameContents/Character/'
RENDERER_MI = '/Game/GameContents/Renderer/MaterialInstance/'
DROP_SCALARS = ('RefractionDepthBias',)      # (every cooked instance holds it; no master has it as a parameter)
TOOL = 'Remake Importer'


class ConvertError(Exception):
    pass


_T = {}


def tools():
    """The game file readers (rk418), imported on first use (they need numpy)."""
    if not _T:
        import numpy
        import pkg418, uprops, skm, skm_fbx, tex, mi
        from schema import Schema
        from binr import B
        import remake_textures
        _T.update(np=numpy, pkg418=pkg418, uprops=uprops, skm=skm, skm_fbx=skm_fbx, tex=tex, mi=mi, B=B, schema=Schema(),
                  rt=remake_textures)
    return _T


# ---------------------------------------------------------------------------------------------------------------------
# the characters in the paks
# ---------------------------------------------------------------------------------------------------------------------

def list_characters(index, categories=CATEGORIES, project=None):
    """The character folders (GameContents/Character/<category>/<folder>) with packages in a Model folder."""
    found = {}
    for name in index.files:
        if not name.startswith(CHAR_ROOT):
            continue
        parts = name[len(CHAR_ROOT):].split('/')
        if len(parts) == 4 and parts[0] in categories and parts[2] == 'Model' and parts[3].endswith('.uasset'):
            found.setdefault((parts[0], parts[1]), []).append(parts[3][:-7])
    order = {c: k for k, c in enumerate(categories)}
    out = []
    for (cat, folder), models in sorted(found.items(), key=lambda kv: (order[kv[0][0]], kv[0][1])):
        rel = os.path.join('GameContents', 'Character', cat, folder)
        imported = bool(project) and os.path.isdir(os.path.join(project, 'Content', rel, 'Model'))
        out.append(dict(category=cat, folder=folder, game_path='/Game/GameContents/Character/%s/%s' % (cat, folder),
                        models=sorted(models), imported=imported))
    names = {}
    for c in out:
        c['who'] = who_of(c['folder'])
        names.setdefault(' '.join(c['who']).lower(), []).append(c)
    for same in names.values():
        for c in same:
            c['job_name'] = 'Remake ' + ' '.join(c['who']) + ('' if len(same) == 1 else ' ' + code_of(c['folder']))
    return out


def code_of(folder):
    m = re.match(r'^([A-Z]{2}\d{4}_\d{2})_', folder)
    return m.group(1) if m else folder


def who_of(folder):
    """'PC0002_00_Tifa_Standard' -> ['Tifa'], 'PC0002_01_Tifa_PurpleDress' -> ['Tifa', 'PurpleDress']"""
    parts = folder.split('_')
    if len(parts) > 2 and re.match(r'^[A-Z]{2}\d{4}$', parts[0]) and parts[1].isdigit():
        parts = parts[2:]
    if len(parts) > 1 and parts[-1] == 'Standard':
        parts = parts[:-1]
    return [p for p in parts if p] or [folder]


def find_character(characters, text):
    """The listed character a name or folder points at (exact folder, then a unique part of one)."""
    t = text.strip().strip('/').split('/')[-1].lower()
    exact = [c for c in characters if c['folder'].lower() == t]
    if exact:
        return exact[0]
    part = [c for c in characters if t in c['folder'].lower()]
    if len(part) == 1:
        return part[0]
    if not part:
        raise ConvertError('no character folder matches %r' % text)
    raise ConvertError('%r matches %d folders: %s' % (text, len(part), ', '.join(c['folder'] for c in part[:12])))


# ---------------------------------------------------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------------------------------------------------

def package_of(path):
    """'/Game/A/B.B' -> '/Game/A/B'"""
    if not path:
        return path
    head, _, last = path.rpartition('/')
    return head + '/' + last.split('.')[0] if head else path.split('.')[0]


def _write_atomic(path, data, mode='wb'):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp%d' % os.getpid()
    with open(tmp, mode, **({} if 'b' in mode else {'encoding': 'utf-8', 'newline': '\n'})) as f:
        f.write(data)
    os.replace(tmp, path)


class Extractor(object):
    """Packages out of the paks, into <root>/End/Content/... (as the game has them)."""

    EXTS = ('.uasset', '.uexp', '.ubulk', '.uptnl')

    def __init__(self, index, root):
        self.index, self.root = index, root
        self.done = {}
        self.bytes = 0

    def local(self, rel):
        return os.path.join(self.root, *rel.split('/'))

    def file(self, rel):
        dst = self.local(rel)
        if rel not in self.done:
            data = self.index.read(rel)
            _write_atomic(dst, data)
            self.done[rel] = len(data)
            self.bytes += len(data)
        return dst

    def package(self, game_path):
        """The local .uasset of a game package (its .uexp/.ubulk next to it), or None if the paks do not have it."""
        rel = rp.game_to_file(package_of(game_path))
        if rel is None or not self.index.has(rel + '.uasset'):
            return None
        for ext in self.EXTS:
            if self.index.has(rel + ext):
                self.file(rel + ext)
        return self.local(rel + '.uasset')


def _project_has(project, game_path):
    rel = package_of(game_path)
    if not rel.startswith('/Game/'):
        return rel.startswith('/Engine/')          # (the engine's own content is in every editor)
    return os.path.isfile(os.path.join(project, 'Content', *rel[6:].split('/')) + '.uasset')


def _lod0(T, pkg, i, end):
    """skm.read, stopping after LOD 0 (the LODs after it are not needed and are not read)."""
    e = pkg.exports[i]
    r = T['B'](pkg.d, end, pkg.names, e['off'] + e['size'])
    skm = T['skm']
    M = {}
    M['guid'] = r.b32()
    M['strip'] = r.un('<BB')
    M['bounds'] = r.un('<7f')
    M['materials'] = r.arr(lambda: dict(material=r.i32(), slot=r.name(), a=r.u32(), b=r.u32(), uv_density=r.un('<4f')))
    M['ref'] = skm.ref_skeleton(r)
    M['lod_count'] = r.i32()
    if M['lod_count'] < 1:
        raise ConvertError('the mesh has no LODs')
    with contextlib.redirect_stdout(io.StringIO()):
        M['lods'] = [skm.lod(r, False, False)]
    return M


def _ref(pkg, i):
    if isinstance(i, int) and i < 0:
        return pkg.import_path(i)
    return None


def _read_json(path):
    try:
        with open(path, encoding='utf-8') as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _load_kh3bonamik(project):
    path = os.path.join(project, 'Content', 'Python', 'rebirth_fx', 'kh3bonamik.py')
    if not os.path.isfile(path):
        return None
    spec = importlib.util.spec_from_file_location('remake_importer_kh3bonamik', path)
    mod = importlib.util.module_from_spec(spec)
    keep = sys.dont_write_bytecode
    sys.dont_write_bytecode = True               # (no __pycache__ of this Python in the project's Content folder)
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.dont_write_bytecode = keep
    return mod


# ---------------------------------------------------------------------------------------------------------------------
# the conversion
# ---------------------------------------------------------------------------------------------------------------------

class Converter(object):
    """Makes the job for one character. `project`: the End project folder (C:/FF7R2UProj): what it already has is
    looked up there. `out_root`: where the files go (default: the project; the same folders below it). `editor_root`:
    how the editor names out_root when that differs (a test run elsewhere); the paths in the job use it."""

    def __init__(self, index, character, project, log=print, out_root=None, editor_root=None, skip_existing_common=True):
        self.index, self.c, self.log = index, character, log
        self.project = os.path.abspath(project)
        self.out_root = os.path.abspath(out_root or project)
        self.editor_root = editor_root
        self.skip_existing_common = skip_existing_common
        self.folder = character['folder']
        self.base = character['game_path']                  # /Game/GameContents/Character/<cat>/<folder>
        self.work = os.path.join(self.out_root, 'Saved', 'RemakeImporter', self.folder)
        self.extracted = os.path.join(self.work, 'extracted')
        self.textures_dir = os.path.join(self.out_root, 'Tools', 'RemakeMaterials', '_build', 'remake_textures')
        self.models_dir = os.path.join(self.out_root, 'Tools', 'RemakeMaterials', '_build', 'remake_models')
        self.bonamik_dir = os.path.join(self.out_root, 'Saved', 'RemakeBonamik')
        self.stem = 'remake_' + '_'.join(character.get('who') or who_of(self.folder)).lower()
        self.job_path = os.path.join(self.work, self.stem + '_job.json')
        self.mis_path = os.path.join(self.work, self.stem + '_mis.json')
        self.notes, self.warnings = [], []
        self.x = Extractor(index, self.extracted)

    # the editor's name of a local path
    def ed(self, path):
        if not self.editor_root:
            return path
        rel = os.path.relpath(path, self.out_root)
        return self.editor_root.rstrip('\\/') + '\\' + rel.replace('/', '\\')

    def warn(self, text):
        self.warnings.append(text)
        self.log('  note: ' + text)

    def run(self, progress=None):
        t0 = time.time()
        T = tools()
        progress = progress or (lambda frac, text: None)
        S = T['schema']
        if not os.path.isdir(os.path.join(self.project, 'Content')):
            raise ConvertError('%s is not the End project folder (no Content folder in it)' % self.project)

        # 1. the character folder's packages
        prefix = rp.game_to_file(self.base) + '/'
        mine = sorted(n for n in self.index.files if n.startswith(prefix))
        self.log('Extracting %s: %d files' % (self.folder, len(mine)))
        for k, rel in enumerate(mine):
            self.x.file(rel)
            if k % 20 == 0:
                progress(0.02 + 0.13 * k / max(1, len(mine)), 'extracting %d of %d files' % (k + 1, len(mine)))
        self.log('  %.1f MB in %s' % (self.x.bytes / 1048576.0, self.extracted))

        # 2. its meshes
        progress(0.15, 'reading the models')
        meshes = []
        others = []
        for rel in mine:
            parts = rel[len(prefix):].split('/')
            if len(parts) != 2 or parts[0] != 'Model' or not rel.endswith('.uasset'):
                continue
            path = self.x.local(rel)
            try:
                pkg = T['pkg418'].Package(path)
            except Exception as ex:
                self.warn('%s does not read (%s): left out' % (parts[1], ex))
                continue
            classes = [pkg.classname(e) for e in pkg.exports]
            for i, cls in enumerate(classes):
                if cls == 'SkeletalMesh':
                    meshes.append(self._mesh(T, pkg, i, rel))
            if 'SkeletalMesh' not in classes:
                others.append('%s (%s)' % (parts[1][:-7], classes[0] if classes else '?'))
                if 'StaticMesh' in classes:
                    self.warn('%s is a static mesh: remake_character.py imports skeletal meshes only, so it is left out' % parts[1][:-7])
        meshes = [m for m in meshes if m]
        if not meshes:
            raise ConvertError('%s has no skeletal mesh in its Model folder (%s)' % (self.folder, ', '.join(others) or 'empty'))
        self.log('Models: %s' % ', '.join('%s (%d bones, %d vertices)' % (m['name'], m['bones'], m['vertices']) for m in meshes))

        # 3. the material instances: the folder's own and every one a mesh uses
        mi_paths = []
        for rel in mine:
            parts = rel[len(prefix):].split('/')
            if len(parts) == 2 and parts[0] == 'Material' and rel.endswith('.uasset'):
                mi_paths.append(rp.file_to_game(rel))
        for m in meshes:
            for slot, mp in m['slots']:
                if mp and package_of(mp) not in mi_paths:
                    mi_paths.append(package_of(mp))
        instances, parents, tex_paths = [], set(), []
        for mp in mi_paths:
            if mp.startswith('/Game/GameContents/Renderer/'):
                continue                # (the renderer's own: in the project already, never remade by a character job)
            local = self.x.package(mp)
            if local is None:
                self.warn('material instance %s is not in the paks' % mp)
                continue
            try:
                read = T['mi'].read(local, S)
            except Exception as ex:
                self.warn('material instance %s does not read (%s): left out' % (mp, str(ex)[:200]))
                continue
            for raw in read:
                instances.append(self._instance(raw, mp, tex_paths))
                parents.add(instances[-1]['parent'])
        if not instances:
            self.warn('no material instances: the models come without materials')
        self.log('Material instances: %d (on %d renderer instances)' % (len(instances), len(parents)))
        for p in sorted(parents):
            if not p:
                self.warn('an instance has no parent')
            elif not p.startswith(RENDERER_MI):
                ours = [i for i in instances if i['path'] == p]
                self.warn('parent %s is not one of the Remake renderer instances%s: the instances step needs it in the project '
                          'first' % (p, ' (it is in this job)' if ours else ''))
            elif not _project_has(self.project, p):
                self.warn('the renderer instance %s is not in the project yet: run run_import_remake_mis.cmd first, or the '
                          'instances step stops' % p)

        # 4. the textures
        t1 = time.time()
        textures, skipped, engine = [], [], []
        own = self.base + '/'
        for k, tp in enumerate(tex_paths):
            progress(0.25 + 0.45 * k / max(1, len(tex_paths)), 'texture %d of %d: %s' % (k + 1, len(tex_paths), tp.rsplit('/', 1)[-1]))
            if tp.startswith('/Engine/'):
                engine.append(tp)
                continue
            if self.skip_existing_common and not tp.startswith(own) and _project_has(self.project, tp):
                skipped.append(tp)
                continue
            t = self._texture(T, tp)
            if t:
                textures.append(t)
        textures.sort(key=lambda t: t['path'])
        self.log('Textures: %d to import (%.0f s)%s%s' % (len(textures), time.time() - t1, ', %d already in the project (%s)' % (
            len(skipped), ', '.join(s.rsplit('/', 1)[-1] for s in skipped)) if skipped else '',
            ', %d of the engine' % len(engine) if engine else ''))

        # 5. the models as FBX, and the skeleton each one goes on
        models = []
        made_skeletons = {}             # the game's skeleton -> what this job's first import of it names it
        registry_path = os.path.join(self.out_root, 'Saved', 'RemakeImporter', 'skeletons.json')
        registry = _read_json(registry_path)
        os.makedirs(self.models_dir, exist_ok=True)
        meshes.sort(key=lambda m: (m['skeleton'] != m['folder'] + '/' + m['name'] + '_Skeleton', m['name']))
        for k, m in enumerate(meshes):
            progress(0.70 + 0.2 * k / len(meshes), 'writing %s.fbx' % m['name'])
            fbx = os.path.join(self.models_dir, m['name'] + '.fbx')
            t1 = time.time()
            info = T['skm_fbx'].write(m['M'], m['pkg'], m['name'], fbx + '.tmp')
            os.replace(fbx + '.tmp', fbx)
            m['fbx_info'] = info
            self.log('  %s.fbx: %d vertices, %d triangles, %d bones, %d slots (%.1f MB, %.0f s)' % (
                m['name'], info['vertices'], info['triangles'], info['bones'], len(info['slots']), os.path.getsize(fbx) / 1048576.0, time.time() - t1))
            entry = dict(fbx=m['name'] + '.fbx', folder=m['folder'], name=m['name'], skeleton=None, materials=self.base + '/Material')
            default = m['folder'] + '/' + m['name'] + '_Skeleton'     # (what the FBX import names a new skeleton)
            skel = m['skeleton']
            if not skel or skel == default:
                made_skeletons.setdefault(skel, default)
            elif skel in made_skeletons:
                entry['skeleton'] = made_skeletons[skel]
            elif _project_has(self.project, skel):
                entry['skeleton'] = skel
            elif registry.get(skel) and _project_has(self.project, registry[skel]):
                entry['skeleton'] = registry[skel]
                self.notes.append('%s goes on %s, the project\'s copy of the game\'s %s' % (m['name'], registry[skel], skel.rsplit('/', 1)[-1]))
            else:
                made_skeletons[skel] = default
                if skel.rsplit('/', 1)[0] == m['folder']:
                    self.notes.append('the game\'s %s is not named after one of its meshes: the import names it %s (a new skeleton '
                                      'takes its first mesh\'s name)%s' % (skel.rsplit('/', 1)[-1], default.rsplit('/', 1)[-1],
                                      '; the other meshes go on it too' if len(meshes) > 1 else ''))
                else:
                    self.warn('%s uses the game\'s %s (from %s), which is not in the project yet: this import makes its own %s. '
                              'Import %s first, then this one again, to share that skeleton' % (
                                  m['name'], skel.rsplit('/', 1)[-1], skel.split('/')[-3], default.rsplit('/', 1)[-1], skel.split('/')[-3]))
            if skel:
                registry[skel] = entry['skeleton'] or default
            remap = [[slot, package_of(mp)] for slot, mp in m['slots'] if mp and package_of(mp) != entry['materials'] + '/' + slot]
            if remap:
                entry['slots'] = remap
            models.append(entry)
            m['pkg'] = m['M'] = None
        try:
            _write_atomic(registry_path, json.dumps(registry, indent=1, sort_keys=True), 'w')
        except Exception as ex:
            self.notes.append('skeletons.json was not written (%s)' % ex)

        # 6. the Bonamik
        progress(0.92, 'Bonamik')
        bonamik = []
        kh3 = None
        try:
            kh3 = _load_kh3bonamik(self.project)
        except Exception as ex:
            self.notes.append('kh3bonamik.py did not load here (%s): the Bonamik was not checked' % ex)
        for m in meshes:
            for bp in m['bnm']:
                local = self.x.package(bp)
                if local is None:
                    self.warn('%s\'s Bonamik %s is not in the paks' % (m['name'], bp))
                    continue
                name = bp.rsplit('/', 1)[-1]
                for ext in ('.uasset', '.uexp'):
                    src = local[:-7] + ext
                    if os.path.isfile(src):
                        os.makedirs(self.bonamik_dir, exist_ok=True)
                        shutil.copyfile(src, os.path.join(self.bonamik_dir, name + ext))
                b = dict(file=name + '.uasset', mesh=m['folder'] + '/' + m['name'])
                if kh3 is not None:
                    try:
                        _, spec, notes, errors, warns = kh3.load_file(os.path.join(self.bonamik_dir, name + '.uasset'))
                        b_summary = kh3.summary(spec)
                        if errors:
                            self.warn('Bonamik %s: %s' % (name, '; '.join(errors[:4])))
                        self.log('  Bonamik %s: %s' % (name, json.dumps(b_summary)))
                    except Exception as ex:
                        self.warn('Bonamik %s did not read in kh3bonamik.py (%s): the bonamik step will say more' % (name, str(ex)[:200]))
                bonamik.append(b)
        if not bonamik:
            self.notes.append('no Bonamik: none of the meshes uses one')

        # 7. the material data and the job
        mis = dict(textures=textures, renderer=[], character=sorted(instances, key=lambda i: i['name']),
                   character_parents=sorted(p for p in parents if p))
        _write_atomic(self.mis_path, json.dumps(mis, indent=1), 'w')
        job = dict(name=self.c.get('job_name') or 'Remake ' + ' '.join(who_of(self.folder)),
                   source='FINAL FANTASY VII REMAKE: GameContents/Character/%s/%s' % (self.c['category'], self.folder),
                   mis=self.ed(self.mis_path), models=models, bonamik=bonamik,
                   importer=dict(tool=TOOL, made=time.strftime('%Y-%m-%d %H:%M:%S'), folder=self.folder,
                                 extracted=self.ed(self.extracted), skeletons={m['skeleton']: registry.get(m['skeleton'])
                                 for m in meshes if m['skeleton']}, notes=self.notes, warnings=self.warnings))
        _write_atomic(self.job_path, json.dumps(job, indent=1), 'w')
        summary = dict(job=self.ed(self.job_path), mis=self.ed(self.mis_path), name=job['name'], folder=self.folder,
                       textures=len(textures), textures_skipped=[s.rsplit('/', 1)[-1] for s in skipped], engine_textures=engine,
                       instances=len(instances), models=[dict(name=m['name'], vertices=m['fbx_info']['vertices'],
                       triangles=m['fbx_info']['triangles'], bones=m['fbx_info']['bones'], lods_in_game=m['lod_count'])
                       for m in meshes], bonamik=[b['file'] for b in bonamik], extracted_mb=round(self.x.bytes / 1048576.0, 1),
                       seconds=round(time.time() - t0, 1), warnings=self.warnings, notes=self.notes)
        _write_atomic(os.path.join(self.work, 'import_summary.json'), json.dumps(summary, indent=1), 'w')
        progress(1.0, 'done')
        self.log('Job: %s (%.0f s)' % (self.job_path, time.time() - t0))
        return summary

    def _mesh(self, T, pkg, i, rel):
        name = pkg.exports[i]['name']
        try:
            cls, v, end = T['uprops'].read_export(T['schema'], pkg, i)
            P = v.py()
            M = _lod0(T, pkg, i, end)
        except Exception as ex:
            self.warn('mesh %s does not read (%s): left out' % (name, str(ex)[:300]))
            return None
        L = M['lods'][0]
        slots = []
        for mm in M['materials']:
            mp = _ref(pkg, mm['material'])
            slots.append((mm['slot'], mp))
            if mp is None:
                self.warn('%s: material slot %s has no material instance in the game' % (name, mm['slot']))
        cloth = [s for s in L['sections'] if s['cloth_section'] >= 0]
        if cloth:
            self.notes.append('%s: %d of its sections are cloth sections in the game (the FBX has them as ordinary geometry)' % (name, len(cloth)))
        folder = rp.file_to_game(rel).rsplit('/', 1)[0]
        return dict(name=name, folder=folder, pkg=pkg, M=M, skeleton=package_of(_ref(pkg, P.get('Skeleton'))),
                    bnm=[package_of(pkg.import_path(-k - 1)) for k, imp in enumerate(pkg.imports) if imp[1] == 'SQEX_BonamikAsset'],
                    slots=slots, bones=len(M['ref']['bones']), vertices=L['vertices']['count'], lod_count=M['lod_count'])

    def _instance(self, raw, game_path, tex_paths):
        out = dict(name=raw['name'], parent=package_of(raw['parent']) if raw['parent'] else None,
                   scalars=[[n, v] for n, v in raw['scalars'] if n not in DROP_SCALARS],
                   vectors=[[n, list(v)] for n, v in raw['vectors']], textures=[], overrides=raw.get('overrides') or {},
                   path=package_of(game_path))
        if out['parent'] and out['parent'].startswith('export:'):
            self.warn('%s: its parent is inside its own package (%s): not supported' % (raw['name'], out['parent']))
        for n, t in raw['textures']:
            if not t:
                self.notes.append('%s: texture parameter %s is empty in the game' % (raw['name'], n))
                continue
            tp = package_of(t)
            out['textures'].append([n, tp])
            if tp not in tex_paths:
                tex_paths.append(tp)
        st = raw.get('static') or {}
        on = [s['name'] for s in st.get('switches', []) if s.get('override')]
        if on or any(s.get('override') for s in st.get('masks', [])):
            self.warn('%s sets its own static switches (%s): remake_character.py keeps its parent\'s' % (raw['name'], ', '.join(on) or 'masks'))
        if out['overrides']:
            self.notes.append('%s overrides %s (not applied by remake_character.py)' % (raw['name'], ', '.join(sorted(out['overrides']))))
        return out

    def _texture(self, T, game_path):
        local = self.x.package(game_path)
        name = game_path.rsplit('/', 1)[-1]
        if local is None:
            self.warn('texture %s is not in the paks' % game_path)
            return None
        try:
            pkg = T['pkg418'].Package(local)
            if pkg.classname(pkg.exports[0]) != 'Texture2D':
                self.warn('%s is a %s, not a Texture2D: left out' % (name, pkg.classname(pkg.exports[0])))
                return None
            pd, data = T['rt'].mip0(pkg, T['schema'], local)
            m0 = pd['mips'][0]
            img, mode, ext = T['rt'].decode(pd['format'], data, m0['x'], m0['y'])
        except NotImplementedError as ex:
            self.warn('texture %s: its format %s has no decoder here: left out' % (name, ex))
            return None
        except Exception as ex:
            self.warn('texture %s does not read (%s): left out' % (name, str(ex)[:200]))
            return None
        png = os.path.join(self.textures_dir, *game_path[len('/Game/'):].split('/')) + ext
        T['rt'].write_image(png, img)
        props = pd['props']
        folder = game_path.rsplit('/', 1)[0]
        return dict(path=game_path, folder=folder, name=name, png=self.ed(png), format=pd['format'], size=[m0['x'], m0['y']],
                    mode=mode, srgb=bool(props.get('SRGB', True)), compression=props.get('CompressionSettings', 'TC_Default'),
                    lod_group=props.get('LODGroup', 'TEXTUREGROUP_World'), filter=props.get('Filter'),
                    address_x=props.get('AddressX'), address_y=props.get('AddressY'), mips=len(pd['mips']))
