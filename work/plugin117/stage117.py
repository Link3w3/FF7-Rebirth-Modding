"""Stage plugin 1.17 for the PC: /data/outputs/stage117/ (files + manifest.json) and the tools."""
import hashlib, json, os, shutil
SRC = '/work/plugin117/src'
OUT = '/data/outputs/stage117'
FILES = [
    ('plugin', 'RebirthSkelCompat.uplugin'),
    ('plugin', 'Source/RebirthSkelCompatEditor/RebirthSkelCompatEditor.Build.cs'),
    ('plugin', 'Source/RebirthSkelCompatEditor/Public/EndSkeletonCompatDataObject.h'),
    ('plugin', 'Source/RebirthSkelCompatEditor/Private/EndSkeletonCompatDataObject.cpp'),
    ('plugin', 'Source/RebirthSkelCompatEditor/Private/EndSkins.cpp'),
    ('plugin', 'Source/RebirthSkelCompatEditor/Private/EndSkinBuild.h'),
    ('plugin', 'Source/RebirthSkelCompatEditor/Private/EndSkinMaker.h'),
    ('plugin', 'Source/RebirthSkelCompatEditor/Private/EndSkinMaker.cpp'),
    ('plugin', 'Source/RebirthSkelCompatEditor/Private/EndPartsBuilder.h'),
    ('plugin', 'Source/RebirthSkelCompatEditor/Private/EndPartsBuilder.cpp'),
    ('plugin', 'Source/RebirthSkelCompatEditor/Private/RebirthSkelCompatEditorModule.cpp'),
    ('plugin', 'Source/RebirthSkelCompatEditor/Private/SkinCore.hpp'),
    ('plugin', 'Source/RebirthSkelCompatEditor/Private/SkelCompatCore.hpp'),
    ('tools', 'make_customization_catalog.py'),
]
def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()
if os.path.isdir(OUT):
    shutil.rmtree(OUT)
os.makedirs(OUT)
man = {'files': []}
for root, rel in FILES:
    src = os.path.join('/work/plugin117/tools', rel) if root == 'tools' else os.path.join(SRC, rel)
    staged = os.path.join(root, rel)
    dst = os.path.join(OUT, staged)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)
    man['files'].append({'root': root, 'src': staged.replace('/', '\\'), 'dst': rel.replace('/', '\\'), 'md5': md5(dst)})
json.dump(man, open(os.path.join(OUT, 'manifest.json'), 'w'), indent=1)
print(json.dumps(man, indent=1))
