"""Building Rebirth (game schema) property trees for nio.Writer: small constructors and the Niagara type table."""
import struct
from rebirth_fx.uprops import V

# editor (UE 4.26) type -> Rebirth VFX1 type hash, underlying type (1 class, 2 struct, 3 enum).
# Hashes come from the game's own cooked data (variables of these types); see notes/FORMAT.md.
TYPES = {
    '/Script/Niagara.NiagaraFloat': (0x8f7f06aa, 2),
    '/Script/Niagara.NiagaraInt32': (0xe205d21c, 2),
    '/Script/Niagara.NiagaraBool': (0x413cb3b2, 2),
    '/Script/CoreUObject.Vector2D': (0x05115eac, 2),
    '/Script/CoreUObject.Vector': (0x8bb24135, 2),
    '/Script/CoreUObject.Vector4': (0x61a8c652, 2),
    '/Script/CoreUObject.LinearColor': (0xe2a7510c, 2),
    '/Script/CoreUObject.Quat': (0x46884021, 2),
    '/Script/CoreUObject.Matrix': (0xcdb4daba, 2),
    '/Script/Niagara.NiagaraID': (0xa6fa14b9, 2),
    '/Script/Niagara.NiagaraSpawnInfo': (0x33954561, 2),
    '/Script/Niagara.ENiagaraExecutionState': (0x95c8586d, 3),
    '/Script/Niagara.ENiagaraExecutionStateSource': (0x215080b4, 3),
    '/Script/Niagara.NiagaraDataInterfaceCurve': (0x80877f55, 1),
    '/Script/Niagara.NiagaraDataInterfaceColorCurve': (0xa634ab99, 1),
    '/Script/Niagara.NiagaraDataInterfaceVectorCurve': (0xa7c132d1, 1),
    '/Script/Niagara.NiagaraDataInterfaceVector2DCurve': (0xcb9b3865, 1),
    '/Script/Engine.Texture': (0xf6708ba8, 1),
}
# per type: (float byte offsets, int32 byte offsets) of its components (FNiagaraTypeLayoutInfo), size in bytes
LAYOUTS = {
    0x8f7f06aa: ([0], [], 4), 0xe205d21c: ([], [0], 4), 0x413cb3b2: ([], [0], 4), 0x95c8586d: ([], [0], 4),
    0x215080b4: ([], [0], 4), 0x05115eac: ([0, 4], [], 8), 0x8bb24135: ([0, 4, 8], [], 12),
    0x61a8c652: ([0, 4, 8, 12], [], 16), 0xe2a7510c: ([0, 4, 8, 12], [], 16), 0x46884021: ([0, 4, 8, 12], [], 16),
    0xcdb4daba: (list(range(0, 64, 4)), [], 64), 0xa6fa14b9: ([], [0, 4], 8), 0x33954561: ([4, 8], [0, 12], 16),
}


def prim(t, v):
    return V('prim', t, 0, 0, v)


def b(v): return prim('BoolProperty', bool(v))
def i32(v): return prim('IntProperty', int(v))
def u32(v): return prim('UInt32Property', int(v))
def f32(v): return prim('FloatProperty', float(v))
def u8(v): return prim('ByteProperty', int(v))


def name(s):
    return V('name', 'NameProperty', 0, 0, s)


def string(s):
    return V('str', 'StrProperty', 0, 0, s)


def obj(index):
    """an FPackageIndex: export k (1-based) > 0, import -(k+1) < 0, null 0"""
    return V('obj', 'ObjectProperty', 0, 0, int(index))


def enum(value_name):
    return V('enum', None, 0, 0, value_name)


def struct_(sname, fields):
    """fields: {property name: V}; None values are left out"""
    return V('struct', sname, 0, 0, {k: x for k, x in fields.items() if x is not None})


def native(sname, value):
    return V('native', sname, 0, 0, value)


def binary(sname, values):
    return V('native', sname, 0, 0, list(values))


def array(items, inner=''):
    return V('array', inner, 0, 0, list(items))


def bytes_array(data):
    return array([u8(x) for x in data], 'Byte')


def zero(t='prim'):
    return V('prim', t, 0, 0, 0, zero=True)


def typedef(type_hash, utype):
    return {'props': struct_('NiagaraTypeDefinition', {}), 'vfx1': {'hash': type_hash, 'ver': 1, 'utype': utype, 'res': 0}}


def var_base(nm, th):
    return native('NiagaraVariableBase', {'Name': nm, 'td': typedef(*th)})


def var(nm, th, data=b''):
    return native('NiagaraVariable', {'Name': nm, 'td': typedef(*th), 'data': bytes(data)})


def var_offset(nm, th, offset):
    return native('NiagaraVariableWithOffset', {'Name': nm, 'td': typedef(*th), 'Offset': int(offset)})


def guid(words):
    return binary('Guid', [int(w) & 0xffffffff for w in words])
