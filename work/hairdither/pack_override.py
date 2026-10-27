"""One IoStore container that overrides the game's /Engine/EngineResources/SpatiotemporalBlueNoiseVolume with ours
(the same package: same name, id, export count and load order as the game's store entry; only pixel data differs).
    pack_override.py <run dir> <out dir> <container name>"""
import json, os, shutil, sys
sys.path[:0] = ['/work/custmat/taken', '/work/custmat', '/work/fx1018/editor/Python']
import pack
from rebirth_fx.zen import Zen
from rebirth_fx import iostore_write as W
from rebirth_fx import matcore

run, out_dir, mod_name = sys.argv[1:4]
rep = json.load(open(os.path.join(run, 'report.json')))
name = rep['package']
data = open(os.path.join(run, name.rsplit('/', 1)[1] + '.zen'), 'rb').read()
assert pack.package_name(data) == name
z = Zen(data)
pid = W.package_id(name)
retail = pack.retail_entries()
e = retail[pid]                                      # the game's own entry for this package
bundles = pack._bundle_count(z)
assert (e['export_count'], e['export_bundle_count']) == (len(z.exports), bundles), (e, len(z.exports), bundles)
imports = [g for g, arcs in matcore.graph_packages(data)]
assert sorted(imports) == sorted(e['imports']), (imports, e['imports'])
rel = name[1:].replace('Engine/', 'Engine/Content/', 1) + '.uasset'      # Engine/Content/EngineResources/...
chunks = [None, dict(id64=pid, type=2, data=data, path=rel)]
entries = [dict(id=pid, name=name, size=len(data), export_count=len(z.exports), export_bundle_count=bundles,
                load_order=e['load_order'], imports=imports)]
cid = W.container_id_from_name(mod_name)
chunks[0] = dict(id64=cid, type=10, data=W.container_header(cid, entries), path=None)
os.makedirs(out_dir, exist_ok=True)
base = os.path.join(out_dir, mod_name)
W.write_container(base, mod_name, chunks, mount='../../../')
shutil.copy(os.path.join(pack.DATA, 'empty_P.pak'), base + '.pak')
back = pack.read_back(base + '.utoc')
assert back.get((pid, 2)) == data
print(mod_name, name, 'load order', e['load_order'], 'imports', len(imports), 'size', len(data))
for p in (base + '.utoc', base + '.ucas', base + '.pak'):
    print('  %-28s %9d' % (os.path.basename(p), os.path.getsize(p)))
