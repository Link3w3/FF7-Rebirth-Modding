"""skins/AnimeMasamune: the anime Masamune's packages as a skin folder of their own ("part": true: nobody wears it; its
packages go into the skins container for the Anime Sephiroth skin's weapon), skin.json written as SkinCore's
WriteSkinJson writes it."""
import json, os, shutil, sys, time

SRC = '/work/anime1025/masamune/out'
DST = sys.argv[1]


def q(s):
    return json.dumps(s, ensure_ascii=True)


def write_skin_json(s):
    o = ['{\n']
    def text(k, v, comma=True):
        o.append(' %s: %s%s\n' % (q(k), q(v), ',' if comma else ''))
    def flag(k, v):
        o.append(' %s: %s,\n' % (q(k), 'true' if v else 'false'))
    def lst(k, v, indent):
        if not v:
            o.append(' ' * indent + '%s: [],\n' % q(k))
            return
        o.append(' ' * indent + '%s: [\n' % q(k))
        for i, x in enumerate(v):
            o.append(' ' * (indent + 1) + q(x) + (',\n' if i + 1 < len(v) else '\n'))
        o.append(' ' * indent + '],\n')
    text('schema', 'CreateACharacterSkin/1')
    text('name', s['name']); text('author', s['author']); text('description', s['description'])
    lst('characters', s['characters'], 1)
    text('model', s['model']); text('skeleton', s['skeleton']); text('family', s['family'])
    flag('proportions', False)
    lst('proportion_bones', [], 1)
    text('voice', s['voice']); text('weapon', s['weapon']); text('anim_blueprint', '')
    o.append(' %s: [],\n' % q('meshes'))
    flag('worn', s['worn'])
    if s.get('part'):
        flag('part', True)
    flag('enabled', True)
    text('preview', '')
    pk = s['packages']
    o.append(' %s: [\n' % q('packages'))
    for i, p in enumerate(pk):
        o.append('  {\n')
        o.append('   %s: %s,\n' % (q('package'), q(p['package'])))
        o.append('   %s: %s,\n' % (q('file'), q(p['file'])))
        o.append('   %s: %d,\n' % (q('size'), p['size']))
        o.append('   %s: %d,\n' % (q('export_count'), p['export_count']))
        o.append('   %s: %d,\n' % (q('export_bundle_count'), p['export_bundle_count']))
        o.append('   %s: %d,\n' % (q('load_order'), p['load_order']))
        lst('imports', p['imports'], 3)
        if not p['bulk']:
            o.append('   %s: []\n' % q('bulk'))
        else:
            o.append('   %s: [\n' % q('bulk'))
            for k, b in enumerate(p['bulk']):
                o.append('    {\n')
                o.append('     %s: %s,\n' % (q('file'), q(b['file'])))
                o.append('     %s: %d\n' % (q('type'), b['type']))
                o.append('    },\n' if k + 1 < len(p['bulk']) else '    }\n')
            o.append('   ]\n')
        o.append('  },\n' if i + 1 < len(pk) else '  }\n')
    o.append(' ],\n')
    text('built', s['built']); text('built_with', s['built_with'], False)
    o.append('}\n')
    return ''.join(o)


entries = json.load(open(os.path.join(SRC, 'store_entries.json')))
skin = dict(name='Anime Masamune', author='',
            description="Anime Sephiroth's Masamune: the game's playable (cut-scale) Masamune on its toon material "
                        "(WE1021_00_Body_Toon, a game material in RebirthGameMaterials_P). Its packages only: the weapon "
                        "of the Anime Sephiroth skin.",
            characters=[], model='', skeleton='', family='', voice='', weapon='', worn=False, part=True,
            packages=entries, built=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            built_with='make_anime_masamune.py (the game\'s packages copied to new paths)')
if os.path.isdir(DST):
    shutil.rmtree(DST)
os.makedirs(DST)
for p in entries:
    for f in [p['file']] + [b['file'] for b in p['bulk']]:
        os.makedirs(os.path.dirname(os.path.join(DST, f)), exist_ok=True)
        shutil.copyfile(os.path.join(SRC, f), os.path.join(DST, f))
open(os.path.join(DST, 'skin.json'), 'w', newline='\n').write(write_skin_json(skin))
print(open(os.path.join(DST, 'skin.json')).read())
