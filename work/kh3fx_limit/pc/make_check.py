"""Writes check_refs.py (editor link): loads every converted KH3 Cascade system of a folder and reports what each
emitter draws with (Required module material, mesh type data mesh, mesh material overrides).
    python3 make_check.py <converted .uasset folder> <package folder> > check_refs.py"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, 'tools')]
import edpkg   # noqa: E402

src, pkg_dir = sys.argv[1], sys.argv[2]
WANT = ('ParticleModuleRequired', 'ParticleModuleTypeDataMesh', 'ParticleModuleMeshMaterial')
paths = {}
for f in sorted(glob.glob(os.path.join(src, '*.uasset'))):
    name = os.path.basename(f)[:-7]
    p = edpkg.EditorPackage.read(open(f, 'rb').read())

    def nm(x):
        return x[0] if x[1] == 0 else '%s_%d' % (x[0], x[1] - 1)

    def obj(i):
        e = p.exports[i - 1]
        chain = [nm(e['name'])]
        while e['outer'] > 0:
            e = p.exports[e['outer'] - 1]
            chain.append(nm(e['name']))
        chain.reverse()
        return chain
    out = []
    for i, e in enumerate(p.exports, 1):
        if e['cls'] < 0:
            c = nm(p.imports[-e['cls'] - 1]['name'])
            if c in WANT:
                ch = obj(i)
                ch[0] = name
                out.append((c, '%s/%s.%s' % (pkg_dir, name, ch[0]) + (':' + '.'.join(ch[1:]) if len(ch) > 1 else '')))
    paths[name] = out
print('import unreal')
print('PATHS = %s' % json.dumps(paths, indent=0))
print('''ROOT = %r
reg = unreal.AssetRegistryHelpers.get_asset_registry()
reg.scan_paths_synchronous([ROOT], True)
result = {}
summary = dict(systems=0, loaded=0, required=0, required_material=0, meshes=0, mesh_set=0, mesh_materials=0, unresolved=[], no_material=[])
for sysname, objs in PATHS.items():
    summary['systems'] += 1
    a = unreal.load_asset('%%s/%%s' %% (ROOT, sysname))
    if a is None:
        summary['unresolved'].append(sysname)
        continue
    summary['loaded'] += 1
    for cls, p in objs:
        o = unreal.find_object(None, p)
        if o is None:
            summary['unresolved'].append(p.rsplit('/', 1)[-1])
            continue
        if cls == 'ParticleModuleRequired':
            summary['required'] += 1
            m = o.get_editor_property('material')
            if m:
                summary['required_material'] += 1
            else:
                summary['no_material'].append(p.rsplit('/', 1)[-1])
        elif cls == 'ParticleModuleTypeDataMesh':
            summary['meshes'] += 1
            if o.get_editor_property('mesh'):
                summary['mesh_set'] += 1
            else:
                summary['no_material'].append('MESH ' + p.rsplit('/', 1)[-1])
        else:
            mm = o.get_editor_property('mesh_materials')
            summary['mesh_materials'] += len([x for x in mm if x])
result['_summary'] = summary
''' % pkg_dir)
