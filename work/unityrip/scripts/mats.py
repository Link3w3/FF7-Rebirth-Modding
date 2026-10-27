import sys, json, UnityPy
env = UnityPy.load(sys.argv[1])
def rd(p): return p.deref_parse_as_object() if hasattr(p, 'deref_parse_as_object') else p.read()
out = {}
for o in env.objects:
    if o.type.name == 'Material':
        m = o.read()
        sp = m.m_SavedProperties
        tex = {}
        for k, v in sp.m_TexEnvs:
            name = None
            if v.m_Texture.path_id:
                try: name = rd(v.m_Texture).m_Name
                except Exception as e: name = 'EXTERNAL(file %d, path %d)' % (v.m_Texture.file_id, v.m_Texture.path_id)
            tex[k] = dict(tex=name, scale=[v.m_Scale.x, v.m_Scale.y], offset=[v.m_Offset.x, v.m_Offset.y])
        floats = {k: v for k, v in sp.m_Floats}
        colors = {k: [c.r, c.g, c.b, c.a] for k, c in sp.m_Colors}
        try: shader = rd(m.m_Shader).m_ParsedForm.m_Name if m.m_Shader.path_id and m.m_Shader.file_id == 0 else 'EXTERNAL(file %d, path %d)' % (m.m_Shader.file_id, m.m_Shader.path_id)
        except Exception as e: shader = 'EXTERNAL? %s' % e
        out[m.m_Name] = dict(shader=shader, keywords=getattr(m, 'm_ValidKeywords', None) or getattr(m, 'm_ShaderKeywords', None),
                             render_queue=m.m_CustomRenderQueue, tags=dict(getattr(m, 'stringTagMap', None) or getattr(m, 'm_StringTagMap', None) or []),
                             textures={k: v for k, v in tex.items() if v['tex']}, floats=floats, colors=colors)
json.dump(out, open(sys.argv[2], 'w'), indent=1)
ext = [(f.name if hasattr(f, 'name') else str(f)) for f in getattr(env.file, 'externals', [])] if hasattr(env, 'file') else []
for af in env.assets if hasattr(env, 'assets') else []:
    print('externals', [getattr(e, 'path', getattr(e, 'name', e)) for e in af.externals])
for k, v in out.items():
    print(k, v['shader'], v['keywords'], 'queue', v['render_queue'], v['tags'])
    print('   tex', {a: b['tex'] for a, b in v['textures'].items()})
    print('   floats', {a: round(b, 3) for a, b in v['floats'].items()})
    print('   colors', {a: [round(x, 3) for x in b] for a, b in v['colors'].items() if b != [1, 1, 1, 1]})
