"""Stage Create a Character System editor 1.19 for the PC: /data/outputs/stage119/ (files + manifest.json):
the plugin's changed sources (1.18's and 1.19's), End's editor module's new AnimGraph nodes and Build.cs, the
AnimBlueprint Maker's tool with the templates (the game's packages and their decoded .template.json), the editor
script, README.md."""
import hashlib, json, os, shutil
SRC = '/work/plugin119/src'
END = '/work/endeditor119/src'
TOOL = '/work/cacsabp/tool'
TPL = '/work/cacsabp/templates_json'
PC = '/work/plugin119/pc'
DOCS = '/work/cacs3146/docs'
OUT = '/data/outputs/stage119'
TEMPLATES = ['PC0000_00_Cloud_Standard_Animation', 'PC0010_00_Sephiroth_Standard_Animation', 'PC0011_00_Vincent_Standard_Animation',
             'SU0004_00_Leviathan_Standard_Animation',
             # (the other characters: listed in templates/templates.json)
             'PC0001_00_Barret_Standard_Animation', 'PC0002_00_Tifa_Standard_Animation', 'PC0003_00_Aerith_Standard_Animation',
             'PC0004_00_RedXIII_Standard_Animation', 'PC0005_00_Yuffie_Standard_Animation', 'PC0007_00_CaitSith_Standard_Animation',
             'PC0008_00_Debumoogle_Standard_Animation', 'PC0009_00_Zack_Standard_Animation', 'PC0012_00_Cid_Standard_Animation']
FILES = [
    ('plugin', SRC, 'RebirthSkelCompat.uplugin'),
    ('plugin', SRC, 'Source/RebirthSkelCompatEditor/RebirthSkelCompatEditor.Build.cs'),
    ('plugin', SRC, 'Source/RebirthSkelCompatEditor/Private/EndAnimBlueprintMaker.h'),
    ('plugin', SRC, 'Source/RebirthSkelCompatEditor/Private/EndAnimBlueprintMaker.cpp'),
    ('plugin', SRC, 'Source/RebirthSkelCompatEditor/Private/EndAnimBlueprintTemplate.h'),
    ('plugin', SRC, 'Source/RebirthSkelCompatEditor/Private/EndAnimBlueprintTemplate.cpp'),
    ('plugin', SRC, 'Source/RebirthSkelCompatEditor/Private/RebirthSkelCompatEditorModule.cpp'),
    ('endeditor', END, 'ENDEditor.Build.cs'),
    ('tools', DOCS, 'README.md'),
    ('tools', PC, 'build_abp_template.py', 'abp/build_abp_template.py'),
]
for f in sorted(os.listdir(os.path.join(END, 'Public'))):
    FILES.append(('endeditor', END, 'Public/' + f))
for f in sorted(os.listdir(os.path.join(END, 'Private'))):
    FILES.append(('endeditor', END, 'Private/' + f))
for rel in ['make_cacs_abp.py', 'README.txt', 'stub.pak', 'lib/zen.py', 'lib/zenrename.py', 'lib/iostore_write.py', 'lib/hdr.py', 'lib/cityhash.py',
            'templates/templates.json']:
    FILES.append(('tools', TOOL, rel, 'abp/' + rel))
for t in TEMPLATES:
    FILES.append(('tools', TOOL, 'templates/%s.uasset' % t, 'abp/templates/%s.uasset' % t))
    FILES.append(('tools', TPL, '%s.template.json' % t, 'abp/templates/%s.template.json' % t))


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
print('%d files staged in %s' % (len(man['files']), OUT))
for f in man['files']:
    print('  %-9s %s' % (f['root'], f['dst']))
