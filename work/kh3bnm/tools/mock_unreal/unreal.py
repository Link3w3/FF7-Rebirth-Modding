"""A strict stand-in for UE 4.26's `unreal` module, enough to run make_chaos_vincent_wing_bonamik.py offline.

Property names and types come from the project's reflection headers; set_editor_property refuses unknown names,
wrong types, ints for enum properties (as UE does), out-of-range integers and wrong fixed-array lengths."""
import copy, json, os, re

BONAMIK = '/work/bnm/Plugins/BonamikPlugin/Source/BonamikRt/Public/'
KBD = '/home/user/ff7r2uproj/Plugins/KBDPlugins/Source/KBDRt/Public/'
LOG = []

def log(text): LOG.append(('log', text)); print('[LogPython]', text)
def log_warning(text): LOG.append(('warning', text)); print('[LogPython] Warning:', text)
def log_error(text): LOG.append(('error', text)); print('[LogPython] Error:', text)


# ---------------------------------------------------------------- enums
def pythonize_upper(name):
    parts = re.findall(r'[A-Z]+(?=[A-Z][a-z]|\d|_|$)|[A-Z]?[a-z]+|\d+|[A-Z]+', name)
    return '_'.join(p.upper() for p in parts)

class EnumBase(object):
    _entries = None
    def __init__(self, name, value): self.name = name; self.value = value
    def __repr__(self): return '<%s.%s: %d>' % (type(self).__name__, self.name, self.value)
    @classmethod
    def cast(cls, value):
        if isinstance(value, cls): return value
        if isinstance(value, bool) or not isinstance(value, int): raise TypeError('cannot cast %r to %s' % (value, cls.__name__))
        for e in cls._entries:
            if e.value == value: return e
        raise ValueError('%s has no value %d' % (cls.__name__, value))

def make_enum(cpp_name, entries):
    cls = type(cpp_name[1:], (EnumBase,), {})
    cls._entries = []
    for i, entry in enumerate(entries):
        e = cls(pythonize_upper(entry), i); cls._entries.append(e); setattr(cls, e.name, e)
    return cls

ENUM_TYPES = {}
for f in os.listdir(BONAMIK):
    if f.startswith('ESQEX_') and f.endswith('.h'):
        text = open(BONAMIK + f).read()
        m = re.search(r'enum\s+(\w+)\s*{([^}]*)}', text)
        if m:
            entries = [e.strip().split('=')[0].strip() for e in m.group(2).split(',') if e.strip()]
            ENUM_TYPES[m.group(1)] = make_enum(m.group(1), entries)
for cls in ENUM_TYPES.values(): globals()[cls.__name__] = cls


# ---------------------------------------------------------------- math structs
class Vector(object):
    def __init__(self, x=0.0, y=0.0, z=0.0): self.x, self.y, self.z = float(x), float(y), float(z)
    def __repr__(self): return 'Vector(%g, %g, %g)' % (self.x, self.y, self.z)
class Quat(object):
    def __init__(self, x=0.0, y=0.0, z=0.0, w=0.0): self.x, self.y, self.z, self.w = float(x), float(y), float(z), float(w)
    def __repr__(self): return 'Quat(%g, %g, %g, %g)' % (self.x, self.y, self.z, self.w)


# ---------------------------------------------------------------- reflected types from headers
def parse_props(path):
    text = open(path).read()
    props = {}
    for m in re.finditer(r'UPROPERTY\([^\n]*\)\s*\n\s*([^;]+?)\s+(\w+)(\[(\d+)\])?;', text):
        props[m.group(2)] = (m.group(1).strip(), int(m.group(4)) if m.group(4) else 1)
    return props

class Wrapped(object):
    _props = {}
    def __init__(self):
        self.__dict__['_v'] = {}
    def _check(self, name, value):
        if name not in self._props:
            raise Exception("Failed to find property '%s' on '%s'" % (name, type(self).__name__))
        ctype, dim = self._props[name]
        if dim > 1:
            value = list(value)
            if len(value) > dim: raise Exception('%s: %d values for a [%d] array' % (name, len(value), dim))
            out = list(self.get_editor_property(name))
            for i, v in enumerate(value): out[i] = check_value(ctype, v, name)
            return out
        return check_value(ctype, value, name)
    def set_editor_property(self, name, value, notify_mode=None):
        self._v[name] = self._check(name, value)
        self._on_set(name)
    def _on_set(self, name): pass
    def get_editor_property(self, name):
        if name not in self._props: raise Exception("Failed to find property '%s' on '%s'" % (name, type(self).__name__))
        if name not in self._v:
            ctype, dim = self._props[name]
            d = default_value(ctype)
            return [copy.deepcopy(d) for _ in range(dim)] if dim > 1 else d
        v = self._v[name]
        return copy.deepcopy(v) if not isinstance(v, (Object,)) else v

def default_value(ctype):
    if ctype in ('float',): return 0.0
    if ctype in ('int32', 'uint32', 'uint8'): return 0
    if ctype == 'bool': return False
    if ctype in ('FString', 'FName'): return ''
    if ctype == 'FVector': return Vector()
    if ctype == 'FQuat': return Quat()
    if ctype.startswith('TArray<'): return []
    if ctype.startswith('TEnumAsByte<'): return ENUM_TYPES[ctype[12:-1]]._entries[0]
    if ctype.endswith('*'): return None
    if ctype.startswith('F') and ctype[1:] in STRUCTS: return STRUCTS[ctype[1:]]()
    return None

def check_value(ctype, value, name):
    if ctype == 'float':
        if isinstance(value, bool) or not isinstance(value, (int, float)): raise TypeError('%s: float expected, got %r' % (name, value))
        return float(value)
    if ctype in ('int32', 'uint32', 'uint8'):
        if isinstance(value, bool) or not isinstance(value, int): raise TypeError('%s: int expected, got %r' % (name, value))
        lo, hi = {'int32': (-2**31, 2**31 - 1), 'uint32': (0, 2**32 - 1), 'uint8': (0, 255)}[ctype]
        if not lo <= value <= hi: raise OverflowError('%s: %d out of %s range' % (name, value, ctype))
        return value
    if ctype == 'bool':
        if not isinstance(value, bool): raise TypeError('%s: bool expected, got %r' % (name, value))
        return value
    if ctype in ('FString', 'FName'):
        if not isinstance(value, str): raise TypeError('%s: str expected, got %r' % (name, value))
        return value
    if ctype == 'FVector':
        if not isinstance(value, Vector): raise TypeError('%s: Vector expected, got %r' % (name, value))
        return copy.deepcopy(value)
    if ctype == 'FQuat':
        if not isinstance(value, Quat): raise TypeError('%s: Quat expected, got %r' % (name, value))
        return copy.deepcopy(value)
    if ctype.startswith('TEnumAsByte<'):
        cls = ENUM_TYPES[ctype[12:-1]]
        if not isinstance(value, cls): raise TypeError('%s: %s entry expected (no implicit int), got %r' % (name, cls.__name__, value))
        return value
    if ctype.startswith('TArray<'):
        inner = ctype[7:-1].strip()
        return [check_value(inner, v, name + '[]') for v in value]
    if ctype.endswith('*'):
        cname = ctype[:-1].strip()[1:]
        if value is None: return None
        want = CLASSES.get(cname) or (Object if cname in ('Object',) else None)
        if want is None: raise TypeError('%s: unknown class %s' % (name, cname))
        if not isinstance(value, want): raise TypeError('%s: %s expected, got %r' % (name, cname, value))
        return value
    if ctype.startswith('F') and ctype[1:] in STRUCTS:
        if not isinstance(value, STRUCTS[ctype[1:]]): raise TypeError('%s: %s expected, got %r' % (name, ctype, value))
        return copy.deepcopy(value)
    raise TypeError('%s: unsupported type %s' % (name, ctype))

STRUCTS = {}
for header, name in (('SQEX_BonamikBodyDesc_v2.h', 'SQEX_BonamikBodyDesc_v2'), ('SQEX_BonamikLinkDesc_v2.h', 'SQEX_BonamikLinkDesc_v2'),
                     ('SQEX_BonamikSolverDesc_v2.h', 'SQEX_BonamikSolverDesc_v2'), ('SQEX_BonamikSceneManagerDesc_v2.h', 'SQEX_BonamikSceneManagerDesc_v2'),
                     ('SQEX_BonamikPlaneDesc_v2.h', 'SQEX_BonamikPlaneDesc_v2'), ('SQEX_BonamikShapeMatchingDesc_v2.h', 'SQEX_BonamikShapeMatchingDesc_v2'),
                     ('SQEX_BonamikPossessionDesc_v2.h', 'SQEX_BonamikPossessionDesc_v2'), ('SQEX_BonamikGroupLOD_v2.h', 'SQEX_BonamikGroupLOD_v2')):
    STRUCTS[name] = type(name, (Wrapped,), {'_props': parse_props(BONAMIK + header)})
for name, cls in STRUCTS.items(): globals()[name] = cls


# ---------------------------------------------------------------- objects
REGISTRY = {}   # package path -> asset
SAVED = []

class Object(Wrapped):
    _props = {}
    _flags_transient = False
    def __init__(self, outer=None, name=None):
        Wrapped.__init__(self)
        self.__dict__['_outer'] = outer
        self.__dict__['_name'] = name or '%s_0' % type(self).__name__
        self.__dict__['_dirty'] = False
    def get_outer(self): return self._outer
    def get_name(self): return self._name
    def get_path_name(self):
        if self._outer is None: return self._name
        sep = '.' if self._outer._outer is None else ':'
        return self._outer.get_path_name() + sep + self._name
    def get_outermost(self):
        o = self
        while o._outer is not None: o = o._outer
        return o
    def modify(self, always=True): self.get_outermost().__dict__['_dirty'] = True; return True
    def _on_set(self, name): self.modify()
    @classmethod
    def static_class(cls): return Class(cls)
    def __repr__(self): return '<%s %s>' % (type(self).__name__, self.get_path_name())
    def __deepcopy__(self, memo): return self   # object references are shared, as UE wrappers are

class Class(object):
    def __init__(self, cls): self.cls = cls

class Package(Object): pass

def _class(name, header=None, base=Object, extra=None):
    props = parse_props(header) if header else {}
    props.update(extra or {})
    cls = type(name, (base,), {'_props': props})
    globals()[name] = cls
    return cls

CLASSES = {}
CLASSES['SkeletalMesh'] = _class('SkeletalMesh', extra={'AssetUserData': ('TArray<UAssetUserData*>', 1), 'asset_user_data': ('TArray<UAssetUserData*>', 1)})
CLASSES['AssetUserData'] = _class('AssetUserData')
CLASSES['DataAsset'] = _class('DataAsset')
CLASSES['SQEX_BonamikAsset_v2'] = _class('SQEX_BonamikAsset_v2', BONAMIK + 'SQEX_BonamikAsset_v2.h')
CLASSES['SQEX_BonamikAsset'] = _class('SQEX_BonamikAsset', BONAMIK + 'SQEX_BonamikAsset.h', base=DataAsset)
CLASSES['SQEX_KineDriverData'] = _class('SQEX_KineDriverData')
CLASSES['SQEX_KBD_AssetUserData'] = _class('SQEX_KBD_AssetUserData', KBD + 'SQEX_KBD_AssetUserData.h', base=AssetUserData)
CLASSES['Object'] = Object
SQEX_KBD_AssetUserData._props.pop('OverrideBonamikDataList', None)

# python-style aliases the way UE exposes them (snake case names for reflected properties work too)
SkeletalMesh._props['asset_user_data'] = SkeletalMesh._props['AssetUserData']

class SkeletalMeshComponent(Object):
    def set_skeletal_mesh(self, mesh, reinit_pose=True): self.__dict__['_mesh'] = mesh
    def get_num_bones(self): return len(self._mesh._bones)
    def get_bone_name(self, i): return Name(self._mesh._bones[i][0])
    def get_parent_bone(self, name):
        names = [b[0] for b in self._mesh._bones]
        p = self._mesh._bones[names.index(str(name))][1]
        return Name(names[p] if p >= 0 else 'None')

class Name(str): pass

NEW_OBJECTS = []
def new_object(type, outer=None, name=None, base_type=None):
    if outer is None: outer = TRANSIENT
    if name is not None and find_object(outer, name) is not None:
        raise Exception('an object named %s already exists in %s (UE would replace it in place)' % (name, outer))
    if name is None:
        n = 0
        while find_object(outer, '%s_%d' % (type.__name__, n)) is not None: n += 1
        name = '%s_%d' % (type.__name__, n)
    obj = type(outer, name)
    NEW_OBJECTS.append(obj)
    return obj

def find_object(outer, name, type=None, follow_redirectors=True):
    for o in NEW_OBJECTS:
        if o._outer is outer and o._name == name: return o
    return None

TRANSIENT = Package(None, '/Engine/Transient')

class DataAssetFactory(Object):
    _props = {'DataAssetClass': ('UClass*', 1), 'data_asset_class': ('UClass*', 1)}
    def set_editor_property(self, name, value, notify_mode=None):
        if name not in ('data_asset_class', 'DataAssetClass'): raise Exception('no property ' + name)
        if not isinstance(value, Class): raise TypeError('data_asset_class wants a Class')
        self._v['data_asset_class'] = value

class _AssetTools(object):
    def create_asset(self, asset_name, package_path, asset_class, factory, calling_context=''):
        path = package_path + '/' + asset_name
        if path in REGISTRY: raise Exception('asset exists: ' + path)
        dac = factory._v.get('data_asset_class')
        cls = dac.cls if dac else asset_class
        pkg = Package(None, path)
        asset = cls(pkg, asset_name)
        asset.modify()
        REGISTRY[path] = asset
        return asset

class AssetToolsHelpers(object):
    @staticmethod
    def get_asset_tools(): return _AssetTools()

class EditorAssetLibrary(object):
    @staticmethod
    def does_asset_exist(path): return path in REGISTRY
    @staticmethod
    def load_asset(path): return REGISTRY.get(path)
    @staticmethod
    def save_loaded_asset(asset, only_if_is_dirty=True):
        pkg = asset.get_outermost()
        if only_if_is_dirty and not pkg._dirty: return True
        SAVED.append(asset.get_path_name()); pkg.__dict__['_dirty'] = False
        return True

class Paths(object):
    @staticmethod
    def project_saved_dir(): return '../../../FF7R2UProj/Saved/'
    @staticmethod
    def convert_relative_path_to_full(p): return os.path.join(OUTDIR, 'Saved')

OUTDIR = '/tmp'
COMMAND_LINE = 'End.uproject'

class SystemLibrary(object):
    @staticmethod
    def get_command_line(): return COMMAND_LINE

class AppMsgType(object):
    OK = 'OK'

DIALOGS = []
class EditorDialog(object):
    @staticmethod
    def show_message(title, message, message_type, default_value=None):
        DIALOGS.append((title, message)); print('[Dialog] %s\n%s' % (title, message))

COOKS = []
class RebirthAssetLibrary(object):
    @staticmethod
    def cook_asset_to_file(path, filename):
        COOKS.append((path, filename)); return 'Cooked %s to %s.' % (path, filename)


def setup_mesh(path, bones, user_data=None):
    pkg = Package(None, path)
    mesh = SkeletalMesh(pkg, path.rsplit('/', 1)[-1])
    mesh.__dict__['_bones'] = bones
    if user_data is not None: mesh._v['asset_user_data'] = user_data
    REGISTRY[path] = mesh
    return mesh


# ---------------------------------------------------------------- additions for kh3bonamik.py
SELECTED = []
ANSWERS = []          # answers for YES_NO dialogs, in order (default: YES)
SYNCED = []

class EditorUtilityLibrary(object):
    @staticmethod
    def get_selected_assets(): return list(SELECTED)

class AppReturnType(object):
    YES = 'YES'
    NO = 'NO'
    OK = 'OK'

AppMsgType.YES_NO = 'YES_NO'

def _show_message(title, message, message_type, default_value=None):
    DIALOGS.append((title, message, message_type))
    print('[Dialog %s] %s\n%s' % (message_type, title, message))
    if message_type == 'YES_NO':
        return ANSWERS.pop(0) if ANSWERS else AppReturnType.YES
    return AppReturnType.OK
EditorDialog.show_message = staticmethod(_show_message)

def _sync(paths): SYNCED.extend(paths)
EditorAssetLibrary.sync_browser_to_objects = staticmethod(_sync)

def _ref_pose_position(self, index):
    name = self._mesh._bones[index][0]
    offsets = self._mesh.__dict__.get('_offsets') or {}
    return Vector(*offsets.get(name, (5.0, 0.0, 0.0)))
SkeletalMeshComponent.get_ref_pose_position = _ref_pose_position
