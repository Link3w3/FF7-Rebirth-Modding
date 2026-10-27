# RM_Surface rebuilt (Create a Character System): builds the editable RM_Surface in the game's own place,
#   /Game/Renderer/Material/RM_Surface
# from RM_SurfaceRebuilt.json and the three Custom node codes next to this file (made by make_editor_material.py from the
# rebuild checked against all 104 of the game's RMI_Surface_* shaders). It declares every RM_Surface parameter and static
# switch under their own names, so every material instance of the game's (and yours) has it as its parent unchanged; the
# Rebirth preview plugin renders the cooked ones through it, each with its own static switches. Cooks leave it out (the
# plugin's cook skip): the game keeps its own RM_Surface.
# Then it compiles each of the game's static permutations (transient instances) and lists any compile errors.
# Run in the End editor: run_build_rebuilt_surface.cmd starts it (UE4Editor.exe -ExecutePythonScript), editor closed first.
# Results: Saved\RebirthSkelCompat\RebuiltSurface\build_result.json (and permutations.json).
import json, os, time, traceback
import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = json.load(open(os.path.join(HERE, 'RM_SurfaceRebuilt.json')))
RMIS = json.load(open(os.path.join(HERE, 'rmi_permutations.json')))
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
OUT = os.path.join(SAVED, 'RebirthSkelCompat', 'RebuiltSurface')
os.makedirs(OUT, exist_ok=True)
RESULT = os.path.join(OUT, 'build_result.json')
results = {'steps': [], 'warnings': []}
MEL = unreal.MaterialEditingLibrary
EAL = unreal.EditorAssetLibrary


def log(key, value):
    results[key] = value
    results['steps'].append(key)
    unreal.log('REBUILTSURFACE %s: %s' % (key, str(value)[:2000]))
    json.dump(results, open(RESULT, 'w'), indent=1)


def warn(text):
    results['warnings'].append(text)
    unreal.log_warning('REBUILTSURFACE ' + text)
    json.dump(results, open(RESULT, 'w'), indent=1)


def setp(obj, name, value):
    try:
        obj.set_editor_property(name, value)
        return True
    except Exception as ex:
        warn('could not set %s.%s: %s' % (obj.get_name(), name, ex))
        return False


def enum(cls_name, value_name):
    cls = getattr(unreal, cls_name)
    return getattr(cls, value_name)


class Graph:
    def __init__(self, material):
        self.m = material
        self.col = {}
        self.count = 0
        self.pos = {}

    def node(self, cls, column, row=None, h=90):
        x = -3200 + 400 * column
        y = self.col.get(column, -4000) if row is None else -4000 + 90 * row
        self.col[column] = y + h
        e = MEL.create_material_expression(self.m, cls, x, y)
        if e is None:
            raise RuntimeError('could not create %s' % cls.__name__)
        self.count += 1
        self.pos[e.get_name()] = (x, y, h)
        return e

    def comment(self, text, columns, width=330):
        """A labelled box around every node in these columns (through the plugin: Python can't reach a material's
        comment boxes)"""
        lib = getattr(unreal, 'RebirthMaterialDiagnosticsLibrary', None)
        xs = {-3200 + 400 * c for c in columns}
        ps = [p for p in self.pos.values() if p[0] in xs]
        if lib is None or not hasattr(lib, 'add_material_comment') or not ps:
            return
        x0, y0 = min(p[0] for p in ps) - 40, min(p[1] for p in ps) - 110
        x1, y1 = max(p[0] for p in ps) + width + 40, max(p[1] + p[2] for p in ps) + 40
        lib.add_material_comment(self.m, x0, y0, x1 - x0, y1 - y0, text)

    def link(self, a, out, b, inp):
        if not MEL.connect_material_expressions(a, out, b, inp):
            raise RuntimeError('could not connect %s[%s] -> %s[%s]' % (a.get_name(), out, b.get_name(), inp))

    def pin(self, a, out, prop):
        if not MEL.connect_material_property(a, out, enum('MaterialProperty', prop)):
            raise RuntimeError('could not connect %s[%s] -> %s' % (a.get_name(), out, prop))


def sampler_type_for(texture):
    """UE's own rule (UMaterialExpressionTextureBase::GetSamplerTypeForTexture)"""
    cs = texture.get_editor_property('compression_settings')
    srgb = texture.get_editor_property('srgb')
    T = unreal.TextureCompressionSettings
    S = unreal.MaterialSamplerType
    if cs == T.TC_NORMALMAP:
        return S.SAMPLERTYPE_NORMAL
    if cs == T.TC_GRAYSCALE:
        return S.SAMPLERTYPE_GRAYSCALE if srgb else S.SAMPLERTYPE_LINEAR_GRAYSCALE
    if cs == T.TC_ALPHA:
        return S.SAMPLERTYPE_ALPHA
    if cs == T.TC_MASKS:
        return S.SAMPLERTYPE_MASKS
    if cs == T.TC_DISTANCE_FIELD_FONT:
        return S.SAMPLERTYPE_DISTANCE_FIELD_FONT
    return S.SAMPLERTYPE_COLOR if srgb else S.SAMPLERTYPE_LINEAR_COLOR


CMOT = {1: 'CMOT_FLOAT1', 2: 'CMOT_FLOAT2', 3: 'CMOT_FLOAT3', 4: 'CMOT_FLOAT4'}


def custom(g, column, code_file, description, output_type, inputs, outputs):
    c = g.node(unreal.MaterialExpressionCustom, column, h=80 + 24 * max(len(inputs), len(outputs) + 1))
    setp(c, 'code', open(os.path.join(HERE, code_file)).read())
    setp(c, 'description', description)
    setp(c, 'output_type', enum('CustomMaterialOutputType', output_type))
    ins = []
    for name in inputs:
        i = unreal.CustomInput()
        i.set_editor_property('input_name', name)
        ins.append(i)
    setp(c, 'inputs', ins)
    outs = []
    for o in outputs:
        x = unreal.CustomOutput()
        x.set_editor_property('output_name', o['name'])
        x.set_editor_property('output_type', enum('CustomMaterialOutputType', CMOT[o['size']]))
        outs.append(x)
    setp(c, 'additional_outputs', outs)
    return c


def build():
    path = SPEC['asset']
    folder, name = path.rsplit('/', 1)
    disk = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()), *folder.split('/')[2:]) + os.sep + name
    if os.path.exists(disk + '.uexp'):
        raise RuntimeError('the cooked RM_Surface is still at %s (.uasset/.uexp): run_build_rebuilt_surface.cmd moves it aside first' % disk)
    try:
        # the editor may still be discovering assets: make sure the asset registry knows this folder as it is on disk
        unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous([folder], True)
    except Exception as ex:
        warn('could not rescan %s: %s' % (folder, ex))
    if EAL.does_asset_exist(path) or os.path.exists(disk + '.uasset'):
        m = EAL.load_asset(path)
        MEL.delete_all_material_expressions(m)
        lib = getattr(unreal, 'RebirthMaterialDiagnosticsLibrary', None)
        if lib is not None and hasattr(lib, 'clear_material_comments'):
            lib.clear_material_comments(m)
        log('asset', 'rebuilt in place: ' + path)
    else:
        m = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
        log('asset', 'created: ' + path)
    if m is None:
        raise RuntimeError('could not create ' + path)
    ms = SPEC['material']
    setp(m, 'shading_model', enum('MaterialShadingModel', ms['shading_model']))
    setp(m, 'blend_mode', enum('BlendMode', ms['blend_mode']))
    setp(m, 'opacity_mask_clip_value', ms['opacity_mask_clip_value'])
    setp(m, 'tangent_space_normal', ms['tangent_space_normal'])
    setp(m, 'two_sided', ms['two_sided'])
    for u in ms['usage']:
        setp(m, 'used_with_' + u, True)

    g = Graph(m)
    one = g.node(unreal.MaterialExpressionConstant, 3)
    setp(one, 'r', 1.0)
    zero = g.node(unreal.MaterialExpressionConstant, 3)
    setp(zero, 'r', 0.0)

    # ---- parameters: every RM_Surface one, by its own name. The ones none of the game's shaders reads are declared
    # apart (columns -3/-2, "Declared only") so every instance's saved values still resolve.
    DECLARED = 'Declared only (no game shader reads these)'
    declared_only = []
    tex = {}
    for t in SPEC['textures']:
        p = g.node(unreal.MaterialExpressionTextureObjectParameter, 0 if t['connected'] else -3, h=170)
        setp(p, 'parameter_name', t['name'])
        setp(p, 'group', 'Textures' if t['connected'] else DECLARED)
        if not t['connected']:
            declared_only.append(p)
            setp(p, 'desc', 'declared only: none of the game\'s RM_Surface shaders reads it')
        texture = unreal.load_asset(t['default'])
        if texture is None:
            warn('default texture missing: %s (%s)' % (t['default'], t['name']))
        else:
            setp(p, 'texture', texture)
            setp(p, 'sampler_type', sampler_type_for(texture))
        tex[t['name']] = p
    vec = {}
    node_vectors = {n[2:] for n in SPEC['node']['inputs'] if n.startswith('V_')}
    for v in SPEC['vectors']:
        used = v['name'] in node_vectors
        p = g.node(unreal.MaterialExpressionVectorParameter, 1 if used else -2, h=150)
        setp(p, 'parameter_name', v['name'])
        setp(p, 'group', 'Contexts' if used else DECLARED)
        setp(p, 'default_value', unreal.LinearColor(*v['default']))
        vec[v['name']] = p
        if not used:
            declared_only.append(p)
            setp(p, 'desc', 'declared only: none of the game\'s RM_Surface shaders reads it')
    for b in SPEC['buffers']:
        cls = getattr(unreal, 'MaterialExpressionShaderResourceBufferObjectParameter', None)
        if cls is None:
            warn('no shader resource buffer parameter class here; %s not declared' % b['name'])
            continue
        p = g.node(cls, -2)
        setp(p, 'parameter_name', b['name'])
        setp(p, 'group', DECLARED)
        setp(p, 'desc', 'the game\'s vertex deformation buffer (its vertex shader): declared only')
        declared_only.append(p)
        buf = unreal.load_asset(b['default'])
        if buf is not None:
            for prop in ('shader_resource_buffer', 'buffer'):
                try:
                    p.set_editor_property(prop, buf)
                    break
                except Exception:
                    pass
    for s in SPEC['scalars']:
        p = g.node(unreal.MaterialExpressionScalarParameter, -2)
        setp(p, 'parameter_name', s['name'])
        setp(p, 'group', DECLARED)
        setp(p, 'default_value', s['default'])
        setp(p, 'desc', 'declared only: none of the game\'s RM_Surface shaders reads it')
        declared_only.append(p)
    # the switches the graph itself uses further on (shading model, vertex expression) are declared there
    graph_switches = {SPEC['vertex_expression']['normal_switch'], SPEC['vertex_expression']['position_switch'], 'Layered_'}
    graph_switches |= {name for name, _ in SPEC['shading_models']}
    sw = {}
    switch_nodes = []
    for s in SPEC['switches']:
        if not s['connected'] and s['name'] in graph_switches:
            continue
        p = g.node(unreal.MaterialExpressionStaticSwitchParameter, 2 if s['connected'] else -2, h=110)
        setp(p, 'parameter_name', s['name'])
        setp(p, 'default_value', False)
        if s['connected']:
            setp(p, 'group', 'Switches')   # (one group: a switch's other nodes, below, are in it too)
            g.link(one, '', p, 'True')
            g.link(zero, '', p, 'False')
            sw[s['input']] = p
            switch_nodes.append(p)
        else:
            setp(p, 'group', DECLARED)
            setp(p, 'desc', 'declared only: none of the game\'s RM_Surface shaders reads it')
            declared_only.append(p)
    log('parameters', {'textures': len(tex), 'vectors': len(vec), 'switches': len(sw)})

    # ---- the node's other inputs
    uvs = []
    for k in range(4):
        u = g.node(unreal.MaterialExpressionTextureCoordinate, 3)
        setp(u, 'coordinate_index', k)
        uvs.append(u)
    stbn_path = SPEC['noise']['texture']
    stbn_tex = unreal.load_asset(stbn_path)
    noise = custom(g, 4, SPEC['noise']['code_file'], 'RMS Noise', 'CMOT_FLOAT4', ['STBN'], [])
    if stbn_tex is None:
        warn('the blue noise %s is missing: the dither is flat' % stbn_path)
        flat = g.node(unreal.MaterialExpressionConstant4Vector, 3)
        setp(flat, 'constant', unreal.LinearColor(0.5, 0.5, 0.5, 0.5))
        noise = flat
    else:
        to = g.node(unreal.MaterialExpressionTextureObject, 3)
        setp(to, 'texture', stbn_tex)
        setp(to, 'sampler_type', sampler_type_for(stbn_tex))
        g.link(to, '', noise, 'STBN')
        try:
            log('blue_noise', '%s %dx%d' % (stbn_path, stbn_tex.blueprint_get_size_x(), stbn_tex.blueprint_get_size_y()))
        except Exception:
            log('blue_noise', stbn_path)
    zero4 = g.node(unreal.MaterialExpressionConstant4Vector, 3)
    setp(zero4, 'constant', unreal.LinearColor(0.0, 0.0, 0.0, 0.0))
    # the object's axes in world space (the rows of its LocalToWorld)
    rows = []
    for axis in ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)):
        c3 = g.node(unreal.MaterialExpressionConstant3Vector, 3)
        setp(c3, 'constant', unreal.LinearColor(axis[0], axis[1], axis[2], 0.0))
        tr = g.node(unreal.MaterialExpressionTransform, 3)
        setp(tr, 'transform_source_type', enum('MaterialVectorCoordTransformSource', 'TRANSFORMSOURCE_LOCAL'))
        setp(tr, 'transform_type', enum('MaterialVectorCoordTransform', 'TRANSFORM_WORLD'))
        g.link(c3, '', tr, '')
        ap = g.node(unreal.MaterialExpressionAppendVector, 4)
        g.link(tr, '', ap, 'A')
        g.link(zero, '', ap, 'B')
        rows.append(ap)
    # the vertex expression: what the game's vertex shader works out for the pixels; here the object-space position (the
    # hologram's body-fixed noise) or the object-space normal (the materia); 0 for the others (bones, ocean)
    wp = g.node(unreal.MaterialExpressionWorldPosition, 3)
    tp = g.node(unreal.MaterialExpressionTransformPosition, 3)
    setp(tp, 'transform_source_type', enum('MaterialPositionTransformSource', 'TRANSFORMPOSSOURCE_WORLD'))
    setp(tp, 'transform_type', enum('MaterialPositionTransformSource', 'TRANSFORMPOSSOURCE_LOCAL'))
    g.link(wp, '', tp, '')
    vpos = g.node(unreal.MaterialExpressionAppendVector, 4)
    g.link(tp, '', vpos, 'A')
    g.link(zero, '', vpos, 'B')
    vn = g.node(unreal.MaterialExpressionVertexNormalWS, 3)
    tn = g.node(unreal.MaterialExpressionTransform, 3)
    setp(tn, 'transform_source_type', enum('MaterialVectorCoordTransformSource', 'TRANSFORMSOURCE_WORLD'))
    setp(tn, 'transform_type', enum('MaterialVectorCoordTransform', 'TRANSFORM_LOCAL'))
    g.link(vn, '', tn, '')
    nn = g.node(unreal.MaterialExpressionNormalize, 4)
    g.link(tn, '', nn, '')
    vnrm = g.node(unreal.MaterialExpressionAppendVector, 4)
    g.link(nn, '', vnrm, 'A')
    g.link(zero, '', vnrm, 'B')
    vx = SPEC['vertex_expression']
    s1 = g.node(unreal.MaterialExpressionStaticSwitchParameter, 5)
    setp(s1, 'parameter_name', vx['normal_switch'])
    setp(s1, 'group', 'Switches')
    g.link(vnrm, '', s1, 'True')
    g.link(zero4, '', s1, 'False')
    s2 = g.node(unreal.MaterialExpressionStaticSwitchParameter, 5)
    setp(s2, 'parameter_name', vx['position_switch'])
    setp(s2, 'group', 'Switches')
    g.link(vpos, '', s2, 'True')
    g.link(s1, '', s2, 'False')

    # ---- the node
    nd = SPEC['node']
    rms = custom(g, 6, nd['code_file'], 'RMS (RM_Surface rebuilt)', 'CMOT_FLOAT3', nd['inputs'], nd['outputs'])
    fixed = {'UV0': uvs[0], 'UV1': uvs[1], 'UV2': uvs[2], 'UV3': uvs[3], 'RMS_Noise': noise, 'RMS_DynamicCoverage': one,
             'RMS_VertexExpression': s2, 'RMS_EBuffer': zero4, 'RMS_LocalToWorld0': rows[0], 'RMS_LocalToWorld1': rows[1],
             'RMS_LocalToWorld2': rows[2]}
    for name in nd['inputs']:
        if name in fixed:
            src = fixed[name]
        elif name.startswith('T_'):
            src = tex[name[2:]]
        elif name.startswith('V_'):
            # a vector parameter's first output is RGB only in this engine: the node takes all four (RGB + A)
            v = vec[name[2:]]
            src = g.node(unreal.MaterialExpressionAppendVector, 1)
            g.link(v, '', src, 'A')
            g.link(v, 'A', src, 'B')
        else:
            src = sw[name]
        g.link(src, '', rms, name)
    log('node', '%d inputs, %d outputs' % (len(nd['inputs']), len(nd['outputs'])))

    en = SPEC['engine']
    sizes = {o['name']: o['size'] for o in nd['outputs']}
    eng = custom(g, 8, en['code_file'], 'RMS Engine (the game\'s base pass)', 'CMOT_FLOAT3', [n for n, _ in en['inputs']], en['outputs'])
    for n, src in en['inputs']:
        g.link(rms, src, eng, n)

    def source(spec):
        kind = spec[0]
        if kind == 'Const':
            c = g.node(unreal.MaterialExpressionConstant, 9)
            setp(c, 'r', spec[1])
            return c, ''
        node = rms if kind == 'RMS' else eng
        out = spec[1]
        if len(spec) > 2:
            mask = g.node(unreal.MaterialExpressionComponentMask, 9)
            for ch in 'rgba':
                setp(mask, ch, 'xyzw'['rgba'.index(ch)] in spec[2])
            g.link(node, out, mask, '')
            return mask, ''
        return node, out

    pins = {'BaseColor': 'MP_BASE_COLOR', 'Metallic': 'MP_METALLIC', 'Specular': 'MP_SPECULAR', 'Roughness': 'MP_ROUGHNESS',
            'AmbientOcclusion': 'MP_AMBIENT_OCCLUSION', 'Normal': 'MP_NORMAL', 'EmissiveColor': 'MP_EMISSIVE_COLOR',
            'Opacity': 'MP_OPACITY', 'OpacityMask': 'MP_OPACITY_MASK'}
    for pin, spec in SPEC['pins'].items():
        node, out = source(spec)
        g.pin(node, out, pins[pin])

    # ---- shading model: the game's static choice; Layered picks Fabric per pixel
    # (never Unlit: UMaterial::RebuildShadingModelField adds every ShadingModel node in the graph, and one Unlit among them
    # makes UE treat the whole material as unlit, so it compiles BaseColor, Metallic, Specular, Roughness, Normal and AO as
    # constants in every permutation; the Unlit permutations are Default Lit with no lit inputs, in the RMS code)
    if any(model == 'MSM_UNLIT' for _, model in SPEC['shading_models']):
        raise RuntimeError('RM_SurfaceRebuilt.json lists MSM_UNLIT among the shading models: every permutation would compile '
                           'without its base colour, metal, specular, roughness, normal and occlusion')
    def sm_node(model):
        s = g.node(unreal.MaterialExpressionShadingModel, 10)
        setp(s, 'shading_model', enum('MaterialShadingModel', model))
        return s
    chain = sm_node('MSM_DEFAULT_LIT')
    no_fabric = None
    for switch, model in SPEC['shading_models']:
        if switch == 'Fabric_':
            no_fabric = chain
        st = g.node(unreal.MaterialExpressionStaticSwitchParameter, 11)
        setp(st, 'parameter_name', switch)
        setp(st, 'group', 'Switches')
        g.link(sm_node(model), '', st, 'True')
        g.link(chain, '', st, 'False')
        chain = st
    layered_if = g.node(unreal.MaterialExpressionIf, 12)
    g.link(rms, 'RMS_ShadingModel', layered_if, 'A')
    setp(layered_if, 'const_b', 7.5)
    cloth = sm_node('MSM_CLOTH')
    g.link(cloth, '', layered_if, 'A > B')
    g.link(no_fabric, '', layered_if, 'A < B')
    layered = g.node(unreal.MaterialExpressionStaticSwitchParameter, 13)
    setp(layered, 'parameter_name', 'Layered_')
    setp(layered, 'group', 'Switches')
    g.link(layered_if, '', layered, 'True')
    g.link(chain, '', layered, 'False')
    # MP_ShadingModel is UMETA(Hidden), so Python's MaterialProperty enum doesn't have it: the plugin connects it by name
    lib = getattr(unreal, 'RebirthMaterialDiagnosticsLibrary', None)
    if lib is None or not hasattr(lib, 'connect_material_property_by_name'):
        raise RuntimeError('the RebirthMaterialPreview plugin is older than this script (no connect_material_property_by_name): '
                           'run run_build_rebuilt_surface.cmd, which builds the plugin first')
    if not lib.connect_material_property_by_name(layered, '', 'MP_ShadingModel'):
        raise RuntimeError('could not connect the Shading Model pin')

    # ---- the Rebirth preview bridges (the editor's recovered skin / fabric / standard, hair and eye lighting)
    for cls_name, ins in SPEC['bridges'].items():
        cls = getattr(unreal, 'MaterialExpression' + cls_name, None)
        if cls is None:
            warn('bridge %s is not in this editor (the RebirthMaterialPreview plugin); skipped' % cls_name)
            continue
        b = g.node(cls, 14)
        for inp, spec in ins.items():
            node, out = source(spec)
            g.link(node, out, b, inp)
    # ---- labelled boxes, so the graph reads at a glance
    g.comment('Declared only: RM_Surface parameters that none of the game\'s 104 RM_Surface shaders reads. Nothing is wired '
              'out of them on purpose; they are here so every instance\'s saved values still resolve.', [-3, -2])
    g.comment('Textures the game\'s shaders read (each by its RM_Surface name)', [0])
    g.comment('Contexts (vector parameters, all four channels)', [1])
    g.comment('Static switches: each one is 1 or 0 for the RMS node', [2])
    g.comment('UVs, blue noise, the object\'s axes and the vertex expression', [3, 4, 5])
    g.comment('RMS: the game\'s RM_Surface, rebuilt from its shaders and checked against all 104 of them', [6], width=420)
    g.comment('The game\'s base pass (filtered roughness, specular, emissive, world normal) and the material\'s pins', [8, 9], width=420)
    g.comment('Shading model: the game\'s static choice (Layered picks Fabric per pixel)', [10, 11, 12, 13])
    g.comment('Rebirth preview bridges: the recovered skin/fabric, hair and eye lighting in this editor', [14])
    log('graph', '%d expressions' % g.count)

    MEL.recompile_material(m)
    EAL.save_loaded_asset(m)
    log('saved', path)
    return m


def diagnose(material, label):
    lib = getattr(unreal, 'RebirthMaterialDiagnosticsLibrary', None)
    if lib is None:
        return {'error': 'no RebirthMaterialDiagnosticsLibrary'}
    try:
        d = json.loads(lib.get_material_diagnostics(material, True))
    except Exception as ex:
        return {'error': str(ex)}
    errors, ok = [], True
    for key in ('resources', 'material_resources'):
        for r in d.get(key, []) or []:
            errors += r.get('compile_errors', []) or []
            if r.get('has_shader_map') and not r.get('compiled_successfully', True):
                ok = False
    return {'ok': ok and not errors, 'errors': errors[:20], 'raw_keys': sorted(d.keys())[:20]}


def test_permutations(m):
    lib = getattr(unreal, 'RebirthMaterialDiagnosticsLibrary', None)
    if lib is None or not hasattr(lib, 'create_static_permutation'):
        warn('the plugin has no create_static_permutation (an older build): the permutations were not compiled here')
        return
    start = time.time()
    # all of them first, so the shader compiler works on them together; then each one waited for and checked
    made = []
    for e in RMIS:
        blend = e.get('blend') or ''
        if blend == 'BLEND_AlphaCompositeColored':
            blend = 'BLEND_AlphaComposite'   # the game's coloured composite is not in this engine
        made.append((e['name'], lib.create_static_permutation(m, e['switches'], blend)))
    log('permutations_started', '%d instances (%.0f s)' % (len(made), time.time() - start))
    report = []
    bad = 0
    for k, (name, mic) in enumerate(made):
        if mic is None:
            d = {'ok': False, 'errors': ['could not create the instance']}
        else:
            d = diagnose(mic, name)
        d['name'] = name
        report.append(d)
        if not d.get('ok'):
            bad += 1
        json.dump(report, open(os.path.join(OUT, 'permutations.json'), 'w'), indent=1)
        unreal.log('REBUILTSURFACE permutation %d/%d %s: %s' % (k + 1, len(made), name, 'ok' if d.get('ok') else d))
    log('permutations', '%d of %d compiled without errors (%.0f s)' % (len(made) - bad, len(made), time.time() - start))


try:
    material = build()
    d = diagnose(material, 'base')
    log('base_compile', d)
    test_permutations(material)
    results['done'] = True
    log('finished', True)
except Exception:
    results['error'] = traceback.format_exc()
    results['done'] = False
    json.dump(results, open(RESULT, 'w'), indent=1)
    unreal.log_error('REBUILTSURFACE failed: ' + results['error'])
finally:
    if os.environ.get('REBUILTSURFACE_QUIT', '1') == '1':
        # Quit a few seconds after this script has returned. Quitting from inside the script (inside the editor's
        # "Executing Python..." step) crashed the editor on its way out with a Slate assertion.
        _quit = {'t': 0.0, 'h': None}

        def _quit_later(dt):
            _quit['t'] += dt
            if _quit['t'] > 3.0 and _quit['h'] is not None:
                unreal.unregister_slate_post_tick_callback(_quit['h'])
                _quit['h'] = None
                unreal.SystemLibrary.quit_editor()

        _quit['h'] = unreal.register_slate_post_tick_callback(_quit_later)
