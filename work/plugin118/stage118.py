"""Stage plugin 1.18 for the PC: /data/outputs/stage118/ (files + manifest.json): the plugin's changed sources,
the AnimBlueprint Maker's tool (abp) and README.md."""
import hashlib, json, os, shutil
SRC = '/work/plugin118/src'
TOOL = '/work/cacsabp/tool'
DOCS = '/work/cacs3146/docs'
OUT = '/data/outputs/stage118'
FILES = [
    ('plugin', SRC, 'RebirthSkelCompat.uplugin'),
    ('plugin', SRC, 'Source/RebirthSkelCompatEditor/RebirthSkelCompatEditor.Build.cs'),
    ('plugin', SRC, 'Source/RebirthSkelCompatEditor/Private/EndAnimBlueprintMaker.h'),
    ('plugin', SRC, 'Source/RebirthSkelCompatEditor/Private/EndAnimBlueprintMaker.cpp'),
    ('plugin', SRC, 'Source/RebirthSkelCompatEditor/Private/RebirthSkelCompatEditorModule.cpp'),
    ('tools', DOCS, 'README.md'),
]
for rel in ['make_cacs_abp.py', 'README.txt', 'stub.pak', 'lib/zen.py', 'lib/zenrename.py', 'lib/iostore_write.py', 'lib/hdr.py',
            'lib/cityhash.py', 'templates/PC0000_00_Cloud_Standard_Animation.uasset', 'templates/PC0010_00_Sephiroth_Standard_Animation.uasset',
            'templates/PC0011_00_Vincent_Standard_Animation.uasset', 'templates/SU0004_00_Leviathan_Standard_Animation.uasset']:
    FILES.append(('tools', TOOL, rel, 'abp/' + rel))


def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()


if os.path.isdir(OUT):
    shutil.rmtree(OUT)
os.makedirs(OUT)
man = {'files': []}
for item in FILES:
    root, base, rel = item[:3]
    dst_rel = item[3] if len(item) > 3 else rel
    src = os.path.join(base, rel)
    staged = os.path.join(root, dst_rel)
    dst = os.path.join(OUT, staged)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)
    man['files'].append({'root': root, 'src': staged.replace('/', '\\'), 'dst': dst_rel.replace('/', '\\'), 'md5': md5(dst)})
json.dump(man, open(os.path.join(OUT, 'manifest.json'), 'w'), indent=1)
print(json.dumps(man, indent=1))
