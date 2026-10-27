"""The FF7 Remake (4.18) renderer's material functions and master materials as graphs (ue_mat), rebuilt from the game:
each node the cooked package kept (parameters, static switches, function calls - with the names of what fed them, even
stripped nodes) where it was, and the stripped arithmetic and Custom nodes worked out from the game's shaders, which
remake_check.py compares every permutation against.

The game's material functions are each a Custom node between their inputs and outputs (the cooked functions keep only
how many expressions they had: inputs + outputs + one, for most)."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ue_mat import Node, Function, Material

MF_ROOT = '/Game/GameContents/Renderer/MaterialFunction'
M_ROOT = '/Game/GameContents/Renderer/Material'


def custom(code, inputs, out_type, desc, outputs=None, name=None):
    return Node('Custom', {k: v for k, v in inputs.items()}, name=name, Code=code.strip(), InputNames=list(inputs),
                OutputType=out_type, Description=desc, AdditionalOutputs=outputs or [])


# ---- material functions -------------------------------------------------------------------------------------------
_FUNCTIONS = {}


def function(name):
    if name not in _FUNCTIONS:
        _FUNCTIONS[name] = globals()['mf_' + name]()
    return _FUNCTIONS[name]


def mf_NormalizeNormalRG():
    f = Function('NormalizeNormalRG', [('NormalRG', 'Vector2', (0.5, 0.5))],
                 'A tangent-space normal from a two-channel normal map (0..1): z rebuilt, normalized.', MF_ROOT + '/NormalizeNormalRG')
    c = custom('''
float2 XY = NormalRG * 2.0 - 1.0;
float Z = sqrt(max(1.0 - dot(XY, XY), 0.0));
return normalize(float3(XY, Z));''', {'NormalRG': f.inp('NormalRG')}, 3, 'NormalizeNormalRG')
    return f.output('Normal', c)


def mf_BlendNormal():
    f = Function('BlendNormal', [('Normal0', 'Vector3', (0, 0, 1)), ('Normal1', 'Vector3', (0, 0, 1))],
                 'Normal1 laid over Normal0 (reoriented normal mapping), normalized.', MF_ROOT + '/BlendNormal')
    c = custom('''
float3 T = Normal0 + float3(0.0, 0.0, 1.0);
float3 U = Normal1 * float3(-1.0, -1.0, 1.0);
return normalize(T * dot(T, U) - U * T.z);''', {'Normal0': f.inp('Normal0'), 'Normal1': f.inp('Normal1')}, 3, 'BlendNormal')
    return f.output('Normal', c)


def mf_FlattenNormal():
    f = Function('FlattenNormal', [('Normal', 'Vector3', (0, 0, 1)), ('Value', 'Scalar', (0.0,))],
                 'The normal moved toward flat (0, 0, 1) by Value, renormalized.', MF_ROOT + '/FlattenNormal')
    c = custom('''
float3 N = lerp(Normal, float3(0.0, 0.0, 1.0), Value);
return N / sqrt(dot(N, N));''', {'Normal': f.inp('Normal'), 'Value': f.inp('Value')}, 3, 'FlattenNormal')
    return f.output('Normal', c)


def mf_NormalizeNormalRGB():
    f = Function('NormalizeNormalRGB', [('NormalRGB', 'Vector3', (0.5, 0.5, 1.0))],
                 'A tangent-space normal from a three-channel normal map (0..1), normalized.', MF_ROOT + '/NormalizeNormalRGB')
    c = custom('return normalize(NormalRGB * 2.0 - 1.0);', {'NormalRGB': f.inp('NormalRGB')}, 3, 'NormalizeNormalRGB')
    return f.output('Normal', c)


def mf_CompositeColor():
    f = Function('CompositeColor', [('R', 'Scalar', (1.0,)), ('G', 'Scalar', (1.0,)), ('B', 'Scalar', (1.0,))],
                 'A color from its three channels.', MF_ROOT + '/CompositeColor')
    c = custom('return float3(R, G, B);', {'R': f.inp('R'), 'G': f.inp('G'), 'B': f.inp('B')}, 3, 'CompositeColor')
    return f.output('Color', c)


def mf_DetectBaking():
    f = Function('DetectBaking', [], 'Whether the game is baking (its lighting or reflection captures): 1 while it does.',
                 MF_ROOT + '/DetectBaking')
    c = custom('return min(Mask, 1.0);', {'Mask': Node('ExternalHook', Hook='BakingMask', Type=1)}, 1, 'DetectBaking')
    return f.output('Baking', c)


def mf_SphericalInterpolateQuaternion():
    f = Function('SphericalInterpolateQuaternion', [('A', 'Vector4', (0, 0, 0, 1)), ('B', 'Vector4', (0, 0, 0, 1)), ('Alpha', 'Scalar', (0.0,))],
                 'The rotation A turned toward B by Alpha (spherical interpolation along the shorter arc), normalized.',
                 MF_ROOT + '/SphericalInterpolateQuaternion')
    From, To = f.inp('A'), f.inp('B')
    c = custom(SLERP_PREFIX.replace('From', 'A').replace('To', 'B') + """
float Theta = acos(abs(D));""" + SLERP_SUFFIX.replace('From', 'A').replace('To', 'B'),
               {'A': From, 'B': To, 'Alpha': f.inp('Alpha')}, 4, 'SphericalInterpolateQuaternion')
    return f.output('Result', c)


def _animate(f, with_position):
    """the game's vertex animation textures: one column per piece (Coordinate), one row per key; the rotation
    (quaternion) interpolated spherically between the keys about Index, the translation (and scale in w) by the texture's
    filtering, the pivot (the position texture's middle row)"""
    size = Node('TextureProperty', {'TextureObject': f.inp('Translation')}, Property='TMTP_TextureSize')
    rows = custom("""
float Inv = 1.0 / Size.y;
return float3((floor(Index) + 0.5) * Inv, (ceil(Index) + 0.5) * Inv, (Index + 0.5) * Inv);""",
                  {'Size': size, 'Index': f.inp('Index')}, 3, 'Key rows')

    def sample(texture, v):
        return (Node('TextureSample', {'TextureObject': texture, 'Coordinates': Node('AppendVector', {'A': f.inp('Coordinate'), 'B': v})},
                     SamplerType='LinearColor'), 5)
    q = call(None, 'SphericalInterpolateQuaternion', A=sample(f.inp('Rotation'), mask(None, rows, 'r')),
             B=sample(f.inp('Rotation'), mask(None, rows, 'g')), Alpha=Node('Frac', {'Input': f.inp('Index')}))
    f.output('Rotation', q)
    f.output('Translation', sample(f.inp('Translation'), mask(None, rows, 'b')))
    if with_position:
        f.output('Position', sample(f.inp('Position'), Node('Constant', R=0.5)))
    return f


def mf_AnimateRigid():
    return _animate(Function('AnimateRigid', [('Coordinate', 'Scalar', (0.0,)), ('Index', 'Scalar', (0.0,)), ('Translation', 'Texture2D', None),
                                              ('Rotation', 'Texture2D', None), ('Position', 'Texture2D', None)],
                             'A rigid piece\'s animation: its rotation, translation (and scale) and pivot at the key Index.',
                             MF_ROOT + '/AnimateRigid'), True)


def mf_AnimateSoft():
    return _animate(Function('AnimateSoft', [('Coordinate', 'Scalar', (0.0,)), ('Index', 'Scalar', (0.0,)), ('Translation', 'Texture2D', None),
                                             ('Rotation', 'Texture2D', None)],
                             'A soft body vertex\'s animation: its rotation (of its tangent frame) and translation at the key Index.',
                             MF_ROOT + '/AnimateSoft'), False)


def mf_AnimateSoftDirectionalTilt():
    """a soft body vertex's swing in the wind: the textures' rows are directions around the piece's local up axis (the
    row from the direction's angle in its local xy plane, wrapping); the pose swings between the direction's key (Tilt 0)
    and the opposite direction's key (Tilt 1), through the rest pose (Tilt 0.5)"""
    f = Function('AnimateSoftDirectionalTilt', [('Coordinate', 'Scalar', (0.0,)), ('LocalVector', 'Vector3', (1, 0, 0)), ('Tilt', 'Scalar', (0.5,)),
                                                ('Translation', 'Texture2D', None), ('Rotation', 'Texture2D', None)],
                 'A soft body vertex\'s swing toward the direction (LocalVector, in the piece\'s space) and away from it, by Tilt '
                 '(0 toward, 0.5 at rest, 1 away): rotation (of its tangent frame) and translation.',
                 MF_ROOT + '/AnimateSoftDirectionalTilt')
    height = mask(None, Node('TextureProperty', {'TextureObject': f.inp('Translation')}, Property='TMTP_TextureSize'), 'g')
    rows = custom("""
float2 D = normalize(LocalVector.xy);
float Row = frac(sign(D.y) * acos(D.x) * 0.15915494 + 1.0 + 0.5 / Height);
return float2(Row, frac(Row + 0.5));""", {'LocalVector': f.inp('LocalVector'), 'Height': height}, 2, 'Direction rows')

    def sample(texture, row):
        # (the rows wrap around: the material's shared wrap sampler)
        return (Node('TextureSample', {'TextureObject': texture, 'Coordinates': Node('AppendVector', {'A': f.inp('Coordinate'), 'B': row})},
                     SamplerType='LinearColor', SamplerSource='SSM_Wrap_WorldGroupSettings'), 5)
    toward, away = mask(None, rows, 'r'), mask(None, rows, 'g')
    f.output('Rotation', custom("""
float4 A = Toward - float4(0.0, 0.0, 0.0, 1.0);
float4 B = Away - float4(0.0, 0.0, 0.0, 1.0);
return lerp(lerp(A, -A, Tilt), lerp(-B, B, Tilt), Tilt) + float4(0.0, 0.0, 0.0, 1.0);""",
                                {'Toward': sample(f.inp('Rotation'), toward), 'Away': sample(f.inp('Rotation'), away), 'Tilt': f.inp('Tilt')},
                                4, 'Swing rotation'))
    f.output('Translation', custom("""
return lerp(lerp(Toward, -Toward, Tilt), lerp(-Away, Away, Tilt), Tilt);""",
                                   {'Toward': sample(f.inp('Translation'), toward), 'Away': sample(f.inp('Translation'), away), 'Tilt': f.inp('Tilt')},
                                   4, 'Swing translation'))
    return f


def tilt_inputs(local_name, current_name, previous_name):
    """the directional tilt's inputs: the animation direction (world space) in the piece's space, and the tilt now and a
    frame ago - the game's 3D noise at the object's position, drifting with the animation time"""
    direction = Node('AppendVector', {'A': Node('AppendVector', {'A': scalar('MaterialExpressionScalarParameter_13', 'AnimateDirection_X', 'Dynamic', 1.0),
                                                                 'B': scalar('MaterialExpressionScalarParameter_14', 'AnimateDirection_Y', 'Dynamic')}),
                                      'B': scalar('MaterialExpressionScalarParameter_15', 'AnimateDirection_Z', 'Dynamic')})
    local = custom('return mul((float3x3)GetPrimitiveData(Parameters.PrimitiveId).LocalToWorld, Direction);', {'Direction': direction},
                   3, 'Local direction', name=local_name)

    def tilt(name, time):
        at = Node('Add', {'A': Node('Multiply', {'A': Node('ObjectPositionWS')}, ConstB=0.01),
                          'B': Node('Frac', {'Input': Node('Multiply', {'A': time, 'B': const3(None, (1.0, 0.5, 0.25))})})})
        return custom("""
float N = Noise.SampleLevel(NoiseSampler, Position, 0.0).x * 2.0 - 1.0;
return saturate(N * 0.5 + 0.5);""", {'Position': at, 'Noise': Node('ExternalHook', Hook='TiltNoise', Type='Texture3D')}, 1, 'Tilt', name=name)
    return (local, tilt(current_name, scalar('MaterialExpressionScalarParameter_11', 'AnimateTime', 'Dynamic')),
            tilt(previous_name, scalar('MaterialExpressionScalarParameter_12', 'PreviousAnimateTime', 'Dynamic')))


def mf_AnimateFluid():
    # (EndMaterial_Water's FluidBody shaders): the position and the normal (0..1; the vertex factory decodes it) at the
    # key's whole index; the vertex is nothing but these
    f = Function('AnimateFluid', [('Coordinate', 'Scalar', (0.0,)), ('Index', 'Scalar', (0.0,)), ('Position', 'Texture2D', None),
                                  ('Normal', 'Texture2D', None)],
                 'A fluid vertex\'s animation: its position and normal (0..1) at the key Index (its whole part).',
                 MF_ROOT + '/AnimateFluid')
    size = Node('TextureProperty', {'TextureObject': f.inp('Position')}, Property='TMTP_TextureSize')
    row = custom('return (floor(Index) + 0.5) / Size.y;', {'Size': size, 'Index': f.inp('Index')}, 1, 'Key row')

    def sample(texture):
        return (Node('TextureSample', {'TextureObject': texture, 'Coordinates': Node('AppendVector', {'A': f.inp('Coordinate'), 'B': row})},
                     SamplerType='LinearColor'), 5)
    f.output('Position', sample(f.inp('Position')))
    f.output('Normal', sample(f.inp('Normal')))
    return f


def mf_HermiteLimited():
    f = Function('HermiteLimited', [('S', 'Scalar', (0.0,)), ('R', 'Scalar', (1.0,))],
                 'The smooth (Hermite) step of S over 0..R, limited to 0..1.', MF_ROOT + '/HermiteLimited')
    c = custom("""
float X = saturate(S / R);
return X * X * (3.0 - 2.0 * X);""", {'S': f.inp('S'), 'R': f.inp('R')}, 1, 'HermiteLimited')
    return f.output('Result', c)


def mf_ExtraSceneDepthFade():
    f = Function('ExtraSceneDepthFade', [('UnitDistance', 'Scalar', (100.0,))],
                 'How far the game\'s extra scene depth lies behind this pixel, in units of UnitDistance.', MF_ROOT + '/ExtraSceneDepthFade')
    c = custom('return (Depth - PixelDepth) / UnitDistance;', {'Depth': Node('ExternalHook', Hook='ExtraSceneDepth', Type=1),
                                                               'PixelDepth': Node('ExternalHook', Hook='PixelDepth', Type=1),
                                                               'UnitDistance': f.inp('UnitDistance')}, 1, 'ExtraSceneDepthFade')
    return f.output('Fade', c)


def mf_DistributeAnimateKeyIndex():
    f = Function('DistributeAnimateKeyIndex', [('AnimateKeyIndex', 'Scalar', (0.0,)), ('AnimateKeyMinimum', 'Scalar', (0.0,)),
                                               ('AnimateKeyMaximum', 'Scalar', (0.0,)), ('AnimateTexture', 'Texture2D', None)],
                 'The key index moved into the keys Minimum..Maximum (as far as the texture has rows), started part way in.',
                 MF_ROOT + '/DistributeAnimateKeyIndex')
    size = Node('TextureProperty', {'TextureObject': f.inp('AnimateTexture')}, Property='TMTP_TextureSize')
    c = custom("""
uint Last = min(uint(Size.y - 1.0), uint(Maximum));
uint Range = Last - uint(Minimum) + 1u;
uint Start = uint(float(Range) * 0.73399353);
return float((uint(Index) + Start) % Range + uint(Minimum)) + frac(Index);""",
               {'Size': size, 'Index': f.inp('AnimateKeyIndex'), 'Minimum': f.inp('AnimateKeyMinimum'), 'Maximum': f.inp('AnimateKeyMaximum')},
               1, 'DistributeAnimateKeyIndex')
    return f.output('AnimateKeyIndex', c)


def mf_LocalPosition():
    f = Function('LocalPosition', [], 'The pixel\'s (or vertex\'s) position in the primitive\'s own space.', MF_ROOT + '/LocalPosition')
    c = custom('return mul(float4(WorldPosition, 1.0), GetPrimitiveData(Parameters.PrimitiveId).WorldToLocal).xyz;',
               {'WorldPosition': Node('WorldPosition')}, 3, 'LocalPosition')
    return f.output('Position', c)


def mf_EncodeReflectance():
    f = Function('EncodeReflectance', [('Reflectance', 'Scalar', (0.04,))],
                 'Specular for a reflectance at normal incidence (the game\'s F0 = 0.16 x Specular^2).', MF_ROOT + '/EncodeReflectance')
    c = custom('return sqrt(Reflectance / 0.16);', {'Reflectance': f.inp('Reflectance')}, 1, 'EncodeReflectance')
    return f.output('Specular', c)


def mf_RotateCoordinateRightAngle():
    f = Function('RotateCoordinateRightAngle', [('Angle', 'Scalar', (0.0,)), ('Coordinate', 'Vector2', (0.0, 0.0))],
                 'The coordinate turned about (0.5, 0.5) by Angle turns, to the nearest quarter turn.',
                 MF_ROOT + '/RotateCoordinateRightAngle')
    c = custom("""
float Q = floor(frac(Angle + 0.125) * 4.0);
float C = abs(Q - 2.0) - 1.0;
float S = 1.0 - abs(Q - 1.0);
float2 P = Coordinate - 0.5;
return float2(dot(float2(C, S), P), dot(float2(-S, C), P)) + 0.5;""", {'Angle': f.inp('Angle'), 'Coordinate': f.inp('Coordinate')},
               2, 'RotateCoordinateRightAngle')
    return f.output('Coordinate', c)


def mf_DistanceFade():
    f = Function('DistanceFade', [('NearDistance', 'Scalar', (0.0,)), ('FarDistance', 'Scalar', (0.0,))],
                 'The pixel faded in by its distance from the camera: 0 at NearDistance (no nearer than the game\'s near '
                 'distance), 1 from FarDistance on; 1 throughout when they are less than a unit apart.', MF_ROOT + '/DistanceFade')
    c = custom("""
float Near = max(ViewNear, NearDistance);
float Inv = 1.0 / max(FarDistance - Near, 1.0);
return Inv < 1.0 ? saturate((PixelDepth - Near) * Inv) : 1.0;""",
               {'NearDistance': f.inp('NearDistance'), 'FarDistance': f.inp('FarDistance'),
                'PixelDepth': Node('ExternalHook', Hook='PixelDepth', Type=1), 'ViewNear': Node('ExternalHook', Hook='NearPlane', Type=1)},
               1, 'DistanceFade')
    return f.output('Fade', c)


def mf_BlendModifier():
    f = Function('BlendModifier', [('X', 'Scalar', (0.0,)), ('Y', 'Scalar', (0.0,)), ('Blend', 'Scalar', (0.0,)), ('Ratio', 'Scalar', (1.0,))],
                 'X modified by Y: their product (Blend 0) to their screen (Blend 1), applied by Ratio.', MF_ROOT + '/BlendModifier')
    c = custom("""
float M = X * Y;
return lerp(X, lerp(M, X + Y - M, Blend), Ratio);""", {'X': f.inp('X'), 'Y': f.inp('Y'), 'Blend': f.inp('Blend'), 'Ratio': f.inp('Ratio')},
               1, 'BlendModifier')
    return f.output('Result', c)


# ---- masters --------------------------------------------------------------------------------------------------------
def tex(name, param, uv, sampler='LinearColor', texture=None, group='Texture', source=None):
    n = Node('TextureSampleParameter2D', {'Coordinates': uv}, name=name, ParameterName=param, SamplerType=sampler,
             Texture=texture, Group=group)
    if source:
        n.props['SamplerSource'] = source
    return n


def switch(name, param, a, b, define=None, default=False):
    return Node('StaticSwitchParameter', {'A': a, 'B': b}, name=name, ParameterName=param, Group='Static',
                DefaultValue=default, Definition=define)


# the game's spherical interpolation (From to To by Alpha), along the shorter arc: the sign of their dot product on the
# first one's angle; linear where they are nearly parallel
SLERP_PREFIX = '''
float D = dot(From, To);
float S = D < 0.0 ? -1.0 : 1.0;'''
SLERP_SUFFIX = '''
float Scale0 = 1.0 - Alpha;
float Scale1 = Alpha;
if (abs(D) < 0.9995)
{
    float InvSin = 1.0 / sin(Theta);
    Scale0 = sin(Theta * (S * Scale0)) * InvSin;
    Scale1 = sin(Theta * Scale1) * InvSin;
}
return normalize(From * Scale0 + To * Scale1);'''


# the detail occlusion (or the hair's variant occlusion) combined with the base: between their product and their minimum
OCCLUSION_MIX = '''
float M = min(Detail, Base);
float P = Detail * Base;
float Q = P + 1.0 - M;
return Q * Q * (M - P) + P;'''


def call(name, fn, **inputs):
    return Node('MaterialFunctionCall', inputs, name=name, Function=function(fn))


def texobj(name, param):
    return Node('TextureObjectParameter', name=name, ParameterName=param, Texture='000000FF_HDR', SamplerType='LinearColor',
                Group='Texture')


def c4(name, v):
    return Node('Constant4Vector', name=name, Constant=tuple(v))


def animation(m, coord, rigid, soft, fluid, tilt=None, prev_key_name=None):
    """the game's vertex animation (its vertex factory applies the transform vectors under the RigidBody, SoftBody,
    FluidBody defines): each body's function at the key index and, for the velocity, at the previous key index;
    rigid/soft/fluid: {current / previous: (call name, switch names...)}"""
    key = scalar('MaterialExpressionScalarParameter_29', 'AnimateKeyIndex', 'Dynamic')
    prev_key = scalar(prev_key_name or ('MaterialExpressionScalarParameter_16' if tilt else 'MaterialExpressionScalarParameter_18'),
                      'PreviousAnimateKeyIndex', 'Dynamic')
    for which, k in (('current', key), ('previous', prev_key)):
        if callable(soft[which].get('index')):
            soft[which]['index'] = soft[which]['index'](k)
    rt = [texobj('MaterialExpressionTextureObjectParameter_2', 'V:R:0:Translation'), texobj('MaterialExpressionTextureObjectParameter_3', 'V:R:1:Rotation'),
          texobj('MaterialExpressionTextureObjectParameter_4', 'V:R:2:Position')]
    st = [texobj('MaterialExpressionTextureObjectParameter_5', 'V:S:0:Translation'), texobj('MaterialExpressionTextureObjectParameter_6', 'V:S:1:Rotation')]
    ft = [texobj('MaterialExpressionTextureObjectParameter_9', 'V:F:0:Position'), texobj('MaterialExpressionTextureObjectParameter_10', 'V:F:1:Normal')]
    fl = call(fluid['call'], 'AnimateFluid', Coordinate=coord, Index=key, Position=ft[0], Normal=ft[1])
    for which, k in (('current', key), ('previous', prev_key)):
        r = rigid[which]
        so = soft[which]
        rc = call(r['call'], 'AnimateRigid', Coordinate=coord, Index=k, Translation=rt[0], Rotation=rt[1], Position=rt[2])
        sc = call(so['call'], 'AnimateSoft', Coordinate=coord, Index=so.get('index', k), Translation=st[0], Rotation=st[1])
        identity = [(0, 0, 0, 1), (0, 0, 0, 1), (0, 0, 0, 0)]
        rig = [switch(r['switches'][i], 'RigidBody', (rc, i), c4(r['defaults'][i], identity[i]), 'STATIC_SWITCH_RIGID_BODY') for i in range(3)]
        sof = [(sc, i) for i in range(2)]
        if tilt:
            tt = tilt[which]
            tc = call(tt['call'], 'AnimateSoftDirectionalTilt', Coordinate=coord, LocalVector=tilt['vector'], Tilt=tt['tilt'],
                      Translation=texobj(tilt['textures'][0], 'V:S:0:Translation'), Rotation=texobj(tilt['textures'][1], 'V:S:1:Rotation'))
            sof = [switch(tt['switches'][i], 'DirectionalTilt', (tc, i), (sc, i)) for i in range(2)]
        sof = [switch(so['switches'][i], 'SoftBody', sof[i], rig[i], 'STATIC_SWITCH_SOFT_BODY') for i in range(2)]
        flu = [switch(fluid[which][i], 'FluidBody', (fl, i), sof[i], 'STATIC_SWITCH_FLUID_BODY') for i in range(2)]
        prefix = '' if which == 'current' else 'Previous'
        m.pin(prefix + 'VertexTransformVector0', flu[0])
        m.pin(prefix + 'VertexTransformVector1', flu[1])
        m.pin(prefix + 'VertexTransformVector2', rig[2])


def mask(name, x, comps):
    return Node('ComponentMask', {'Input': x}, name=name, R='r' in comps, G='g' in comps, B='b' in comps, A='a' in comps)


# the detail normal chain's node names: the base map's mask and call, then per detail its mask, normalize call, one-minus,
# flatten call, blend call and switch (Standard's, Fabric's and Subsurface's)
DETAIL_NAMES = (('MaterialExpressionComponentMask_3', 'MaterialExpressionMaterialFunctionCall_1'),
                [('MaterialExpressionComponentMask_8', 'MaterialExpressionMaterialFunctionCall_4', 'MaterialExpressionOneMinus_0',
                  'MaterialExpressionMaterialFunctionCall_6', 'MaterialExpressionMaterialFunctionCall_0', 'MaterialExpressionStaticSwitchParameter_0'),
                 ('MaterialExpressionComponentMask_0', 'MaterialExpressionMaterialFunctionCall_2', 'MaterialExpressionOneMinus_1',
                  'MaterialExpressionMaterialFunctionCall_3', 'MaterialExpressionMaterialFunctionCall_7', 'MaterialExpressionStaticSwitchParameter_1'),
                 ('MaterialExpressionComponentMask_1', 'MaterialExpressionMaterialFunctionCall_8', 'MaterialExpressionOneMinus_2',
                  'MaterialExpressionMaterialFunctionCall_9', 'MaterialExpressionMaterialFunctionCall_10', 'MaterialExpressionStaticSwitchParameter_2')])


def detail_normal(normal, dopac, dnorm, names=DETAIL_NAMES):
    """the base normal map, then up to three detail maps (Detail:0..2) laid over it, each flattened where the detail opacity
    (its channel of the detail opacity map) is low"""
    (bmask, bcall), details = names
    prev = call(bcall, 'NormalizeNormalRG', NormalRG=mask(bmask, normal, 'rg'))
    for k, (nmask, ncall, om, fcall, blend, sw) in enumerate(details):
        dn = call(ncall, 'NormalizeNormalRG', NormalRG=mask(nmask, dnorm[k], 'rg'))
        flat = call(fcall, 'FlattenNormal', Normal=dn, Value=Node('OneMinus', {'Input': (dopac, 1 + k)}, name=om))
        prev = switch(sw, 'Detail:%d' % k, call(blend, 'BlendNormal', Normal0=prev, Normal1=flat), prev)
    return prev


def detail_occlusion(uv2, occl, mix_name='MaterialExpressionCustom_2'):
    """the occlusion (UV1), or with DetailOcclusion mixed with the detail occlusion (UV2): Standard's, Fabric's and
    Subsurface's nodes"""
    docc = tex('MaterialExpressionTextureSampleParameter2D_9', '2:4:DetailOcclusion', uv2, 'Alpha', 'FF000000_BC4')
    occ_mix = custom(OCCLUSION_MIX, {'Detail': (docc, 4), 'Base': (occl, 4)}, 1, 'Detail occlusion', name=mix_name)
    return switch('MaterialExpressionStaticSwitchParameter_14', 'DetailOcclusion', occ_mix,
                  mask('MaterialExpressionComponentMask_11', (occl, 5), 'a'))


def detail_coverage(cover, dcover):
    """with Coverage the coverage map's, times (with DetailCoverage) the detail coverage map's: Standard's and Fabric's nodes"""
    dcov = switch('MaterialExpressionStaticSwitchParameter_7', 'DetailCoverage', mask('MaterialExpressionComponentMask_13', (dcover, 5), 'a'),
                  Node('Constant', name='MaterialExpressionConstant_4', R=1.0))
    return switch('MaterialExpressionStaticSwitchParameter_4', 'Coverage',
                  Node('Multiply', {'A': (cover, 4), 'B': dcov}, name='MaterialExpressionMultiply_3'),
                  Node('Constant', name='MaterialExpressionConstant_0', R=1.0))


def EndMaterial_Standard():
    _SHARED.clear()
    m = Material('EndMaterial_Standard', M_ROOT + '/EndMaterial_Standard')
    uv0 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_1', CoordinateIndex=0)
    uv1 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_3', CoordinateIndex=1)
    uv2 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_8', CoordinateIndex=2)

    color = tex('MaterialExpressionTextureSampleParameter2D_6', '0:0:Color', uv0, 'Color', '767676FF_sRGB')
    normal = tex('MaterialExpressionTextureSampleParameter2D_7', '0:3:Normal', uv0, 'LinearColor', '8080FF00')
    mrv = tex('MaterialExpressionTextureSampleParameter2D_4', '0:2:Metallic/Roughness/Variant', uv0, 'LinearColor', '008000FF')
    occl = tex('MaterialExpressionTextureSampleParameter2D_5', '1:0:Occlusion', uv1, 'Alpha', 'FF000000_BC4')
    cover = tex('MaterialExpressionTextureSampleParameter2D_2', '0:1:Coverage', uv0, 'Alpha', 'FF000000_BC4')
    dopac = tex('MaterialExpressionTextureSampleParameter2D_17', '0:5:DetailOpacity', uv0, 'LinearColor', '000000FF')
    dnorm = [tex('MaterialExpressionTextureSampleParameter2D_14', '2:0:DetailNormal:0', uv2, 'LinearColor', '8080FF00'),
             tex('MaterialExpressionTextureSampleParameter2D_0', '2:1:DetailNormal:1', uv2, 'LinearColor', '8080FF00'),
             tex('MaterialExpressionTextureSampleParameter2D_1', '2:2:DetailNormal:2', uv2, 'LinearColor', '8080FF00')]
    dcover = tex('MaterialExpressionTextureSampleParameter2D_3', '2:3:DetailCoverage', uv2, 'Alpha', 'FF000000_BC4')

    m.pin('Normal', detail_normal(normal, dopac, dnorm))
    m.pin('BaseColor', mask('MaterialExpressionComponentMask_2', color, 'rgb'))
    m.pin('Metallic', mask('MaterialExpressionComponentMask_4', (mrv, 5), 'r'))
    m.pin('Roughness', mask('MaterialExpressionComponentMask_5', (mrv, 5), 'g'))
    shiny = switch('MaterialExpressionStaticSwitchParameter_20', 'Shiny', Node('Constant', name='MaterialExpressionConstant_6', R=0.16),
                   Node('Constant', name='MaterialExpressionConstant_3', R=0.04))
    m.pin('Specular', call('MaterialExpressionMaterialFunctionCall_5', 'EncodeReflectance', Reflectance=shiny))
    m.pin('AmbientOcclusion', detail_occlusion(uv2, occl))
    cov = detail_coverage(cover, dcover)
    m.pin('OpacityMask', switch('MaterialExpressionStaticSwitchParameter_24', 'LiteDecal', cov, cov, 'STATIC_SWITCH_LITE_DECAL'))
    m.pin('EmissiveColor', standard_emissive(uv0, uv2, mrv))
    # the vertex: the piece's (or vertex's) column in the animation textures, and with IdentifierCoverage the piece's id (the
    # noise slice its coverage dithers with)
    coord = mask('MaterialExpressionComponentMask_36', Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_11', CoordinateIndex=3), 'r')
    local, tilt_now, tilt_prev = tilt_inputs('MaterialExpressionCustom_6', 'MaterialExpressionCustom_7', 'MaterialExpressionCustom_10')
    animation(m, coord,
              rigid={'current': {'call': 'MaterialExpressionMaterialFunctionCall_15', 'switches': ['MaterialExpressionStaticSwitchParameter_15', 'MaterialExpressionStaticSwitchParameter_51', 'MaterialExpressionStaticSwitchParameter_54'],
                                 'defaults': ['MaterialExpressionConstant4Vector_7', 'MaterialExpressionConstant4Vector_8', 'MaterialExpressionConstant4Vector_9']},
                     'previous': {'call': 'MaterialExpressionMaterialFunctionCall_17', 'switches': ['MaterialExpressionStaticSwitchParameter_44', 'MaterialExpressionStaticSwitchParameter_46', 'MaterialExpressionStaticSwitchParameter_43'],
                                  'defaults': ['MaterialExpressionConstant4Vector_4', 'MaterialExpressionConstant4Vector_5', 'MaterialExpressionConstant4Vector_6']}},
              soft={'current': {'call': 'MaterialExpressionMaterialFunctionCall_20', 'switches': ['MaterialExpressionStaticSwitchParameter_34', 'MaterialExpressionStaticSwitchParameter_52']},
                    'previous': {'call': 'MaterialExpressionMaterialFunctionCall_19', 'switches': ['MaterialExpressionStaticSwitchParameter_45', 'MaterialExpressionStaticSwitchParameter_47']}},
              fluid={'call': 'MaterialExpressionMaterialFunctionCall_24', 'current': ['MaterialExpressionStaticSwitchParameter_50', 'MaterialExpressionStaticSwitchParameter_53'],
                     'previous': ['MaterialExpressionStaticSwitchParameter_41', 'MaterialExpressionStaticSwitchParameter_42']},
              tilt={'vector': local, 'textures': ['MaterialExpressionTextureObjectParameter_7', 'MaterialExpressionTextureObjectParameter_8'],
                    'current': {'call': 'MaterialExpressionMaterialFunctionCall_18', 'switches': ['MaterialExpressionStaticSwitchParameter_25', 'MaterialExpressionStaticSwitchParameter_26'],
                                'tilt': tilt_now},
                    'previous': {'call': 'MaterialExpressionMaterialFunctionCall_16', 'switches': ['MaterialExpressionStaticSwitchParameter_30', 'MaterialExpressionStaticSwitchParameter_32'],
                                 'tilt': tilt_prev}})
    m.pin('VertexContextVector0', Node('AppendVector', {'A': const3('MaterialExpressionConstant3Vector_15', (0, 0, 0)), 'B': switch(
        'MaterialExpressionStaticSwitchParameter_29', 'IdentifierCoverage', Node('Multiply', {'A': coord}, name='MaterialExpressionMultiply_15', ConstB=256.0),
        Node('Constant', name='MaterialExpressionConstant_9', R=0.0))}))
    m.props.update(shading_model='MSM_DefaultLit', tangent_space_normal=True)
    return m


_SHARED = {}


def scalar(name, param, group, default=0.0):
    # one node per name in a master (a parameter read in several places)
    if name not in _SHARED:
        _SHARED[name] = Node('ScalarParameter', name=name, ParameterName=param, Group=group, DefaultValue=default)
    return _SHARED[name]


def const3(name, v):
    return Node('Constant3Vector', name=name, Constant=tuple(v) + (0.0,))


def standard_emissive(uv0, uv2, mrv, flow=True, reference=True, conditional=True, extra_add='MaterialExpressionAdd_0', interior=True,
                      flow_names=('MaterialExpressionTextureSampleParameter2D_20', 'MaterialExpressionTextureSampleParameter2D_21'),
                      conditional_off='MaterialExpressionConstant_7'):
    """EndMaterial_Standard's emissive: a base layer (a texture, its LDR one, or white), an extra layer on UV2 that the
    coordinate offsets move, a flow layer (UV2 carried along the flow map, two phases blended), an interior (a cube map
    seen through the UV2 tile), tinted by the stationary and the dynamic colours, scaled by the variant channel, the
    game's conditional scale, and - unless the material radiates - nothing while the game bakes. EndMaterial_Subsurface's
    is the same nodes without the flow and the interior (flow=False), Reference and ConditionalEmissive"""
    baking = call('MaterialExpressionMaterialFunctionCall_12', 'DetectBaking')

    def layer(hdr, ldr, sw_ldr, m_ldr, m_hdr):
        return switch(sw_ldr, 'LDREmissive', mask(m_ldr, ldr, 'rgb'), mask(m_hdr, hdr, 'rgb'))

    # the base layer
    base = switch('MaterialExpressionStaticSwitchParameter_13', 'IdentityEmissive', const3('MaterialExpressionConstant3Vector_3', (1, 1, 1)),
                  layer(tex('MaterialExpressionTextureSampleParameter2D_26', '0:4:Emissive', uv0, 'LinearColor', '000000FF_HDR'),
                        tex('MaterialExpressionTextureSampleParameter2D_10', '0:6:LDREmissive', uv0, 'Color', '000000FF_sRGB'),
                        'MaterialExpressionStaticSwitchParameter_11', 'MaterialExpressionComponentMask_16', 'MaterialExpressionComponentMask_14'))
    # the extra layer, on UV2 moved by the stationary and the dynamic offsets
    soff = switch('MaterialExpressionStaticSwitchParameter_10', 'StationaryEmissive',
                  Node('AppendVector', {'A': scalar('MaterialExpressionScalarParameter_9', 'StationaryCoordinateOffset_X', 'Stationary'),
                                        'B': scalar('MaterialExpressionScalarParameter_10', 'StationaryCoordinateOffset_Y', 'Stationary')},
                       name='MaterialExpressionAppendVector_1'),
                  Node('Constant2Vector', name='MaterialExpressionConstant2Vector_0', R=0.0, G=0.0))
    doff = switch('MaterialExpressionStaticSwitchParameter_9', 'DynamicEmissive',
                  Node('AppendVector', {'A': scalar('MaterialExpressionScalarParameter_0', 'DynamicCoordinateOffset_X', 'Dynamic'),
                                        'B': scalar('MaterialExpressionScalarParameter_4', 'DynamicCoordinateOffset_Y', 'Dynamic')},
                       name='MaterialExpressionAppendVector_0'),
                  Node('Constant2Vector', name='MaterialExpressionConstant2Vector_1', R=0.0, G=0.0))
    extra_uv = Node('Add', {'A': uv2, 'B': Node('Add', {'A': soff, 'B': doff})}, name=extra_add)
    # (no game instance has IdentityEmissive with ExtraEmissive: white, as the base's)
    extra = switch('MaterialExpressionStaticSwitchParameter_21', 'ExtraEmissive',
                   switch('MaterialExpressionStaticSwitchParameter_31', 'IdentityEmissive', const3('MaterialExpressionConstant3Vector_9', (1, 1, 1)),
                          layer(tex('MaterialExpressionTextureSampleParameter2D_8', '2:4:Emissive', extra_uv, 'LinearColor', '000000FF_HDR'),
                                tex('MaterialExpressionTextureSampleParameter2D_11', '2:5:LDREmissive', extra_uv, 'Color', '000000FF_sRGB'),
                                'MaterialExpressionStaticSwitchParameter_12', 'MaterialExpressionComponentMask_17', 'MaterialExpressionComponentMask_15')),
                   const3('MaterialExpressionConstant3Vector_14', (0, 0, 0)))
    if not flow:
        return standard_emissive_tail(Node('Add', {'A': base, 'B': extra}), mrv, baking, reference, conditional, conditional_off)
    # the flow layer: UV2 carried along the flow direction (speed x distance per unit of phase), two phases half a period
    # apart blended so that each fades out as it wraps; the distortion map offsets the phase
    speed = tex(flow_names[0], '0:6:FlowSpeed/Distortion/Distance', uv0, 'LinearColor', 'FF00FFFF')
    direction = tex('MaterialExpressionTextureSampleParameter2D_18', '0:7:FlowDirection', uv0, 'LinearColor', '8080FF00')
    phase = Node('Add', {'A': (speed, 2), 'B': scalar('MaterialExpressionScalarParameter_11', 'AnimateTime', 'Dynamic')})
    p0 = Node('Frac', {'Input': phase})
    p1 = Node('Frac', {'Input': Node('Add', {'A': phase}, ConstB=0.5)})
    flow_dir = custom('return normalize(-(Direction * 2.0 - 1.0));', {'Direction': mask('MaterialExpressionComponentMask_31', direction, 'rg')},
                      2, 'Flow direction')
    reach = Node('Multiply', {'A': (speed, 3), 'B': (speed, 1)})
    uv_a = Node('Add', {'A': Node('Multiply', {'A': Node('Multiply', {'A': p0, 'B': flow_dir}), 'B': reach}), 'B': uv2},
                name='MaterialExpressionAdd_5')
    uv_b = Node('Add', {'A': Node('Multiply', {'A': Node('Multiply', {'A': p1, 'B': flow_dir}), 'B': reach}), 'B': uv2},
                name='MaterialExpressionAdd_6')
    flow_a = layer(tex('MaterialExpressionTextureSampleParameter2D_12', '2:4:Emissive', uv_a, 'LinearColor', '000000FF_HDR'),
                   tex('MaterialExpressionTextureSampleParameter2D_13', '2:5:LDREmissive', uv_a, 'Color', '000000FF_sRGB'),
                   'MaterialExpressionStaticSwitchParameter_17', 'MaterialExpressionComponentMask_20', 'MaterialExpressionComponentMask_19')
    flow_b = layer(tex('MaterialExpressionTextureSampleParameter2D_15', '2:4:Emissive', uv_b, 'LinearColor', '000000FF_HDR'),
                   tex('MaterialExpressionTextureSampleParameter2D_16', '2:5:LDREmissive', uv_b, 'Color', '000000FF_sRGB'),
                   'MaterialExpressionStaticSwitchParameter_18', 'MaterialExpressionComponentMask_22', 'MaterialExpressionComponentMask_21')
    blend = Node('Abs', {'Input': Node('Subtract', {'A': Node('Multiply', {'A': p0}, ConstB=2.0)}, ConstB=1.0)})
    flow_opacity = tex(flow_names[1], '0:8:FlowOpacity', uv0, 'Alpha', 'FF000000_BC4')
    flowing = Node('Multiply', {'A': Node('Multiply', {'A': Node('LinearInterpolate', {'A': flow_a, 'B': flow_b, 'Alpha': blend}),
                                                        'B': (flow_opacity, 4)}),
                                'B': Node('OneMinus', {'Input': baking})}, name='MaterialExpressionMultiply_11')
    flow = switch('MaterialExpressionStaticSwitchParameter_16', 'FlowEmissive', flowing, const3('MaterialExpressionConstant3Vector_4', (0, 0, 0)))
    if not interior:
        return standard_emissive_tail(Node('Add', {'A': Node('Add', {'A': base, 'B': extra}), 'B': flow}), mrv, baking, reference, conditional,
                                      conditional_off)
    # the interior: each quarter of the UV2 tile a room (turned by a quarter turn per quarter), its cube map seen where the
    # view (in tangent space) leaves the room's box
    view_t = Node('Transform', {'Input': Node('CameraVectorWS')}, TransformSourceType='TRANSFORMSOURCE_World', TransformType='TRANSFORM_Tangent')
    room = custom('''
float2 Tile = UV * 2.0;
int2 Cell = int2(Tile);
float Turn = float((Cell.x + Cell.y * 2) & 3) * 1.5707964;
float2 Local = frac(Tile) * 2.0 - 1.0;
float3 P = float3(Local.x, -Local.y, -1.0);
float3 D = float3(-View.x, View.y, View.z);
float3 InvD = 1.0 / D;
float3 T = abs(InvD) - P * InvD;
float3 H = min(min(T.z, T.y), T.x) * D + P;
float S, C;
sincos(Turn, S, C);
return float3(H.z * C + H.x * S, H.x * C - H.z * S, H.y);''', {'UV': uv2, 'View': view_t}, 3, 'Interior', name='MaterialExpressionCustom_9')
    cube_hdr = Node('TextureSampleParameterCube', {'Coordinates': room}, name='MaterialExpressionTextureSampleParameterCube_2',
                    ParameterName='0:7:EmissiveCube', SamplerType='LinearColor', Texture='000000FF_Cube', Group='Texture', Cube=True)
    cube_ldr = Node('TextureSampleParameterCube', {'Coordinates': room}, name='MaterialExpressionTextureSampleParameterCube_0',
                    ParameterName='0:8:LDREmissiveCube', SamplerType='Color', Texture='000000FF_sRGB_Cube', Group='Texture', Cube=True)
    interior = switch('MaterialExpressionStaticSwitchParameter_22', 'CubeEmissive',
                      layer(cube_hdr, cube_ldr, 'MaterialExpressionStaticSwitchParameter_23', 'MaterialExpressionComponentMask_30',
                            'MaterialExpressionComponentMask_29'),
                      const3('MaterialExpressionConstant3Vector_5', (0, 0, 0)))
    color = Node('Add', {'A': interior, 'B': Node('Add', {'A': Node('Add', {'A': base, 'B': extra}), 'B': flow})})
    return standard_emissive_tail(color, mrv, baking, reference, conditional, conditional_off)


def standard_emissive_tail(color, mrv, baking, reference=True, conditional=True, conditional_off='MaterialExpressionConstant_7'):
    """the Standard emissive's tints and scales (its nodes' names: Standard's, Subsurface's and InvisibleBody's)"""
    # the tints
    stationary = switch('MaterialExpressionStaticSwitchParameter_8', 'StationaryEmissive',
                        Node('Multiply', {'A': call('MaterialExpressionMaterialFunctionCall_14', 'CompositeColor',
                                                    R=scalar('MaterialExpressionScalarParameter_6', 'StationaryEmissiveColor_X', 'Stationary', 1.0),
                                                    G=scalar('MaterialExpressionScalarParameter_7', 'StationaryEmissiveColor_Y', 'Stationary', 1.0),
                                                    B=scalar('MaterialExpressionScalarParameter_8', 'StationaryEmissiveColor_Z', 'Stationary', 1.0)),
                                          'B': scalar('MaterialExpressionScalarParameter_5', 'StationaryEmissiveIntensity', 'Stationary', 1.0)},
                             name='MaterialExpressionMultiply_4'),
                        const3('MaterialExpressionConstant3Vector_2', (1, 1, 1)))
    dynamic = switch('MaterialExpressionStaticSwitchParameter_6', 'DynamicEmissive',
                     Node('Multiply', {'A': call('MaterialExpressionMaterialFunctionCall_13', 'CompositeColor',
                                                 R=scalar('MaterialExpressionScalarParameter_1', 'DynamicEmissiveColor_X', 'Dynamic', 1.0),
                                                 G=scalar('MaterialExpressionScalarParameter_2', 'DynamicEmissiveColor_Y', 'Dynamic', 1.0),
                                                 B=scalar('MaterialExpressionScalarParameter_3', 'DynamicEmissiveColor_Z', 'Dynamic', 1.0)),
                                       'B': scalar('MaterialExpressionScalarParameter_17', 'DynamicEmissiveIntensity', 'Dynamic', 1.0)},
                          name='MaterialExpressionMultiply_6'),
                     const3('MaterialExpressionConstant3Vector_1', (1, 1, 1)))
    color = Node('Multiply', {'A': Node('Multiply', {'A': color, 'B': stationary}), 'B': dynamic})
    # the variant channel (no game instance turns Reference on: as off)
    if reference:
        variant = mask('MaterialExpressionComponentMask_23', (mrv, 3), 'r')
        variant = switch('MaterialExpressionStaticSwitchParameter_19', 'Reference', Node('Multiply', {'A': variant}, name='MaterialExpressionMultiply_7', ConstB=1.0),
                         variant)
    else:
        variant = mask(None, (mrv, 3), 'r')
    radiation = custom('return Baking != 0.0 ? Radiation : 1.0;',
                       {'Radiation': switch('MaterialExpressionStaticSwitchParameter_5', 'Radiation', Node('Constant', name='MaterialExpressionConstant_1', R=1.0),
                                            Node('Constant', name='MaterialExpressionConstant_2', R=0.0)),
                        'Baking': baking}, 1, 'Radiation')
    scaled = Node('Multiply', {'A': color, 'B': variant})
    if conditional:
        scaled = Node('Multiply', {'A': scaled, 'B': switch('MaterialExpressionStaticSwitchParameter_27', 'ConditionalEmissive',
                                                            Node('ExternalHook', name='MaterialExpressionCustom_29', Hook='ConditionalEmissive', Type=1),
                                                            Node('Constant', name=conditional_off, R=1.0))})
    emissive = Node('Multiply', {'A': scaled, 'B': radiation}, name='MaterialExpressionMultiply_5')
    return switch('MaterialExpressionStaticSwitchParameter_3', 'Emissive', emissive, const3('MaterialExpressionConstant3Vector_0', (0, 0, 0)))


def EndMaterial_Skin():
    _SHARED.clear()
    m = Material('EndMaterial_Skin', M_ROOT + '/EndMaterial_Skin')
    uv0 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_1', CoordinateIndex=0)
    uv1 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_3', CoordinateIndex=1)
    uv2 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_8', CoordinateIndex=2)

    color = tex('MaterialExpressionTextureSampleParameter2D_6', '0:0:Color', uv0, 'Color', '767676FF_sRGB')
    normal = tex('MaterialExpressionTextureSampleParameter2D_7', '0:3:Normal', uv0, 'LinearColor', '8080FF00')
    wrinkle = tex('MaterialExpressionTextureSampleParameter2D_2', '0:4:WrinkleNormal', uv0, 'LinearColor', '8080FF00')
    mrv = tex('MaterialExpressionTextureSampleParameter2D_4', '0:2:Metallic/Roughness/Variant', uv0, 'LinearColor', '008000FF')
    occl = tex('MaterialExpressionTextureSampleParameter2D_5', '1:0:Occlusion', uv1, 'Alpha', 'FF000000_BC4')
    dopac = tex('MaterialExpressionTextureSampleParameter2D_17', '0:5:DetailOpacity', uv0, 'LinearColor', '000000FF')
    dnorm = [tex('MaterialExpressionTextureSampleParameter2D_14', '2:0:DetailNormal:0', uv2, 'LinearColor', '8080FF00'),
             tex('MaterialExpressionTextureSampleParameter2D_0', '2:1:DetailNormal:1', uv2, 'LinearColor', '8080FF00'),
             tex('MaterialExpressionTextureSampleParameter2D_1', '2:2:DetailNormal:2', uv2, 'LinearColor', '8080FF00')]
    pores = [tex('MaterialExpressionTextureSampleParameter2D_3', '2:0:DetailPores:0', uv2, 'Alpha', 'FF000000_BC4'),
             tex('MaterialExpressionTextureSampleParameter2D_8', '2:1:DetailPores:1', uv2, 'Alpha', 'FF000000_BC4'),
             tex('MaterialExpressionTextureSampleParameter2D_9', '2:2:DetailPores:2', uv2, 'Alpha', 'FF000000_BC4')]

    # normal: the base map (or, with BoneExpressive, the base map turned from the wrinkle map), then the detail maps
    base_n = call('MaterialExpressionMaterialFunctionCall_1', 'NormalizeNormalRG', NormalRG=mask('MaterialExpressionComponentMask_3', normal, 'rg'))
    wrinkle_n = call('MaterialExpressionMaterialFunctionCall_13', 'NormalizeNormalRG', NormalRG=mask('MaterialExpressionComponentMask_7', wrinkle, 'rg'))
    # the base normal turned toward the wrinkle normal by the expression's weight (the game's shader: none), along the
    # shorter arc (the game's spherical interpolation: the sign on the first vector's angle)
    expressive = custom(SLERP_PREFIX + '''
float Theta = acos(min(abs(D), 0.9995));''' + SLERP_SUFFIX, {'From': base_n, 'To': wrinkle_n,
                                                            'Alpha': Node('Constant', name='MaterialExpressionConstant_2', R=0.0)},
                        3, 'Bone expressive normal', name='MaterialExpressionCustom_1')
    sw3 = switch('MaterialExpressionStaticSwitchParameter_3', 'BoneExpressive', expressive, base_n, 'STATIC_SWITCH_BONE_EXPRESSIVE')
    prev = sw3
    for k, (nmask, ncall, om, fcall, bcall, sw) in enumerate([
            ('MaterialExpressionComponentMask_8', 'MaterialExpressionMaterialFunctionCall_4', 'MaterialExpressionOneMinus_0',
             'MaterialExpressionMaterialFunctionCall_6', 'MaterialExpressionMaterialFunctionCall_0', 'MaterialExpressionStaticSwitchParameter_0'),
            ('MaterialExpressionComponentMask_0', 'MaterialExpressionMaterialFunctionCall_2', 'MaterialExpressionOneMinus_1',
             'MaterialExpressionMaterialFunctionCall_3', 'MaterialExpressionMaterialFunctionCall_7', 'MaterialExpressionStaticSwitchParameter_1'),
            ('MaterialExpressionComponentMask_1', 'MaterialExpressionMaterialFunctionCall_8', 'MaterialExpressionOneMinus_2',
             'MaterialExpressionMaterialFunctionCall_9', 'MaterialExpressionMaterialFunctionCall_10', 'MaterialExpressionStaticSwitchParameter_2')]):
        dn = call(ncall, 'NormalizeNormalRG', NormalRG=mask(nmask, dnorm[k], 'rg'))
        flat = call(fcall, 'FlattenNormal', Normal=dn, Value=Node('OneMinus', {'Input': (dopac, 1 + k)}, name=om))
        prev = switch(sw, 'Detail:%d' % k, call(bcall, 'BlendNormal', Normal0=prev, Normal1=flat), prev)
    m.pin('Normal', prev)

    m.pin('BaseColor', mask('MaterialExpressionComponentMask_2', color, 'rgb'))
    m.pin('Metallic', Node('Constant', name='MaterialExpressionConstant_1', R=0.0))
    m.pin('Roughness', mask('MaterialExpressionComponentMask_5', (mrv, 5), 'g'))
    # specular: the variant channel, darkened by each detail's pores where the detail shows, as a reflectance
    variant = mask('MaterialExpressionComponentMask_6', (mrv, 5), 'b')
    prev = variant
    for k, (lname, mname, sw) in enumerate([
            ('MaterialExpressionLinearInterpolate_0', 'MaterialExpressionMultiply_0', 'MaterialExpressionStaticSwitchParameter_4'),
            ('MaterialExpressionLinearInterpolate_1', 'MaterialExpressionMultiply_1', 'MaterialExpressionStaticSwitchParameter_5'),
            ('MaterialExpressionLinearInterpolate_2', 'MaterialExpressionMultiply_3', 'MaterialExpressionStaticSwitchParameter_6')]):
        pore = Node('LinearInterpolate', {'B': (pores[k], 4), 'Alpha': (dopac, 1 + k)}, name=lname, ConstA=1.0)
        prev = switch(sw, 'Detail:%d' % k, Node('Multiply', {'A': pore, 'B': prev}, name=mname), prev)
    refl = Node('Max', {'A': Node('Multiply', {'A': prev}, name='MaterialExpressionMultiply_2', ConstB=0.0325)},
                name='MaterialExpressionMax_0', ConstB=0.0025)
    m.pin('Specular', call('MaterialExpressionMaterialFunctionCall_5', 'EncodeReflectance', Reflectance=refl))
    m.pin('AmbientOcclusion', mask('MaterialExpressionComponentMask_18', (occl, 5), 'a'))
    m.pin('Opacity', Node('Constant', name='MaterialExpressionConstant_0', R=1.0))
    coord = mask('MaterialExpressionComponentMask_36', Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_11', CoordinateIndex=3), 'r')
    animation(m, coord,
              rigid={'current': {'call': 'MaterialExpressionMaterialFunctionCall_15', 'switches': ['MaterialExpressionStaticSwitchParameter_15', 'MaterialExpressionStaticSwitchParameter_51', 'MaterialExpressionStaticSwitchParameter_54'],
                                 'defaults': ['MaterialExpressionConstant4Vector_7', 'MaterialExpressionConstant4Vector_8', 'MaterialExpressionConstant4Vector_9']},
                     'previous': {'call': 'MaterialExpressionMaterialFunctionCall_28', 'switches': ['MaterialExpressionStaticSwitchParameter_77', 'MaterialExpressionStaticSwitchParameter_79', 'MaterialExpressionStaticSwitchParameter_76'],
                                  'defaults': ['MaterialExpressionConstant4Vector_19', 'MaterialExpressionConstant4Vector_20', 'MaterialExpressionConstant4Vector_21']}},
              soft={'current': {'call': 'MaterialExpressionMaterialFunctionCall_20', 'switches': ['MaterialExpressionStaticSwitchParameter_34', 'MaterialExpressionStaticSwitchParameter_52']},
                    'previous': {'call': 'MaterialExpressionMaterialFunctionCall_29', 'switches': ['MaterialExpressionStaticSwitchParameter_78', 'MaterialExpressionStaticSwitchParameter_80']}},
              fluid={'call': 'MaterialExpressionMaterialFunctionCall_24', 'current': ['MaterialExpressionStaticSwitchParameter_50', 'MaterialExpressionStaticSwitchParameter_53'],
                     'previous': ['MaterialExpressionStaticSwitchParameter_74', 'MaterialExpressionStaticSwitchParameter_75']})
    m.props.update(shading_model='MSM_PreintegratedSkin', tangent_space_normal=True)
    return m


def EndMaterial_Hair():
    _SHARED.clear()
    m = Material('EndMaterial_Hair', M_ROOT + '/EndMaterial_Hair')
    uv0 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_1', CoordinateIndex=0)
    uv1 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_3', CoordinateIndex=1)

    color = tex('MaterialExpressionTextureSampleParameter2D_6', '0:0:Color', uv0, 'Color', '767676FF_sRGB')
    normal = tex('MaterialExpressionTextureSampleParameter2D_7', '0:3:Normal', uv0, 'LinearColor', '8080FF00')
    mrv = tex('MaterialExpressionTextureSampleParameter2D_4', '0:2:Metallic/Roughness/Variant', uv0, 'LinearColor', '008000FF')
    cover = tex('MaterialExpressionTextureSampleParameter2D_2', '0:1:Coverage', uv0, 'Alpha', 'FF000000_BC4')
    occl = tex('MaterialExpressionTextureSampleParameter2D_5', '1:0:Occlusion', uv1, 'Alpha', 'FF000000_BC4')
    bent = tex('MaterialExpressionTextureSampleParameter2D_0', '1:1:BentNormal', uv1, 'LinearColor', '8080FF00')

    # the normal: with TransformedNormal (the game's hair), the world-space normal facing the camera square to the strand,
    # which runs along the normal map's up (green) direction; the switch only sets the define both its inputs read
    n = call('MaterialExpressionMaterialFunctionCall_1', 'NormalizeNormalRG', NormalRG=mask('MaterialExpressionComponentMask_3', normal, 'rg'))
    transformed = custom('''
#if STATIC_SWITCH_TRANSFORMED_NORMAL
float3 Across = normalize(cross(float3(0.0, 1.0, 0.0), Normal));
float3 Strand = mul(cross(Across, Normal), Parameters.TangentToWorld);
return normalize(Parameters.CameraVector - dot(Parameters.CameraVector, Strand) * Strand);
#else
return Normal;
#endif''', {'Normal': n}, 3, 'Hair normal', name='MaterialExpressionCustom_0')
    m.pin('Normal', switch('MaterialExpressionStaticSwitchParameter_0', 'TransformedNormal', transformed, transformed,
                           'STATIC_SWITCH_TRANSFORMED_NORMAL', default=True))
    m.pin('BaseColor', mask('MaterialExpressionComponentMask_2', color, 'rgb'))
    m.pin('Metallic', Node('Constant', name='MaterialExpressionConstant_1', R=0.0))
    # keratin's reflectance (index of refraction 1.55)
    m.pin('Specular', call('MaterialExpressionMaterialFunctionCall_5', 'EncodeReflectance',
                           Reflectance=Node('Constant', name='MaterialExpressionConstant_3', R=0.04652)))
    m.pin('Roughness', mask('MaterialExpressionComponentMask_5', (mrv, 5), 'g'))
    m.pin('OpacityMask', switch('MaterialExpressionStaticSwitchParameter_4', 'Coverage', mask('MaterialExpressionComponentMask_16', (cover, 5), 'a'),
                                Node('Constant', name='MaterialExpressionConstant_0', R=1.0)))
    m.pin('AmbientOcclusion', custom(OCCLUSION_MIX, {'Detail': (mrv, 3), 'Base': (occl, 4)}, 1, 'Variant occlusion',
                                     name='MaterialExpressionCustom_2'))
    # the bent normal, in world space, as the tangent output (GBuffer D, where the other models have the vertex normal)
    bent_n = call('MaterialExpressionMaterialFunctionCall_0', 'NormalizeNormalRGB', NormalRGB=mask('MaterialExpressionComponentMask_0', bent, 'rgb'))
    m.pin('TangentOutput', Node('Transform', {'Input': bent_n}, TransformSourceType='TRANSFORMSOURCE_Tangent',
                                TransformType='TRANSFORM_World'))
    # each card its own noise slice for the coverage's dither: its id from UV2's u
    m.pin('VertexContextVector0', Node('AppendVector', {'A': const3(None, (0, 0, 0)), 'B': Node('Multiply', {'A': mask(None, Node(
        'TextureCoordinate', CoordinateIndex=2), 'r')}, ConstB=256.0)}))
    m.props.update(shading_model='MSM_Hair', tangent_space_normal=True)
    return m


# the eye: a frame about the gaze normal (the eye's own normal map), its tangent from the mesh's
EYE_FRAME = """
float3 B = normalize(cross(Gaze, Parameters.TangentToWorld[0])) * Parameters.UnMirrored;
float3 T = normalize(cross(B, Gaze)) * Parameters.UnMirrored;"""


def EndMaterial_Eye():
    _SHARED.clear()
    m = Material('EndMaterial_Eye', M_ROOT + '/EndMaterial_Eye')
    uv0 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_1', CoordinateIndex=0)
    uv1 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_3', CoordinateIndex=1)

    normal = tex('MaterialExpressionTextureSampleParameter2D_7', '0:3:Normal', uv0, 'LinearColor', '8080FF00')
    gaze = tex('MaterialExpressionTextureSampleParameter2D_1', '0:5:Normal(Gaze)', uv0, 'LinearColor', '8080FF00')
    inner = tex('MaterialExpressionTextureSampleParameter2D_0', '0:4:Normal(Inner)', uv0, 'LinearColor', '8080FF00')
    occl = tex('MaterialExpressionTextureSampleParameter2D_5', '1:0:Occlusion', uv1, 'Alpha', 'FF000000_BC4')

    def world(n):
        return Node('Transform', {'Input': n}, TransformSourceType='TRANSFORMSOURCE_Tangent', TransformType='TRANSFORM_World')
    sclera_w = world(call('MaterialExpressionMaterialFunctionCall_1', 'NormalizeNormalRG', NormalRG=mask('MaterialExpressionComponentMask_3', normal, 'rg')))
    gaze_w = world(call('MaterialExpressionMaterialFunctionCall_2', 'NormalizeNormalRG', NormalRG=mask('MaterialExpressionComponentMask_0', gaze, 'rg')))
    inner_w = world(call('MaterialExpressionMaterialFunctionCall_4', 'NormalizeNormalRG', NormalRG=mask('MaterialExpressionComponentMask_1', inner, 'rg')))

    # the cornea: a dome over the iris (P: the distance from the eye's center in iris radii; its height
    # 0.385 (1 - R^2) + 0.0385), its normal from its two tangents (radial, around), in the gaze frame
    cornea = custom(EYE_FRAME + """
float2 P = (UV * 2.0 - 1.0) * 2.0;
float R = length(P);
float2 D = normalize(P);
float3 N = normalize(cross(float3(D, -0.77 * R), float3(-D.y, D.x, 0.0)));
return mul(N, float3x3(T, B, Gaze));""", {'UV': uv0, 'Gaze': gaze_w}, 3, 'Cornea normal')
    cornea_mask = custom("""
float R = length((UV * 2.0 - 1.0) * 2.0);
return saturate(1.0 - smoothstep(0.8, 1.2, R));""", {'UV': uv0}, 1, 'Cornea mask')
    surface = Node('Normalize', {'VectorInput': Node('LinearInterpolate', {'A': sclera_w, 'B': cornea, 'Alpha': cornea_mask})},
                   name='MaterialExpressionNormalize_0')
    m.pin('Normal', switch('MaterialExpressionStaticSwitchParameter_0', 'TransformedNormal', surface, surface,
                           'STATIC_SWITCH_TRANSFORMED_NORMAL', default=True))

    # the iris seen through the cornea: the view refracted at the cornea (index of refraction 1.38), carried down to the
    # iris plane through the cornea's depth there
    offset = custom(EYE_FRAME + """
float2 P = (UV * 2.0 - 1.0) * 2.0;
float R2 = dot(P, P);
float3 Ray = refract(-Parameters.CameraVector, Cornea, 1.0 / 1.38);
float3 L = float3(dot(T, Ray), dot(B, Ray), dot(Gaze, Ray));
float Depth = saturate(1.0 - R2) * 0.385 + (1.0 - saturate((R2 - 1.0) / 0.2)) * 0.0385;
return L.xy / -L.z * Depth * 0.32;""", {'UV': uv0, 'Gaze': gaze_w, 'Cornea': cornea}, 2, 'Iris offset')
    iris_uv = Node('Add', {'A': uv0, 'B': offset}, name='MaterialExpressionAdd_3')
    color = tex('MaterialExpressionTextureSampleParameter2D_6', '0:0:Color', iris_uv, 'Color', '767676FF_sRGB')
    emissive = tex('MaterialExpressionTextureSampleParameter2D_26', '0:6:Emissive', iris_uv, 'LinearColor', '000000FF_HDR')
    m.pin('BaseColor', mask('MaterialExpressionComponentMask_2', color, 'rgb'))
    m.pin('Metallic', Node('Constant', name='MaterialExpressionConstant_20', R=0.0))
    m.pin('Roughness', Node('Constant', name='MaterialExpressionConstant_21', R=0.1))
    # the ring about the iris's edge (0 at the center and outside, 1 at two thirds of the radius)
    ring = custom("""
float2 P = (UV * 2.0 - 1.0) * 2.0;
float R2 = dot(P, P);
return saturate(saturate(R2) * saturate(1.0 - sqrt(R2)) / 0.149);""", {'UV': iris_uv}, 1, 'Iris ring')
    m.pin('Specular', call('MaterialExpressionMaterialFunctionCall_12', 'EncodeReflectance',
                           Reflectance=Node('Add', {'A': Node('Multiply', {'A': ring}, ConstB=0.004)}, name='MaterialExpressionAdd_1', ConstB=0.0455)))
    m.pin('AmbientOcclusion', mask('MaterialExpressionComponentMask_16', (occl, 5), 'a'))
    m.pin('IrisMask', Node('LinearInterpolate', {'Alpha': ring}, ConstA=0.5, ConstB=0.7))
    # the iris's normal (the tangent output): the sclera's out to the cornea's edge, the gaze normal's to the iris's edge,
    # within it a bowl about the center, blended with the inner normal map at the edge
    m.pin('TangentOutput', custom(EYE_FRAME + """
float2 P = (UV * 2.0 - 1.0) * 2.0;
float R2 = dot(P, P);
float R = sqrt(R2);
float InIris = saturate(1.0 - smoothstep(0.9, 1.0, R));
float InCornea = saturate(1.0 - smoothstep(0.8, 1.2, R));
float3 Outer = lerp(Sclera, Gaze, InIris);
Outer = Outer / length(Outer);
float3 Bowl = mul(normalize(float3(-P, max(2.25 - R2, 0.0))), float3x3(T, B, Gaze));
float3 Iris = lerp(Inner, Bowl, InIris);
Iris = Iris / length(Iris);
float3 N = lerp(Outer, Iris, InCornea);
return N / length(N);""", {'UV': iris_uv, 'Sclera': sclera_w, 'Gaze': gaze_w, 'Inner': inner_w}, 3, 'Iris normal'))

    tint = call('MaterialExpressionMaterialFunctionCall_13', 'CompositeColor',
                R=Node('ScalarParameter', name='MaterialExpressionScalarParameter_1', ParameterName='DynamicEmissiveColor_X', DefaultValue=1.0, Group='Dynamic'),
                G=Node('ScalarParameter', name='MaterialExpressionScalarParameter_2', ParameterName='DynamicEmissiveColor_Y', DefaultValue=1.0, Group='Dynamic'),
                B=Node('ScalarParameter', name='MaterialExpressionScalarParameter_3', ParameterName='DynamicEmissiveColor_Z', DefaultValue=1.0, Group='Dynamic'))
    dyn = switch('MaterialExpressionStaticSwitchParameter_6', 'DynamicEmissive',
                 Node('Multiply', {'A': tint, 'B': Node('ScalarParameter', name='MaterialExpressionScalarParameter_17',
                                                         ParameterName='DynamicEmissiveIntensity', DefaultValue=1.0, Group='Dynamic')},
                      name='MaterialExpressionMultiply_6'),
                 Node('Constant3Vector', name='MaterialExpressionConstant3Vector_2', Constant=(1.0, 1.0, 1.0, 0.0)))
    m.pin('EmissiveColor', switch('MaterialExpressionStaticSwitchParameter_3', 'Emissive',
                                  Node('Multiply', {'A': mask('MaterialExpressionComponentMask_7', emissive, 'rgb'), 'B': dyn},
                                       name='MaterialExpressionMultiply_5'),
                                  Node('Constant3Vector', name='MaterialExpressionConstant3Vector_4', Constant=(0.0, 0.0, 0.0, 0.0))))
    m.props.update(shading_model='MSM_Eye', tangent_space_normal=True)
    return m


def EndMaterial_Sand():
    _SHARED.clear()
    m = Material('EndMaterial_Sand', M_ROOT + '/EndMaterial_Sand')
    uv0 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_1', CoordinateIndex=0)
    uv1 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_3', CoordinateIndex=1)
    # the flowed layers sampled with the unflowed coordinate's derivatives (no mip seam where the flow wraps)
    dx = Node('DDX', {'Value': uv0}, name='MaterialExpressionDDX_2')
    dy = Node('DDY', {'Value': uv0}, name='MaterialExpressionDDY_2')
    noise = Node('ExternalHook', Hook='BlueNoise', Type=3)

    def tx(name, param, uv, sampler, texture, derivative=False):
        n = Node('TextureSampleParameter2D', {'Coordinates': uv, 'CoordinatesDX': dx, 'CoordinatesDY': dy}, name=name, ParameterName=param,
                 SamplerType=sampler, Texture=texture, Group='Texture')
        if derivative:
            n.props['MipValueMode'] = 'TMVM_Derivative'
        return n
    speed = tx('MaterialExpressionTextureSampleParameter2D_8', '0:6:FlowSpeed/Distortion/Distance', uv0, 'LinearColor', 'FF00FFFF')
    direction = tx('MaterialExpressionTextureSampleParameter2D_18', '0:7:FlowDirection', uv0, 'LinearColor', '8080FF00')
    # the flow: the coordinate carried along the flow direction (speed x distance per unit of phase), the phase offset by the
    # noise (times the distortion), one of the two phases half a period apart chosen per pixel by the noise
    flowed = custom("""
float Phase = Noise * Speed.g + Time;
float P0 = frac(Phase);
float P1 = frac(Phase + 0.5);
float2 D = normalize(-(Direction * 2.0 - 1.0));
float Reach = Speed.b * Speed.r;
float2 A = P0 * D * Reach + UV;
float2 B = D * P1 * Reach + UV;
return abs(P0 * 2.0 - 1.0) < Noise ? A : B;""", {'UV': uv0, 'Speed': mask(None, speed, 'rgb'), 'Direction': mask(None, direction, 'rg'),
                                              'Time': scalar('MaterialExpressionScalarParameter_11', 'AnimateTime', 'Dynamic'),
                                              'Noise': mask(None, noise, 'r')}, 2, 'Flow', name='MaterialExpressionCustom_6')
    uv = switch('MaterialExpressionStaticSwitchParameter_5', 'Flow', flowed, uv0)
    normal = tx('MaterialExpressionTextureSampleParameter2D_7', '0:3:Normal', uv0, 'LinearColor', '8080FF00')
    detail = tx('MaterialExpressionTextureSampleParameter2D_1', '0:4:DetailNormal', uv, 'LinearColor', '8080FF00', True)
    color = tx('MaterialExpressionTextureSampleParameter2D_6', '0:0:Color', uv, 'Color', '767676FF_sRGB', True)
    mrv = tx('MaterialExpressionTextureSampleParameter2D_4', '0:2:Metallic/Roughness/Variant', uv0, 'LinearColor', '008000FF')
    cover = tx('MaterialExpressionTextureSampleParameter2D_2', '0:1:Coverage', uv0, 'Alpha', 'FF000000_BC4')
    occl = tex('MaterialExpressionTextureSampleParameter2D_5', '1:0:Occlusion', uv1, 'Alpha', 'FF000000_BC4')
    m.pin('Normal', call('MaterialExpressionMaterialFunctionCall_0', 'BlendNormal',
                         Normal0=call('MaterialExpressionMaterialFunctionCall_1', 'NormalizeNormalRG', NormalRG=mask('MaterialExpressionComponentMask_3', normal, 'rg')),
                         Normal1=call('MaterialExpressionMaterialFunctionCall_2', 'NormalizeNormalRG', NormalRG=mask('MaterialExpressionComponentMask_0', detail, 'rg'))))
    m.pin('BaseColor', mask('MaterialExpressionComponentMask_2', color, 'rgb'))
    m.pin('Metallic', mask('MaterialExpressionComponentMask_4', (mrv, 5), 'r'))
    # the grains: each pixel rough as far as the noise takes it
    m.pin('Roughness', Node('LinearInterpolate', {'A': mask('MaterialExpressionComponentMask_5', (mrv, 5), 'g'), 'Alpha': mask(None, noise, 'r')},
                            name='MaterialExpressionLinearInterpolate_0', ConstB=1.0))
    m.pin('Specular', call('MaterialExpressionMaterialFunctionCall_5', 'EncodeReflectance', Reflectance=Node('Constant', name='MaterialExpressionConstant_3', R=0.04)))
    m.pin('AmbientOcclusion', mask('MaterialExpressionComponentMask_11', (occl, 5), 'a'))
    # soft: the coverage fades in over 50 units in front of the game's extra scene depth
    soft = switch('MaterialExpressionStaticSwitchParameter_3', 'Soft', call('MaterialExpressionMaterialFunctionCall_11', 'HermiteLimited',
                  S=call('MaterialExpressionMaterialFunctionCall_16', 'ExtraSceneDepthFade', UnitDistance=Node('Constant', name='MaterialExpressionConstant_14', R=50.0)),
                  R=Node('Constant', name='MaterialExpressionConstant_15', R=1.0)), Node('Constant', name='MaterialExpressionConstant_10', R=1.0), default=True)
    coverage = switch('MaterialExpressionStaticSwitchParameter_4', 'Coverage', mask('MaterialExpressionComponentMask_12', (cover, 4), 'r'),
                      Node('Constant', name='MaterialExpressionConstant_0', R=1.0))
    opacity = Node('Multiply', {'A': soft, 'B': coverage}, name='MaterialExpressionMultiply_10')
    m.pin('OpacityMask', switch('MaterialExpressionStaticSwitchParameter_0', 'ExistentPixelVelocity', opacity, opacity,
                                'STATIC_SWITCH_EXISTENT_PIXEL_VELOCITY', default=True))
    # (the game's Reference switch reaches nothing these shaders read)
    m.extra_nodes = [switch('MaterialExpressionStaticSwitchParameter_19', 'Reference', Node('Multiply', {'A': mask(None, (mrv, 3), 'r')}, name='MaterialExpressionMultiply_7', ConstB=1.0),
                            mask('MaterialExpressionComponentMask_23', (mrv, 3), 'r'))]
    coord = mask('MaterialExpressionComponentMask_36', Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_11', CoordinateIndex=3), 'r')
    kmin = scalar('MaterialExpressionScalarParameter_0', 'AnimateKeyMinimum', 'Dynamic')
    kmax = scalar('MaterialExpressionScalarParameter_1', 'AnimateKeyMaximum', 'Dynamic')
    soft_tex = texobj('MaterialExpressionTextureObjectParameter_5', 'V:S:0:Translation')

    def distributed(sw, fc):
        return lambda k: switch(sw, 'DistributeAnimateKeyIndex', call(fc, 'DistributeAnimateKeyIndex', AnimateKeyIndex=k, AnimateKeyMinimum=kmin,
                                                                            AnimateKeyMaximum=kmax, AnimateTexture=soft_tex), k)
    animation(m, coord,
              rigid={'current': {'call': 'MaterialExpressionMaterialFunctionCall_15', 'switches': ['MaterialExpressionStaticSwitchParameter_15', 'MaterialExpressionStaticSwitchParameter_51', 'MaterialExpressionStaticSwitchParameter_54'],
                                 'defaults': ['MaterialExpressionConstant4Vector_7', 'MaterialExpressionConstant4Vector_8', 'MaterialExpressionConstant4Vector_9']},
                     'previous': {'call': 'MaterialExpressionMaterialFunctionCall_26', 'switches': ['MaterialExpressionStaticSwitchParameter_70', 'MaterialExpressionStaticSwitchParameter_72', 'MaterialExpressionStaticSwitchParameter_69'],
                                  'defaults': ['MaterialExpressionConstant4Vector_16', 'MaterialExpressionConstant4Vector_17', 'MaterialExpressionConstant4Vector_18']}},
              soft={'current': {'call': 'MaterialExpressionMaterialFunctionCall_20', 'switches': ['MaterialExpressionStaticSwitchParameter_34', 'MaterialExpressionStaticSwitchParameter_52'],
                                'index': distributed('MaterialExpressionStaticSwitchParameter_1', 'MaterialExpressionMaterialFunctionCall_3')},
                    'previous': {'call': 'MaterialExpressionMaterialFunctionCall_27', 'switches': ['MaterialExpressionStaticSwitchParameter_71', 'MaterialExpressionStaticSwitchParameter_73'],
                                 'index': distributed('MaterialExpressionStaticSwitchParameter_2', 'MaterialExpressionMaterialFunctionCall_4')}},
              fluid={'call': 'MaterialExpressionMaterialFunctionCall_24', 'current': ['MaterialExpressionStaticSwitchParameter_50', 'MaterialExpressionStaticSwitchParameter_53'],
                     'previous': ['MaterialExpressionStaticSwitchParameter_67', 'MaterialExpressionStaticSwitchParameter_68']})
    # each piece its own noise slice for the coverage's dither: its id from UV2's u
    m.pin('VertexContextVector0', Node('AppendVector', {'A': const3(None, (0, 0, 0)), 'B': Node('Multiply', {'A': mask(None, Node(
        'TextureCoordinate', CoordinateIndex=2), 'r')}, ConstB=256.0)}))
    m.props.update(shading_model='MSM_DefaultLit', tangent_space_normal=True)
    return m


def flow_phases(speed, direction, uv, time, adds):
    """the game's flow: the coordinate carried along the flow direction (speed x distance per unit of phase), the phase
    offset by the distortion; two phases half a period apart; returns the two coordinates and the first phase"""
    phase = Node('Add', {'A': (speed, 2), 'B': time})
    p0 = Node('Frac', {'Input': phase})
    p1 = Node('Frac', {'Input': Node('Add', {'A': phase}, ConstB=0.5)})
    d = custom('return normalize(-(Direction * 2.0 - 1.0));', {'Direction': mask(None, direction, 'rg')}, 2, 'Flow direction')
    reach = Node('Multiply', {'A': (speed, 3), 'B': (speed, 1)})
    uv_a = Node('Add', {'A': Node('Multiply', {'A': Node('Multiply', {'A': p0, 'B': d}), 'B': reach}), 'B': uv}, name=adds[0])
    uv_b = Node('Add', {'A': Node('Multiply', {'A': Node('Multiply', {'A': p1, 'B': d}), 'B': reach}), 'B': uv}, name=adds[1])
    return uv_a, uv_b, phase


FLOW_BLEND = """
return lerp(A, B, abs(frac(Phase) * 2.0 - 1.0));"""


def EndMaterial_BlackBody():
    _SHARED.clear()
    m = Material('EndMaterial_BlackBody', M_ROOT + '/EndMaterial_BlackBody')
    uv0 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_1', CoordinateIndex=0)
    # FixedCoordinate: the base layers in the view's own coordinates
    uv = switch('MaterialExpressionStaticSwitchParameter_0', 'FixedCoordinate',
                custom('return UV;', {'UV': Node('ExternalHook', Hook='ViewportUV', Type=2)}, 2, 'Viewport coordinate', name='MaterialExpressionCustom_0'),
                uv0)
    time = scalar('MaterialExpressionScalarParameter_11', 'AnimateTime', 'Dynamic')
    emissive = tex('MaterialExpressionTextureSampleParameter2D_26', '0:4:Emissive', uv, 'LinearColor', '000000FF_HDR')
    base = mask('MaterialExpressionComponentMask_14', emissive, 'rgb')

    def emis(name, param, at):
        return mask(None, tex(name, param, at, 'LinearColor', '000000FF_HDR'), 'rgb')
    # drift: the emissive carried along the animation's direction (in the surface's tangent space) by the flow context's
    # distance, two phases blended smoothly
    context = tex('MaterialExpressionTextureSampleParameter2D_5', '0:7:FlowContext', uv0, 'LinearColor', 'FF00FFFF')
    direction_ws = Node('Normalize', {'VectorInput': Node('AppendVector', {'A': Node('AppendVector', {
        'A': scalar('MaterialExpressionScalarParameter_13', 'AnimateDirection_X', 'Dynamic', 1.0),
        'B': scalar('MaterialExpressionScalarParameter_14', 'AnimateDirection_Y', 'Dynamic')}),
        'B': scalar('MaterialExpressionScalarParameter_15', 'AnimateDirection_Z', 'Dynamic')})})
    drift_dir = mask(None, Node('Transform', {'Input': direction_ws}, TransformSourceType='TRANSFORMSOURCE_World', TransformType='TRANSFORM_Tangent'), 'rg')
    dphase = Node('Add', {'A': (context, 2), 'B': time})
    d0 = Node('Frac', {'Input': dphase})
    d1 = Node('Frac', {'Input': Node('Add', {'A': dphase}, ConstB=0.5)})
    da = Node('Add', {'A': Node('Multiply', {'A': Node('Multiply', {'A': d0, 'B': drift_dir}), 'B': (context, 3)}), 'B': uv0}, name='MaterialExpressionAdd_4')
    db = Node('Add', {'A': Node('Multiply', {'A': Node('Multiply', {'A': d1, 'B': drift_dir}), 'B': (context, 3)}), 'B': uv0}, name='MaterialExpressionAdd_6')
    dw = custom('float W = abs(P * 2.0 - 1.0);\nreturn W * W * (3.0 - 2.0 * W);', {'P': d0}, 1, 'Drift blend')
    drift = Node('LinearInterpolate', {'A': emis('MaterialExpressionTextureSampleParameter2D_4', '0:4:Emissive', da),
                                       'B': emis('MaterialExpressionTextureSampleParameter2D_7', '0:4:Emissive', db), 'Alpha': dw},
                 name='MaterialExpressionLinearInterpolate_0')
    drifted = switch('MaterialExpressionStaticSwitchParameter_2', 'Drift', drift, base)
    # flow: one layer, or two (the second's own maps) blended by the flow opacity
    s1 = tex('MaterialExpressionTextureSampleParameter2D_6', '0:9:FlowSpeed/Distortion/Distance', uv0, 'LinearColor', 'FF00FFFF')
    f1 = tex('MaterialExpressionTextureSampleParameter2D_18', '0:8:FlowDirection', uv0, 'LinearColor', '8080FF00')
    a1, b1, ph1 = flow_phases(s1, f1, uv0, time, ['MaterialExpressionAdd_0', 'MaterialExpressionAdd_1'])
    s2 = tex('MaterialExpressionTextureSampleParameter2D_9', '0:C:FlowSpeed/Distortion/Distance', uv0, 'LinearColor', 'FF00FFFF')
    f2 = tex('MaterialExpressionTextureSampleParameter2D_8', '0:B:FlowDirection', uv0, 'LinearColor', '8080FF00')
    a2, b2, ph2 = flow_phases(s2, f2, uv0, time, ['MaterialExpressionAdd_3', 'MaterialExpressionAdd_11'])
    e1a, e1b = emis('MaterialExpressionTextureSampleParameter2D_3', '0:4:Emissive', a1), emis('MaterialExpressionTextureSampleParameter2D_12', '0:4:Emissive', b1)
    e2a, e2b = emis('MaterialExpressionTextureSampleParameter2D_11', '0:A:Emissive', a2), emis('MaterialExpressionTextureSampleParameter2D_10', '0:A:Emissive', b2)
    single = custom(FLOW_BLEND, {'A': e1a, 'B': e1b, 'Phase': ph1}, 3, 'Flow', name='MaterialExpressionCustom_3')
    opacity = tex('MaterialExpressionTextureSampleParameter2D_19', '0:D:FlowOpacity', uv0, 'Alpha', 'FF000000_BC4')
    double = custom("""
float3 F1 = lerp(A1, B1, abs(frac(Phase1) * 2.0 - 1.0));
float3 F2 = lerp(A2, B2, abs(frac(Phase2) * 2.0 - 1.0));
return lerp(F1, F2, saturate(Opacity));""", {'A1': e1a, 'B1': e1b, 'Phase1': ph1, 'A2': e2a, 'B2': e2b, 'Phase2': ph2, 'Opacity': (opacity, 4)},
                    3, 'Double flow', name='MaterialExpressionCustom_11')
    flowed = switch('MaterialExpressionStaticSwitchParameter_8', 'Flow', switch('MaterialExpressionStaticSwitchParameter_9', 'DoubleFlow', double, single), drifted)
    color = switch('MaterialExpressionStaticSwitchParameter_11', 'LDREmissive',
                   (tex('MaterialExpressionTextureSampleParameter2D_13', '0:6:LDREmissive', uv, 'Color', '000000FF_sRGB'), 0), flowed)
    # not radiating: while the game bakes, the partial emissive instead
    partial = mask(None, tex('MaterialExpressionTextureSampleParameter2D_0', '0:5:PartialEmissive', uv, 'LinearColor', '000000FF_HDR'), 'rgb')
    baking = call('MaterialExpressionMaterialFunctionCall_12', 'DetectBaking')
    color = switch('MaterialExpressionStaticSwitchParameter_5', 'Radiation', color,
                   custom('return Baking != 0.0 ? Partial : Color;', {'Partial': partial, 'Color': color, 'Baking': baking}, 3, 'Radiation',
                          name='MaterialExpressionCustom_4'))
    dynamic = switch('MaterialExpressionStaticSwitchParameter_6', 'DynamicEmissive',
                     Node('Multiply', {'A': call('MaterialExpressionMaterialFunctionCall_13', 'CompositeColor',
                                                 R=scalar('MaterialExpressionScalarParameter_1', 'DynamicEmissiveColor_X', 'Dynamic', 1.0),
                                                 G=scalar('MaterialExpressionScalarParameter_2', 'DynamicEmissiveColor_Y', 'Dynamic', 1.0),
                                                 B=scalar('MaterialExpressionScalarParameter_3', 'DynamicEmissiveColor_Z', 'Dynamic', 1.0)),
                                       'B': scalar('MaterialExpressionScalarParameter_17', 'DynamicEmissiveIntensity', 'Dynamic', 1.0)},
                          name='MaterialExpressionMultiply_2'),
                     const3('MaterialExpressionConstant3Vector_1', (1, 1, 1)))
    conditional = switch('MaterialExpressionStaticSwitchParameter_27', 'ConditionalEmissive',
                         Node('ExternalHook', name='MaterialExpressionCustom_29', Hook='ConditionalEmissive', Type=1),
                         Node('Constant', name='MaterialExpressionConstant_7', R=1.0))
    m.pin('EmissiveColor', switch('MaterialExpressionStaticSwitchParameter_3', 'Emissive',
                                  Node('Multiply', {'A': Node('Multiply', {'A': color, 'B': dynamic}), 'B': conditional}, name='MaterialExpressionMultiply_14'),
                                  const3('MaterialExpressionConstant3Vector_0', (0, 0, 0))))
    m.pin('OpacityMask', switch('MaterialExpressionStaticSwitchParameter_4', 'Coverage',
                                mask('MaterialExpressionComponentMask_16', (tex('MaterialExpressionTextureSampleParameter2D_2', '0:1:Coverage', uv, 'Alpha', 'FF000000_BC4'), 4), 'r'),
                                Node('Constant', name='MaterialExpressionConstant_0', R=1.0)))
    # the depth toward the camera (the game's GBuffer F, its w)
    m.pin('CameraRelativeDepth', switch('MaterialExpressionStaticSwitchParameter_1', 'CameraRelativeDepth',
                                        Node('Multiply', {'A': (tex('MaterialExpressionTextureSampleParameter2D_1', '0:6:Depth', uv, 'LinearColor', '000000FF_HDR'), 1)},
                                             name='MaterialExpressionMultiply_0', ConstB=-1.0),
                                        Node('Constant', name='MaterialExpressionConstant_3', R=0.0), 'STATIC_SWITCH_CAMERA_RELATIVE_DEPTH'))
    coord = mask('MaterialExpressionComponentMask_36', Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_11', CoordinateIndex=3), 'r')
    animation(m, coord,
              rigid={'current': {'call': 'MaterialExpressionMaterialFunctionCall_15', 'switches': ['MaterialExpressionStaticSwitchParameter_15', 'MaterialExpressionStaticSwitchParameter_51', 'MaterialExpressionStaticSwitchParameter_54'],
                                 'defaults': ['MaterialExpressionConstant4Vector_7', 'MaterialExpressionConstant4Vector_8', 'MaterialExpressionConstant4Vector_9']},
                     'previous': {'call': 'MaterialExpressionMaterialFunctionCall_17', 'switches': ['MaterialExpressionStaticSwitchParameter_44', 'MaterialExpressionStaticSwitchParameter_46', 'MaterialExpressionStaticSwitchParameter_43'],
                                  'defaults': ['MaterialExpressionConstant4Vector_4', 'MaterialExpressionConstant4Vector_5', 'MaterialExpressionConstant4Vector_6']}},
              soft={'current': {'call': 'MaterialExpressionMaterialFunctionCall_20', 'switches': ['MaterialExpressionStaticSwitchParameter_34', 'MaterialExpressionStaticSwitchParameter_52']},
                    'previous': {'call': 'MaterialExpressionMaterialFunctionCall_19', 'switches': ['MaterialExpressionStaticSwitchParameter_45', 'MaterialExpressionStaticSwitchParameter_47']}},
              fluid={'call': 'MaterialExpressionMaterialFunctionCall_24', 'current': ['MaterialExpressionStaticSwitchParameter_50', 'MaterialExpressionStaticSwitchParameter_53'],
                     'previous': ['MaterialExpressionStaticSwitchParameter_41', 'MaterialExpressionStaticSwitchParameter_42']},
              prev_key_name='MaterialExpressionScalarParameter_16')
    m.props.update(shading_model='MSM_Unlit', tangent_space_normal=True)
    return m


def EndMaterial_Menu():
    # the menus' (user interface) material: the color as it is
    _SHARED.clear()
    m = Material('EndMaterial_Menu', M_ROOT + '/EndMaterial_Menu')
    uv0 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_1', CoordinateIndex=0)
    m.pin('EmissiveColor', (tex('MaterialExpressionTextureSampleParameter2D_6', '0:Color', uv0, 'Color', '767676FF_sRGB'), 0))
    m.props.update(shading_model='MSM_Unlit', domain='MD_UI')
    return m


def tint(switch_name, param, multiply, call_name, color_names, intensity_name, group, off_name):
    """a tint (the stationary or the dynamic one): its colour's three scalars times its intensity, or white"""
    return switch(switch_name, param,
                  Node('Multiply', {'A': call(call_name, 'CompositeColor',
                                              R=scalar(color_names[0], group + 'EmissiveColor_X', group, 1.0),
                                              G=scalar(color_names[1], group + 'EmissiveColor_Y', group, 1.0),
                                              B=scalar(color_names[2], group + 'EmissiveColor_Z', group, 1.0)),
                                    'B': scalar(intensity_name, group + 'EmissiveIntensity', group, 1.0)}, name=multiply),
                  const3(off_name, (1, 1, 1)))


def fabric_emissive(uv0, uv2, mrv):
    """EndMaterial_Fabric's emissive: as the Standard's without its flow and interior layers - a base layer (a texture, its
    LDR one, or white), an extra layer on UV2 that the coordinate offsets move, tinted by the stationary and the dynamic
    colours, scaled by the variant channel, the game's conditional scale, and - unless the material radiates - nothing while
    the game bakes"""
    baking = call('MaterialExpressionMaterialFunctionCall_16', 'DetectBaking')

    def layer(hdr, ldr, sw_ldr, m_ldr, m_hdr):
        return switch(sw_ldr, 'LDREmissive', mask(m_ldr, ldr, 'rgb'), mask(m_hdr, hdr, 'rgb'))
    base = switch('MaterialExpressionStaticSwitchParameter_24', 'IdentityEmissive', const3('MaterialExpressionConstant3Vector_5', (1, 1, 1)),
                  layer(tex('MaterialExpressionTextureSampleParameter2D_13', '0:4:Emissive', uv0, 'LinearColor', '000000FF_HDR'),
                        tex('MaterialExpressionTextureSampleParameter2D_15', '0:6:LDREmissive', uv0, 'Color', '000000FF_sRGB'),
                        'MaterialExpressionStaticSwitchParameter_23', 'MaterialExpressionComponentMask_27', 'MaterialExpressionComponentMask_26'))
    soff = switch('MaterialExpressionStaticSwitchParameter_19', 'StationaryEmissive',
                  Node('AppendVector', {'A': scalar('MaterialExpressionScalarParameter_13', 'StationaryCoordinateOffset_X', 'Stationary'),
                                        'B': scalar('MaterialExpressionScalarParameter_14', 'StationaryCoordinateOffset_Y', 'Stationary')},
                       name='MaterialExpressionAppendVector_2'),
                  Node('Constant2Vector', name='MaterialExpressionConstant2Vector_0', R=0.0, G=0.0))
    doff = switch('MaterialExpressionStaticSwitchParameter_17', 'DynamicEmissive',
                  Node('AppendVector', {'A': scalar('MaterialExpressionScalarParameter_7', 'DynamicCoordinateOffset_X', 'Dynamic'),
                                        'B': scalar('MaterialExpressionScalarParameter_8', 'DynamicCoordinateOffset_Y', 'Dynamic')},
                       name='MaterialExpressionAppendVector_1'),
                  Node('Constant2Vector', name='MaterialExpressionConstant2Vector_1', R=0.0, G=0.0))
    extra_uv = Node('Add', {'A': uv2, 'B': Node('Add', {'A': soff, 'B': doff})}, name='MaterialExpressionAdd_0')
    # (no game instance has IdentityEmissive with ExtraEmissive: white, as the base's)
    extra = switch('MaterialExpressionStaticSwitchParameter_21', 'ExtraEmissive',
                   switch('MaterialExpressionStaticSwitchParameter_31', 'IdentityEmissive', const3('MaterialExpressionConstant3Vector_9', (1, 1, 1)),
                          layer(tex('MaterialExpressionTextureSampleParameter2D_11', '2:4:Emissive', extra_uv, 'LinearColor', '000000FF_HDR'),
                                tex('MaterialExpressionTextureSampleParameter2D_12', '2:5:LDREmissive', extra_uv, 'Color', '000000FF_sRGB'),
                                'MaterialExpressionStaticSwitchParameter_20', 'MaterialExpressionComponentMask_23', 'MaterialExpressionComponentMask_22')),
                   const3('MaterialExpressionConstant3Vector_14', (0, 0, 0)))
    color = Node('Add', {'A': base, 'B': extra})
    stationary = tint('MaterialExpressionStaticSwitchParameter_18', 'StationaryEmissive', 'MaterialExpressionMultiply_8',
                      'MaterialExpressionMaterialFunctionCall_15', ['MaterialExpressionScalarParameter_10', 'MaterialExpressionScalarParameter_11',
                                                                    'MaterialExpressionScalarParameter_12'],
                      'MaterialExpressionScalarParameter_9', 'Stationary', 'MaterialExpressionConstant3Vector_4')
    dynamic = tint('MaterialExpressionStaticSwitchParameter_16', 'DynamicEmissive', 'MaterialExpressionMultiply_7',
                   'MaterialExpressionMaterialFunctionCall_14', ['MaterialExpressionScalarParameter_4', 'MaterialExpressionScalarParameter_5',
                                                                 'MaterialExpressionScalarParameter_6'],
                   'MaterialExpressionScalarParameter_0', 'Dynamic', 'MaterialExpressionConstant3Vector_3')
    color = Node('Multiply', {'A': Node('Multiply', {'A': color, 'B': stationary}), 'B': dynamic})
    variant = mask(None, (mrv, 3), 'r')
    conditional = switch('MaterialExpressionStaticSwitchParameter_25', 'ConditionalEmissive',
                         Node('ExternalHook', name='MaterialExpressionCustom_5', Hook='ConditionalEmissive', Type=1),
                         Node('Constant', name='MaterialExpressionConstant_15', R=1.0))
    radiation = custom('return Baking != 0.0 ? Radiation : 1.0;',
                       {'Radiation': switch('MaterialExpressionStaticSwitchParameter_22', 'Radiation', Node('Constant', name='MaterialExpressionConstant_12', R=1.0),
                                            Node('Constant', name='MaterialExpressionConstant_13', R=0.0)),
                        'Baking': baking}, 1, 'Radiation')
    emissive = Node('Multiply', {'A': Node('Multiply', {'A': Node('Multiply', {'A': color, 'B': variant}), 'B': conditional}), 'B': radiation},
                    name='MaterialExpressionMultiply_12')
    return switch('MaterialExpressionStaticSwitchParameter_26', 'Emissive', emissive, const3('MaterialExpressionConstant3Vector_6', (0, 0, 0)))


def EndMaterial_Fabric():
    _SHARED.clear()
    m = Material('EndMaterial_Fabric', M_ROOT + '/EndMaterial_Fabric')
    uv0 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_1', CoordinateIndex=0)
    uv1 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_3', CoordinateIndex=1)
    uv2 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_8', CoordinateIndex=2)

    color = tex('MaterialExpressionTextureSampleParameter2D_6', '0:0:Color', uv0, 'Color', '767676FF_sRGB')
    normal = tex('MaterialExpressionTextureSampleParameter2D_7', '0:3:Normal', uv0, 'LinearColor', '8080FF00')
    mrv = tex('MaterialExpressionTextureSampleParameter2D_4', '0:2:Metallic/Roughness/Variant', uv0, 'LinearColor', '008000FF')
    occl = tex('MaterialExpressionTextureSampleParameter2D_5', '1:0:Occlusion', uv1, 'Alpha', 'FF000000_BC4')
    cover = tex('MaterialExpressionTextureSampleParameter2D_2', '0:1:Coverage', uv0, 'Alpha', 'FF000000_BC4')
    dopac = tex('MaterialExpressionTextureSampleParameter2D_17', '0:5:DetailOpacity', uv0, 'LinearColor', '000000FF')
    dnorm = [tex('MaterialExpressionTextureSampleParameter2D_14', '2:0:DetailNormal:0', uv2, 'LinearColor', '8080FF00'),
             tex('MaterialExpressionTextureSampleParameter2D_0', '2:1:DetailNormal:1', uv2, 'LinearColor', '8080FF00'),
             tex('MaterialExpressionTextureSampleParameter2D_1', '2:2:DetailNormal:2', uv2, 'LinearColor', '8080FF00')]
    dcover = tex('MaterialExpressionTextureSampleParameter2D_3', '2:3:DetailCoverage', uv2, 'Alpha', 'FF000000_BC4')
    gfd = tex('MaterialExpressionTextureSampleParameter2D_10', '0:8:Gloss/Fluff/Distribution', uv0, 'LinearColor', '008000FF')
    selective = tex('MaterialExpressionTextureSampleParameter2D_8', '0:9:Selective', uv0, 'Alpha', 'FF000000_BC4')

    m.pin('Normal', detail_normal(normal, dopac, dnorm))
    m.pin('BaseColor', mask('MaterialExpressionComponentMask_2', color, 'rgb'))
    m.pin('Metallic', mask('MaterialExpressionComponentMask_4', (mrv, 5), 'r'))
    m.pin('Roughness', mask('MaterialExpressionComponentMask_5', (mrv, 5), 'g'))
    m.pin('Specular', call('MaterialExpressionMaterialFunctionCall_5', 'EncodeReflectance',
                           Reflectance=Node('Constant', name='MaterialExpressionConstant_3', R=0.04)))
    m.pin('AmbientOcclusion', detail_occlusion(uv2, occl))
    m.pin('OpacityMask', detail_coverage(cover, dcover))
    m.pin('EmissiveColor', fabric_emissive(uv0, uv2, mrv))
    # the cloth: the fur (none; with Fur the back's, the front's, or neither's - no game instance has Fur without FurBack: the
    # front's and the plain one's are guesses), the gloss and the fluff (GBuffer D), the distribution (the clear coat)
    fur = switch('MaterialExpressionStaticSwitchParameter_6', 'Fur',
                 switch('MaterialExpressionStaticSwitchParameter_9', 'FurBack', Node('Constant', name='MaterialExpressionConstant_9', R=0.875),
                        switch('MaterialExpressionStaticSwitchParameter_8', 'FurFront', Node('Constant', name='MaterialExpressionConstant_8', R=0.625),
                               Node('Constant', name='MaterialExpressionConstant_6', R=0.75))),
                 Node('Constant', name='MaterialExpressionConstant_5', R=0.0))
    m.pin('ClothData', Node('AppendVector', {'A': fur, 'B': mask(None, gfd, 'rg')}))
    m.pin('ClearCoat', mask('MaterialExpressionComponentMask_6', gfd, 'b'))
    # Selective: each pixel cloth where the selective map is above the noise, Default Lit elsewhere
    m.pin('Selective', switch('MaterialExpressionStaticSwitchParameter_3', 'Selective', mask('MaterialExpressionComponentMask_14', (selective, 5), 'a'),
                              Node('Constant', name='MaterialExpressionConstant_7', R=1.0), 'STATIC_SWITCH_SELECTIVE'))
    # with IdentifierCoverage each piece its own noise slice for the coverage's dither: its id from UV3's u
    m.pin('VertexContextVector0', switch('MaterialExpressionStaticSwitchParameter_5', 'IdentifierCoverage',
                                         Node('AppendVector', {'A': const3(None, (0, 0, 0)), 'B': Node('Multiply', {'A': mask(None, Node(
                                             'TextureCoordinate', CoordinateIndex=3), 'r')}, ConstB=256.0)}, name='MaterialExpressionAppendVector_0'),
                                         c4('MaterialExpressionConstant4Vector_0', (0, 0, 0, 0))))
    m.props.update(shading_model='MSM_Cloth', tangent_space_normal=True)
    return m


def EndMaterial_Subsurface():
    _SHARED.clear()
    m = Material('EndMaterial_Subsurface', M_ROOT + '/EndMaterial_Subsurface')
    uv0 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_1', CoordinateIndex=0)
    uv1 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_3', CoordinateIndex=1)
    uv2 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_8', CoordinateIndex=2)

    color = tex('MaterialExpressionTextureSampleParameter2D_6', '0:0:Color', uv0, 'Color', '767676FF_sRGB')
    normal = tex('MaterialExpressionTextureSampleParameter2D_7', '0:3:Normal', uv0, 'LinearColor', '8080FF00')
    mrv = tex('MaterialExpressionTextureSampleParameter2D_4', '0:2:Metallic/Roughness/Variant', uv0, 'LinearColor', '008000FF')
    occl = tex('MaterialExpressionTextureSampleParameter2D_5', '1:0:Occlusion', uv1, 'Alpha', 'FF000000_BC4')
    cover = tex('MaterialExpressionTextureSampleParameter2D_2', '0:1:Coverage', uv0, 'Alpha', 'FF000000_BC4')
    dopac = tex('MaterialExpressionTextureSampleParameter2D_17', '0:5:DetailOpacity', uv0, 'LinearColor', '000000FF')
    dnorm = [tex('MaterialExpressionTextureSampleParameter2D_14', '2:0:DetailNormal:0', uv2, 'LinearColor', '8080FF00'),
             tex('MaterialExpressionTextureSampleParameter2D_0', '2:1:DetailNormal:1', uv2, 'LinearColor', '8080FF00'),
             tex('MaterialExpressionTextureSampleParameter2D_1', '2:2:DetailNormal:2', uv2, 'LinearColor', '8080FF00')]
    dcover = tex('MaterialExpressionTextureSampleParameter2D_3', '2:3:DetailCoverage', uv2, 'Alpha', 'FF000000_BC4')
    distribution = tex('MaterialExpressionTextureSampleParameter2D_13', '0:8:Distribution', uv0, 'Alpha', 'FF000000_BC4')

    m.pin('Normal', detail_normal(normal, dopac, dnorm))
    m.pin('BaseColor', mask('MaterialExpressionComponentMask_2', color, 'rgb'))
    m.pin('Metallic', mask('MaterialExpressionComponentMask_4', (mrv, 5), 'r'))
    m.pin('Roughness', mask('MaterialExpressionComponentMask_5', (mrv, 5), 'g'))
    m.pin('Specular', call('MaterialExpressionMaterialFunctionCall_5', 'EncodeReflectance',
                           Reflectance=Node('Constant', name='MaterialExpressionConstant_3', R=0.04)))
    m.pin('AmbientOcclusion', detail_occlusion(uv2, occl, 'MaterialExpressionCustom_3'))
    m.pin('OpacityMask', detail_coverage(cover, dcover))
    # (no game instance has Emissive on: the Standard's nodes, as the Subsurface's have them)
    m.pin('EmissiveColor', standard_emissive(uv0, uv2, mrv, flow=False, reference=False, conditional=False, extra_add='MaterialExpressionAdd_1'))
    # the subsurface distribution (GBuffer D's w)
    m.pin('Distribution', mask(None, (distribution, 5), 'a'))
    coord = mask('MaterialExpressionComponentMask_36', Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_11', CoordinateIndex=3), 'r')
    local, tilt_now, tilt_prev = tilt_inputs('MaterialExpressionCustom_1', 'MaterialExpressionCustom_2', 'MaterialExpressionCustom_6')
    animation(m, coord,
              rigid={'current': {'call': 'MaterialExpressionMaterialFunctionCall_15', 'switches': ['MaterialExpressionStaticSwitchParameter_15', 'MaterialExpressionStaticSwitchParameter_51', 'MaterialExpressionStaticSwitchParameter_54'],
                                 'defaults': ['MaterialExpressionConstant4Vector_7', 'MaterialExpressionConstant4Vector_8', 'MaterialExpressionConstant4Vector_9']},
                     'previous': {'call': 'MaterialExpressionMaterialFunctionCall_16', 'switches': ['MaterialExpressionStaticSwitchParameter_25', 'MaterialExpressionStaticSwitchParameter_27', 'MaterialExpressionStaticSwitchParameter_24'],
                                  'defaults': ['MaterialExpressionConstant4Vector_0', 'MaterialExpressionConstant4Vector_1', 'MaterialExpressionConstant4Vector_2']}},
              soft={'current': {'call': 'MaterialExpressionMaterialFunctionCall_20', 'switches': ['MaterialExpressionStaticSwitchParameter_34', 'MaterialExpressionStaticSwitchParameter_52']},
                    'previous': {'call': 'MaterialExpressionMaterialFunctionCall_17', 'switches': ['MaterialExpressionStaticSwitchParameter_26', 'MaterialExpressionStaticSwitchParameter_28']}},
              fluid={'call': 'MaterialExpressionMaterialFunctionCall_24', 'current': ['MaterialExpressionStaticSwitchParameter_50', 'MaterialExpressionStaticSwitchParameter_53'],
                     'previous': ['MaterialExpressionStaticSwitchParameter_22', 'MaterialExpressionStaticSwitchParameter_23']},
              tilt={'vector': local, 'textures': ['MaterialExpressionTextureObjectParameter_7', 'MaterialExpressionTextureObjectParameter_8'],
                    'current': {'call': 'MaterialExpressionMaterialFunctionCall_18', 'switches': ['MaterialExpressionStaticSwitchParameter_16', 'MaterialExpressionStaticSwitchParameter_17'],
                                'tilt': tilt_now},
                    'previous': {'call': 'MaterialExpressionMaterialFunctionCall_11', 'switches': ['MaterialExpressionStaticSwitchParameter_18', 'MaterialExpressionStaticSwitchParameter_20'],
                                 'tilt': tilt_prev}},
              prev_key_name='MaterialExpressionScalarParameter_18')
    m.props.update(shading_model='MSM_SubsurfaceProfile', tangent_space_normal=True)
    return m


def EndMaterial_Blood():
    _SHARED.clear()
    m = Material('EndMaterial_Blood', M_ROOT + '/EndMaterial_Blood')
    uv0 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_1', CoordinateIndex=0)
    uv1 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_3', CoordinateIndex=1)
    normal = tex('MaterialExpressionTextureSampleParameter2D_7', '0:3:Normal', uv0, 'LinearColor', '8080FF00')
    cover = tex('MaterialExpressionTextureSampleParameter2D_2', '0:1:Coverage', uv0, 'Alpha', 'FF000000_BC4')
    occl = tex('MaterialExpressionTextureSampleParameter2D_5', '1:0:Occlusion', uv1, 'Alpha', 'FF000000_BC4')
    # the blood's two values (one-texel textures: read at their middle, clamped)
    middle = Node('Constant2Vector', name='MaterialExpressionConstant2Vector_1', R=0.5, G=0.5)
    oxygen = tex('MaterialExpressionTextureSampleParameter2D_6', 'C:0:OxygenSaturation', middle, 'Alpha', '767676FF_BC4',
                 source='SSM_Clamp_WorldGroupSettings')
    hematocrit = tex('MaterialExpressionTextureSampleParameter2D_0', 'C:1:Hematocrit', middle, 'Alpha', '767676FF_BC4',
                     source='SSM_Clamp_WorldGroupSettings')
    m.pin('Normal', call('MaterialExpressionMaterialFunctionCall_14', 'NormalizeNormalRG', NormalRG=mask('MaterialExpressionComponentMask_6', normal, 'rg')))
    # the colour: venous (deoxygenated) to arterial (oxygenated) red by the oxygen saturation, as dense as the hematocrit
    blood = Node('LinearInterpolate', {'A': const3(None, (0.08022, 0.003677, 0.008023)), 'B': const3(None, (0.913099, 0.0, 0.001518)),
                                       'Alpha': (oxygen, 4)})
    m.pin('BaseColor', Node('LinearInterpolate', {'A': const3(None, (0, 0, 0)), 'B': blood, 'Alpha': (hematocrit, 4)},
                            name='MaterialExpressionLinearInterpolate_1'))
    m.pin('Metallic', Node('Constant', name='MaterialExpressionConstant_5', R=0.0))
    m.pin('Roughness', Node('Constant', name='MaterialExpressionConstant_8', R=0.0))
    # blood's reflectance (index of refraction about 1.4)
    m.pin('Specular', call('MaterialExpressionMaterialFunctionCall_5', 'EncodeReflectance', Reflectance=Node('Constant', name='MaterialExpressionConstant_3', R=0.027)))
    m.pin('AmbientOcclusion', mask('MaterialExpressionComponentMask_11', (occl, 5), 'a'))
    cov = switch('MaterialExpressionStaticSwitchParameter_5', 'Coverage', mask('MaterialExpressionComponentMask_0', (cover, 5), 'a'),
                 Node('Constant', name='MaterialExpressionConstant_0', R=1.0))
    m.pin('OpacityMask', switch('MaterialExpressionStaticSwitchParameter_24', 'LiteDecal', cov, cov, 'STATIC_SWITCH_LITE_DECAL'))
    m.props.update(shading_model='MSM_PreintegratedSkin', tangent_space_normal=True)
    return m


# the materia's interior: the view refracted at the surface (index 1: unbent), a swirl - the 3D noise about the
# (pre-skinned) normal, the three axes turning once per unit of time - along it, and three octaves of the noise (each
# about one axis, at half the last's scale) multiplied, sharpened (^4, x64), brightest facing the view
MATERIA_INTERIOR = """
float D = dot(Normal, CameraVector);
float3 R = Normal * D - CameraVector;
R = normalize(R - Normal * sqrt(1.0 - (1.0 - D * D)));
float S, C;
sincos(Phase * 6.2831855, S, C);
float3x3 RX = float3x3(1.0, 0.0, 0.0, 0.0, C, -S, 0.0, S, C);
float3x3 RY = float3x3(C, 0.0, S, 0.0, 1.0, 0.0, -S, 0.0, C);
float3x3 RZ = float3x3(C, -S, 0.0, S, C, 0.0, 0.0, 0.0, 1.0);
float Swirl = Noise.Sample(NoiseSampler, mul(mul(RZ, mul(RY, RX)), Inner * 0.5 + 0.5) * 0.5).x;
float3 Offset = Swirl * R;
float N = Noise.Sample(NoiseSampler, mul(RX, (Offset * 1.2 + Inner) * 0.5 + 0.5)).x;
N *= Noise.Sample(NoiseSampler, mul(RY, ((Inner + Offset) * 0.5 + 0.5) * 0.5)).x;
N *= Noise.Sample(NoiseSampler, mul(RZ, ((Offset * 0.8 + Inner) * 0.5 + 0.5) * 0.25)).x;
N = N * N;
N = N * N;
float F = saturate(D);
return N * 64.0 * (F * F);"""

# the pixel's normal in the mesh's own (unskinned) space: the normal map in the vertex's unskinned tangent frame
PRE_SKINNED_NORMAL = """
float3 Y = cross(TangentZ.xyz, TangentX) * TangentZ.w;
return normalize(mul(Normal, float3x3(TangentX, Y, TangentZ.xyz)));"""


def EndMaterial_Materia():
    _SHARED.clear()
    m = Material('EndMaterial_Materia', M_ROOT + '/EndMaterial_Materia')
    uv0 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_1', CoordinateIndex=0)
    uv1 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_3', CoordinateIndex=1)
    normal = tex('MaterialExpressionTextureSampleParameter2D_7', '0:3:Normal', uv0, 'LinearColor', '8080FF00')
    occl = tex('MaterialExpressionTextureSampleParameter2D_5', '1:0:Occlusion', uv1, 'Alpha', 'FF000000_BC4')
    n = call('MaterialExpressionMaterialFunctionCall_1', 'NormalizeNormalRG', NormalRG=mask('MaterialExpressionComponentMask_3', normal, 'rg'))
    m.pin('Normal', n)
    # a clear crystal: black, smooth, reflectance 0.1, all its colour its interior's
    m.pin('BaseColor', const3('MaterialExpressionConstant3Vector_2', (0, 0, 0)))
    m.pin('Metallic', Node('Constant', name='MaterialExpressionConstant_4', R=0.0))
    m.pin('Roughness', Node('Constant', name='MaterialExpressionConstant_10', R=0.0))
    m.pin('Specular', call('MaterialExpressionMaterialFunctionCall_5', 'EncodeReflectance', Reflectance=Node('Constant', name='MaterialExpressionConstant_3', R=0.1)))
    m.pin('AmbientOcclusion', mask('MaterialExpressionComponentMask_11', (occl, 5), 'a'))
    m.pin('OpacityMask', Node('Constant', name='MaterialExpressionConstant_0', R=1.0))
    inner = switch('MaterialExpressionStaticSwitchParameter_3', 'PreSkinndNormal',
                   custom(PRE_SKINNED_NORMAL, {'Normal': n, 'TangentX': Node('ExternalHook', Hook='PreSkinnedTangentX', Type=3),
                                               'TangentZ': Node('ExternalHook', Hook='PreSkinnedTangentZ', Type=4)},
                          3, 'Pre-skinned normal', name='MaterialExpressionCustom_2'),
                   Node('PixelNormalWS', name='MaterialExpressionPixelNormalWS_1'), 'STATIC_SWITCH_PRE_SKINNED_NORMAL', default=True)
    interior = custom(MATERIA_INTERIOR, {'Normal': Node('PixelNormalWS'), 'CameraVector': Node('CameraVectorWS'), 'Inner': inner,
                                         'Phase': Node('Frac', {'Input': scalar('MaterialExpressionScalarParameter_0', 'AnimateTime', 'Dynamic')}),
                                         'Noise': Node('ExternalHook', Hook='VolumeNoise', Type='Texture3D')}, 1, 'Materia interior')
    # (no game instance turns Reference on: as off)
    glow = switch('MaterialExpressionStaticSwitchParameter_0', 'Reference', Node('Multiply', {'A': interior}, name='MaterialExpressionMultiply_4', ConstB=1.0),
                  mask('MaterialExpressionComponentMask_10', interior, 'r'))
    tint = Node('Multiply', {'A': call('MaterialExpressionMaterialFunctionCall_13', 'CompositeColor',
                                       R=scalar('MaterialExpressionScalarParameter_1', 'DynamicEmissiveColor_X', 'Dynamic', 1.0),
                                       G=scalar('MaterialExpressionScalarParameter_2', 'DynamicEmissiveColor_Y', 'Dynamic', 1.0),
                                       B=scalar('MaterialExpressionScalarParameter_3', 'DynamicEmissiveColor_Z', 'Dynamic', 1.0)),
                             'B': scalar('MaterialExpressionScalarParameter_17', 'DynamicEmissiveIntensity', 'Dynamic', 1.0)})
    m.pin('EmissiveColor', Node('Multiply', {'A': glow, 'B': tint}, name='MaterialExpressionMultiply_0'))
    m.props.update(shading_model='MSM_DefaultLit', tangent_space_normal=True)
    return m


def EndMaterial_Standard_Classify():
    _SHARED.clear()
    m = Material('EndMaterial_Standard_Classify', M_ROOT + '/EndMaterial_Standard_Classify')
    uv0 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_1', CoordinateIndex=0)
    uv1 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_3', CoordinateIndex=1)
    normal = tex('MaterialExpressionTextureSampleParameter2D_7', '0:3:Normal', uv0, 'LinearColor', '8080FF00')
    occl = tex('MaterialExpressionTextureSampleParameter2D_5', '1:0:Occlusion', uv1, 'Alpha', 'FF000000_BC4')
    n = call('MaterialExpressionMaterialFunctionCall_1', 'NormalizeNormalRG', NormalRG=mask('MaterialExpressionComponentMask_3', normal, 'rg'))
    m.pin('Normal', n)
    m.pin('BaseColor', const3('MaterialExpressionConstant3Vector_2', (0, 0, 0)))
    m.pin('Metallic', Node('Constant', name='MaterialExpressionConstant_4', R=0.0))
    m.pin('Roughness', Node('Constant', name='MaterialExpressionConstant_10', R=0.0))
    m.pin('Specular', call('MaterialExpressionMaterialFunctionCall_13', 'EncodeReflectance', Reflectance=Node('Constant', name='MaterialExpressionConstant_9', R=0.1)))
    m.pin('AmbientOcclusion', mask('MaterialExpressionComponentMask_11', (occl, 5), 'a'))
    # each piece (UV2's whole u) its class: its row of the classify texture (one row per class, as many rows as the
    # texture is tall in widths), the colour of its interior and its coverage
    piece_u = mask(None, Node('TextureCoordinate', CoordinateIndex=2), 'r')
    classify = Node('TextureObjectParameter', name='MaterialExpressionTextureObjectParameter_0', ParameterName='2:0:Classify',
                    Texture='FFFFFFFF_sRGB', SamplerType='Color', Group='Texture')
    row = custom("""
uint Piece = (uint)floor(U);
float Index = Piece == 0u ? Index0 : (Piece == 1u ? Index1 : (Piece == 2u ? Index2 : (Piece == 3u ? Index3 : 0.0)));
return float2(0.5, (floor(Index) + 0.5) / float((uint)round(Size.y / Size.x)));""",
                 {'U': piece_u, 'Size': Node('TextureProperty', {'TextureObject': classify}, Property='TMTP_TextureSize'),
                  'Index0': scalar('MaterialExpressionScalarParameter_13', 'DynamicClassifyIndex_0', 'Dynamic'),
                  'Index1': scalar('MaterialExpressionScalarParameter_14', 'DynamicClassifyIndex_1', 'Dynamic'),
                  'Index2': scalar('MaterialExpressionScalarParameter_15', 'DynamicClassifyIndex_2', 'Dynamic'),
                  'Index3': scalar('MaterialExpressionScalarParameter_16', 'DynamicClassifyIndex_3', 'Dynamic')}, 2, 'Classify row')
    cls = Node('TextureSample', {'TextureObject': classify, 'Coordinates': row}, SamplerType='Color', MipValueMode='TMVM_MipLevel', ConstMipValue=0.0)
    m.pin('OpacityMask', switch('MaterialExpressionStaticSwitchParameter_4', 'Coverage', mask('MaterialExpressionComponentMask_20', (cls, 5), 'a'),
                                Node('Constant', name='MaterialExpressionConstant_0', R=1.0)))
    inner = switch('MaterialExpressionStaticSwitchParameter_3', 'PreSkinndNormal',
                   custom(PRE_SKINNED_NORMAL, {'Normal': n, 'TangentX': Node('ExternalHook', Hook='PreSkinnedTangentX', Type=3),
                                               'TangentZ': Node('ExternalHook', Hook='PreSkinnedTangentZ', Type=4)},
                          3, 'Pre-skinned normal', name='MaterialExpressionCustom_4'),
                   Node('PixelNormalWS', name='MaterialExpressionPixelNormalWS_1'), 'STATIC_SWITCH_PRE_SKINNED_NORMAL', default=True)
    # the materia's interior, each piece a quarter turn on from the last
    phase = custom('return frac(float((uint)floor(U)) * 0.25 + Time);',
                   {'U': piece_u, 'Time': scalar('MaterialExpressionScalarParameter_0', 'AnimateTime', 'Dynamic')}, 1, 'Piece phase')
    interior = custom(MATERIA_INTERIOR, {'Normal': Node('PixelNormalWS'), 'CameraVector': Node('CameraVectorWS'), 'Inner': inner,
                                         'Phase': phase, 'Noise': Node('ExternalHook', Hook='VolumeNoise', Type='Texture3D')}, 1, 'Materia interior')
    # (no game instance turns Reference on: as off)
    glow = switch('MaterialExpressionStaticSwitchParameter_0', 'Reference', Node('Multiply', {'A': interior}, name='MaterialExpressionMultiply_4', ConstB=1.0),
                  mask('MaterialExpressionComponentMask_10', interior, 'r'))
    color = switch('MaterialExpressionStaticSwitchParameter_12', 'Classify', mask('MaterialExpressionComponentMask_21', cls, 'rgb'),
                   c4('MaterialExpressionConstant4Vector_0', (1, 1, 1, 1)))
    scale = Node('Multiply', {'A': Node('ExternalHook', Hook='ConditionalEmissive', Type=1)}, ConstB=100.0)
    m.pin('EmissiveColor', Node('Multiply', {'A': glow, 'B': Node('Multiply', {'A': color, 'B': scale})}, name='MaterialExpressionMultiply_1'))
    m.props.update(shading_model='MSM_DefaultLit', tangent_space_normal=True)
    return m


# the hologram's glow: an edge (and facing) brightness - the sum of the Fresnel-like (1 - N.V)^5 + (N.V)^5, the upward
# facing half brighter - where the occlusion and N.V together pass one (their sum to the power of the exponent)
HOLOGRAM_GLOW = """
float NoV = saturate(dot(Normal, CameraVector));
float A = 1.0 - NoV;
float A2 = A * A;
float N2 = NoV * NoV;
float Edge = (A * (A2 * A2) + NoV * (N2 * N2)) * (Normal.z * 0.5 + 0.5);
float X = Occlusion + NoV;
float P = X < 0.000001 ? 0.0 : pow(abs(X), Exponent * Exponent);
return lerp(0.0003, 1.0, saturate(Occlusion + P - 1.0) * Edge);"""

# the hologram's sparkle: the blue noise volume in the primitive's space (one cell per 1/32 unit, repeating every 2)
HOLOGRAM_SPARKLE = """
return Noise.Load(int4(int3(floor(frac(Position * 0.5) * 64.0)), 0)).x;"""

# the hologram's Perlin pattern: a facing term and three octaves of the noise volume drifting with time
HOLOGRAM_PERLIN = """
float NoV = saturate(dot(Normal, CameraVector));
float G = Occlusion * (NoV * (1.0 - exp2(NoV * -15.2003126)));
float N1 = Noise.Sample(NoiseSampler, Position * 0.005 + float3(0.0, 0.66, Time * 2.0)).x;
float N2 = Noise.Sample(NoiseSampler, Position * 0.005 + float3(0.0, 0.33, -Time)).x;
float N3 = Noise.Sample(NoiseSampler, Position * 0.0025 + float3(0.0, 0.0, Time)).x;
float P = max(G * ((N3 * N3 * 0.8 + 0.2) * (N1 * 0.33 + N2 * 0.66)), 0.0);
return P * P;"""

# the hologram's eye: the cornea (the gaze normal blended in across the cornea), the iris seen through it (the view
# refracted at the surface, index 1.38, carried down to the iris plane), the pupil darkening the occlusion
HOLOGRAM_CORNEA = """
float R = length((UV * 2.0 - 1.0) * 2.0);
return saturate(1.0 - smoothstep(0.8, 1.2, R));"""
HOLOGRAM_IRIS_UV = EYE_FRAME + """
float2 P = (UV * 2.0 - 1.0) * 2.0;
float R2 = dot(P, P);
float3 Ray = refract(-Parameters.CameraVector, Normal, 1.0 / 1.38);
float3 L = float3(dot(T, Ray), dot(B, Ray), dot(Gaze, Ray));
float Depth = saturate(1.0 - R2) * 0.385 + (1.0 - saturate((R2 - 1.0) / 0.2)) * 0.0385;
return UV + L.xy / -L.z * Depth * Cornea * 0.32;"""
HOLOGRAM_PUPIL = """
float R = length((UV * 2.0 - 1.0) * 2.0);
return lerp(Occlusion, Occlusion * smoothstep(0.23, 0.25, R), Cornea);"""


def EndMaterial_Hologram():
    _SHARED.clear()
    m = Material('EndMaterial_Hologram', M_ROOT + '/EndMaterial_Hologram')
    uv0 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_0', CoordinateIndex=0)
    uv1 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_3', CoordinateIndex=1)
    uv2 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_8', CoordinateIndex=2)
    normal = tex('MaterialExpressionTextureSampleParameter2D_8', '0:3:Normal', uv0, 'LinearColor', '8080FF00')
    gaze = tex('MaterialExpressionTextureSampleParameter2D_2', '0:5:Normal(Gaze)', uv0, 'LinearColor', '8080FF00')
    mrv = tex('MaterialExpressionTextureSampleParameter2D_0', '0:2:Metallic/Roughness/Variant', uv0, 'LinearColor', '000000FF')
    occl = tex('MaterialExpressionTextureSampleParameter2D_5', '1:0:Occlusion', uv1, 'Alpha', 'FF000000_BC4')
    cover = tex('MaterialExpressionTextureSampleParameter2D_11', '0:1:Coverage', uv0, 'Alpha', 'FF000000_BC4')
    dcover = tex('MaterialExpressionTextureSampleParameter2D_12', '2:3:DetailCoverage', uv2, 'Alpha', 'FF000000_BC4')
    dopac = tex('MaterialExpressionTextureSampleParameter2D_17', '0:5:DetailOpacity', uv0, 'LinearColor', '000000FF')
    dnorm = [tex('MaterialExpressionTextureSampleParameter2D_14', '2:0:DetailNormal:0', uv2, 'LinearColor', '8080FF00'),
             tex('MaterialExpressionTextureSampleParameter2D_9', '2:1:DetailNormal:1', uv2, 'LinearColor', '8080FF00'),
             tex('MaterialExpressionTextureSampleParameter2D_10', '2:2:DetailNormal:2', uv2, 'LinearColor', '8080FF00')]
    names = (('MaterialExpressionComponentMask_9', 'MaterialExpressionMaterialFunctionCall_2'),
             [('MaterialExpressionComponentMask_10', 'MaterialExpressionMaterialFunctionCall_4', 'MaterialExpressionOneMinus_0',
               'MaterialExpressionMaterialFunctionCall_6', 'MaterialExpressionMaterialFunctionCall_3', 'MaterialExpressionStaticSwitchParameter_1'),
              ('MaterialExpressionComponentMask_13', 'MaterialExpressionMaterialFunctionCall_7', 'MaterialExpressionOneMinus_1',
               'MaterialExpressionMaterialFunctionCall_8', 'MaterialExpressionMaterialFunctionCall_9', 'MaterialExpressionStaticSwitchParameter_5'),
              ('MaterialExpressionComponentMask_14', 'MaterialExpressionMaterialFunctionCall_10', 'MaterialExpressionOneMinus_2',
               'MaterialExpressionMaterialFunctionCall_12', 'MaterialExpressionMaterialFunctionCall_13', 'MaterialExpressionStaticSwitchParameter_2')])
    m.pin('Normal', detail_normal(normal, dopac, dnorm, names))
    # unlit: only the emissive (and the coverage) count; no opacity (the composite adds the glow)
    m.pin('BaseColor', Node('Constant', name='MaterialExpressionConstant_3', R=0.0))
    m.pin('Metallic', Node('Constant', name='MaterialExpressionConstant_0', R=0.0))
    m.pin('Specular', Node('Constant', name='MaterialExpressionConstant_1', R=0.5))
    m.pin('Roughness', Node('Constant', name='MaterialExpressionConstant_4', R=0.5))
    m.pin('Opacity', Node('Constant', name='MaterialExpressionConstant_6', R=0.0))
    dcov = switch('MaterialExpressionStaticSwitchParameter_8', 'DetailCoverage', mask('MaterialExpressionComponentMask_21', (dcover, 5), 'a'),
                  Node('Constant', name='MaterialExpressionConstant_8', R=1.0))
    m.pin('OpacityMask', switch('MaterialExpressionStaticSwitchParameter_0', 'Coverage',
                                Node('Multiply', {'A': (cover, 4), 'B': dcov}, name='MaterialExpressionMultiply_3'),
                                Node('Constant', name='MaterialExpressionConstant_2', R=1.0)))
    nws, cam = Node('PixelNormalWS'), Node('CameraVectorWS')
    occ = (occl, 4)
    # (no game instance turns Reference on: as off)
    exponent = switch('MaterialExpressionStaticSwitchParameter_4', 'Reference', Node('Multiply', {'A': mask(None, (mrv, 2), 'r')}, name='MaterialExpressionMultiply_4', ConstB=1.0),
                      mask('MaterialExpressionComponentMask_1', (mrv, 2), 'r'))
    glow = custom(HOLOGRAM_GLOW, {'Normal': nws, 'CameraVector': cam, 'Occlusion': occ, 'Exponent': exponent}, 1, 'Hologram glow')
    local = call('MaterialExpressionMaterialFunctionCall_0', 'LocalPosition')
    sparkle = custom(HOLOGRAM_SPARKLE, {'Position': local, 'Noise': Node('ExternalHook', Hook='BlueNoiseVolume', Type='Texture3D')}, 1, 'Hologram sparkle')
    blue = Node('Multiply', {'A': glow, 'B': sparkle}, name='MaterialExpressionMultiply_9')
    # the eye: the glow of the cornea (its own normal, the pupil's occlusion) toward the plain glow at grazing angles
    gaze_w = Node('Transform', {'Input': call('MaterialExpressionMaterialFunctionCall_16', 'NormalizeNormalRG',
                                              NormalRG=mask('MaterialExpressionComponentMask_3', gaze, 'rg'))},
                  TransformSourceType='TRANSFORMSOURCE_Tangent', TransformType='TRANSFORM_World')
    cornea = custom(HOLOGRAM_CORNEA, {'UV': uv0}, 1, 'Cornea mask')
    surface = Node('Normalize', {'VectorInput': Node('LinearInterpolate', {'A': nws, 'B': gaze_w, 'Alpha': cornea})})
    iris_uv = custom(HOLOGRAM_IRIS_UV, {'UV': uv0, 'Normal': nws, 'Gaze': gaze_w, 'Cornea': cornea}, 2, 'Iris coordinate')
    pupil = custom(HOLOGRAM_PUPIL, {'UV': iris_uv, 'Occlusion': occ, 'Cornea': cornea}, 1, 'Pupil occlusion')
    eye_glow = custom(HOLOGRAM_GLOW, {'Normal': surface, 'CameraVector': cam, 'Occlusion': pupil, 'Exponent': Node('OneMinus', {'Input': cornea})},
                      1, 'Cornea glow')
    fresnel = custom('float A = 1.0 - saturate(dot(Normal, CameraVector));\nreturn lerp(0.0455, 1.0, A * (A * A) * (A * A));',
                     {'Normal': nws, 'CameraVector': cam}, 1, 'Cornea Fresnel')
    eye = Node('Multiply', {'A': Node('LinearInterpolate', {'A': eye_glow, 'B': glow, 'Alpha': fresnel}), 'B': sparkle}, name='MaterialExpressionMultiply_8')
    perlin = custom(HOLOGRAM_PERLIN, {'Normal': nws, 'CameraVector': cam, 'Occlusion': occ, 'Position': local,
                                      'Time': Node('Frac', {'Input': scalar('MaterialExpressionScalarParameter_0', 'AnimateTime', 'Dynamic')}),
                                      'Noise': Node('ExternalHook', Hook='VolumeNoise', Type='Texture3D')}, 1, 'Hologram Perlin')
    perlin = Node('Multiply', {'A': perlin}, name='MaterialExpressionMultiply_13', ConstB=1.0)
    plain = switch('MaterialExpressionStaticSwitchParameter_13', 'Perlin', perlin,
                   switch('MaterialExpressionStaticSwitchParameter_12', 'Blue', blue, Node('Constant', name='MaterialExpressionConstant_16', R=0.0)))
    with_eye = switch('MaterialExpressionStaticSwitchParameter_17', 'Perlin', plain,
                      switch('MaterialExpressionStaticSwitchParameter_15', 'Blue', eye, Node('Constant', name='MaterialExpressionConstant_17', R=0.0)))
    effect = switch('MaterialExpressionStaticSwitchParameter_7', 'Eye', with_eye, plain)
    tint = Node('Multiply', {'A': call('MaterialExpressionMaterialFunctionCall_14', 'CompositeColor',
                                       R=scalar('MaterialExpressionScalarParameter_1', 'DynamicEmissiveColor_X', 'Dynamic', 1.0),
                                       G=scalar('MaterialExpressionScalarParameter_2', 'DynamicEmissiveColor_Y', 'Dynamic', 1.0),
                                       B=scalar('MaterialExpressionScalarParameter_3', 'DynamicEmissiveColor_Z', 'Dynamic', 1.0)),
                             'B': scalar('MaterialExpressionScalarParameter_17', 'DynamicEmissiveIntensity', 'Dynamic', 1.0)})
    # soft: fading in over 50 units in front of the game's extra scene depth
    soft = switch('MaterialExpressionStaticSwitchParameter_3', 'Soft', call('MaterialExpressionMaterialFunctionCall_11', 'HermiteLimited',
                  S=call('MaterialExpressionMaterialFunctionCall_5', 'ExtraSceneDepthFade', UnitDistance=Node('Constant', name='MaterialExpressionConstant_14', R=50.0)),
                  R=Node('Constant', name='MaterialExpressionConstant_15', R=1.0)), Node('Constant', name='MaterialExpressionConstant_10', R=1.0), default=True)
    m.pin('EmissiveColor', Node('Multiply', {'A': Node('Multiply', {'A': Node('Multiply', {'A': tint, 'B': effect}), 'B': soft}),
                                             'B': Node('ExternalHook', Hook='ConditionalEmissive', Type=1)}, name='MaterialExpressionMultiply_5'))
    m.props.update(shading_model='MSM_Unlit', blend='AlphaComposite', fog='pixel', tangent_space_normal=True)
    return m


def EndMaterial_InvisibleBody():
    # the Standard's nodes (without its directional tilt, interior, LiteDecal and IdentifierCoverage), unlit and translucent
    _SHARED.clear()
    m = Material('EndMaterial_InvisibleBody', M_ROOT + '/EndMaterial_InvisibleBody')
    uv0 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_1', CoordinateIndex=0)
    uv1 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_3', CoordinateIndex=1)
    uv2 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_8', CoordinateIndex=2)
    normal = tex('MaterialExpressionTextureSampleParameter2D_7', '0:3:Normal', uv0, 'LinearColor', '8080FF00')
    mrv = tex('MaterialExpressionTextureSampleParameter2D_4', '0:2:Metallic/Roughness/Variant', uv0, 'LinearColor', '008000FF')
    occl = tex('MaterialExpressionTextureSampleParameter2D_5', '1:0:Occlusion', uv1, 'Alpha', 'FF000000_BC4')
    cover = tex('MaterialExpressionTextureSampleParameter2D_2', '0:1:Coverage', uv0, 'Alpha', 'FF000000_BC4')
    dopac = tex('MaterialExpressionTextureSampleParameter2D_17', '0:5:DetailOpacity', uv0, 'LinearColor', '000000FF')
    dnorm = [tex('MaterialExpressionTextureSampleParameter2D_14', '2:0:DetailNormal:0', uv2, 'LinearColor', '8080FF00'),
             tex('MaterialExpressionTextureSampleParameter2D_0', '2:1:DetailNormal:1', uv2, 'LinearColor', '8080FF00'),
             tex('MaterialExpressionTextureSampleParameter2D_1', '2:2:DetailNormal:2', uv2, 'LinearColor', '8080FF00')]
    dcover = tex('MaterialExpressionTextureSampleParameter2D_3', '2:3:DetailCoverage', uv2, 'Alpha', 'FF000000_BC4')
    m.pin('Normal', detail_normal(normal, dopac, dnorm))
    m.pin('BaseColor', Node('Constant', name='MaterialExpressionConstant_6', R=0.0))
    m.pin('Metallic', Node('Constant', name='MaterialExpressionConstant_7', R=0.0))
    m.pin('Specular', Node('Constant', name='MaterialExpressionConstant_8', R=0.5))
    m.pin('Roughness', Node('Constant', name='MaterialExpressionConstant_9', R=0.5))
    m.pin('Opacity', Node('Constant', name='MaterialExpressionConstant_10', R=0.0))
    m.pin('AmbientOcclusion', detail_occlusion(uv2, occl))
    m.pin('OpacityMask', detail_coverage(cover, dcover))
    m.pin('EmissiveColor', standard_emissive(uv0, uv2, mrv, interior=False, conditional_off='MaterialExpressionConstant_12',
                                             flow_names=('MaterialExpressionTextureSampleParameter2D_6', 'MaterialExpressionTextureSampleParameter2D_19')))
    coord = mask('MaterialExpressionComponentMask_36', Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_11', CoordinateIndex=3), 'r')
    animation(m, coord,
              rigid={'current': {'call': 'MaterialExpressionMaterialFunctionCall_15', 'switches': ['MaterialExpressionStaticSwitchParameter_15', 'MaterialExpressionStaticSwitchParameter_51', 'MaterialExpressionStaticSwitchParameter_54'],
                                 'defaults': ['MaterialExpressionConstant4Vector_7', 'MaterialExpressionConstant4Vector_8', 'MaterialExpressionConstant4Vector_9']},
                     'previous': {'call': 'MaterialExpressionMaterialFunctionCall_23', 'switches': ['MaterialExpressionStaticSwitchParameter_56', 'MaterialExpressionStaticSwitchParameter_58', 'MaterialExpressionStaticSwitchParameter_55'],
                                  'defaults': ['MaterialExpressionConstant4Vector_10', 'MaterialExpressionConstant4Vector_11', 'MaterialExpressionConstant4Vector_12']}},
              soft={'current': {'call': 'MaterialExpressionMaterialFunctionCall_20', 'switches': ['MaterialExpressionStaticSwitchParameter_34', 'MaterialExpressionStaticSwitchParameter_52']},
                    'previous': {'call': 'MaterialExpressionMaterialFunctionCall_25', 'switches': ['MaterialExpressionStaticSwitchParameter_57', 'MaterialExpressionStaticSwitchParameter_59']}},
              fluid={'call': 'MaterialExpressionMaterialFunctionCall_24', 'current': ['MaterialExpressionStaticSwitchParameter_50', 'MaterialExpressionStaticSwitchParameter_53'],
                     'previous': ['MaterialExpressionStaticSwitchParameter_48', 'MaterialExpressionStaticSwitchParameter_49']},
              prev_key_name='MaterialExpressionScalarParameter_18')
    m.props.update(shading_model='MSM_Unlit', blend='AlphaComposite', fog='vertex', tangent_space_normal=True)
    return m


def vparam(name, param, group, default=(0.0, 0.0, 0.0, 0.0)):
    if name not in _SHARED:
        _SHARED[name] = Node('VectorParameter', name=name, ParameterName=param, Group=group, DefaultValue=tuple(default))
    return _SHARED[name]


def vec4(vp):
    """a vector parameter as the game's materials read one: its RGB and its A appended back together"""
    return Node('AppendVector', {'A': (vp, 0), 'B': (vp, 4)})


# the particles' random number for the coordinates' distribution (-1..1): a hash of the seed in the particle's dynamic
# parameter (its w, in 1/1024ths)
PARTICLE_RANDOM = """
uint Seed = (uint)(frac(Value - 0.99951171875) * 1024.0);
return frac(sin(float(Seed) * 92.2228) * 43758.5453) * 2.0 - 1.0;"""

# the particle's visibility: its colour's alpha, the nearly invisible and the nearly opaque snapped
PARTICLE_VISIBILITY = """
float A = Alpha < 0.000001 ? 0.0 : Alpha;
return A > 0.999999 ? 1.0 : min(A, 1.0);"""

# a layer's coordinate: the texture coordinate turned, offset (the offset spread by the distribution, per particle),
# moved by the parallax and scaled - or with FlipBook the particle's sub-image coordinate (moved by the parallax)
LAYER_COORDINATE = """
float2 UV = Rotated + (Offset + (Offset * Distribution.xz + Distribution.yw) * Random) + Parallax;
UV *= Scale;
return FlipBook >= 0.5 ? SubUV + Parallax : UV;"""

# the game's particle visibility by the view (the particle vertex factories apply it to the particle's alpha and cull
# the particle where it is 0, or nearer than y): by the angle at the emitter between the particle and the camera and by
# the camera's distance from the emitter (ViewDependentParticle: the angle's start and range, the distance's start and
# range); nothing for other vertex factories
PARTICLE_VIEW_MODIFIER = """
#if PARTICLE_SPRITE_FACTORY || PARTICLE_MESH_FACTORY || PARTICLE_BEAMTRAIL_FACTORY
float3 ToParticle = ParticlePosition - EmitterPosition;
ToParticle *= rsqrt(max(dot(ToParticle, ToParticle), 0.01));
float3 ToCamera = CameraPosition - EmitterPosition;
float Distance2 = dot(ToCamera, ToCamera);
ToCamera *= rsqrt(max(Distance2, 0.01));
float Angle = acos(clamp(-dot(ToParticle, ToCamera), -1.0, 1.0));
float2 F = saturate((float2(Angle, sqrt(Distance2)) - ViewDependentParticle.xz) / max(ViewDependentParticle.yw, 0.00001));
return float4(min(1.0 + F.x - F.y, 1.0), max(ViewNear, NearDistance), 0.0, 0.0);
#else
return float4(0.0, 0.0, 0.0, 0.0);
#endif"""


def particle_view_modifier(emitter, vdp, near):
    return custom(PARTICLE_VIEW_MODIFIER, {'ParticlePosition': Node('ParticlePositionWS'), 'CameraPosition': Node('CameraPositionWS'),
                                           'EmitterPosition': (emitter, 0), 'ViewDependentParticle': vec4(vdp), 'NearDistance': near,
                                           'ViewNear': Node('ExternalHook', Hook='NearPlane', Type=1)}, 4, 'Particle view modifier')


def layer_coordinates(layers, uv, random, subuv):
    """the coordinate of each texture layer: layers [(custom name, rotate call name, flipbook, rotation, offset, scale,
    distribution, parallax)] - the parameters as nodes, parallax its offset (float2)"""
    out = []
    for cname, rname, flip, rot, off, scale, dist, par in layers:
        rotated = call(rname, 'RotateCoordinateRightAngle', Angle=rot, Coordinate=uv)
        out.append(custom(LAYER_COORDINATE, {'Rotated': rotated, 'Offset': mask(None, vec4(off), 'rg'), 'Distribution': vec4(dist),
                                             'Scale': mask(None, vec4(scale), 'rg'), 'Random': random, 'Parallax': par, 'FlipBook': flip,
                                             'SubUV': subuv}, 2, 'Layer coordinate', name=cname))
    return out


def EndMaterial_Directional():
    """the game's directional distortion: the scene behind moved along the surface's (or the particle's) tangent, by an
    intensity from the layers' textures (with the view dependency, the edge, the modifier, the visibility, the distance
    fade and the soft fade) - the game's distortion pass, as PixelIndependentVector0; its base pass draws nothing"""
    _SHARED.clear()
    m = Material('EndMaterial_Directional', M_ROOT + '/EndMaterial_Directional')
    uv = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_1', CoordinateIndex=0)
    random = custom(PARTICLE_RANDOM, {'Value': (Node('DynamicParameter', ParamNames=['Param1', 'Param2', 'Param3', 'Param4']), 3)}, 1,
                    'Particle random')
    subuv = (Node('ParticleSubUVProperties'), 0)
    nws, cam = Node('PixelNormalWS'), Node('CameraVectorWS')
    zero2 = Node('Constant2Vector', name='MaterialExpressionConstant2Vector_0', R=0.0, G=0.0)
    mip = Node('Constant', name='MaterialExpressionConstant_6', R=0.0)

    def layer_tex(name, param, coord, default):
        return Node('TextureSampleParameter2D', {'Coordinates': coord, 'MipValue': mip}, name=name, ParameterName=param, SamplerType='Alpha',
                    Texture=default, Group='Texture', MipValueMode='TMVM_MipBias')

    def params(k, flip, rot, off, scale, dist, par):
        sp = 'Coordinate' if k == 0 else 'Cordinate'     # (the game's spelling)
        return (scalar('MaterialExpressionScalarParameter_%d' % flip, '%d:Coordinate:FlipBook(Boolean)' % k, 'Dynamic'),
                scalar('MaterialExpressionScalarParameter_%d' % rot, '%d:Coordinate:Rotation(Float1)' % k, 'Dynamic'),
                vparam('MaterialExpressionVectorParameter_%d' % off, '%d:Coordinate:Offset(Float2)' % k, 'Dynamic'),
                vparam('MaterialExpressionVectorParameter_%d' % scale, '%d:Coordinate:Scale(Float2)' % k, 'Dynamic'),
                vparam('MaterialExpressionVectorParameter_%d' % dist, '%d:Coordinate:Distribution(Float4)' % k, 'Dynamic'),
                scalar('MaterialExpressionScalarParameter_%d' % par, '%d:%s:Parallax(Float1)' % (k, sp), 'Dynamic', 1.0))
    p = [params(0, 0, 1, 0, 4, 15, 24), params(1, 3, 6, 5, 6, 17, 28), params(2, 5, 4, 9, 10, 18, 25), params(3, 11, 10, 8, 11, 19, 27)]
    # the parallax layer (1): its height times the parallax along the view in tangent space
    c1, = layer_coordinates([('MaterialExpressionCustom_5', 'MaterialExpressionMaterialFunctionCall_7') + p[1][:5] +
                             (Node('Multiply', {'A': p[1][5]}, ConstB=0.0),)], uv, random, subuv)
    height = layer_tex('MaterialExpressionTextureSampleParameter2D_4', '1:Parallax', c1, '000000FF_BC4')
    view_t = mask(None, Node('Transform', {'Input': cam}, TransformSourceType='TRANSFORMSOURCE_World', TransformType='TRANSFORM_Tangent'), 'rg')
    shift = Node('Multiply', {'A': Node('Multiply', {'A': (height, 4), 'B': Node('Max', {'A': scalar('MaterialExpressionScalarParameter_9', 'L:Parallax(Float1)', 'Dynamic')}, ConstB=0.0)}),
                              'B': view_t}, name='MaterialExpressionMultiply_9')
    parallax = switch('MaterialExpressionStaticSwitchParameter_1', 'Parallax', shift, zero2)
    c0, c2, c3 = layer_coordinates([(cn, rn) + p[k][:5] + (Node('Multiply', {'A': p[k][5], 'B': parallax}),)
                                    for k, cn, rn in ((0, 'MaterialExpressionCustom_4', 'MaterialExpressionMaterialFunctionCall_3'),
                                                      (2, 'MaterialExpressionCustom_6', 'MaterialExpressionMaterialFunctionCall_9'),
                                                      (3, 'MaterialExpressionCustom_10', 'MaterialExpressionMaterialFunctionCall_6'))],
                                   uv, random, subuv)
    directional = layer_tex('MaterialExpressionTextureSampleParameter2D_1', '0:Directional', c0, 'FF000000_BC4')
    visibility_t = layer_tex('MaterialExpressionTextureSampleParameter2D_3', '2:Visibility', c2, 'FF000000_BC4')
    modifier_t = layer_tex('MaterialExpressionTextureSampleParameter2D_5', '3:Modifier', c3, 'FF000000_BC4')
    base = Node('Clamp', {'Input': (directional, 4)}, name='MaterialExpressionClamp_1')
    modifier = switch('MaterialExpressionStaticSwitchParameter_19', 'Modifier',
                      call('MaterialExpressionMaterialFunctionCall_16', 'BlendModifier', X=base,
                           Y=mask('MaterialExpressionComponentMask_29', (modifier_t, 5), 'a'),
                           Blend=Node('Clamp', {'Input': scalar('MaterialExpressionScalarParameter_12', 'L:Blend(Float1)', 'Dynamic')}, name='MaterialExpressionClamp_14'),
                           Ratio=Node('Clamp', {'Input': scalar('MaterialExpressionScalarParameter_13', 'L:Modifier(Float1)', 'Dynamic', 1.0)}, name='MaterialExpressionClamp_15')),
                      base)
    view = switch('MaterialExpressionStaticSwitchParameter_10', 'ViewDependent',
                  custom("""
float NoV = min(abs(dot(Normal, CameraVector)), 1.0);
return lerp(1.0, pow(NoV, exp2(Tone)), ViewDependency);""", {'Normal': nws, 'CameraVector': cam,
                                                             'Tone': scalar('MaterialExpressionScalarParameter_14', 'L:ToneViewDependency(Float1)', 'Dynamic'),
                                                             'ViewDependency': Node('Clamp', {'Input': scalar('MaterialExpressionScalarParameter_22', 'L:ViewDependency(Float1)', 'Dynamic')})},
                         1, 'View dependency', name='MaterialExpressionCustom_2'),
                  Node('Constant', name='MaterialExpressionConstant_2', R=1.0), 'STATIC_SWITCH_VIEW_DEPENDENT', default=True)
    edge = switch('MaterialExpressionStaticSwitchParameter_13', 'Edge',
                  custom('return min(abs(dot(Normal, CameraVector)), 1.0);', {'Normal': nws, 'CameraVector': cam}, 1, 'Edge',
                         name='MaterialExpressionCustom_3'),
                  Node('Constant', name='MaterialExpressionConstant_11', R=1.0))
    particle = custom(PARTICLE_VISIBILITY, {'Alpha': (Node('ParticleColor'), 4)}, 1, 'Particle visibility')
    visibility = switch('MaterialExpressionStaticSwitchParameter_0', 'Visibility', mask('MaterialExpressionComponentMask_6', (visibility_t, 5), 'a'),
                        Node('Constant', name='MaterialExpressionConstant_0', R=1.0))
    near = scalar('MaterialExpressionScalarParameter_30', 'L:NearDistance(Float1)', 'System')
    fade = call('MaterialExpressionMaterialFunctionCall_2', 'DistanceFade', NearDistance=near,
                FarDistance=scalar('MaterialExpressionScalarParameter_33', 'L:FarDistance(Float1)', 'System'))
    soft = switch('MaterialExpressionStaticSwitchParameter_21', 'Soft',
                  call('MaterialExpressionMaterialFunctionCall_0', 'HermiteLimited',
                       S=call('MaterialExpressionMaterialFunctionCall_4', 'ExtraSceneDepthFade', UnitDistance=Node('Constant', name='MaterialExpressionConstant_1', R=50.0)),
                       R=Node('Constant', name='MaterialExpressionConstant_15', R=1.0)),
                  Node('Constant', name='MaterialExpressionConstant_7', R=1.0))
    coverage = Node('Clamp', {'Input': scalar('MaterialExpressionScalarParameter_17', 'A:0:Coverage(Float1)', 'System', 1.0)})
    x = Node('Multiply', {'A': modifier, 'B': Node('Multiply', {'A': view, 'B': Node('Multiply', {'A': particle, 'B': edge})})})
    for f in (coverage, visibility, fade, soft):
        x = Node('Multiply', {'A': x, 'B': f})
    intensity = Node('Multiply', {'A': x, 'B': Node('Max', {'A': scalar('MaterialExpressionScalarParameter_2', 'L:Directional(Float1)', 'Dynamic')}, ConstB=0.0)},
                     name='MaterialExpressionMultiply_1')
    # (the velocity switches tell the game's distortion pass the direction - the tangent, the normal, the binormal)
    v = switch('MaterialExpressionStaticSwitchParameter_2', 'VelocityTangent', intensity, intensity, 'STATIC_SWITCH_VELOCITY_TANGENT')
    v = switch('MaterialExpressionStaticSwitchParameter_4', 'VelocityBinormal', v, v, 'STATIC_SWITCH_VELOCITY_BINORMAL')
    v = switch('MaterialExpressionStaticSwitchParameter_3', 'VelocityNormal', v, v, 'STATIC_SWITCH_VELOCITY_NORMAL')
    m.pin('PixelIndependentVector0', v)
    m.pin('VertexContextVector0', particle_view_modifier(vparam('MaterialExpressionVectorParameter_3', 'A:1:EmitterPosition(Float3)', 'System'),
                                                         vparam('MaterialExpressionVectorParameter_14', 'A:3:ViewDependentParticle(Float4)', 'System'), near))
    # (the base pass draws nothing: no emissive, no opacity)
    m.pin('Opacity', Node('Constant', R=0.0))
    # (the game's base pass of it draws nothing at all - not even the editor's selection colour)
    m.props.update(shading_model='MSM_Unlit', blend='AlphaComposite', distortion=True, base_pass_draws_nothing=True, tangent_space_normal=True)
    return m


def mf_DecodeSGrayInexact():
    f = Function('DecodeSGrayInexact', [('sGray', 'Scalar', (0.5,))], 'An sRGB-encoded gray made linear (roughly: its square).',
                 MF_ROOT + '/DecodeSGrayInexact')
    return f.output('Gray', custom('return sGray * sGray;', {'sGray': f.inp('sGray')}, 1, 'DecodeSGrayInexact'))


def mf_Luminance709():
    # (the game's weights, whatever the name: Rec. 601's)
    f = Function('Luminance709', [('RGB', 'Vector3', (1.0, 1.0, 1.0))], 'The luminance of a colour.', MF_ROOT + '/Luminance709')
    return f.output('Luminance', custom('return dot(RGB, float3(0.299, 0.587, 0.114));', {'RGB': f.inp('RGB')}, 1, 'Luminance709'))


# the particle's layer coordinate (EndMaterial_Particle's): the texture coordinate turned, offset (spread per particle),
# moved by the parallax and scaled - or with FlipBook the particle's sub-image coordinate (one of its two sub-images,
# dithered by their blend), moved by the parallax; the derivatives the texture is sampled with: the coordinate's - with
# FlipBook the first sub-image's (continuous where the dithered choice is not)
PARTICLE_LAYER_UV = """
float2 UV = Rotated + (Offset + (Offset * Distribution.xz + Distribution.yw) * Random) + Parallax;
return UV * Scale;"""
PARTICLE_LAYER_COORDINATE = """
float2 Flip = ((Noise.x * 0.99609375 + 0.001953125 >= SubUVLerp) ? SubUV0 : SubUV1) + Parallax;
return FlipBook >= 0.5 ? Flip : UV;"""
PARTICLE_LAYER_DX = 'return FlipBook >= 0.5 ? ddx(SubUV0 + Parallax) : ddx(UV);'
PARTICLE_LAYER_DY = 'return FlipBook >= 0.5 ? ddy(SubUV0 + Parallax) : ddy(UV);'

# the particle's tone: a colour (and its alpha) and a luminance between their first and second values, by X raised to
# the tone exponents (2^Tone...), softened toward the smooth (Hermite) step by Hermite; the colour times the luminance and
# the alpha
PARTICLE_TONE = """
float T = X < 0.000001 ? 0.0 : pow(X, exp2(ToneColor));
T *= lerp(1.0, T * (3.0 - 2.0 * T), Hermite);
float4 C = lerp(First, Second, T);
float U = X < 0.000001 ? 0.0 : pow(X, exp2(ToneLuminance));
U *= lerp(1.0, U * (3.0 - 2.0 * U), Hermite);
return C.rgb * lerp(FirstLuminance, SecondLuminance, U) * C.a;"""

# the particle's emissive: its colour by the luminance (spread per particle by the distribution) and, under the
# exposure condition, the game's conditional scale
PARTICLE_EMIT = """
float L = max(Luminance + (Luminance * Distribution.x + Distribution.y) * Random, 0.0);
return Color * L * (ExposureCondition > 0.5 ? Conditional : 1.0);"""


def particle_tone(x, prefix, color_name, lum_name, hermite_name, names):
    """a tone custom: names (first colour, second colour, first luminance, second luminance) as (node name, parameter)"""
    (fc, fcp), (sc, scp), (fl, flp), (sl, slp) = names
    return custom(PARTICLE_TONE, {'X': x, 'ToneColor': scalar(*color_name, 'Dynamic'), 'ToneLuminance': scalar(*lum_name, 'Dynamic'),
                                  'Hermite': Node('Clamp', {'Input': scalar(*hermite_name, 'Dynamic', 1.0)}),
                                  'First': Node('Clamp', {'Input': vec4(vparam(fc, fcp, 'Dynamic'))}),
                                  'Second': Node('Clamp', {'Input': vec4(vparam(sc, scp, 'Dynamic'))}),
                                  'FirstLuminance': Node('Max', {'A': scalar(fl, flp, 'Dynamic')}, ConstB=0.0),
                                  'SecondLuminance': Node('Max', {'A': scalar(sl, slp, 'Dynamic', 1.0)}, ConstB=0.0)}, 3, prefix + ' tone')


def EndMaterial_Particle():
    """the game's particles: four texture layers (the colour or gray, the opacity, the occlusion, the diffuse and the
    normal; the parallax; the visibility; the modifier) on the particle's coordinates, the emissive graded by tones
    (and an extra tone by the edge or the radius), the opacity, lit (the game's volumetric lighting modes) or unlit; the
    game's translucent pass dims it by the particle's visibility (PixelContextVector1) and coverage (the opacity mask)"""
    _SHARED.clear()
    m = Material('EndMaterial_Particle', M_ROOT + '/EndMaterial_Particle')
    uv = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_1', CoordinateIndex=0)
    random = custom(PARTICLE_RANDOM, {'Value': (Node('DynamicParameter', ParamNames=['Param1', 'Param2', 'Param3', 'Param4']), 3)}, 1,
                    'Particle random')
    sub = Node('ParticleSubUVProperties')
    noise = Node('ExternalHook', Hook='BlueNoise', Type=3)
    nws, cam = Node('PixelNormalWS'), Node('CameraVectorWS')
    zero2 = Node('Constant2Vector', name='MaterialExpressionConstant2Vector_0', R=0.0, G=0.0)

    def params(k, flip, rot, off, scale, dist, par):
        sp = 'Coordinate' if k == 0 else 'Cordinate'     # (the game's spelling)
        return (scalar('MaterialExpressionScalarParameter_%d' % flip, '%d:0:Coordinate:0:FlipBook(Boolean)' % k, 'Dynamic'),
                scalar('MaterialExpressionScalarParameter_%d' % rot, '%d:0:Coordinate:1:Rotation(Float1)' % k, 'Dynamic'),
                vparam('MaterialExpressionVectorParameter_%d' % off, '%d:0:Coordinate:2:Offset(Float2)' % k, 'Dynamic'),
                vparam('MaterialExpressionVectorParameter_%d' % scale, '%d:0:Coordinate:3:Scale(Float2)' % k, 'Dynamic'),
                vparam('MaterialExpressionVectorParameter_%d' % dist, '%d:0:Coordinate:5:Distribution(Float4)' % k, 'Dynamic'),
                scalar('MaterialExpressionScalarParameter_%d' % par, '%d:0:%s:4:Parallax(Float1)' % (k, sp), 'Dynamic', 1.0))

    def layer(k, names, parallax):
        cn, dxn, dyn, rn = names
        flip, rot, off, scale, dist, par = params(*[k] + list({0: (0, 1, 0, 4, 15, 24), 1: (3, 6, 5, 6, 17, 28), 2: (5, 4, 9, 10, 18, 25),
                                                                   3: (11, 10, 8, 11, 19, 27)}[k]))
        shift = Node('Multiply', {'A': par, 'B': parallax}) if parallax is not None else Node('Multiply', {'A': par}, ConstB=0.0)
        rotated = call(rn, 'RotateCoordinateRightAngle', Angle=rot, Coordinate=uv)
        uvk = custom(PARTICLE_LAYER_UV, {'Rotated': rotated, 'Offset': mask(None, vec4(off), 'rg'), 'Distribution': vec4(dist),
                                        'Scale': mask(None, vec4(scale), 'rg'), 'Random': random, 'Parallax': shift}, 2, 'Layer UV')
        coord = custom(PARTICLE_LAYER_COORDINATE, {'UV': uvk, 'FlipBook': flip, 'SubUV0': (sub, 0), 'SubUV1': (sub, 1), 'SubUVLerp': (sub, 2),
                                                   'Noise': noise, 'Parallax': shift}, 2, 'Layer coordinate', name=cn)
        dx = custom(PARTICLE_LAYER_DX, {'UV': uvk, 'FlipBook': flip, 'SubUV0': (sub, 0), 'Parallax': shift}, 2, 'Layer DDX', name=dxn)
        dy = custom(PARTICLE_LAYER_DY, {'UV': uvk, 'FlipBook': flip, 'SubUV0': (sub, 0), 'Parallax': shift}, 2, 'Layer DDY', name=dyn)
        return coord, dx, dy

    def ltex(name, param, lay, sampler, default):
        coord, dx, dy = lay
        return Node('TextureSampleParameter2D', {'Coordinates': coord, 'CoordinatesDX': dx, 'CoordinatesDY': dy}, name=name, ParameterName=param,
                    SamplerType=sampler, Texture=default, Group='Texture', MipValueMode='TMVM_Derivative')
    # the parallax layer (1): its height times the parallax along the view in tangent space
    l1 = layer(1, ('MaterialExpressionCustom_5', 'MaterialExpressionCustom_41', 'MaterialExpressionCustom_42', 'MaterialExpressionMaterialFunctionCall_7'), None)
    height = ltex('MaterialExpressionTextureSampleParameter2D_4', '1:0:0:Parallax', l1, 'Alpha', '000000FF_BC4')
    view_t = mask(None, Node('Transform', {'Input': cam}, TransformSourceType='TRANSFORMSOURCE_World', TransformType='TRANSFORM_Tangent'), 'rg')
    shift = Node('Multiply', {'A': Node('Multiply', {'A': (height, 4), 'B': Node('Max', {'A': scalar('MaterialExpressionScalarParameter_9', 'L:2:Parallax(Float1)', 'Dynamic')}, ConstB=0.0)}),
                              'B': view_t}, name='MaterialExpressionMultiply_9')
    parallax = switch('MaterialExpressionStaticSwitchParameter_1', '2:Parallax', shift, zero2)
    l0 = layer(0, ('MaterialExpressionCustom_4', 'MaterialExpressionCustom_36', 'MaterialExpressionCustom_40', 'MaterialExpressionMaterialFunctionCall_3'), parallax)
    l2 = layer(2, ('MaterialExpressionCustom_6', 'MaterialExpressionCustom_43', 'MaterialExpressionCustom_44', 'MaterialExpressionMaterialFunctionCall_9'), parallax)
    l3 = layer(3, ('MaterialExpressionCustom_10', 'MaterialExpressionCustom_45', 'MaterialExpressionCustom_46', 'MaterialExpressionMaterialFunctionCall_6'), parallax)
    color_t = ltex('MaterialExpressionTextureSampleParameter2D_6', '0:0:0:Color', l0, 'Color', '767676FF_sRGB')
    gray_t = ltex('MaterialExpressionTextureSampleParameter2D_1', '0:1:0:Gray', l0, 'Alpha', '767676FF_BC4')
    opacity_t = ltex('MaterialExpressionTextureSampleParameter2D_0', '0:2:0:Opacity', l0, 'Alpha', 'FF000000_BC4')
    diffuse_t = ltex('MaterialExpressionTextureSampleParameter2D_10', '0:3:0:Diffuse', l0, 'Color', 'FFFFFFFF_sRGB')
    normal_t = ltex('MaterialExpressionTextureSampleParameter2D_11', '0:4:0:Normal', l0, 'LinearColor', '8080FF00')
    occlusion_t = ltex('MaterialExpressionTextureSampleParameter2D_2', '0:5:0:Occlusion', l0, 'Alpha', 'FF000000_BC4')
    visibility_t = ltex('MaterialExpressionTextureSampleParameter2D_3', '2:0:0:Visibility', l2, 'Alpha', 'FF000000_BC4')
    modifier_t = ltex('MaterialExpressionTextureSampleParameter2D_5', '3:0:0:Modifier', l3, 'Alpha', 'FF000000_BC4')

    # the colour (or the gray), graded by the tone of its luminance (modified by the modifier layer's gray) - or as it is
    gray = switch('MaterialExpressionStaticSwitchParameter_8', 'B:Gray',
                  call('MaterialExpressionMaterialFunctionCall_1', 'DecodeSGrayInexact', sGray=mask('MaterialExpressionComponentMask_27', (gray_t, 5), 'a')),
                  Node('Constant', name='MaterialExpressionConstant_3', R=1.0))
    color = switch('MaterialExpressionStaticSwitchParameter_2', '0:Color', mask('MaterialExpressionComponentMask_25', color_t, 'rgb'),
                   const3('MaterialExpressionConstant3Vector_9', (1, 1, 1)))
    lum = call('MaterialExpressionMaterialFunctionCall_5', 'Luminance709',
               RGB=custom('return saturate(Color * Gray);', {'Color': color, 'Gray': gray}, 3, 'Graded colour', name='MaterialExpressionCustom_12'))
    mod_gray = call('MaterialExpressionMaterialFunctionCall_12', 'DecodeSGrayInexact', sGray=mask('MaterialExpressionComponentMask_29', (modifier_t, 5), 'a'))
    blend = Node('Clamp', {'Input': scalar('MaterialExpressionScalarParameter_12', 'L:B:Blend(Float1)', 'Dynamic')}, name='MaterialExpressionClamp_14')
    ratio = Node('Clamp', {'Input': scalar('MaterialExpressionScalarParameter_13', 'L:C:Modifier(Float1)', 'Dynamic', 1.0)}, name='MaterialExpressionClamp_15')
    graded = switch('MaterialExpressionStaticSwitchParameter_4', 'F:Modifier',
                    call('MaterialExpressionMaterialFunctionCall_15', 'BlendModifier', X=lum, Y=mod_gray, Blend=blend, Ratio=ratio), lum)
    tone = particle_tone(graded, 'Colour', ('MaterialExpressionScalarParameter_16', 'L:5:ToneColor(Float1)'),
                         ('MaterialExpressionScalarParameter_21', 'L:6:ToneLuminance(Float1)'), ('MaterialExpressionScalarParameter_23', 'L:9:Hermite(Float1)'),
                         [('MaterialExpressionVectorParameter_1', 'L:7:Tone:0:FirstColor(RGBA)'), ('MaterialExpressionVectorParameter_2', 'L:7:Tone:2:SecondColor(RGBA)'),
                          ('MaterialExpressionScalarParameter_19', 'L:7:Tone:1:FirstLuminance(Float1)'),
                          ('MaterialExpressionScalarParameter_20', 'L:7:Tone:3:SecondLuminance(Float1)')])
    grade = switch('MaterialExpressionStaticSwitchParameter_5', '5:Grade',
                   Node('Multiply', {'A': switch('MaterialExpressionStaticSwitchParameter_7', '0:Color', Node('Saturate', {'Input': color}, name='MaterialExpressionMultiply_30'),
                                                 const3('MaterialExpressionConstant3Vector_1', (1, 1, 1))), 'B': tone}, name='MaterialExpressionMultiply_31'),
                   const3('MaterialExpressionConstant3Vector_3', (1, 1, 1)))
    core = switch('MaterialExpressionStaticSwitchParameter_12', '8:Identity', Node('Multiply', {'A': color, 'B': gray}, name='MaterialExpressionMultiply_36'),
                  Node('Multiply', {'A': grade}, ConstB=1.0, name='MaterialExpressionMultiply_29'))
    # the extra tone: of the edge (the facing) or of the radius
    edge_v = custom('return min(abs(dot(Normal, CameraVector)), 1.0);', {'Normal': nws, 'CameraVector': cam}, 1, 'Edge', name='MaterialExpressionCustom_3')
    ex_in = Node('Multiply', {'A': switch('MaterialExpressionStaticSwitchParameter_13', '6:Edge', edge_v, Node('Constant', name='MaterialExpressionConstant_11', R=1.0)),
                              'B': switch('MaterialExpressionStaticSwitchParameter_3', '7:Radius', particle_radius(),
                                          Node('Constant', name='MaterialExpressionConstant_12', R=1.0))})
    ex = particle_tone(ex_in, 'Extra', ('MaterialExpressionScalarParameter_35', 'L:D:EXToneColor(Float1)'),
                       ('MaterialExpressionScalarParameter_36', 'L:E:EXToneLuminance(Float1)'), ('MaterialExpressionScalarParameter_37', 'L:D:EXHermite(Float1)'),
                       [('MaterialExpressionVectorParameter_12', 'L:F:EXTone:0:FirstColor(RGBA)'), ('MaterialExpressionVectorParameter_13', 'L:F:EXTone:2:SecondColor(RGBA)'),
                        ('MaterialExpressionScalarParameter_31', 'L:F:EXTone:1:FirstLuminance(Float1)'),
                        ('MaterialExpressionScalarParameter_34', 'L:F:EXTone:3:SecondLuminance(Float1)')])
    ex.name = 'MaterialExpressionMultiply_33'
    extra = Node('Multiply', {'A': switch('MaterialExpressionStaticSwitchParameter_15', '6:Edge', ex, const3('MaterialExpressionConstant3Vector_4', (1, 1, 1))),
                              'B': switch('MaterialExpressionStaticSwitchParameter_16', '7:Radius', ex, const3('MaterialExpressionConstant3Vector_11', (1, 1, 1)))})
    pcolor = Node('ParticleColor')
    emit_color = Node('Multiply', {'A': Node('Multiply', {'A': core, 'B': extra}), 'B': Node('Saturate', {'Input': (pcolor, 0)})})
    ld = mask(None, vec4(vparam('MaterialExpressionVectorParameter_20', 'L:G:LuminanceDistribution(Float2)', 'Dynamic')), 'rg')
    emit = custom(PARTICLE_EMIT, {'Color': emit_color, 'Luminance': Node('Max', {'A': scalar('MaterialExpressionScalarParameter_2', 'L:0:Luminance(Float1)', 'Dynamic', 1.0)}, ConstB=0.0),
                                  'Distribution': ld, 'Random': random, 'ExposureCondition': scalar('MaterialExpressionScalarParameter_26', 'A:4:ExposureCondition(Float1)', 'System'),
                                  'Conditional': Node('ExternalHook', Hook='ConditionalEmissive', Type=1)}, 3, 'Emissive', name='MaterialExpressionCustom_29')
    m.pin('EmissiveColor', switch('MaterialExpressionStaticSwitchParameter_20', 'D:Emit', emit, Node('Constant', name='MaterialExpressionConstant_8', R=0.0)))
    # the opacity: the opacity layer's, raised to 2^ToneOpacity
    opacity = switch('MaterialExpressionStaticSwitchParameter_6', '1:Opacity',
                     custom('return X < 0.000001 ? 0.0 : pow(X, exp2(Tone));',
                            {'X': (opacity_t, 4), 'Tone': scalar('MaterialExpressionScalarParameter_15', 'L:I:ToneOpacity(Float1)', 'Dynamic')}, 1,
                            'Opacity tone', name='MaterialExpressionCustom_31'),
                     Node('Constant', name='MaterialExpressionConstant_1', R=1.0))
    m.pin('Opacity', Node('Multiply', {'A': opacity, 'B': Node('Clamp', {'Input': scalar('MaterialExpressionScalarParameter_7', 'L:1:Opacity(Float1)', 'Dynamic')})},
                          name='MaterialExpressionMultiply_20'))
    # the coverage (the game's translucent pass and its depth pass): the view dependency by the particle's visibility
    view = switch('MaterialExpressionStaticSwitchParameter_10', 'N:ViewDependent',
                  custom("""
float NoV = min(abs(dot(Normal, CameraVector)), 1.0);
return lerp(1.0, NoV < 0.000001 ? 0.0 : pow(NoV, exp2(Tone)), ViewDependency);""",
                         {'Normal': nws, 'CameraVector': cam, 'Tone': scalar('MaterialExpressionScalarParameter_14', 'L:H:ToneViewDependency(Float1)', 'Dynamic'),
                          'ViewDependency': Node('Clamp', {'Input': scalar('MaterialExpressionScalarParameter_22', 'L:8:ViewDependency(Float1)', 'Dynamic')})},
                         1, 'View dependency', name='MaterialExpressionCustom_2'),
                  Node('Constant', name='MaterialExpressionConstant_2', R=1.0), 'STATIC_SWITCH_VIEW_DEPENDENT', default=True)
    particle = custom(PARTICLE_VISIBILITY, {'Alpha': (pcolor, 4)}, 1, 'Particle visibility')
    m.pin('OpacityMask', Node('Multiply', {'A': view, 'B': particle}, name='MaterialExpressionMultiply_27'))
    # the visibility (the game's translucent pass): the visibility layer, the coverage, the distance fade, the soft fade
    near = scalar('MaterialExpressionScalarParameter_30', 'L:NearDistance(Float1)', 'System')
    vis = Node('Multiply', {'A': Node('Multiply', {'A': switch('MaterialExpressionStaticSwitchParameter_0', '3:Visibility', mask('MaterialExpressionComponentMask_6', (visibility_t, 5), 'a'),
                                                                Node('Constant', name='MaterialExpressionConstant_0', R=1.0)),
                                                    'B': Node('Clamp', {'Input': scalar('MaterialExpressionScalarParameter_8', 'L:3:Visibility(Float1)', 'Dynamic', 1.0)})}),
                            'B': Node('Clamp', {'Input': scalar('MaterialExpressionScalarParameter_17', 'A:0:Coverage(Float1)', 'System', 1.0)})})
    fade = call('MaterialExpressionMaterialFunctionCall_2', 'DistanceFade', NearDistance=near,
                FarDistance=scalar('MaterialExpressionScalarParameter_32', 'L:FarDistance(Float1)', 'System'))
    soft = switch('MaterialExpressionStaticSwitchParameter_21', 'C:Soft',
                  call('MaterialExpressionMaterialFunctionCall_0', 'HermiteLimited',
                       S=call('MaterialExpressionMaterialFunctionCall_10', 'ExtraSceneDepthFade', UnitDistance=Node('Constant', name='MaterialExpressionConstant_14', R=50.0)),
                       R=Node('Constant', name='MaterialExpressionConstant_15', R=1.0)),
                  Node('Constant', name='MaterialExpressionConstant_7', R=1.0))
    m.pin('PixelContextVector1', Node('Multiply', {'A': soft, 'B': Node('Multiply', {'A': fade, 'B': vis})}))
    # lit: the diffuse (its layer, its colour)
    diffuse = Node('Multiply', {'A': switch('MaterialExpressionStaticSwitchParameter_17', '9:Diffuse', mask('MaterialExpressionComponentMask_1', diffuse_t, 'rgb'),
                                            const3('MaterialExpressionConstant3Vector_5', (1, 1, 1))),
                                'B': mask(None, Node('Clamp', {'Input': vec4(vparam('MaterialExpressionVectorParameter_16', 'L:A:Diffuse(RGBA)', 'Dynamic'))}), 'rgb')},
                   name='MaterialExpressionMultiply_1')
    m.pin('BaseColor', switch('MaterialExpressionStaticSwitchParameter_23', '4:Lit', diffuse, const3('MaterialExpressionConstant3Vector_7', (0, 0, 0))))
    m.pin('AmbientOcclusion', switch('MaterialExpressionStaticSwitchParameter_14', 'O:Occlusion', mask('MaterialExpressionComponentMask_14', (occlusion_t, 5), 'a'),
                                     Node('Constant', name='MaterialExpressionConstant_4', R=1.0)))
    # the normal layer's normal turned back by the layer's rotation (not with FlipBook)
    flip0, rot0 = params(0, 0, 1, 0, 4, 15, 24)[:2]
    turned = custom("""
float Q = floor(frac(Angle + 0.125) * 4.0);
float C = abs(Q - 2.0) - 1.0;
float S = 1.0 - abs(Q - 1.0);
float2 R = float2(dot(float2(C, -S), Normal.xy), dot(float2(S, C), Normal.xy));
return float3(FlipBook >= 0.5 ? Normal.xy : R, Normal.z);""",
                    {'Normal': call('MaterialExpressionMaterialFunctionCall_11', 'NormalizeNormalRG', NormalRG=mask('MaterialExpressionComponentMask_0', normal_t, 'rg')),
                     'Angle': rot0, 'FlipBook': flip0}, 3, 'Layer normal', name='MaterialExpressionCustom_1')
    m.pin('Normal', switch('MaterialExpressionStaticSwitchParameter_18', 'A:Normal', turned, const3('MaterialExpressionConstant3Vector_6', (0, 0, 1))))
    # the vertex: the animation (the piece's column: UV1's u) and the view modifier
    coord = mask('MaterialExpressionComponentMask_36', Node('TextureCoordinate', CoordinateIndex=1), 'r')
    key = scalar('MaterialExpressionScalarParameter_29', 'V:0:AnimateKeyIndex(Float1)', 'Dynamic')
    rc = call('MaterialExpressionMaterialFunctionCall_4', 'AnimateRigid', Coordinate=coord, Index=key,
              Translation=texobj('MaterialExpressionTextureObjectParameter_2', 'V:R:0:Translation'), Rotation=texobj('MaterialExpressionTextureObjectParameter_3', 'V:R:1:Rotation'),
              Position=texobj('MaterialExpressionTextureObjectParameter_4', 'V:R:2:Position'))
    sc = call('MaterialExpressionMaterialFunctionCall_20', 'AnimateSoft', Coordinate=coord, Index=key,
              Translation=texobj('MaterialExpressionTextureObjectParameter_5', 'V:S:0:Translation'), Rotation=texobj('MaterialExpressionTextureObjectParameter_6', 'V:S:1:Rotation'))
    fc = call('MaterialExpressionMaterialFunctionCall_24', 'AnimateFluid', Coordinate=coord, Index=key,
              Position=texobj('MaterialExpressionTextureObjectParameter_9', 'V:F:0:Position'), Normal=texobj('MaterialExpressionTextureObjectParameter_10', 'V:F:1:Normal'))
    rig = [switch(n, 'K:RigidBody', (rc, i), c4(d, v), 'STATIC_SWITCH_RIGID_BODY')
           for i, (n, d, v) in enumerate((('MaterialExpressionStaticSwitchParameter_11', 'MaterialExpressionConstant4Vector_3', (0, 0, 0, 1)),
                                          ('MaterialExpressionStaticSwitchParameter_36', 'MaterialExpressionConstant4Vector_4', (0, 0, 0, 1)),
                                          ('MaterialExpressionStaticSwitchParameter_42', 'MaterialExpressionConstant4Vector_5', (0, 0, 0, 0))))]
    sof = [switch(n, 'L:SoftBody', (sc, i), rig[i], 'STATIC_SWITCH_SOFT_BODY') for i, n in enumerate(('MaterialExpressionStaticSwitchParameter_34', 'MaterialExpressionStaticSwitchParameter_40'))]
    flu = [switch(n, 'M:FluidBody', (fc, i), sof[i], 'STATIC_SWITCH_FLUID_BODY') for i, n in enumerate(('MaterialExpressionStaticSwitchParameter_35', 'MaterialExpressionStaticSwitchParameter_41'))]
    for prefix in ('', 'Previous'):
        m.pin(prefix + 'VertexTransformVector0', flu[0])
        m.pin(prefix + 'VertexTransformVector1', flu[1])
        m.pin(prefix + 'VertexTransformVector2', rig[2])
    m.pin('VertexContextVector0', particle_view_modifier(vparam('MaterialExpressionVectorParameter_3', 'A:1:EmitterPosition(Float3)', 'System'),
                                                         vparam('MaterialExpressionVectorParameter_14', 'A:3:ViewDependentParticle(Float4)', 'System'), near))
    m.props.update(shading_model='MSM_Unlit', blend='AlphaComposite', fog='pixel', particle_visibility=True, tangent_space_normal=True)
    return m


def particle_radius():
    """the pixel's distance from the emitter, in units of the radius (by the object's scale in z), limited to 1"""
    radius = Node('Multiply', {'A': Node('Max', {'A': scalar('MaterialExpressionScalarParameter_18', 'L:4:Radius(Float1)', 'Dynamic', 100.0)}, ConstB=0.0),
                               'B': mask(None, (vparam('MaterialExpressionVectorParameter_7', 'A:2:ObjectScale(Float3)', 'System'), 0), 'b')})
    return custom('return min(length(Position - Center) / max(Radius, 0.00001), 1.0);',
                  {'Position': Node('WorldPosition'), 'Center': (vparam('MaterialExpressionVectorParameter_3', 'A:1:EmitterPosition(Float3)', 'System'), 0),
                   'Radius': radius}, 1, 'Radius', name='MaterialExpressionCustom_8')



def mf_ExponentialAttenuation():
    f = Function('ExponentialAttenuation', [('RGB', 'Vector3', (1.0, 1.0, 1.0)), ('Visibility', 'Scalar', (1.0,))],
                 'RGB dimmed by Visibility to its 8th power (three squarings).', MF_ROOT + '/ExponentialAttenuation')
    c = custom("""
float V2 = Visibility * Visibility;
float V4 = V2 * V2;
return RGB * (V4 * V4);""", {'RGB': f.inp('RGB'), 'Visibility': f.inp('Visibility')}, 3, 'ExponentialAttenuation')
    return f.output('RGB', c)


def body_animation(m, coord, rigid=('MaterialExpressionMaterialFunctionCall_0', 'MaterialExpressionStaticSwitchParameter_0',
                                    'MaterialExpressionStaticSwitchParameter_51', 'MaterialExpressionStaticSwitchParameter_54'),
                   soft=('MaterialExpressionMaterialFunctionCall_1', 'MaterialExpressionStaticSwitchParameter_34', 'MaterialExpressionStaticSwitchParameter_52'),
                   fluid=('MaterialExpressionMaterialFunctionCall_2', 'MaterialExpressionStaticSwitchParameter_50', 'MaterialExpressionStaticSwitchParameter_53'),
                   defaults=('MaterialExpressionConstant4Vector_7', 'MaterialExpressionConstant4Vector_8', 'MaterialExpressionConstant4Vector_9')):
    """the forward-lit masters' vertex animation (Glass, Jewel, Thin, Water): the rigid, soft and fluid bodies at the key
    index, the previous transform the same as the current one"""
    key = scalar('MaterialExpressionScalarParameter_29', 'AnimateKeyIndex', 'Dynamic')
    rc = call(rigid[0], 'AnimateRigid', Coordinate=coord, Index=key, Translation=texobj('MaterialExpressionTextureObjectParameter_2', 'V:R:0:Translation'),
              Rotation=texobj('MaterialExpressionTextureObjectParameter_3', 'V:R:1:Rotation'), Position=texobj('MaterialExpressionTextureObjectParameter_4', 'V:R:2:Position'))
    sc = call(soft[0], 'AnimateSoft', Coordinate=coord, Index=key, Translation=texobj('MaterialExpressionTextureObjectParameter_5', 'V:S:0:Translation'),
              Rotation=texobj('MaterialExpressionTextureObjectParameter_6', 'V:S:1:Rotation'))
    fc = call(fluid[0], 'AnimateFluid', Coordinate=coord, Index=key, Position=texobj('MaterialExpressionTextureObjectParameter_9', 'V:F:0:Position'),
              Normal=texobj('MaterialExpressionTextureObjectParameter_10', 'V:F:1:Normal'))
    identity = [(0, 0, 0, 1), (0, 0, 0, 1), (0, 0, 0, 0)]
    rig = [switch(rigid[1 + i], 'RigidBody', (rc, i), c4(defaults[i], identity[i]), 'STATIC_SWITCH_RIGID_BODY') for i in range(3)]
    sof = [switch(soft[1 + i], 'SoftBody', (sc, i), rig[i], 'STATIC_SWITCH_SOFT_BODY') for i in range(2)]
    flu = [switch(fluid[1 + i], 'FluidBody', (fc, i), sof[i], 'STATIC_SWITCH_FLUID_BODY') for i in range(2)]
    for prefix in ('', 'Previous'):
        m.pin(prefix + 'VertexTransformVector0', flu[0])
        m.pin(prefix + 'VertexTransformVector1', flu[1])
        m.pin(prefix + 'VertexTransformVector2', rig[2])


GLASS_DETAIL_NAMES = (('MaterialExpressionComponentMask_3', 'MaterialExpressionMaterialFunctionCall_14'),
                      [('MaterialExpressionComponentMask_6', 'MaterialExpressionMaterialFunctionCall_15', 'MaterialExpressionOneMinus_3',
                        'MaterialExpressionMaterialFunctionCall_16', 'MaterialExpressionMaterialFunctionCall_17', 'MaterialExpressionStaticSwitchParameter_11'),
                       ('MaterialExpressionComponentMask_12', 'MaterialExpressionMaterialFunctionCall_18', 'MaterialExpressionOneMinus_4',
                        'MaterialExpressionMaterialFunctionCall_19', 'MaterialExpressionMaterialFunctionCall_20', 'MaterialExpressionStaticSwitchParameter_12'),
                       ('MaterialExpressionComponentMask_26', 'MaterialExpressionMaterialFunctionCall_21', 'MaterialExpressionOneMinus_5',
                        'MaterialExpressionMaterialFunctionCall_22', 'MaterialExpressionMaterialFunctionCall_23', 'MaterialExpressionStaticSwitchParameter_6')])


def glass_emissive(uv0, uv2, mrv):
    """EndMaterial_Glass's emissive: the base layer (its texture, its LDR one, or white) and the extra layer on UV2 that the
    coordinate offsets move, tinted by the stationary and the dynamic colours, dimmed by the variant channel's 8th power
    (ExponentialAttenuation), and - unless the glass radiates - nothing while the game bakes"""
    baking = call('MaterialExpressionMaterialFunctionCall_24', 'DetectBaking')
    soff = switch('MaterialExpressionStaticSwitchParameter_18', 'StationaryEmissive',
                  Node('AppendVector', {'A': scalar('MaterialExpressionScalarParameter_9', 'StationaryCoordinateOffset_X', 'Stationary'),
                                        'B': scalar('MaterialExpressionScalarParameter_10', 'StationaryCoordinateOffset_Y', 'Stationary')},
                       name='MaterialExpressionAppendVector_1'),
                  Node('Constant2Vector', name='MaterialExpressionConstant2Vector_0', R=0.0, G=0.0))
    doff = switch('MaterialExpressionStaticSwitchParameter_16', 'DynamicEmissive',
                  Node('AppendVector', {'A': scalar('MaterialExpressionScalarParameter_0', 'DynamicCoordinateOffset_X', 'Dynamic'),
                                        'B': scalar('MaterialExpressionScalarParameter_4', 'DynamicCoordinateOffset_Y', 'Dynamic')},
                       name='MaterialExpressionAppendVector_0'),
                  Node('Constant2Vector', name='MaterialExpressionConstant2Vector_1', R=0.0, G=0.0))
    extra_uv = Node('Add', {'A': uv2, 'B': Node('Add', {'A': soff, 'B': doff})}, name='MaterialExpressionAdd_1')
    base = switch('MaterialExpressionStaticSwitchParameter_23', 'IdentityEmissive', const3('MaterialExpressionConstant3Vector_4', (1, 1, 1)),
                  switch('MaterialExpressionStaticSwitchParameter_19', 'LDREmissive',
                         mask('MaterialExpressionComponentMask_37', tex('MaterialExpressionTextureSampleParameter2D_24', '0:6:LDREmissive', uv0, 'Color', '000000FF_sRGB'), 'rgb'),
                         mask('MaterialExpressionComponentMask_27', tex('MaterialExpressionTextureSampleParameter2D_20', '0:4:Emissive', uv0, 'LinearColor', '000000FF_HDR'), 'rgb')))
    extra = switch('MaterialExpressionStaticSwitchParameter_21', 'ExtraEmissive',
                   switch('MaterialExpressionStaticSwitchParameter_31', 'IdentityEmissive', const3('MaterialExpressionConstant3Vector_9', (1, 1, 1)),
                          switch('MaterialExpressionStaticSwitchParameter_20', 'LDREmissive',
                                 mask('MaterialExpressionComponentMask_38', tex('MaterialExpressionTextureSampleParameter2D_25', '2:5:LDREmissive', extra_uv, 'Color', '000000FF_sRGB'), 'rgb'),
                                 mask('MaterialExpressionComponentMask_36', tex('MaterialExpressionTextureSampleParameter2D_23', '2:4:Emissive', extra_uv, 'LinearColor', '000000FF_HDR'), 'rgb'))),
                   const3('MaterialExpressionConstant3Vector_14', (0, 0, 0)))
    stationary = switch('MaterialExpressionStaticSwitchParameter_17', 'StationaryEmissive',
                        Node('Multiply', {'A': call('MaterialExpressionMaterialFunctionCall_27', 'CompositeColor',
                                                    R=scalar('MaterialExpressionScalarParameter_6', 'StationaryEmissiveColor_X', 'Stationary', 1.0),
                                                    G=scalar('MaterialExpressionScalarParameter_7', 'StationaryEmissiveColor_Y', 'Stationary', 1.0),
                                                    B=scalar('MaterialExpressionScalarParameter_8', 'StationaryEmissiveColor_Z', 'Stationary', 1.0)),
                                          'B': scalar('MaterialExpressionScalarParameter_5', 'StationaryEmissiveIntensity', 'Stationary', 1.0)},
                             name='MaterialExpressionMultiply_5'),
                        const3('MaterialExpressionConstant3Vector_3', (1, 1, 1)))
    dynamic = switch('MaterialExpressionStaticSwitchParameter_10', 'DynamicEmissive',
                     Node('Multiply', {'A': call('MaterialExpressionMaterialFunctionCall_25', 'CompositeColor',
                                                 R=scalar('MaterialExpressionScalarParameter_1', 'DynamicEmissiveColor_X', 'Dynamic', 1.0),
                                                 G=scalar('MaterialExpressionScalarParameter_2', 'DynamicEmissiveColor_Y', 'Dynamic', 1.0),
                                                 B=scalar('MaterialExpressionScalarParameter_3', 'DynamicEmissiveColor_Z', 'Dynamic', 1.0)),
                                       'B': scalar('MaterialExpressionScalarParameter_17', 'DynamicEmissiveIntensity', 'Dynamic', 1.0)},
                          name='MaterialExpressionMultiply_6'),
                     const3('MaterialExpressionConstant3Vector_2', (1, 1, 1)))
    tinted = Node('Multiply', {'A': Node('Multiply', {'A': Node('Add', {'A': base, 'B': extra}), 'B': stationary}), 'B': dynamic},
                  name='MaterialExpressionMultiply_4')
    dimmed = call('MaterialExpressionMaterialFunctionCall_26', 'ExponentialAttenuation', RGB=tinted,
                  Visibility=mask('MaterialExpressionComponentMask_28', (mrv, 3), 'r'))
    radiation = custom('return Baking != 0.0 ? Radiation : 1.0;',
                       {'Radiation': switch('MaterialExpressionStaticSwitchParameter_14', 'Radiation', Node('Constant', name='MaterialExpressionConstant_4', R=1.0),
                                            Node('Constant', name='MaterialExpressionConstant_6', R=0.0)),
                        'Baking': baking}, 1, 'Radiation')
    return switch('MaterialExpressionStaticSwitchParameter_7', 'Emissive', Node('Multiply', {'A': dimmed, 'B': radiation}, name='MaterialExpressionMultiply_7'),
                  const3('MaterialExpressionConstant3Vector_1', (0, 0, 0)))


def EndMaterial_Glass():
    """the game's glass (forward lit, alpha composite; STATIC_SWITCH_GLASS): the colour (or a premultiplied colour, its
    alpha the transparency), metallic and roughness, the opacity map, up to three detail normals, the lead's stronger
    reflectance, the emissive; the pass premultiplies the diffuse by the opacity and passes the emissive through"""
    _SHARED.clear()
    m = Material('EndMaterial_Glass', M_ROOT + '/EndMaterial_Glass')
    uv0 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_1', CoordinateIndex=0)
    uv1 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_3', CoordinateIndex=1)
    uv2 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_4', CoordinateIndex=2)
    color = tex('MaterialExpressionTextureSampleParameter2D_6', '0:0:Color', uv0, 'Color', '767676FF_sRGB')
    pmc = tex('MaterialExpressionTextureSampleParameter2D_14', '0:6:PreMultipliedColor', uv0, 'Color', '767676FF_sRGB')
    opac = tex('MaterialExpressionTextureSampleParameter2D_13', '0:6:Opacity', uv0, 'Alpha', '000000FF_BC4')
    normal = tex('MaterialExpressionTextureSampleParameter2D_7', '0:3:Normal', uv0, 'LinearColor', '8080FF00')
    mrv = tex('MaterialExpressionTextureSampleParameter2D_4', '0:2:Metallic/Roughness/Variant', uv0, 'LinearColor', '008000FF')
    occl = tex('MaterialExpressionTextureSampleParameter2D_5', '1:0:Occlusion', uv1, 'Alpha', 'FF000000_BC4')
    dopac = tex('MaterialExpressionTextureSampleParameter2D_16', '0:5:DetailOpacity', uv0, 'LinearColor', '000000FF')
    dnorm = [tex('MaterialExpressionTextureSampleParameter2D_2', '2:0:DetailNormal:0', uv2, 'LinearColor', '8080FF00'),
             tex('MaterialExpressionTextureSampleParameter2D_18', '2:1:DetailNormal:1', uv2, 'LinearColor', '8080FF00'),
             tex('MaterialExpressionTextureSampleParameter2D_19', '2:2:DetailNormal:2', uv2, 'LinearColor', '8080FF00')]
    cover = tex('MaterialExpressionTextureSampleParameter2D_21', '0:1:Coverage', uv0, 'Alpha', 'FF000000_BC4')
    dcover = tex('MaterialExpressionTextureSampleParameter2D_22', '2:3:DetailCoverage', uv2, 'Alpha', 'FF000000_BC4')
    docc = tex('MaterialExpressionTextureSampleParameter2D_27', '2:4:DetailOcclusion', uv2, 'Alpha', 'FF000000_BC4')

    m.pin('BaseColor', switch('MaterialExpressionStaticSwitchParameter_3', 'PreMultipliedColor', mask('MaterialExpressionComponentMask_1', pmc, 'rgb'),
                              mask('MaterialExpressionComponentMask_2', color, 'rgb')))
    m.pin('Metallic', mask('MaterialExpressionComponentMask_4', (mrv, 5), 'r'))
    m.pin('Roughness', mask('MaterialExpressionComponentMask_5', (mrv, 5), 'g'))
    lead = switch('MaterialExpressionStaticSwitchParameter_2', 'Lead', Node('Constant', name='MaterialExpressionConstant_1', R=0.08),
                  Node('Constant', name='MaterialExpressionConstant_3', R=0.04))
    m.pin('Specular', call('MaterialExpressionMaterialFunctionCall_5', 'EncodeReflectance', Reflectance=lead))
    m.pin('Normal', detail_normal(normal, dopac, dnorm, GLASS_DETAIL_NAMES))
    # the glass type (its define picks the pass's glass composition): the opacity, the premultiplied colour's alpha
    # the transparency; the clear coat the same
    opacity = switch('MaterialExpressionStaticSwitchParameter_1', 'Glass',
                     switch('MaterialExpressionStaticSwitchParameter_4', 'PreMultipliedColor', Node('OneMinus', {'Input': (pmc, 4)}, name='MaterialExpressionOneMinus_0'),
                            mask('MaterialExpressionComponentMask_22', (opac, 4), 'r')),
                     Node('Constant', name='MaterialExpressionConstant_2', R=1.0), 'STATIC_SWITCH_GLASS', default=True)
    m.pin('Opacity', opacity)
    m.pin('ClearCoat', opacity)
    m.pin('AmbientOcclusion', Node('Min', {'A': mask(None, (occl, 4), 'r'),
                                           'B': switch('MaterialExpressionStaticSwitchParameter_24', 'DetailOcclusion',
                                                       mask('MaterialExpressionComponentMask_39', (docc, 4), 'r'),
                                                       Node('Constant', name='MaterialExpressionConstant_12', R=1.0))}, name='MaterialExpressionMin_0'))
    dcov = switch('MaterialExpressionStaticSwitchParameter_15', 'DetailCoverage', mask('MaterialExpressionComponentMask_33', (dcover, 4), 'r'),
                  Node('Constant', name='MaterialExpressionConstant_7', R=1.0))
    m.pin('OpacityMask', switch('MaterialExpressionStaticSwitchParameter_9', 'Coverage',
                                Node('Multiply', {'A': (cover, 4), 'B': dcov}, name='MaterialExpressionMultiply_0'),
                                Node('Constant', name='MaterialExpressionConstant_0', R=1.0)))
    m.pin('EmissiveColor', glass_emissive(uv0, uv2, mrv))
    # (the glass pass does not read it: a neutral visibility)
    m.pin('PixelContextVector1', c4(None, (1, 1, 1, 1)))
    body_animation(m, mask('MaterialExpressionComponentMask_0', Node('TextureCoordinate', CoordinateIndex=3), 'r'))
    m.props.update(shading_model='MSM_DefaultLit', blend='AlphaComposite', fog='pixel', tangent_space_normal=True)
    return m



def mf_SphericalInterpolateVector():
    f = Function('SphericalInterpolateVector', [('Left', 'Vector3', (0, 0, 1)), ('Right', 'Vector3', (0, 0, 1)), ('Ratio', 'Scalar', (0.0,))],
                 'Left turned toward Right by Ratio (spherical interpolation along the shorter arc), normalized.',
                 MF_ROOT + '/SphericalInterpolateVector')
    c = custom(SLERP_PREFIX.replace('From', 'Left').replace('To', 'Right') + """
float Theta = acos(abs(D));""" + SLERP_SUFFIX.replace('From', 'Left').replace('To', 'Right').replace('Alpha', 'Ratio'),
               {'Left': f.inp('Left'), 'Right': f.inp('Right'), 'Ratio': f.inp('Ratio')}, 3, 'SphericalInterpolateVector')
    return f.output('Result', c)


def EndMaterial_Tear():
    """the game's tear film (forward lit, alpha composite; STATIC_SWITCH_TEAR): no colour, a weak reflectance, the normal
    map (or its flip book: the frames a vertical strip of square ones, the key index's two frames' normals turned one
    into the other), the visibility map; the pass draws only the specular, by the visibility"""
    _SHARED.clear()
    m = Material('EndMaterial_Tear', M_ROOT + '/EndMaterial_Tear')
    uv0 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_1', CoordinateIndex=0)
    uv1 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_3', CoordinateIndex=1)
    normal_t = Node('TextureObjectParameter', name='MaterialExpressionTextureObjectParameter_0', ParameterName='0:3:Normal', Texture='8080FF00',
                    SamplerType='LinearColor', Group='Texture')
    vis_t = Node('TextureObjectParameter', name='MaterialExpressionTextureObjectParameter_2', ParameterName='0:7:Visibility', Texture='FF000000_BC4',
                 SamplerType='Alpha', Group='Texture')
    key = switch('MaterialExpressionStaticSwitchParameter_19', 'Reference', Node('Multiply', {'A': scalar('MaterialExpressionScalarParameter_29', 'AnimateKeyIndex', 'Dynamic')},
                                                                                     name='MaterialExpressionMultiply_3', ConstB=1.0),
                 scalar('MaterialExpressionScalarParameter_29', 'AnimateKeyIndex', 'Dynamic'))
    # the flip book's frames: the texture's height over its width of them, the key index's two
    size = Node('TextureProperty', {'TextureObject': normal_t}, Property='TMTP_TextureSize')
    frames = Node('Divide', {'A': mask(None, size, 'g'), 'B': mask(None, size, 'r')})
    step = Node('Divide', {'A': mask(None, size, 'r'), 'B': mask(None, size, 'g')})
    k = Node('Fmod', {'A': key, 'B': frames})

    def frame(rounding, name):
        return Node('AppendVector', {'A': mask(None, uv0, 'r'),
                                     'B': Node('Multiply', {'A': Node('Add', {'A': Node(rounding, {'Input': k}), 'B': mask(None, uv0, 'g')}), 'B': step})},
                    name=name)
    uv_a = switch('MaterialExpressionStaticSwitchParameter_4', 'FlipBook', frame('Floor', 'MaterialExpressionAppendVector_5'), uv0)
    uv_b = switch('MaterialExpressionStaticSwitchParameter_0', 'FlipBook', frame('Ceil', 'MaterialExpressionAppendVector_6'), uv0)
    ratio = Node('Frac', {'Input': k}, name='MaterialExpressionFrac_0')
    n_a = call('MaterialExpressionMaterialFunctionCall_14', 'NormalizeNormalRG',
               NormalRG=mask('MaterialExpressionComponentMask_6', Node('TextureSample', {'TextureObject': normal_t, 'Coordinates': uv_a}, SamplerType='LinearColor'), 'rg'))
    n_b = call('MaterialExpressionMaterialFunctionCall_1', 'NormalizeNormalRG',
               NormalRG=mask('MaterialExpressionComponentMask_13', Node('TextureSample', {'TextureObject': normal_t, 'Coordinates': uv_b}, SamplerType='LinearColor'), 'rg'))
    m.pin('Normal', switch('MaterialExpressionStaticSwitchParameter_3', 'FlipBook',
                           call('MaterialExpressionMaterialFunctionCall_2', 'SphericalInterpolateVector', Left=n_a, Right=n_b, Ratio=ratio), n_a))
    vis_a = mask(None, (Node('TextureSample', {'TextureObject': vis_t, 'Coordinates': uv_a}, SamplerType='Alpha'), 4), 'r')
    vis_b = mask(None, (Node('TextureSample', {'TextureObject': vis_t, 'Coordinates': uv_b}, SamplerType='Alpha'), 4), 'r')
    vis = switch('MaterialExpressionStaticSwitchParameter_2', 'FlipBook',
                 Node('LinearInterpolate', {'A': vis_a, 'B': vis_b, 'Alpha': ratio}, name='MaterialExpressionLinearInterpolate_1'),
                 mask('MaterialExpressionComponentMask_9', (Node('TextureSample', {'TextureObject': vis_t, 'Coordinates': uv0}, SamplerType='Alpha'), 4), 'r'))
    m.pin('PixelContextVector1', vis)
    m.pin('BaseColor', const3('MaterialExpressionConstant3Vector_6', (0, 0, 0)))
    m.pin('Metallic', Node('Constant', name='MaterialExpressionConstant_5', R=0.0))
    m.pin('Roughness', Node('Constant', name='MaterialExpressionConstant_8', R=0.0))
    m.pin('Specular', call('MaterialExpressionMaterialFunctionCall_5', 'EncodeReflectance', Reflectance=Node('Constant', name='MaterialExpressionConstant_3', R=0.0325)))
    # the tear type (its define picks the pass's tear composition): the film's opacity, the clear coat the same
    tear = switch('MaterialExpressionStaticSwitchParameter_1', 'Tear', Node('Constant', name='MaterialExpressionConstant_1', R=0.047608017921447754),
                  Node('Constant', name='MaterialExpressionConstant_2', R=1.0), 'STATIC_SWITCH_TEAR', default=True)
    m.pin('Opacity', tear)
    m.pin('ClearCoat', tear)
    m.pin('OpacityMask', Node('Constant', name='MaterialExpressionConstant_0', R=1.0))
    m.pin('AmbientOcclusion', mask('MaterialExpressionComponentMask_11', (tex('MaterialExpressionTextureSampleParameter2D_5', '1:0:Occlusion', uv1, 'Alpha', 'FF000000_BC4'), 4), 'r'))
    m.props.update(shading_model='MSM_DefaultLit', blend='AlphaComposite', fog='pixel', tangent_space_normal=True)
    return m



def EndMaterial_Thin():
    """the game's thin surfaces (forward lit; STATIC_SWITCH_THIN: cloth, leaves, paper): Standard's colour, metallic and
    roughness, detail normals, occlusion, coverage and emissive, and the thickness (PixelContextVector0) by which the
    pass blends the light through the surface with the light on it"""
    _SHARED.clear()
    m = Material('EndMaterial_Thin', M_ROOT + '/EndMaterial_Thin')
    uv0 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_1', CoordinateIndex=0)
    uv1 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_3', CoordinateIndex=1)
    uv2 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_8', CoordinateIndex=2)
    color = tex('MaterialExpressionTextureSampleParameter2D_6', '0:0:Color', uv0, 'Color', '767676FF_sRGB')
    normal = tex('MaterialExpressionTextureSampleParameter2D_7', '0:3:Normal', uv0, 'LinearColor', '8080FF00')
    mrv = tex('MaterialExpressionTextureSampleParameter2D_4', '0:2:Metallic/Roughness/Variant', uv0, 'LinearColor', '008000FF')
    occl = tex('MaterialExpressionTextureSampleParameter2D_5', '1:0:Occlusion', uv1, 'Alpha', 'FF000000_BC4')
    cover = tex('MaterialExpressionTextureSampleParameter2D_2', '0:1:Coverage', uv0, 'Alpha', 'FF000000_BC4')
    dopac = tex('MaterialExpressionTextureSampleParameter2D_17', '0:5:DetailOpacity', uv0, 'LinearColor', '000000FF')
    dnorm = [tex('MaterialExpressionTextureSampleParameter2D_14', '2:0:DetailNormal:0', uv2, 'LinearColor', '8080FF00'),
             tex('MaterialExpressionTextureSampleParameter2D_0', '2:1:DetailNormal:1', uv2, 'LinearColor', '8080FF00'),
             tex('MaterialExpressionTextureSampleParameter2D_1', '2:2:DetailNormal:2', uv2, 'LinearColor', '8080FF00')]
    dcover = tex('MaterialExpressionTextureSampleParameter2D_3', '2:3:DetailCoverage', uv2, 'Alpha', 'FF000000_BC4')
    thick = tex('MaterialExpressionTextureSampleParameter2D_12', '0:7:Thickness', uv0, 'Alpha', 'FF000000_BC4')

    m.pin('Normal', detail_normal(normal, dopac, dnorm))
    m.pin('BaseColor', mask('MaterialExpressionComponentMask_2', color, 'rgb'))
    m.pin('Metallic', mask('MaterialExpressionComponentMask_4', (mrv, 5), 'r'))
    m.pin('Roughness', mask('MaterialExpressionComponentMask_5', (mrv, 5), 'g'))
    m.pin('Specular', call('MaterialExpressionMaterialFunctionCall_5', 'EncodeReflectance', Reflectance=Node('Constant', name='MaterialExpressionConstant_3', R=0.04)))
    # the thin type (its define picks the pass's thin composition; the opacity it does not read)
    m.pin('Opacity', switch('MaterialExpressionStaticSwitchParameter_16', 'Thin', Node('Constant', name='MaterialExpressionConstant_9', R=1.0),
                            Node('Constant', name='MaterialExpressionConstant_8', R=1.0), 'STATIC_SWITCH_THIN', default=True))
    m.pin('AmbientOcclusion', detail_occlusion(uv2, occl))
    m.pin('OpacityMask', detail_coverage(cover, dcover))
    m.pin('EmissiveColor', standard_emissive(uv0, uv2, mrv, flow=False, reference=False, conditional=False, extra_add='MaterialExpressionAdd_1',
                                             interior=False))
    m.pin('PixelContextVector0', mask(None, (thick, 4), 'r'))
    # (the thin pass does not read it: a neutral visibility)
    m.pin('PixelContextVector1', c4(None, (1, 1, 1, 1)))
    coord = mask('MaterialExpressionComponentMask_36', Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_11', CoordinateIndex=3), 'r')
    animation(m, coord,
              rigid={'current': {'call': 'MaterialExpressionMaterialFunctionCall_15', 'switches': ['MaterialExpressionStaticSwitchParameter_15', 'MaterialExpressionStaticSwitchParameter_51', 'MaterialExpressionStaticSwitchParameter_54'],
                                 'defaults': ['MaterialExpressionConstant4Vector_7', 'MaterialExpressionConstant4Vector_8', 'MaterialExpressionConstant4Vector_9']},
                     'previous': {'call': 'MaterialExpressionMaterialFunctionCall_32', 'switches': ['MaterialExpressionStaticSwitchParameter_84', 'MaterialExpressionStaticSwitchParameter_86', 'MaterialExpressionStaticSwitchParameter_83'],
                                  'defaults': ['MaterialExpressionConstant4Vector_22', 'MaterialExpressionConstant4Vector_23', 'MaterialExpressionConstant4Vector_24']}},
              soft={'current': {'call': 'MaterialExpressionMaterialFunctionCall_20', 'switches': ['MaterialExpressionStaticSwitchParameter_34', 'MaterialExpressionStaticSwitchParameter_52']},
                    'previous': {'call': 'MaterialExpressionMaterialFunctionCall_33', 'switches': ['MaterialExpressionStaticSwitchParameter_85', 'MaterialExpressionStaticSwitchParameter_87']}},
              fluid={'call': 'MaterialExpressionMaterialFunctionCall_24', 'current': ['MaterialExpressionStaticSwitchParameter_50', 'MaterialExpressionStaticSwitchParameter_53'],
                     'previous': ['MaterialExpressionStaticSwitchParameter_81', 'MaterialExpressionStaticSwitchParameter_82']},
              prev_key_name='MaterialExpressionScalarParameter_18')
    m.props.update(shading_model='MSM_DefaultLit', blend='AlphaComposite', fog='vertex', tangent_space_normal=True)
    return m


def EndMaterial_Jewel():
    """the game's jewels (forward lit; STATIC_SWITCH_JEWEL): a colour, roughness, normal and occlusion, and the stone's
    volume (PixelContextVector0: its extinction, its transparency distance and its thickness, from single-value textures)
    through which the pass refracts and absorbs the scene behind it"""
    _SHARED.clear()
    m = Material('EndMaterial_Jewel', M_ROOT + '/EndMaterial_Jewel')
    uv0 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_1', CoordinateIndex=0)
    uv1 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_2', CoordinateIndex=1)
    centre = Node('Constant2Vector', name='MaterialExpressionConstant2Vector_1', R=0.5, G=0.5)
    clamp = 'ESamplerSourceMode::SSM_Clamp_WorldGroupSettings'
    color = tex('MaterialExpressionTextureSampleParameter2D_6', 'C:0:Color', centre, 'Color', 'FFFFFFFF_sRGB', source=clamp)
    thick = tex('MaterialExpressionTextureSampleParameter2D_8', 'C:3:Thickness', centre, 'Alpha', 'FF000000_BC4', source=clamp)
    transp = tex('MaterialExpressionTextureSampleParameter2D_9', 'C:2:Transparency', centre, 'Alpha', 'FF000000_BC4', source=clamp)
    extinct = tex('MaterialExpressionTextureSampleParameter2D_2', 'C:1:Extinct', centre, 'Alpha', '000000FF_BC4', source=clamp)
    normal = tex('MaterialExpressionTextureSampleParameter2D_12', '0:3:Normal', uv0, 'LinearColor', '8080FF00')
    mrv = tex('MaterialExpressionTextureSampleParameter2D_5', '0:2:Metallic/Roughness/Variant', uv0, 'LinearColor', '008000FF')
    occl = tex('MaterialExpressionTextureSampleParameter2D_13', '1:0:Occlusion', uv1, 'Alpha', 'FF000000_BC4')
    cover = tex('MaterialExpressionTextureSampleParameter2D_11', '0:1:Coverage', uv0, 'Alpha', 'FF000000_BC4')

    m.pin('BaseColor', mask('MaterialExpressionComponentMask_2', color, 'rgb'))
    m.pin('Metallic', Node('Constant', name='MaterialExpressionConstant_9', R=0.0))
    m.pin('Specular', call('MaterialExpressionMaterialFunctionCall_5', 'EncodeReflectance', Reflectance=Node('Constant', name='MaterialExpressionConstant_3', R=0.1)))
    m.pin('Roughness', mask('MaterialExpressionComponentMask_14', (mrv, 5), 'g'))
    m.pin('Normal', call('MaterialExpressionMaterialFunctionCall_6', 'NormalizeNormalRG', NormalRG=mask('MaterialExpressionComponentMask_17', normal, 'rg')))
    m.pin('AmbientOcclusion', mask('MaterialExpressionComponentMask_18', (occl, 4), 'r'))
    # the jewel type (its define picks the pass's jewel composition; the opacity it does not read)
    m.pin('Opacity', switch('MaterialExpressionStaticSwitchParameter_1', 'Jewel', Node('Constant', name='MaterialExpressionConstant_4', R=1.0),
                            Node('Constant', name='MaterialExpressionConstant_2', R=1.0), 'STATIC_SWITCH_JEWEL', default=True))
    m.pin('OpacityMask', switch('MaterialExpressionStaticSwitchParameter_9', 'Coverage', Node('Multiply', {'A': (cover, 4)}, name='MaterialExpressionMultiply_3', ConstB=1.0),
                                Node('Constant', name='MaterialExpressionConstant_10', R=1.0)))
    # the stone's volume: its extinction, its transparency distance and its thickness (centimetres)
    m.pin('PixelContextVector0', Node('AppendVector', {'A': Node('AppendVector', {'A': Node('AppendVector', {
        'A': mask(None, (extinct, 4), 'r'), 'B': Node('Multiply', {'A': mask(None, (transp, 4), 'r')}, ConstB=100.0)}),
        'B': Node('Multiply', {'A': mask(None, (thick, 4), 'r')}, ConstB=100.0)}), 'B': Node('Constant', R=0.0)}))
    # (the jewel pass does not read it: a neutral visibility)
    m.pin('PixelContextVector1', c4(None, (1, 1, 1, 1)))
    body_animation(m, mask('MaterialExpressionComponentMask_0', Node('TextureCoordinate', CoordinateIndex=3), 'r'))
    m.props.update(shading_model='MSM_DefaultLit', blend='AlphaComposite', fog='vertex', tangent_space_normal=True)
    return m


# two flow-mapped layers half a period apart, blended by a smooth weight of the first one's phase (the second at its
# fullest where the first one jumps back)
FLOW_HERMITE = """
float T = abs(Phase * 2.0 - 1.0);
return {result}(lerp(A, B, T * T * (3.0 - 2.0 * T)));"""


def EndMaterial_Water():
    """the game's water (forward lit; STATIC_SWITCH_WATER): two layers of its normal map carried along the flow map
    (on UV1) half a period apart, flattened by the normal context map (its flatness, phase and reach), the colour and the
    volume (extinction, transparency distance, thickness: single-value maps), the foam ("Form") flowing the same way by
    its own context map; the pass refracts (index 1.333) and absorbs the scene behind it, fades to it in the shallows,
    and turns the surface to lit, fully rough foam by the foam's share. FluidBody: a flat normal (the fluid's vertices
    carry its shape) and no foam; WaterThickness: the depth limited (FluidBody: by the thickness map)"""
    _SHARED.clear()
    m = Material('EndMaterial_Water', M_ROOT + '/EndMaterial_Water')
    uv0 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_1', CoordinateIndex=0)
    uv1 = Node('TextureCoordinate', name='MaterialExpressionTextureCoordinate_3', CoordinateIndex=1)
    centre = Node('Constant2Vector', name='MaterialExpressionConstant2Vector_1', R=0.5, G=0.5)
    clamp = 'ESamplerSourceMode::SSM_Clamp_WorldGroupSettings'
    color = tex('MaterialExpressionTextureSampleParameter2D_6', 'C:0:Color', centre, 'Color', 'FFFFFFFF_sRGB', source=clamp)
    volume = tex('MaterialExpressionTextureSampleParameter2D_5', 'C:1:Extinct/Transparency/Thickness', centre, 'LinearColor', '00FFFFFF',
                 source=clamp)
    flow = tex('MaterialExpressionTextureSampleParameter2D_1', '1:0:Flow', uv1, 'LinearColor', '8080FF00')
    ncontext = tex('MaterialExpressionTextureSampleParameter2D_11', '1:1:NormalContext', uv1, 'LinearColor', 'FFFFFFFF')
    fcontext = tex('MaterialExpressionTextureSampleParameter2D_3', '1:2:FormContext', uv1, 'LinearColor', 'FFFFFFFF')
    time = scalar('MaterialExpressionScalarParameter_0', 'AnimateTime', 'Dynamic')
    # the flow: the direction the map points away from (none for a fluid body)
    direction = switch('MaterialExpressionStaticSwitchParameter_5', 'FluidBody',
                       Node('Constant2Vector', name='MaterialExpressionConstant2Vector_0', R=0.0, G=0.0),
                       custom('return normalize(-(Flow * 2.0 - 1.0));', {'Flow': mask(None, flow, 'rg')}, 2, 'Flow direction',
                              name='MaterialExpressionCustom_2'), 'STATIC_SWITCH_FLUID_BODY')

    def layers(context, adds):
        """a context map's two coordinates (its phase offset plus the time, and that half a period on; carried along the
        flow by its reach) and the first phase"""
        phase = Node('Add', {'A': mask(None, (context, 5), 'g'), 'B': time})
        p0 = Node('Frac', {'Input': phase})
        p1 = Node('Frac', {'Input': Node('Add', {'A': phase}, ConstB=0.5)})
        reach = mask(None, (context, 5), 'b')
        uv_a = Node('Add', {'A': uv0, 'B': Node('Multiply', {'A': Node('Multiply', {'A': p0, 'B': direction}), 'B': reach})}, name=adds[0])
        uv_b = Node('Add', {'A': uv0, 'B': Node('Multiply', {'A': Node('Multiply', {'A': p1, 'B': direction}), 'B': reach})}, name=adds[1])
        return uv_a, uv_b, p0

    # the normal: its two layers blended, flattened by the context's flatness (FluidBody: flat)
    na_uv, nb_uv, nphase = layers(ncontext, ('MaterialExpressionAdd_0', 'MaterialExpressionAdd_4'))
    n_a = call('MaterialExpressionMaterialFunctionCall_3', 'NormalizeNormalRG',
               NormalRG=mask('MaterialExpressionComponentMask_3', tex('MaterialExpressionTextureSampleParameter2D_7', '0:0:Normal', na_uv,
                                                                      'LinearColor', '8080FF00'), 'rg'))
    n_b = call('MaterialExpressionMaterialFunctionCall_8', 'NormalizeNormalRG',
               NormalRG=mask('MaterialExpressionComponentMask_7', tex('MaterialExpressionTextureSampleParameter2D_4', '0:0:Normal', nb_uv,
                                                                      'LinearColor', '8080FF00'), 'rg'))
    flowing = custom(FLOW_HERMITE.format(result='normalize'), {'A': n_a, 'B': n_b, 'Phase': nphase}, 3, 'Flow normal',
                     name='MaterialExpressionCustom_3')
    flat = call('MaterialExpressionMaterialFunctionCall_6', 'FlattenNormal', Normal=flowing,
                Value=Node('OneMinus', {'Input': mask(None, (ncontext, 5), 'r')}, name='MaterialExpressionOneMinus_0'))
    m.pin('Normal', switch('MaterialExpressionStaticSwitchParameter_7', 'FluidBody', const3('MaterialExpressionConstant3Vector_1', (0, 0, 1)),
                           flat, 'STATIC_SWITCH_FLUID_BODY'))
    m.pin('BaseColor', mask('MaterialExpressionComponentMask_2', color, 'rgb'))
    m.pin('Metallic', Node('Constant', name='MaterialExpressionConstant_9', R=0.0))
    m.pin('Specular', call('MaterialExpressionMaterialFunctionCall_5', 'EncodeReflectance', Reflectance=Node('Constant', name='MaterialExpressionConstant_3', R=0.02)))
    m.pin('Roughness', Node('Constant', name='MaterialExpressionConstant_5', R=0.0))
    m.pin('AmbientOcclusion', Node('Constant', name='MaterialExpressionConstant_14', R=1.0))
    m.pin('OpacityMask', Node('Constant', name='MaterialExpressionConstant_1', R=1.0))
    # the water type and its kinds (their defines pick the pass's water composition; the opacity it does not read)
    water = switch('MaterialExpressionStaticSwitchParameter_1', 'Water', Node('Constant', name='MaterialExpressionConstant_4', R=1.0),
                   Node('Constant', name='MaterialExpressionConstant_2', R=1.0), 'STATIC_SWITCH_WATER', default=True)
    edge = switch('MaterialExpressionStaticSwitchParameter_3', 'WaterEdge', water, water, 'STATIC_SWITCH_WATER_EDGE')
    m.pin('Opacity', switch('MaterialExpressionStaticSwitchParameter_9', 'WaterEnvironment', edge, edge, 'STATIC_SWITCH_WATER_ENVIRONMENT'))
    # the foam: its two layers blended, by the context's amount (FluidBody: none)
    fa_uv, fb_uv, fphase = layers(fcontext, ('MaterialExpressionAdd_1', 'MaterialExpressionAdd_3'))
    form_a = tex('MaterialExpressionTextureSampleParameter2D_0', '0:1:Form', fa_uv, 'Alpha', '000000FF_BC4')
    form_b = tex('MaterialExpressionTextureSampleParameter2D_10', '0:1:Form', fb_uv, 'Alpha', '000000FF_BC4')
    form = custom(FLOW_HERMITE.format(result=''), {'A': mask(None, (form_a, 4), 'r'), 'B': mask(None, (form_b, 4), 'r'), 'Phase': fphase}, 1,
                  'Flow foam')
    foam = switch('MaterialExpressionStaticSwitchParameter_6', 'FluidBody', Node('Constant', name='MaterialExpressionConstant_8', R=0.0),
                  Node('Multiply', {'A': mask(None, (fcontext, 5), 'r'), 'B': form}, name='MaterialExpressionMultiply_11'), 'STATIC_SWITCH_FLUID_BODY')
    # the depth limit (centimetres): the thickness map's for a fluid body, otherwise none to speak of
    unlimited = Node('Constant', name='MaterialExpressionConstant_11', R=100000.0)
    thick = switch('MaterialExpressionStaticSwitchParameter_2', 'WaterThickness',
                   switch('MaterialExpressionStaticSwitchParameter_8', 'FluidBody',
                          Node('Multiply', {'A': mask(None, (volume, 5), 'b')}, name='MaterialExpressionMultiply_1', ConstB=100.0), unlimited,
                          'STATIC_SWITCH_FLUID_BODY'),
                   unlimited, 'STATIC_SWITCH_WATER_THICKNESS')
    # the water's volume: its extinction, its transparency distance (centimetres), its depth limit; the foam's share
    m.pin('PixelContextVector0', Node('AppendVector', {'A': Node('AppendVector', {'A': Node('AppendVector', {
        'A': mask(None, (volume, 5), 'r'), 'B': Node('Multiply', {'A': mask(None, (volume, 5), 'g')}, ConstB=100.0)}),
        'B': thick}), 'B': foam}))
    # (the water pass does not read it: a neutral visibility)
    m.pin('PixelContextVector1', c4(None, (1, 1, 1, 1)))
    body_animation(m, mask('MaterialExpressionComponentMask_0', Node('TextureCoordinate', CoordinateIndex=3), 'r'))
    m.props.update(shading_model='MSM_DefaultLit', blend='AlphaComposite', fog='pixel', tangent_space_normal=True)
    return m


MASTERS = {'EndMaterial_Particle': EndMaterial_Particle, 'EndMaterial_Directional': EndMaterial_Directional, 'EndMaterial_InvisibleBody': EndMaterial_InvisibleBody, 'EndMaterial_Hologram': EndMaterial_Hologram, 'EndMaterial_Blood': EndMaterial_Blood, 'EndMaterial_Materia': EndMaterial_Materia, 'EndMaterial_Standard_Classify': EndMaterial_Standard_Classify, 'EndMaterial_Standard': EndMaterial_Standard, 'EndMaterial_Skin': EndMaterial_Skin, 'EndMaterial_Hair': EndMaterial_Hair,
           'EndMaterial_Eye': EndMaterial_Eye, 'EndMaterial_Sand': EndMaterial_Sand, 'EndMaterial_BlackBody': EndMaterial_BlackBody,
           'EndMaterial_Menu': EndMaterial_Menu, 'EndMaterial_Fabric': EndMaterial_Fabric, 'EndMaterial_Subsurface': EndMaterial_Subsurface,
           'EndMaterial_Glass': EndMaterial_Glass, 'EndMaterial_Tear': EndMaterial_Tear, 'EndMaterial_Thin': EndMaterial_Thin,
           'EndMaterial_Jewel': EndMaterial_Jewel, 'EndMaterial_Water': EndMaterial_Water}
