"""Decodes what survey.py found the effects need: meshes -> fbx/<KH3 folder>/<name>.fbx, textures ->
tex/<KH3 folder>/<name>.png + settings in tex_settings.json; mesh_info.json lists every mesh written.

    python3 convert_needed.py <Effects folder>
"""
import json
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, 'tools')]
import kh3mesh   # noqa: E402
import kh3tex    # noqa: E402

root = sys.argv[1]
need = json.load(open(os.path.join(HERE, 'needed.json')))


def rel(path):
    pkg = path.split('.', 1)[0]
    return pkg[len('/Game/Effects/'):]


mesh_info, tex_settings, errors = {}, {}, {}
for p in need['meshes']:
    r = rel(p)
    src = os.path.join(root, *r.split('/'))
    out_dir = os.path.join(HERE, 'fbx', *r.split('/')[:-1])
    try:
        os.makedirs(out_dir, exist_ok=True)
        m, out = kh3mesh.write_fbx(src + '.uasset', out_dir)
        mesh_info[p] = dict(fbx=os.path.relpath(out, HERE), name=m['name'], verts=len(m['positions']),
                            tris=len(m['indices']) // 3, uvs=len(m['uvs']), colors=bool(m['colors']),
                            slots=[s['name'] for s in m['slots']], sections=len(m['sections']))
    except Exception as e:
        errors[p] = traceback.format_exc()[-600:]
for p in need['textures']:
    r = rel(p)
    src = os.path.join(root, *r.split('/'))
    out_dir = os.path.join(HERE, 'tex', *r.split('/')[:-1])
    try:
        os.makedirs(out_dir, exist_ok=True)
        ua, ue = open(src + '.uasset', 'rb').read(), open(src + '.uexp', 'rb').read()
        ub = open(src + '.ubulk', 'rb').read() if os.path.isfile(src + '.ubulk') else b''
        t = kh3tex.read_texture(ua, ue, ub)
        st = kh3tex.settings(ua, ue)
        img = kh3tex.import_image(t, st['CompressionSettings'])
        out = os.path.join(out_dir, t['name'] + '.png')
        img.save(out)
        st.update(png=os.path.relpath(out, HERE), name=t['name'], format=t['format'], size=[t['w'], t['h']])
        tex_settings[p] = st
    except Exception as e:
        errors[p] = traceback.format_exc()[-600:]
json.dump(mesh_info, open(os.path.join(HERE, 'mesh_info.json'), 'w'), indent=1)
json.dump(tex_settings, open(os.path.join(HERE, 'tex_settings.json'), 'w'), indent=1)
json.dump(errors, open(os.path.join(HERE, 'convert_errors.json'), 'w'), indent=1)
print('meshes', len(mesh_info), 'textures', len(tex_settings), 'errors', len(errors))
for p, e in list(errors.items())[:8]:
    print('ERR', p, e.strip().splitlines()[-1])
