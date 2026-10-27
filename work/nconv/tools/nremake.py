"""Renderers for ported Remake emitters: a game renderer template (SQEX fields, its material's kind) with the material,
mesh, material parameter bindings and per-particle material parameter bindings of a recipe (rmrebirth.py).

recipe (one per emitter, JSON):
  kind: 'mesh' | 'sprite'
  template_from / template_export: a game package and the renderer export to start from
  material: the game material instance (object path)
  mesh: (mesh) the static mesh (object path); pivot: [x, y, z] (default 0)
  bindings: [{name, type ('float'|'vector2'|'bool'|'color'|'texture'), value [4] | texture path, resident}]
  ip: {k: [4 x [factor...]]}   (nindep2) - the renderer binds exactly these
  cull: 'Double' | 'Front' | ... (VfxCullMode, with VfxOverrideCullMode)
  sub_images: [h, v] (sprite flip-books)
"""
import copy
import gv
from gv import struct_ as S, b, name, obj, enum, array, zero

TYPE = {'float': (0x8f7f06aa, 2), 'vector2': (0x05115eac, 2), 'bool': (0x413cb3b2, 2), 'color': (0xe2a7510c, 2),
        'texture': (0xf6708ba8, 1)}
PREFIX = {'mesh': 'FX_Gen_Mesh_0_SetParticleMaterialParameter.IndependentParameter',
          'sprite': 'FX_Gen_Sprite_0_SetParticleMaterialParameter.IndependentParameter'}


def material_binding(out, spec):
    th = TYPE[spec['type']]
    tex = spec['type'] == 'texture'
    val = spec.get('value')
    if tex:
        const = zero()
        texture = obj(out.import_index(val)) if val else zero()
    else:
        vals = [float(x) for x in (list(val) + [0.0, 0.0, 0.0, 0.0])[:4]]
        const = gv.binary('LinearColor', vals) if any(abs(x) > 0 for x in vals) else zero()
        texture = zero()
    return S('NiagaraMaterialAttributeBinding', {
        'MaterialParameterName': name(spec['name']),
        'NiagaraVariable': gv.var_base('None', th),
        'ResolvedNiagaraVariable': gv.var_base('None', th),
        'm_ConstantValue': const,
        'm_Texture': texture,
        'm_bIsStatic': b(True),
        'm_bIsDynamic': b(False),
        'm_bIsTexture': b(tex),
        'm_bIsBuffer': b(False),
        'm_bIsResidentResource': b(bool(spec.get('resident')) and tex)})


def _attr_bindings(p, f, keys, schema_keys):
    for key in keys:
        if key not in schema_keys:
            continue
        eb = p.get(key)
        exists = False
        if eb is not None:
            from nconvert import pv
            exists = bool(pv(eb, 'bBindingExistsOnSource'))
        if exists:
            f[key] = S('NiagaraVariableAttributeBinding', {'bBindingExistsOnSource': b(True)})
        else:
            f.pop(key, None)


def renderer(src, out, index, outer, recipe):
    from nconvert import pv, enum_tail, out_schema_keys, Fail
    cls, p = src.export(index)
    t = copy.deepcopy(recipe['template'])
    f = t.value
    kind = recipe['kind']
    binds = [material_binding(out, x) for x in recipe['bindings']]
    f['MaterialParameterBindings'] = array(binds)
    ips = set(int(k) for k in recipe['ip'])
    for k in range(8):
        key = 'VfxMaterialIndependentParameters%d_Binding' % k
        if k not in ips:
            f.pop(key, None)
        elif key not in f:
            raise Fail('the template binds no material parameter %d' % k)
    if recipe.get('cull'):
        f['VfxOverrideCullMode'] = b(True)
        f['VfxCullMode'] = enum(recipe['cull'])
    else:
        f.pop('VfxOverrideCullMode', None)
        f.pop('VfxCullMode', None)
    if kind == 'mesh':
        if cls != 'NiagaraMeshRendererProperties':
            raise Fail('emitter renderer %d is a %s, the recipe a mesh' % (index, cls))
        meshes = f['Meshes'].value
        m0 = meshes[0].value
        m0['Mesh'] = obj(out.import_index(recipe['mesh']))
        pivot = recipe.get('pivot') or [0.0, 0.0, 0.0]
        if any(abs(x) > 0 for x in pivot):
            m0['PivotOffset'] = gv.binary('Vector', pivot)
        else:
            m0.pop('PivotOffset', None)
        m0.pop('Rotation', None)
        m0['Scale'] = gv.binary('Vector', recipe.get('mesh_scale') or [1.0, 1.0, 1.0])
        del meshes[1:]
        f['bOverrideMaterials'] = b(True)
        ov = f['OverrideMaterials'].value
        ov[0].value['ExplicitMat'] = obj(out.import_index(recipe['material']))
        del ov[1:]
        for key, enum_name in (('FacingMode', 'ENiagaraMeshFacingMode'), ('SortMode', 'ENiagaraSortMode')):
            v = pv(p, key)
            if v is not None:
                f[key] = enum(enum_tail(v))
            else:
                f.pop(key, None)
        _attr_bindings(p, f, ('PositionBinding', 'ColorBinding', 'VelocityBinding', 'MeshOrientationBinding', 'ScaleBinding',
                              'SubImageIndexBinding', 'DynamicMaterialBinding', 'DynamicMaterial1Binding',
                              'DynamicMaterial2Binding', 'DynamicMaterial3Binding', 'MaterialRandomBinding',
                              'NormalizedAgeBinding', 'CameraOffsetBinding'),
                       out_schema_keys('NiagaraMeshRendererProperties'))
        return out.add_export('NiagaraMeshRendererProperties_%d' % index, outer,
                              '/Script/Niagara.NiagaraMeshRendererProperties', t, tail=b'\0' * 4, flags=0x8, filter_flags=0)
    if cls != 'NiagaraSpriteRendererProperties':
        raise Fail('emitter renderer %d is a %s, the recipe a sprite' % (index, cls))
    f['Material'] = obj(out.import_index(recipe['material']))
    sub = recipe.get('sub_images')
    if sub and (sub[0] > 1 or sub[1] > 1):
        f['SubImageSize'] = gv.binary('Vector2D', [float(sub[0]), float(sub[1])])
    else:
        f.pop('SubImageSize', None)
        f.pop('VfxSubImage', None)
    for key in ('FacingMode', 'Alignment', 'SortMode'):
        v = pv(p, key)
        if v is not None:
            f[key] = enum(enum_tail(v))
        else:
            f.pop(key, None)
    so = pv(p, 'SortOrderHint')
    if so is not None:
        f['SortOrderHint'] = gv.i32(so)
    _attr_bindings(p, f, ('PositionBinding', 'ColorBinding', 'VelocityBinding', 'SpriteRotationBinding', 'SpriteSizeBinding',
                          'SpriteFacingBinding', 'SpriteAlignmentBinding', 'SubImageIndexBinding', 'DynamicMaterialBinding',
                          'CameraOffsetBinding', 'UVScaleBinding', 'MaterialRandomBinding', 'CustomSortingBinding',
                          'NormalizedAgeBinding'),
                   out_schema_keys('NiagaraSpriteRendererProperties'))
    return out.add_export('NiagaraSpriteRendererProperties_%d' % index, outer,
                          '/Script/Niagara.NiagaraSpriteRendererProperties', t, tail=b'\0' * 8, flags=0x8, filter_flags=0)
