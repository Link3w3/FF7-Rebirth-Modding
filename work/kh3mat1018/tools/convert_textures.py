"""KH3 Shader textures -> PNG + the import settings KH3 had (tex_settings.json): /Game/Shader/X -> /Game/KH3/Shader/X."""
import json, os, sys, traceback
sys.path[:0] = ['/work/kh3fx', '/work/kh3bnm/src/rebirth_fx']
import kh3tex
root, classes, out_dir = sys.argv[1], json.load(open(sys.argv[2])), sys.argv[3]
os.makedirs(out_dir, exist_ok=True)
info, errors = {}, {}
for rel, cls in sorted(classes.items()):
    if cls != 'Texture2D':
        continue
    base = os.path.join(root, rel)
    ub = open(base + '.ubulk', 'rb').read() if os.path.isfile(base + '.ubulk') else b''
    ua, ue = open(base + '.uasset', 'rb').read(), open(base + '.uexp', 'rb').read()
    try:
        t = kh3tex.read_texture(ua, ue, ub)
        st = kh3tex.settings(ua, ue)
        img = kh3tex.import_image(t, st['CompressionSettings'])
        png = os.path.join(out_dir, rel.replace('/', '__') + '.png')
        img.save(png)
        game_path = '/Game/' + rel
        info[game_path] = dict(st, name=os.path.basename(rel), png=os.path.relpath(png, out_dir), format=t['format'],
                               size=[t['w'], t['h']], dest='/Game/KH3/' + os.path.dirname(rel))
    except Exception as e:
        errors[rel] = '%s: %s' % (type(e).__name__, str(e)[:200])
json.dump(info, open(os.path.join(out_dir, 'tex_settings.json'), 'w'), indent=1)
print(len(info), 'textures,', len(errors), 'errors')
import collections
print(collections.Counter(v['format'] for v in info.values()))
print(collections.Counter(v['CompressionSettings'] for v in info.values()))
for r, e in errors.items():
    print('ERR', r, e)
