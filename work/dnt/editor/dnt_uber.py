"""Dissidia NT's own look for its outfits' cloth, Phase B of the Dissidia NT materials (task #606): the "uber" masters
and their instances, in the open editor (editor link or Output Log, Cmd: py "C:/FF7R2UProj/Tools/Dissidia/pipeline/dnt_uber.py").

Dissidia NT shades its characters (PBB family, its G-buffer and forward passes) with its gloss / reflectance / metal map
(dnt_tex_v2.py makes them Unreal's roughness, metal and colour), its normal map, an occlusion map, and a rim light: the
scene's rim table entry of the material (cRimTbl[rmIndex]: a colour and a power) times (1 - N.V)^power, added to the
light it gets. Unreal's deferred lighting has no place for that rim in the light loop, so the masters give it as
emission: RimColor x RimIntensity x (1 - N.V)^RimPower, tinted by the albedo (RimAlbedoTint) and darkened by the
occlusion, every value a parameter (live-editable in the game once made with Game Materials).

  masters()     M_DNT_Uber (opaque) and M_DNT_Uber_Masked (cut out by its Coverage map) in
                /Game/Character/Player/PC0010_19_DissidiaNT_Sephiroth/Material/Master, both two-sided (Dissidia NT's coat,
                cape and torn cloth show their inside);
  instances()   for every outfit's cloth slot (models/<model>_mats.json: role Cloth), MI_PC0010_19_<outfit>_<slot>_Uber
                next to its first instance (same textures), on M_DNT_Uber or, for the cloth cut out by its alpha, on
                M_DNT_Uber_Masked; nothing else is changed (the models keep their instances until wear() puts these on);
  wear()        the models' cloth slots on the _Uber instances (and back: wear(False)).

Phase C (10-27): the hair and skin as well, on masters drawn as the game's hair and skin families (Game Materials:
rebirth_fx/gamemat/convert.py's GAME_FAMILY_MASTERS names them: the game's hair and skin lighting, their own code):
  M_DNT_Hair    cut out by its Coverage map, two-sided, no metal (the hair family has none), its Rebirth Hair Data the
                vertex normal (the hair family's bent normal: Dissidia NT's hair has no bent normal map), the rim;
  M_DNT_Skin    opaque, no metal, Specular 0.33 (the skin family's pores from it: Dissidia NT's skin reflectance about
                0.017), the rim;
  instances() / wear() take the roles too: Skin, Face, Mouth -> M_DNT_Skin; Hair, Lash -> M_DNT_Hair. The eyes keep
  Rebirth's own eye material (the game's eye family needs Rebirth's eye surface: Dissidia NT's eye is one texture).

The _Uber instances go into the game with Game Materials (rebirth_fx.gamematerials.make: their own shader code on the
game's surface carriers, in RebirthGameMaterials_P), not in the skins: the skins' Extra Assets leave them and their
textures out (dnt_import.py's _skin_assets).

Result: Saved/ModExtract/dnt/dnt_uber_result.json."""
import json
import os
import traceback

import unreal

SAVED = os.path.normpath(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()))
SRC = os.path.join(SAVED, 'ModExtract', 'dnt')
RESULT = os.path.join(SRC, 'dnt_uber_result.json')
ROOT = '/Game/Character/Player/PC0010_19_DissidiaNT_Sephiroth'
MASTERS = ROOT + '/Material/Master'
OPAQUE = 'M_DNT_Uber'
MASKED = 'M_DNT_Uber_Masked'
HAIR = 'M_DNT_Hair'
SKIN = 'M_DNT_Skin'
# a role's master (dnt_import's roles; Eye: none, Rebirth's own eye stays)
ROLE_MASTER = {'Cloth': OPAQUE, 'Skin': SKIN, 'Face': SKIN, 'Mouth': SKIN, 'Hair': HAIR, 'Lash': HAIR}
OUTFITS = ['1p1c', '1p2c', '1p3c', '2p1c', '2p2c', '2p3c', '3p1c', '3p2c', '3p3c']
MASKED_CLOTH = {'2p': [3]}          # (dnt_import.py's: cloth whose albedo alpha cuts holes)
# the rim's defaults (Dissidia NT's scene tables give each stage its own: these are a soft white edge light)
RIM = {'RimPower': 3.0, 'RimIntensity': 0.25, 'RimAlbedoTint': 0.5}
RIM_COLOR = (1.0, 1.0, 1.0, 1.0)
SPECULAR = 0.5
SKIN_SPECULAR = 0.33     # (the game's skin family: pores = 0.16 Specular^2 / 0.0325, Remake's skin F0 = 0.0325 pores)
# texture parameters: (name, sampler, default) - the names of the game's standard surface carrier (Game Materials maps
# a material's textures onto the carrier's by these names first)
ST = unreal.MaterialSamplerType
WHITE = '/Engine/EngineResources/WhiteSquareTexture'
GREY_WHITE = '/Engine/EngineResources/WhiteSquareTexture'
TEXTURES = [('Color', ST.SAMPLERTYPE_COLOR, WHITE),
            ('Normal', ST.SAMPLERTYPE_NORMAL, '/Engine/EngineMaterials/DefaultNormal'),
            ('Roughness', ST.SAMPLERTYPE_ALPHA, None),
            ('Metallic', ST.SAMPLERTYPE_ALPHA, None),
            ('WideOcclusion', ST.SAMPLERTYPE_ALPHA, None)]
COVERAGE = ('Coverage', ST.SAMPLERTYPE_ALPHA, None)
# each master: masked, two-sided, its textures, metal, specular, hair data
SPECS = {OPAQUE: dict(masked=False, two_sided=True, textures=TEXTURES, metal=True, specular=SPECULAR, hair=False),
         MASKED: dict(masked=True, two_sided=True, textures=TEXTURES + [COVERAGE], metal=True, specular=SPECULAR, hair=False),
         HAIR: dict(masked=True, two_sided=True, textures=[t for t in TEXTURES if t[0] != 'Metallic'] + [COVERAGE], metal=False,
                    specular=SPECULAR, hair=True),
         SKIN: dict(masked=False, two_sided=False, textures=[t for t in TEXTURES if t[0] != 'Metallic'], metal=False,
                    specular=SKIN_SPECULAR, hair=False)}
# (10-27, the Masamunes) M_DNT_Uber with Dissidia NT's emission (PBB-EmN: the 2p1c sword's lit panel, its type 19 map):
# Emissive x EmissiveIntensity added to the rim
EMISSIVE = 'M_DNT_Uber_Emissive'
EMISSIVE_INTENSITY = 4.0
BLACKS = ['/Engine/EngineResources/Black', '/Engine/EngineResources/BlackSquareTexture', '/Engine/EngineMaterials/BlackSquareTexture']
SPECS[EMISSIVE] = dict(masked=False, two_sided=True, textures=TEXTURES + [('Emissive', ST.SAMPLERTYPE_COLOR, 'BLACK')], metal=True,
                       specular=SPECULAR, hair=False, emissive=True)

# the game's cylindrical hair normal (read out of RMI_Surface_Hair_Wide's base pass), in tangent space: B the normal map's
# normal, V the camera vector, S the two-sided sign (undone here: the engine flips a back face's normal, and this one
# faces the camera on either side). Dissidia NT's strands run along its tangent (its textures' V: the meshes' tangents
# follow V); GAME_HAIR_STRAND_NOISE is the game's blue noise in the game's passes (Game Materials), none in the editor.
CYLINDRICAL_NORMAL = r'''float3 b = B * rsqrt(max(dot(B, B), 1e-8));
float3 T = float3(1.0, 0.0, 0.0) - b.x * b;
T = T * rsqrt(max(dot(T, T), 1e-8));
float3 X = V * rsqrt(max(dot(V, V), 1e-8));
float d = dot(X, T);
#ifdef GAME_HAIR_STRAND_NOISE
float n = GAME_HAIR_STRAND_NOISE;
#else
float n = 0.5;
#endif
if (abs(d) < 0.05)
    d = sign(n * 2.0 - 1.0 + d * 20.0) * 0.05;
float3 C = X - d * T;
return C * rsqrt(max(dot(C, C), 1e-8)) * S;
'''

MEL = unreal.MaterialEditingLibrary


def _link(a, out, b, inp):
    """connect a's output `out` to b's input `inp` ('': a single-input node's one input), or raise (before the master is
    saved: the editor's material connections fail silently)"""
    if not MEL.connect_material_expressions(a, out, b, inp):
        raise RuntimeError('could not connect %s.%r to %s.%r' % (a.get_name(), out, b.get_name(), inp))
EAL = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
results = {}


def log(text):
    unreal.log('DNT UBER ' + text)


def save():
    tmp = RESULT + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=1, default=str)
    os.replace(tmp, RESULT)


def _grey_default():
    """a grey (TC_Alpha) texture for the grey maps' defaults: one of the outfits' own (the sampler type must match)"""
    for o in OUTFITS:
        p = '%s/Texture/%s/PC0010_19_DNT_%s_M00_O' % (ROOT, o, o)
        if EAL.does_asset_exist(p):
            return unreal.load_asset(p)
    return None


def _master(name, masked=None):
    spec = SPECS[name]
    masked = spec['masked']
    full = '%s/%s' % (MASTERS, name)
    if EAL.does_asset_exist(full):
        mat = unreal.load_asset(full)
        MEL.delete_all_material_expressions(mat)
        redone = True
    else:
        mat = AT.create_asset(name, MASTERS, unreal.Material, unreal.MaterialFactoryNew())
        redone = False
    mat.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    mat.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MASKED if masked else unreal.BlendMode.BLEND_OPAQUE)
    mat.set_editor_property('two_sided', spec['two_sided'])
    if masked:
        mat.set_editor_property('opacity_mask_clip_value', 0.333)
    mat.set_editor_property('used_with_skeletal_mesh', True)

    def node(cls, x, y):
        return MEL.create_material_expression(mat, cls, x, y)

    grey = _grey_default()
    samples = {}
    y = -400
    for pname, sampler, default in spec['textures']:
        e = node(unreal.MaterialExpressionTextureSampleParameter2D, -1200, y)
        e.set_editor_property('parameter_name', pname)
        e.set_editor_property('sampler_type', sampler)
        if default == 'BLACK':
            default = next((b for b in BLACKS if EAL.does_asset_exist(b)), WHITE)
        tex = unreal.load_asset(default) if default else grey
        if tex is not None:
            e.set_editor_property('texture', tex)
        e.set_editor_property('group', 'Dissidia NT Textures')
        samples[pname] = e
        y += 260

    def scalar(pname, value, x, y_, group='Dissidia NT Rim'):
        e = node(unreal.MaterialExpressionScalarParameter, x, y_)
        e.set_editor_property('parameter_name', pname)
        e.set_editor_property('default_value', value)
        e.set_editor_property('group', group)
        return e

    rim_power = scalar('RimPower', RIM['RimPower'], -1200, y + 40)
    rim_intensity = scalar('RimIntensity', RIM['RimIntensity'], -1200, y + 140)
    rim_tint = scalar('RimAlbedoTint', RIM['RimAlbedoTint'], -1200, y + 240)
    specular = scalar('Specular', spec['specular'], -1200, y + 340, 'Dissidia NT Surface')
    rim_color = node(unreal.MaterialExpressionVectorParameter, -1200, y + 440)
    rim_color.set_editor_property('parameter_name', 'RimColor')
    rim_color.set_editor_property('default_value', unreal.LinearColor(*RIM_COLOR))
    rim_color.set_editor_property('group', 'Dissidia NT Rim')

    # the surface
    MEL.connect_material_property(samples['Color'], '', unreal.MaterialProperty.MP_BASE_COLOR)
    rim_normal = None
    if spec['hair']:
        # (10-27 fix) the hair family's normal is the game's cylindrical hair normal (Rebirth's own hair writes it: its
        # deferred hair lighting finds the strand from it and the view): the view direction less its part along the
        # strand, broken along the strand by the game's noise where the view is almost across it. With the plain
        # normal map normal there the lighting found no strand where the hair faces the camera: lit and unlit blocks.
        sign = node(unreal.MaterialExpressionTwoSidedSign, -1000, y + 640)
        cam = node(unreal.MaterialExpressionCameraVectorWS, -1000, y + 720)
        cam_t = node(unreal.MaterialExpressionTransform, -850, y + 720)
        cam_t.set_editor_property('transform_source_type', unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD)
        cam_t.set_editor_property('transform_type', unreal.MaterialVectorCoordTransform.TRANSFORM_TANGENT)
        _link(cam, '', cam_t, '')
        cyl = node(unreal.MaterialExpressionCustom, -600, y + 640)
        cyl.set_editor_property('code', CYLINDRICAL_NORMAL)
        cyl.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT3)
        cyl.set_editor_property('description', 'DNT cylindrical hair normal')
        ins = []
        for n in ('B', 'V', 'S'):
            ci = unreal.CustomInput()
            ci.set_editor_property('input_name', n)
            ins.append(ci)
        cyl.set_editor_property('inputs', ins)
        _link(samples['Normal'], '', cyl, 'B')
        _link(cam_t, '', cyl, 'V')
        _link(sign, '', cyl, 'S')
        MEL.connect_material_property(cyl, '', unreal.MaterialProperty.MP_NORMAL)
        # the rim keeps the surface's own normal (the cylindrical one faces the camera: no rim at all)
        flip = node(unreal.MaterialExpressionMultiply, -850, y + 820)
        _link(samples['Normal'], '', flip, 'A')
        _link(sign, '', flip, 'B')
        rim_normal = node(unreal.MaterialExpressionTransform, -700, y + 820)
        rim_normal.set_editor_property('transform_source_type', unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_TANGENT)
        rim_normal.set_editor_property('transform_type', unreal.MaterialVectorCoordTransform.TRANSFORM_WORLD)
        _link(flip, '', rim_normal, '')
    else:
        MEL.connect_material_property(samples['Normal'], '', unreal.MaterialProperty.MP_NORMAL)
    MEL.connect_material_property(samples['Roughness'], 'R', unreal.MaterialProperty.MP_ROUGHNESS)
    if 'Metallic' in samples:
        MEL.connect_material_property(samples['Metallic'], 'R', unreal.MaterialProperty.MP_METALLIC)
    MEL.connect_material_property(samples['WideOcclusion'], 'R', unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
    MEL.connect_material_property(specular, '', unreal.MaterialProperty.MP_SPECULAR)
    if masked:
        MEL.connect_material_property(samples['Coverage'], 'R', unreal.MaterialProperty.MP_OPACITY_MASK)

    # the rim: RimColor x RimIntensity x (1 - N.V)^RimPower x lerp(1, albedo, RimAlbedoTint) x occlusion
    fresnel = node(unreal.MaterialExpressionFresnel, -800, y + 40)
    fresnel.set_editor_property('base_reflect_fraction', 0.0)
    MEL.connect_material_expressions(rim_power, '', fresnel, 'ExponentIn')
    if rim_normal is not None:
        _link(rim_normal, '', fresnel, 'Normal')
    one = node(unreal.MaterialExpressionConstant3Vector, -800, y + 200)
    one.set_editor_property('constant', unreal.LinearColor(1.0, 1.0, 1.0, 1.0))
    tint = node(unreal.MaterialExpressionLinearInterpolate, -600, y + 200)
    MEL.connect_material_expressions(one, '', tint, 'A')
    MEL.connect_material_expressions(samples['Color'], '', tint, 'B')
    MEL.connect_material_expressions(rim_tint, '', tint, 'Alpha')
    m1 = node(unreal.MaterialExpressionMultiply, -600, y + 40)
    MEL.connect_material_expressions(rim_color, '', m1, 'A')
    MEL.connect_material_expressions(rim_intensity, '', m1, 'B')
    m2 = node(unreal.MaterialExpressionMultiply, -450, y + 40)
    MEL.connect_material_expressions(m1, '', m2, 'A')
    MEL.connect_material_expressions(fresnel, '', m2, 'B')
    m3 = node(unreal.MaterialExpressionMultiply, -300, y + 100)
    MEL.connect_material_expressions(m2, '', m3, 'A')
    MEL.connect_material_expressions(tint, '', m3, 'B')
    m4 = node(unreal.MaterialExpressionMultiply, -150, y + 100)
    MEL.connect_material_expressions(m3, '', m4, 'A')
    MEL.connect_material_expressions(samples['WideOcclusion'], 'R', m4, 'B')
    if spec.get('emissive'):
        # (the emissive master) the emission map x EmissiveIntensity, added to the rim
        e_int = scalar('EmissiveIntensity', EMISSIVE_INTENSITY, -450, y + 300, 'Dissidia NT Surface')
        e_mul = node(unreal.MaterialExpressionMultiply, -300, y + 260)
        _link(samples['Emissive'], '', e_mul, 'A')
        _link(e_int, '', e_mul, 'B')
        e_add = node(unreal.MaterialExpressionAdd, -100, y + 200)
        _link(m4, '', e_add, 'A')
        _link(e_mul, '', e_add, 'B')
        MEL.connect_material_property(e_add, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    else:
        MEL.connect_material_property(m4, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)

    # (Phase C) the hair family's Rebirth Hair Data: its bent normal, encoded (* 0.5 + 0.5); the vertex normal here
    if spec['hair']:
        out = node(unreal.MaterialExpressionRebirthHairOutput, -150, y + 400)
        vn = node(unreal.MaterialExpressionVertexNormalWS, -800, y + 400)
        half = node(unreal.MaterialExpressionConstant, -800, y + 500)
        half.set_editor_property('r', 0.5)
        mul = node(unreal.MaterialExpressionMultiply, -600, y + 400)
        MEL.connect_material_expressions(vn, '', mul, 'A')
        MEL.connect_material_expressions(half, '', mul, 'B')
        add = node(unreal.MaterialExpressionAdd, -400, y + 400)
        MEL.connect_material_expressions(mul, '', add, 'A')
        MEL.connect_material_expressions(half, '', add, 'B')
        MEL.connect_material_expressions(add, '', out, 'EncodedWideBentNormal')

    MEL.recompile_material(mat)
    saved = EAL.save_loaded_asset(mat, False)
    return {'path': mat.get_path_name(), 'redone': redone, 'saved': bool(saved),
            'textures': [str(n) for n in MEL.get_texture_parameter_names(mat)],
            'scalars': [str(n) for n in MEL.get_scalar_parameter_names(mat)],
            'vectors': [str(n) for n in MEL.get_vector_parameter_names(mat)]}


def masters(names=(OPAQUE, MASKED, HAIR, SKIN)):
    out = results.setdefault('masters', {})
    for name in names:
        try:
            out[name] = _master(name)
        except Exception:
            out[name] = {'error': traceback.format_exc()[-1500:]}
        log('master %s: %s' % (name, json.dumps(out[name])[:300]))
    save()


def _spec(o):
    return json.load(open(os.path.join(SRC, 'models', 'PC0010_19_DNT_%s_mats.json' % o), encoding='utf-8'))


def uber_name(o, slot):
    return 'MI_PC0010_19_%s_%s_Uber' % (o, slot)


def _master_of(o, s):
    """the master of a slot (models/<model>_mats.json slot), or None (the eyes: Rebirth's own)"""
    name = ROLE_MASTER.get(s['role'])
    if name == OPAQUE and s['material'] in MASKED_CLOTH.get(o[:2], []):
        name = MASKED
    return name


def instances(outfits=OUTFITS, roles=('Cloth',)):
    out = results.setdefault('instances', {})
    factory = unreal.MaterialInstanceConstantFactoryNew()
    parents = {}
    for o in outfits:
        made = {}
        try:
            spec = _spec(o)
        except Exception:
            out[o] = {'error': traceback.format_exc()[-600:]}
            continue
        folder = '%s/Material/%s' % (ROOT, o)
        for s in spec['slots']:
            if s['role'] not in roles:
                continue
            master = _master_of(o, s)
            if master is None:
                continue
            if master not in parents:
                parents[master] = unreal.load_asset('%s/%s' % (MASTERS, master))
            parent = parents[master]
            if parent is None:
                made[s['slot']] = {'error': 'no master %s (run masters() first)' % master}
                continue
            name = uber_name(o, s['slot'])
            path = '%s/%s' % (folder, name)
            try:
                mi = unreal.load_asset(path) if EAL.does_asset_exist(path) else None
                if mi is None:
                    mi = AT.create_asset(name, folder, unreal.MaterialInstanceConstant, factory)
                MEL.set_material_instance_parent(mi, parent)
                params = set(str(n) for n in MEL.get_texture_parameter_names(parent))
                done, missing = [], []
                for param, tex_name in s['textures'].items():
                    if param not in params:
                        continue
                    tex = unreal.load_asset('%s/Texture/%s/%s.%s' % (ROOT, o, tex_name, tex_name))
                    if tex is None:
                        missing.append('%s (no texture %s)' % (param, tex_name))
                        continue
                    MEL.set_material_instance_texture_parameter_value(mi, param, tex)
                    got = MEL.get_material_instance_texture_parameter_value(mi, param)
                    (done if got is not None and got.get_path_name() == tex.get_path_name() else missing).append(param)
                MEL.update_material_instance(mi)
                EAL.save_loaded_asset(mi, False)
                made[s['slot']] = {'path': path, 'parent': master, 'set': done, 'not_set': missing,
                                   'unset_params': sorted(params - set(done))}
            except Exception:
                made[s['slot']] = {'error': traceback.format_exc()[-800:]}
        out.setdefault(o, {}).update(made)
        log('instances %s: %d' % (o, len(made)))
        save()


def wear(on=True, outfits=OUTFITS, roles=('Cloth',)):
    """the models' slots of these roles on the _Uber instances (on=False: back on the first instances)"""
    out = results['wear'] = {}
    for o in outfits:
        try:
            spec = _spec(o)
            # (the slot names as the model has them: "DNT_Skin0" came in as "DNT", Unreal's FBX import cut its _Skin<n>)
            slots = {}
            for s in spec['slots']:
                if s['role'] in roles and _master_of(o, s):
                    slots[s['slot']] = s['slot']
                    if s['slot'].startswith('DNT_Skin'):
                        slots['DNT'] = s['slot']
            sm = unreal.load_asset('%s/Model/PC0010_19_DNT_%s' % (ROOT, o))
            mats = sm.get_editor_property('materials')
            changed = []
            for i in range(len(mats)):
                slot = mats[i]
                sname = str(slot.get_editor_property('material_slot_name'))
                if sname not in slots:
                    continue
                own = slots[sname]
                path = '%s/Material/%s/%s' % (ROOT, o, uber_name(o, own) if on else 'MI_PC0010_19_%s_%s' % (o, own))
                mi = unreal.load_asset(path) if EAL.does_asset_exist(path) else None
                if mi is None:
                    changed.append(sname + ': no ' + path)
                    continue
                slot.set_editor_property('material_interface', mi)
                mats[i] = slot
                changed.append(sname)
            sm.set_editor_property('materials', mats)
            EAL.save_loaded_asset(sm, False)
            out[o] = changed
        except Exception:
            out[o] = {'error': traceback.format_exc()[-800:]}
    save()


def uber_instances(outfits=OUTFITS, roles=('Cloth',)):
    """the object paths of the outfits' _Uber instances of these roles (for rebirth_fx.gamematerials.make)"""
    paths = []
    for o in outfits:
        for s in _spec(o)['slots']:
            if s['role'] in roles and _master_of(o, s):
                p = '%s/Material/%s/%s' % (ROOT, o, uber_name(o, s['slot']))
                if EAL.does_asset_exist(p) and p + '.' + uber_name(o, s['slot']) not in paths:
                    paths.append(p + '.' + uber_name(o, s['slot']))
    return paths
