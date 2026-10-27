import unreal
result = {}
names = [n for n in dir(unreal) if ('Particle' in n or 'Cascade' in n) and ('Library' in n or 'Factory' in n or 'Helper' in n or 'Util' in n)]
result['libs'] = names
ps = unreal.new_object(unreal.ParticleSystem, unreal.find_object(None, '/Engine/Transient'), 'SandalphonProbePS')
try:
    result['emitters'] = str(ps.get_editor_property('emitters'))
except Exception as e:
    result['emitters_err'] = str(e)
em = unreal.new_object(unreal.ParticleSpriteEmitter, ps, 'SandalphonProbeEmitter')
for prop in ['lod_levels', 'emitter_name', 'emitter_render_mode']:
    try:
        result['emitter.' + prop] = str(em.get_editor_property(prop))
    except Exception as e:
        result['emitter.' + prop + '_err'] = str(e)
lod = unreal.new_object(unreal.ParticleLODLevel, em, 'SandalphonProbeLOD')
for prop in ['modules', 'required_module', 'spawn_module', 'type_data_module', 'enabled', 'level']:
    try:
        result['lod.' + prop] = str(lod.get_editor_property(prop))
    except Exception as e:
        result['lod.' + prop + '_err'] = str(e)
# what the system / emitter / LOD classes expose to Python
result['ps_props'] = [p for p in dir(ps) if not p.startswith('_')][:200]
result['sys_lib'] = [n for n in dir(unreal.SystemLibrary) if 'property' in n.lower()][:50]
