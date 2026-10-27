"""KH3 Bonamik to Bonamik v2 (Rebirth FX > KH3 Bonamik To Bonamik v2...).

Turns a KINGDOM HEARTS III Bonamik (a cooked SQEX_BonamikAsset: <name>.uasset with its <name>.uexp next to it) into a
FINAL FANTASY VII REBIRTH Bonamik: a SQEX_BonamikAsset with a SQEX_BonamikAsset_v2 inside, the way the game keeps its
own 2.x Bonamiks (for example Sephiroth's PC0010_10_BNM). KH3 and Rebirth's v2 both run Bonamik 2.4 (version 2401), so
every body, link, plane, group, LOD and precomputed count is copied as it is; only the type names change
(SQEX_BonamikBodyDesc -> SQEX_BonamikBodyDesc_v2, ESQEX_Bonamik_CollisionShape_Capsule -> ..._v2_Capsule).

In the editor: select the character's skeletal mesh in the Content Browser (or right-click it), then
Rebirth FX > KH3 Bonamik To Bonamik v2... and pick one or more KH3 *_Bonamik.uasset files. Each one becomes an asset of
the same name next to the mesh and goes into the mesh's Asset User Data (SQEX_KBD_AssetUserData > Bonamik Data List).
Every bone the Bonamik moves or collides with has to be in the mesh, under its KH3 name; nothing is saved otherwise.
The editor's Bonamik preview only shows 3.x data, so test the result in game.

Python:  import rebirth_fx.kh3bonamik as k
         k.convert_file(r'D:/KH3/p_ex011_Bonamik.uasset', mesh='/Game/Character/p_ex011/p_ex011')
Without the editor:  python kh3bonamik.py <file.uasset> [out.json]   (reads, converts and checks; writes the v2 data)
"""
import json
import os
import struct
import sys
import time
import traceback

try:
    import unreal
except ImportError:  # outside the editor: reading, converting and checking still work
    unreal = None

TOOL = 'KH3 Bonamik To Bonamik v2'
V2_OBJECT_NAME = 'SQEX_BonamikAsset_v2_0'   # what the game's own v2 Bonamiks call their v2 object
REBIRTH_VERSION = 2401                      # Bonamik 2.4.01: Rebirth's v2 data (PC0010_10_BNM) and KH3's
DEFAULT_FOLDER = '/Game/KH3Bonamik'         # where a Bonamik goes when no mesh is selected
NO_ID = 0xFFFFFFFF


# ---------------------------------------------------------------------------------------------------------------------
# Bonamik v2 as Rebirth defines it: the property order and types of USQEX_BonamikAsset_v2 and its structs
# (from the BonamikRt headers; the same order the game's cooked v2 Bonamiks use). Kinds: u32 i32 u8 bool f32 str name
# vec quat object, ('enum', E), ('struct', S), ('array', kind). The third value is the C++ array size.
# ---------------------------------------------------------------------------------------------------------------------

V2_TYPES = {
    'SQEX_BonamikAsset_v2': [
        ('m_SkeletalMesh', 'object', 1),
        ('m_VersionNo', 'u32', 1),
        ('m_SceneManager', ('struct', 'SQEX_BonamikSceneManagerDesc_v2'), 1),
        ('m_Solvers', ('array', ('struct', 'SQEX_BonamikSolverDesc_v2')), 1),
        ('m_Bodies', ('array', ('struct', 'SQEX_BonamikBodyDesc_v2')), 1),
        ('m_Links', ('array', ('struct', 'SQEX_BonamikLinkDesc_v2')), 1),
        ('m_Planes', ('array', ('struct', 'SQEX_BonamikPlaneDesc_v2')), 1),
        ('m_ShapeMatchings', ('array', ('struct', 'SQEX_BonamikShapeMatchingDesc_v2')), 1),
        ('m_Possessions', ('array', ('struct', 'SQEX_BonamikPossessionDesc_v2')), 1),
        ('m_TotalKinematics', 'u32', 1),
        ('m_TotalConstraints', 'u32', 1),
        ('m_TotalCones', 'u32', 1),
        ('m_TotalLinks', 'u32', 1),
        ('m_TotalCollisions', 'u32', 1),
        ('m_TotalSelfCollisions', 'u32', 1),
        ('m_TotalChainRootParticles', 'u32', 1),
        ('m_TotalPCLinkCones', 'u32', 1),
        ('m_TotalLateralLinkCones', 'u32', 1),
        ('m_bAlwaysUse60FPSsetting', 'bool', 1),
        ('m_IgnoreEffectors', ('array', 'name'), 1),
        ('m_TeleportDistance', 'f32', 1),
        ('m_BonamikReferenceGroup', 'str', 1),
        ('m_ReferenceGroups', ('array', 'name'), 1),
        ('m_BonamikCheckGroundBodyPosGroups', ('array', 'str'), 1),
        ('m_CheckGroundBodyPosGroups', ('array', 'name'), 1),
        ('m_BonamikGroupLODs', ('array', ('struct', 'SQEX_BonamikGroupLOD_v2')), 1),
        ('m_BonamikAccurateBoundsUpdate', 'bool', 1),
        ('m_PreRollStepOnResume', 'i32', 1),
    ],
    'SQEX_BonamikSceneManagerDesc_v2': [
        ('m_IsEnable', 'bool', 1),
        ('m_IsUseGPU', 'bool', 1),
        ('m_SubStep', 'u32', 1),
        ('m_Dt', 'f32', 1),
        ('m_TotalGroup', 'u32', 1),
        ('m_GroupName', 'str', 48),
        ('m_IsEnableLSS', 'bool', 1),
        ('m_LSScoeff_tran', 'f32', 1),
        ('m_LSScoeff_rot', 'f32', 1),
        ('m_RootName', 'str', 1),
        ('m_IsEnableLocalForce', 'bool', 1),
        ('m_Gravity', 'vec', 1),
        ('m_WindForce', 'vec', 1),
        ('m_DirRange', 'vec', 1),
        ('m_ForceRange', 'vec', 1),
        ('m_TotalLinkBatches', 'u32', 1),
        ('m_TotalLinksInBatch', 'u32', 15),
        ('m_TotalConeBatches', 'u32', 1),
        ('m_TotalConesInBatch', 'u32', 15),
        ('m_TotalCollisionBatches', 'u32', 1),
        ('m_TotalCollisionsInBatch', 'u32', 15),
        ('m_TotalSelfCollisionBatches', 'u32', 1),
        ('m_TotalSelfCollisionsInBatch', 'u32', 15),
        ('m_JointLinkSimulationMode', ('enum', 'ESQEX_Bonamik_JointLinkSimulationMode_v2'), 1),
        ('m_FastMotionHandlingMode', ('enum', 'ESQEX_Bonamik_FastMotionHandling_v2'), 1),
        ('m_EnableGroundCollision', 'bool', 1),
        ('m_RefUpVec', 'u32', 1),
    ],
    'SQEX_BonamikSolverDesc_v2': [
        ('m_GroupId', 'u32', 1),
        ('m_GroupName', 'str', 1),
        ('m_IsEnable', 'bool', 1),
        ('m_IsUseConeSEQ', 'bool', 1),
        ('m_IsEnableDraw', 'bool', 1),
        ('m_ColIter', 'u32', 1),
        ('m_ConsIter', 'u32', 1),
        ('m_ConeIter', 'u32', 1),
        ('m_LinkIter', 'u32', 1),
        ('m_SolverIter', 'u32', 1),
        ('m_TagId', 'u32', 1),
        ('m_CollisionTagId', 'u32', 1),
        ('m_EnableGround', 'bool', 1),
        ('m_LODdistance', 'f32', 1),
        ('m_RefUpVec', 'i32', 1),
    ],
    'SQEX_BonamikBodyDesc_v2': [
        ('m_Index', 'u32', 1),
        ('m_JointName', 'str', 1),
        ('m_ParentBodyName', 'str', 1),
        ('m_ChildBodyName', 'str', 1),
        ('m_ParentId', 'i32', 1),
        ('m_ChildId', 'i32', 1),
        ('m_GroupId', 'u32', 1),
        ('m_ColId', 'i32', 8),
        ('m_IsKinematic', 'bool', 1),
        ('m_IsCollision', 'bool', 1),
        ('m_IsMultipleCollisionObject', 'bool', 1),
        ('m_Mass', 'f32', 1),
        ('m_Inertia', 'f32', 1),
        ('m_Radius', 'f32', 1),
        ('m_Damping', 'f32', 1),
        ('m_Bounciness', 'f32', 1),
        ('m_Friction', 'f32', 1),
        ('m_WindDrag', 'f32', 1),
        ('m_WindLift', 'f32', 1),
        ('m_LocalTransCoeff', 'f32', 1),
        ('m_MaxLocalTrans', 'f32', 1),
        ('m_ColShape', ('enum', 'ESQEX_Bonamik_CollisionShape_v2'), 1),
        ('m_AddiConstType', ('enum', 'ESQEX_Bonamik_ConstraintType_v2'), 1),
        ('m_AddiConstStr', 'f32', 1),
        ('m_AddiConstRad', 'f32', 1),
        ('m_LocalTransform', 'vec', 1),
        ('m_LocalRotation', 'quat', 1),
        ('m_CollisionBatchNo', 'u32', 1),
        ('m_LocalScale', 'vec', 1),
        ('m_ConcaveRatio', 'f32', 1),
        ('m_LFcoeff', 'f32', 1),
        ('m_ParkRate', 'f32', 1),
        ('m_MaxLF', 'f32', 1),
        ('m_LFdrag', 'f32', 1),
        ('m_LFlift', 'f32', 1),
    ],
    'SQEX_BonamikLinkDesc_v2': [
        ('m_ParentBodyName', 'str', 1),
        ('m_ChildBodyName', 'str', 1),
        ('m_ParentId', 'u32', 1),
        ('m_ChildId', 'u32', 1),
        ('m_LinkType', ('enum', 'ESQEX_Bonamik_LinkType_v2'), 1),
        ('m_IsSelfCollision', 'bool', 1),
        ('m_EnableJointTwist', 'bool', 1),
        ('m_EnableCone', 'bool', 1),
        ('m_EnableConeAnimation', 'bool', 1),
        ('m_LinkStr', 'f32', 1),
        ('m_LinkParentStr', 'f32', 1),
        ('m_ConeInnerStr', 'f32', 1),
        ('m_ConeOuterStr', 'f32', 1),
        ('m_ConeParentStr', 'f32', 1),
        ('m_LimitY', 'f32', 1),
        ('m_LimitZ', 'f32', 1),
        ('m_ConeOffsetY', 'f32', 1),
        ('m_ConeOffsetZ', 'f32', 1),
        ('m_LimitOffsetY', 'f32', 1),
        ('m_LimitOffsetZ', 'f32', 1),
        ('m_IsCollisionReceiver', 'bool', 1),
        ('m_IsCollisionRepulsor', 'bool', 1),
        ('m_IsLRA', 'bool', 1),
        ('m_LRAstr', 'f32', 1),
        ('m_LRAdamping', 'f32', 1),
        ('m_LinkBatchNo', 'u32', 1),
        ('m_ConeBatchNo', 'u32', 1),
        ('m_CollisionBatchNo', 'u32', 1),
        ('m_PinRadius', 'f32', 1),
        ('m_PinStr', 'f32', 1),
        ('m_KdiTrans', 'f32', 1),
        ('m_KdiRot', 'f32', 1),
        ('m_ConcaveRatio', 'f32', 1),
    ],
    'SQEX_BonamikPlaneDesc_v2': [
        ('m_GroupId', 'u32', 1),
        ('m_ParticleAName', 'str', 1),
        ('m_ParticleBName', 'str', 1),
        ('m_ParticleCName', 'str', 1),
        ('m_ParticleA', 'i32', 1),
        ('m_ParticleB', 'i32', 1),
        ('m_ParticleC', 'i32', 1),
        ('m_Index', 'u32', 1),
        ('m_Thickness', 'f32', 1),
        ('m_Offset', 'f32', 1),
        ('m_IsCollision', 'bool', 1),
        ('m_CollisionBatchNo', 'i32', 1),
        ('m_ColId', 'i32', 8),
    ],
    'SQEX_BonamikShapeMatchingDesc_v2': [
        ('m_TotalParticle', 'i32', 1),
        ('m_RegionSize', 'i32', 1),
        ('m_Stiffness', 'f32', 1),
        ('m_ParticleIds', 'u32', 50),
    ],
    'SQEX_BonamikPossessionDesc_v2': [
        ('m_BodyName', 'str', 1),
        ('m_BodyId', 'i32', 1),
        ('m_Time', 'f32', 1),
        ('m_Mode', ('enum', 'ESQEX_Bonamik_PossessionMode_v2'), 1),
        ('m_SubMode', 'i32', 1),
        ('m_IsFlow', 'bool', 1),
        ('m_DrawingRadius', 'f32', 1),
        ('m_TimeToActivateNext', 'f32', 1),
        ('m_Magnitude', 'f32', 1),
        ('m_IncrementalMagnitude', 'f32', 1),
        ('m_MaxMagnitude', 'f32', 1),
        ('m_DelayTime', 'f32', 1),
    ],
    'SQEX_BonamikGroupLOD_v2': [
        ('Groups', ('array', 'name'), 1),
        ('MinSize', 'f32', 1),
        ('BlendTime', 'f32', 1),
        ('PreRollTime', 'f32', 1),
    ],
}
V2_FIELDS = dict((t, dict((f[0], (f[1], f[2])) for f in fields)) for t, fields in V2_TYPES.items())

V2_ENUMS = {
    'ESQEX_Bonamik_CollisionShape_v2': [
        'ESQEX_Bonamik_CollisionShape_v2_None', 'ESQEX_Bonamik_CollisionShape_v2_Sphere',
        'ESQEX_Bonamik_CollisionShape_v2_Capsule', 'ESQEX_Bonamik_CollisionShape_v2_Inverse_Sphere',
        'ESQEX_Bonamik_CollisionShape_v2_Inverse_Capsule', 'ESQEX_Bonamik_CollisionShape_v2_ReservedA',
        'ESQEX_Bonamik_CollisionShape_v2_Plane', 'ESQEX_Bonamik_CollisionShape_v2_ReservedB',
        'ESQEX_Bonamik_CollisionShape_v2_Box', 'ESQEX_Bonamik_CollisionShape_v2_Self_Collision'],
    'ESQEX_Bonamik_ConstraintType_v2': [
        'ESQEX_Bonamik_ConstraintType_v2_None', 'ESQEX_Bonamik_ConstraintType_v2_Sphere',
        'ESQEX_Bonamik_ConstraintType_v2_Spring', 'ESQEX_Bonamik_ConstraintType_v2_GroundAttach',
        'ESQEX_Bonamik_ConstraintType_v2_SecondOrder_Sphere'],
    'ESQEX_Bonamik_FastMotionHandling_v2': [
        'ESQEX_Bonamik_FMH_v2_NONE', 'ESQEX_Bonamik_FMH_v2_LOCAL_FORCE', 'ESQEX_Bonamik_FMH_v2_LSS'],
    'ESQEX_Bonamik_JointLinkSimulationMode_v2': [
        'ESQEX_Bonamik_JOINTLINK_MODE_v2_SEQ', 'ESQEX_Bonamik_JOINTLINK_MODE_v2_BATCH'],
    'ESQEX_Bonamik_LinkType_v2': [
        'ESQEX_Bonamik_LinkType_v2_Lateral', 'ESQEX_Bonamik_LinkType_v2_ParentChild', 'ESQEX_Bonamik_LinkType_v2_Bending',
        'ESQEX_Bonamik_LinkType_v2_PinConstraint', 'ESQEX_Bonamik_LinkType_v2_KdiConstraint',
        'ESQEX_Bonamik_LinkType_v2_ReactionTransfer', 'ESQEX_Bonamik_LinkType_v2_InverseFreeConstraint'],
    'ESQEX_Bonamik_PossessionMode_v2': [
        'ESQEX_Bonamik_PSSMODE_v2_SWING_Y', 'ESQEX_Bonamik_PSSMODE_v2_SWING_Z', 'ESQEX_Bonamik_PSSMODE_v2_RANDOM_ROLL'],
}

# KH3 fields Rebirth's v2 has no place for. Dropping them changes nothing when they are empty (as in KH3's own files).
KNOWN_DROPS = {'m_FpsCorrection': 'per-group frame rate corrections (v2 has none)'}


class ConvertError(Exception):
    """A reason the file can't be converted, worded for the person converting it."""


class Enum(object):
    """An entry of a v2 enum: the enum's C++ name, the entry's number and its C++ name."""

    def __init__(self, enum, value):
        self.enum, self.value = enum, value
        self.entry = V2_ENUMS[enum][value]

    def __eq__(self, other):
        return isinstance(other, Enum) and (self.enum, self.value) == (other.enum, other.value)

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash((self.enum, self.value))

    def __repr__(self):
        return self.entry


class Vec(tuple):
    """FVector (x, y, z)"""


class Quat(tuple):
    """FQuat (x, y, z, w)"""


class Static(dict):
    """The elements of a C++ fixed-size array as tagged properties store them: {index: value}, defaults left out."""


# ---------------------------------------------------------------------------------------------------------------------
# Reading a cooked UE4 package with tagged properties (KH3 is UE 4.17; this reads the 4.1x-4.2x legacy format)
# ---------------------------------------------------------------------------------------------------------------------

PACKAGE_TAG = 0x9E2A83C1
PKG_FILTER_EDITOR_ONLY = 0x80000000
NATIVE_STRUCTS = {'Vector': '<3f', 'Quat': '<4f', 'Rotator': '<3f', 'Vector2D': '<2f', 'LinearColor': '<4f',
                  'Color': '<4B', 'Guid': '<4I', 'IntPoint': '<2i', 'Vector4': '<4f', 'IntVector': '<3i',
                  'Plane': '<4f', 'Box': '<6fB', 'Box2D': '<4fB'}


class _Reader(object):
    def __init__(self, data, pos=0, names=None, end=None):
        self.d = data
        self.p = pos
        self.names = names or []
        self.end = len(data) if end is None else end

    def take(self, n):
        if n < 0 or self.p + n > self.end:
            raise ConvertError('the file ends early (wanted %d bytes at %d of %d): is the .uexp the one that goes with '
                               'this .uasset?' % (n, self.p, self.end))
        v = self.d[self.p:self.p + n]
        self.p += n
        return v

    def unpack(self, fmt):
        size = struct.calcsize(fmt)
        v = struct.unpack(fmt, self.take(size))
        return v[0] if len(v) == 1 else v

    def i32(self):
        return self.unpack('<i')

    def u32(self):
        return self.unpack('<I')

    def i64(self):
        return self.unpack('<q')

    def fstring(self):
        n = self.i32()
        if n == 0:
            return ''
        if n < 0:
            if n < -(1 << 20):
                raise ConvertError('a broken string length (%d) at %d' % (n, self.p - 4))
            return self.take(-2 * n).decode('utf-16-le', 'replace').rstrip('\0')
        if n > (1 << 20):
            raise ConvertError('a broken string length (%d) at %d' % (n, self.p - 4))
        return self.take(n).decode('latin-1').rstrip('\0')

    def fname(self):
        index, number = self.i32(), self.i32()
        if not 0 <= index < len(self.names):
            raise ConvertError('a name index (%d) outside the name table (%d names) at %d' % (index, len(self.names), self.p - 8))
        name = self.names[index]
        return name if number == 0 else '%s_%d' % (name, number - 1)


class Package(object):
    """The summary, names, imports and exports of a legacy (pre-IoStore) cooked .uasset (+ .uexp)."""

    def __init__(self, uasset, uexp=b''):
        self.data = uasset + uexp
        self.header_size = len(uasset)
        r = _Reader(uasset)
        if len(uasset) < 32:
            raise ConvertError('the .uasset is too small to be a package')
        tag = r.u32()
        if tag != PACKAGE_TAG:
            raise ConvertError('this is not a UE4 .uasset (it doesn\'t start with the package tag). Rebirth\'s own '
                               'IoStore packages and other formats can\'t be read here; pick the KH3 file')
        self.legacy = r.i32()
        if not -8 <= self.legacy <= -2:
            raise ConvertError('package format %d is not one this reads (UE 4.x writes -2 to -7)' % self.legacy)
        if self.legacy != -4:
            r.i32()  # UE3 version
        self.ue4 = r.i32()
        self.licensee = r.i32()
        ver = self.ue4 or 522  # an unversioned package (KH3's) uses its engine's newest layout
        self.ver = ver
        count = r.i32()
        for _ in range(max(0, count)):
            if self.legacy == -2:
                r.take(8)                 # enum-based custom versions
            elif self.legacy >= -5:
                r.take(20)
                r.fstring()               # guid-based with a friendly name
            else:
                r.take(20)                # optimized: guid + version
        self.total_header_size = r.i32()
        r.fstring()                       # folder name
        self.flags = r.u32()
        self.cooked_editor_free = bool(self.flags & PKG_FILTER_EDITOR_ONLY)
        self.name_count, self.name_offset = r.i32(), r.i32()
        if ver >= 516 and not self.cooked_editor_free:
            r.fstring()                   # localization id
        if ver >= 459:
            r.i32(), r.i32()              # gatherable text data
        self.export_count, self.export_offset = r.i32(), r.i32()
        self.import_count, self.import_offset = r.i32(), r.i32()
        for what, count, offset in (('name', self.name_count, self.name_offset),
                                    ('export', self.export_count, self.export_offset),
                                    ('import', self.import_count, self.import_offset)):
            if count < 0 or count > 1000000 or (count and not 0 < offset < len(uasset)):
                raise ConvertError('the package header is not one this reads (%s table %d at %d)' % (what, count, offset))
        # names
        r.p = self.name_offset
        self.names = []
        for _ in range(self.name_count):
            self.names.append(r.fstring())
            if ver >= 504:
                r.take(4)                 # the two name hashes
        r.names = self.names
        # imports
        r.p = self.import_offset
        self.imports = []
        for _ in range(self.import_count):
            class_package, class_name = r.fname(), r.fname()
            outer = r.i32()
            name = r.fname()
            if ver >= 520 and not self.cooked_editor_free:
                r.fname()                 # package name
            self.imports.append(dict(class_package=class_package, class_name=class_name, outer=outer, name=name))
        # exports
        r.p = self.export_offset
        self.exports = []
        for _ in range(self.export_count):
            e = dict(cls=r.i32(), sup=r.i32())
            e['template'] = r.i32() if ver >= 508 else 0
            e['outer'] = r.i32()
            e['name'] = r.fname()
            e['flags'] = r.u32()
            if ver >= 511:
                e['size'], e['offset'] = r.i64(), r.i64()
            else:
                e['size'], e['offset'] = r.i32(), r.i32()
            r.take(12)                    # forced export, not for client, not for server
            r.take(20)                    # package guid, package flags
            if ver >= 365:
                r.take(4)                 # not always loaded for editor game
            if ver >= 485:
                r.take(4)                 # is asset
            if ver >= 507:
                r.take(20)                # preload dependencies
            if not 0 <= e['offset'] <= len(self.data) or e['size'] < 0 or e['offset'] + e['size'] > len(self.data):
                if e['offset'] + e['size'] > len(self.data) and not uexp:
                    raise ConvertError('the .uexp file is missing: it has to be next to the .uasset, with the same name')
                raise ConvertError('export %s points outside the file (is the .uexp the one that goes with this .uasset?)' % e['name'])
            self.exports.append(e)

    def ref_name(self, index):
        if index < 0 and -index - 1 < len(self.imports):
            return self.imports[-index - 1]['name']
        if index > 0 and index - 1 < len(self.exports):
            return self.exports[index - 1]['name']
        return None

    def class_name(self, export):
        return self.ref_name(export['cls'])

    def export_reader(self, export):
        return _Reader(self.data, export['offset'], self.names, export['offset'] + export['size'])


def _read_tag(r):
    name = r.fname()
    if name == 'None':
        return None
    tag = dict(name=name, type=r.fname())
    tag['size'], tag['index'] = r.i32(), r.i32()
    t = tag['type']
    if t == 'StructProperty':
        tag['struct'] = r.fname()
        r.take(16)
    elif t == 'BoolProperty':
        tag['bool'] = r.unpack('<B')
    elif t in ('ByteProperty', 'EnumProperty'):
        tag['enum'] = r.fname()
    elif t in ('ArrayProperty', 'SetProperty'):
        tag['inner'] = r.fname()
    elif t == 'MapProperty':
        tag['inner'], tag['value'] = r.fname(), r.fname()
    if r.unpack('<B'):
        r.take(16)                        # property guid
    return tag


def _read_scalar(r, t, size, enum=None):
    if t == 'IntProperty':
        return r.unpack('<i')
    if t == 'UInt32Property':
        return r.unpack('<I')
    if t == 'Int8Property':
        return r.unpack('<b')
    if t == 'Int16Property':
        return r.unpack('<h')
    if t == 'UInt16Property':
        return r.unpack('<H')
    if t == 'Int64Property':
        return r.unpack('<q')
    if t == 'UInt64Property':
        return r.unpack('<Q')
    if t == 'FloatProperty':
        return r.unpack('<f')
    if t == 'DoubleProperty':
        return r.unpack('<d')
    if t == 'StrProperty':
        return r.fstring()
    if t == 'NameProperty':
        return r.fname()
    if t == 'EnumProperty':
        return r.fname()
    if t == 'ByteProperty':
        if (enum and enum != 'None') or size == 8:
            return r.fname()              # an enum entry, by name
        return r.unpack('<B')
    if t == 'BoolProperty':
        return bool(r.unpack('<B'))
    if t in ('ObjectProperty', 'ClassProperty', 'WeakObjectProperty', 'LazyObjectProperty', 'InterfaceProperty'):
        return ('object', r.i32())
    return None


def _read_struct(r, struct_name, size=None):
    if struct_name in NATIVE_STRUCTS and (size is None or size == struct.calcsize(NATIVE_STRUCTS[struct_name])):
        v = r.unpack(NATIVE_STRUCTS[struct_name])
        return list(v) if isinstance(v, tuple) else [v]
    return read_properties(r)


def read_properties(r):
    """Tagged properties up to 'None': an ordered dict-like list -> {name: value}; a C++ fixed-size array comes back as
    Static({index: value}) when more than its first element is stored."""
    out = Props()
    while True:
        tag = _read_tag(r)
        if tag is None:
            return out
        start = r.p
        end = start + tag['size']
        if tag['size'] < 0 or end > r.end:
            raise ConvertError('property %s says it is %d bytes, past the end of the object' % (tag['name'], tag['size']))
        t = tag['type']
        try:
            if t == 'BoolProperty':
                value = bool(tag['bool'])
            elif t == 'StructProperty':
                value = _read_struct(r, tag['struct'], tag['size'])
                if isinstance(value, Props):
                    value.struct = tag['struct']
            elif t == 'ArrayProperty':
                value = _read_array(r, tag, end)
            elif t in ('MapProperty', 'SetProperty', 'TextProperty', 'SoftObjectProperty', 'SoftClassProperty',
                       'DelegateProperty', 'MulticastDelegateProperty'):
                r.take(tag['size'])
                value = ('unread', t)
            else:
                value = _read_scalar(r, t, tag['size'], tag.get('enum'))
                if value is None:
                    r.take(tag['size'])
                    value = ('unread', t)
        except ConvertError:
            raise
        except Exception as error:
            raise ConvertError('could not read property %s (%s): %s' % (tag['name'], t, error))
        if r.p != end:
            raise ConvertError('property %s (%s) is %d bytes but %d were read: the file is not in the format this '
                               'reads' % (tag['name'], t, tag['size'], r.p - start))
        out.add(tag['name'], tag['index'], value)


def _read_array(r, tag, end):
    count = r.i32()
    if count < 0 or count > 1000000:
        raise ConvertError('array %s has a broken length (%d)' % (tag['name'], count))
    inner = tag['inner']
    if inner == 'StructProperty':
        itag = _read_tag(r)
        if itag is None:
            raise ConvertError('array %s has no element description' % tag['name'])
        per = None
        if count and itag['struct'] in NATIVE_STRUCTS:
            per = itag['size'] // count
        values = []
        for _ in range(count):
            v = _read_struct(r, itag['struct'], per)
            if isinstance(v, Props):
                v.struct = itag['struct']
            values.append(v)
        return values
    if inner == 'BoolProperty':
        return [bool(r.unpack('<B')) for _ in range(count)]
    if inner == 'ByteProperty':
        per = (tag['size'] - 4) // count if count else 1
        return [_read_scalar(r, inner, per, 'None' if per == 1 else 'enum') for _ in range(count)]
    values = []
    for _ in range(count):
        v = _read_scalar(r, inner, None)
        if v is None:
            r.p = end
            return ('unread', 'array of ' + inner)
        values.append(v)
    return values


class Props(object):
    """Tagged properties of one object or struct, in file order."""

    def __init__(self):
        self.order = []
        self.values = {}
        self.struct = None

    def add(self, name, index, value):
        if name not in self.values:
            self.order.append(name)
            self.values[name] = Static({index: value}) if index else value
            return
        old = self.values[name]
        if not isinstance(old, Static):
            old = Static({0: old})
            self.values[name] = old
        old[index] = value

    def get(self, name, default=None):
        return self.values.get(name, default)

    def __contains__(self, name):
        return name in self.values

    def items(self):
        return [(n, self.values[n]) for n in self.order]


def read_kh3_bonamik(path):
    """(asset name, Props of its SQEX_BonamikAsset) from a KH3 <name>.uasset (or its .uexp)."""
    base, ext = os.path.splitext(path)
    if ext.lower() not in ('.uasset', '.uexp'):
        raise ConvertError('pick the .uasset of the KH3 Bonamik (with its .uexp next to it)')
    uasset_path, uexp_path = base + '.uasset', base + '.uexp'
    if not os.path.isfile(uasset_path):
        raise ConvertError('%s is not there (the .uasset and the .uexp have to be in the same folder)' % uasset_path)
    with open(uasset_path, 'rb') as f:
        uasset = f.read()
    uexp = b''
    if os.path.isfile(uexp_path):
        with open(uexp_path, 'rb') as f:
            uexp = f.read()
    package = Package(uasset, uexp)
    exports = [e for e in package.exports if package.class_name(e) == 'SQEX_BonamikAsset']
    if not exports:
        classes = sorted(set(str(package.class_name(e)) for e in package.exports))
        if 'SQEX_BonamikAsset_v2' in classes:
            raise ConvertError('this is already a v2 Bonamik (it has a SQEX_BonamikAsset_v2 inside)')
        raise ConvertError('this package holds no SQEX_BonamikAsset (it has %s)' % (', '.join(classes) or 'nothing'))
    export = exports[0]
    props = read_properties(package.export_reader(export))
    return export['name'], props


# ---------------------------------------------------------------------------------------------------------------------
# KH3 -> v2: the same fields under their v2 types
# ---------------------------------------------------------------------------------------------------------------------

class Notes(object):
    def __init__(self):
        self.dropped = {}      # (where, field) -> [count, non-empty count]
        self.converted = {}    # what was retyped: 'int -> uint32' etc. -> count
        self.warnings = []

    def drop(self, where, field, value):
        entry = self.dropped.setdefault((where, field), [0, 0])
        entry[0] += 1
        if not _is_empty(value):
            entry[1] += 1

    def retype(self, what):
        self.converted[what] = self.converted.get(what, 0) + 1

    def lines(self):
        out = []
        for (where, field), (count, used) in sorted(self.dropped.items()):
            why = KNOWN_DROPS.get(field, 'v2 has no such field')
            if used:
                out.append('%s.%s left out (%s): %d of %d had values' % (where, field, why, used, count))
            else:
                out.append('%s.%s left out (%s; it was empty everywhere)' % (where, field, why))
        for what, count in sorted(self.converted.items()):
            out.append('%d value(s) %s' % (count, what))
        return out + self.warnings


def _is_empty(value):
    if value is None or value == '' or value is False or value == 0:
        return True
    if isinstance(value, (list, tuple, dict, Static)):
        return len(value) == 0
    if isinstance(value, Props):
        return not value.order
    return False


def _zero(kind):
    if kind in ('u32', 'i32', 'u8'):
        return 0
    if kind == 'f32':
        return 0.0
    if kind == 'bool':
        return False
    if kind in ('str', 'name'):
        return ''
    if kind == 'vec':
        return Vec((0.0, 0.0, 0.0))
    if kind == 'quat':
        return Quat((0.0, 0.0, 0.0, 0.0))
    if isinstance(kind, tuple) and kind[0] == 'enum':
        return Enum(kind[1], 0)
    if isinstance(kind, tuple) and kind[0] == 'array':
        return []
    raise ConvertError('no zero for %r' % (kind,))


def _enum_entry(enum, value, where):
    entries = V2_ENUMS[enum]
    if isinstance(value, int) and not isinstance(value, bool):
        if 0 <= value < len(entries):
            return Enum(enum, value)
        raise ConvertError('%s: %s has no entry %d' % (where, enum, value))
    if not isinstance(value, str):
        raise ConvertError('%s: an enum value was expected, the file has %r' % (where, value))
    name = value.split('::')[-1]
    for i, entry in enumerate(entries):
        plain = entry.replace('_v2_', '_')
        if name in (entry, plain) or (('::' in value) and plain.endswith('_' + name)):
            return Enum(enum, i)
    raise ConvertError('%s: %s is not an entry of %s' % (where, value, enum))


def _float32(value):
    return struct.unpack('<f', struct.pack('<f', float(value)))[0]


def convert_value(kind, value, where, notes):
    if isinstance(value, tuple) and value and value[0] == 'unread':
        raise ConvertError('%s: the file stores it as %s, which this can\'t read' % (where, value[1]))
    if kind == 'u32':
        if isinstance(value, bool) or not isinstance(value, int):
            raise ConvertError('%s: a whole number was expected, the file has %r' % (where, value))
        if value < 0:
            notes.retype('stored signed, kept as the same uint32 bits')
            value &= 0xFFFFFFFF
        if value > 0xFFFFFFFF:
            raise ConvertError('%s: %d does not fit a uint32' % (where, value))
        return value
    if kind in ('i32', 'u8'):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ConvertError('%s: a whole number was expected, the file has %r' % (where, value))
        if kind == 'u8':
            if not 0 <= value <= 255:
                raise ConvertError('%s: %d does not fit a byte' % (where, value))
            return value
        if value > 0x7FFFFFFF:
            if value > 0xFFFFFFFF:
                raise ConvertError('%s: %d does not fit an int32' % (where, value))
            notes.retype('stored unsigned, kept as the same int32 bits')
            value -= 1 << 32
        if value < -0x80000000:
            raise ConvertError('%s: %d does not fit an int32' % (where, value))
        return value
    if kind == 'f32':
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ConvertError('%s: a number was expected, the file has %r' % (where, value))
        if isinstance(value, int):
            notes.retype('stored as whole numbers, turned into floats')
        return _float32(value)
    if kind == 'bool':
        if isinstance(value, bool):
            return value
        if isinstance(value, int) and value in (0, 1):
            notes.retype('stored as 0/1, turned into booleans')
            return bool(value)
        raise ConvertError('%s: true/false was expected, the file has %r' % (where, value))
    if kind in ('str', 'name'):
        if not isinstance(value, str):
            raise ConvertError('%s: text was expected, the file has %r' % (where, value))
        return value
    if kind in ('vec', 'quat'):
        n = 3 if kind == 'vec' else 4
        if not isinstance(value, list) or len(value) != n:
            raise ConvertError('%s: %d numbers were expected, the file has %r' % (where, n, value))
        out = tuple(_float32(x) for x in value)
        return Vec(out) if kind == 'vec' else Quat(out)
    if kind == 'object':
        raise ConvertError('%s: object references are not converted' % where)
    if kind[0] == 'enum':
        return _enum_entry(kind[1], value, where)
    if kind[0] == 'struct':
        if not isinstance(value, Props):
            raise ConvertError('%s: a %s was expected, the file has %r' % (where, kind[1], value))
        return convert_struct(kind[1], value, where, notes)
    if kind[0] == 'array':
        if not isinstance(value, list):
            raise ConvertError('%s: a list was expected, the file has %r' % (where, value))
        return [convert_value(kind[1], v, '%s[%d]' % (where, i), notes) for i, v in enumerate(value)]
    raise ConvertError('%s: unknown kind %r' % (where, kind))


def convert_struct(type_name, props, where, notes):
    """{v2 field: value} for the fields the file stores (a fixed-size array becomes a full list, unstored elements 0)."""
    fields = V2_FIELDS[type_name]
    out = {}
    short = where.split('[')[0]
    for name, value in props.items():
        if name not in fields:
            notes.drop(short, name, value)
            continue
        kind, dim = fields[name]
        if kind == 'object':
            if not _is_empty(value) and value != ('object', 0):
                notes.warnings.append('%s.%s (a reference to another asset) was left empty' % (where, name))
            continue
        if dim > 1:
            elements = value if isinstance(value, Static) else Static({0: value})
            full = [_zero(kind)] * dim
            for index, element in elements.items():
                if not 0 <= index < dim:
                    raise ConvertError('%s.%s[%d]: v2 has only %d of these' % (where, name, index, dim))
                full[index] = convert_value(kind, element, '%s.%s[%d]' % (where, name, index), notes)
            out[name] = full
        else:
            if isinstance(value, Static):
                raise ConvertError('%s.%s: the file has several of these, v2 has one' % (where, name))
            out[name] = convert_value(kind, value, '%s.%s' % (where, name), notes)
    return out


def convert(props):
    """(the v2 data as {field: value}, Notes) from the Props of a KH3 SQEX_BonamikAsset."""
    notes = Notes()
    if 'm_VersionNo' not in props:
        if any(n in props for n in ('mBodies', 'mGroups', 'mSceneManager')):
            raise ConvertError('this is a Bonamik 3.x asset (mBodies/mGroups), not a 2.x one like KH3\'s')
        raise ConvertError('this SQEX_BonamikAsset has no m_VersionNo: it is not a Bonamik 2.x asset')
    spec = convert_struct('SQEX_BonamikAsset_v2', props, 'v2', notes)
    if 'm_SceneManager' not in spec:
        spec['m_SceneManager'] = {}
    return spec, notes


def check(spec):
    """(errors, warnings) about the converted data itself: ids, ranges and the precomputed counts."""
    errors, warnings = [], []
    version = spec.get('m_VersionNo', 0)
    if not 2000 <= version < 3000:
        errors.append('it is a Bonamik %d asset; only 2.x (2000-2999) data goes into v2' % version)
    elif version != REBIRTH_VERSION:
        warnings.append('it is Bonamik %d data; Rebirth\'s own v2 Bonamiks are %d' % (version, REBIRTH_VERSION))
    bodies = spec.get('m_Bodies', [])
    links = spec.get('m_Links', [])
    solvers = spec.get('m_Solvers', [])
    n = len(bodies)
    if not bodies:
        errors.append('it has no bodies')
    for i, b in enumerate(bodies):
        if b.get('m_Index', i) != i:
            warnings.append('body %d says it is body %d' % (i, b.get('m_Index')))
        if not b.get('m_JointName'):
            errors.append('body %d has no bone' % i)
        for key in ('m_ParentId', 'm_ChildId'):
            if not -1 <= b.get(key, -1) < n:
                errors.append('body %d (%s): %s %d is not a body' % (i, b.get('m_JointName'), key, b.get(key)))
        if solvers and b.get('m_GroupId', 0) >= len(solvers):
            warnings.append('body %d (%s) is in group %d of %d' % (i, b.get('m_JointName'), b.get('m_GroupId'), len(solvers)))
    for i, l in enumerate(links):
        for key, name_key in (('m_ParentId', 'm_ParentBodyName'), ('m_ChildId', 'm_ChildBodyName')):
            body = l.get(key, 0)
            if not 0 <= body < n:
                errors.append('link %d: %s %d is not a body' % (i, key, body))
            elif l.get(name_key) and bodies[body].get('m_JointName') != l.get(name_key):
                warnings.append('link %d: %s is %s but body %d is on %s' % (i, name_key, l.get(name_key), body,
                                                                             bodies[body].get('m_JointName')))
    for i, p in enumerate(spec.get('m_Planes', [])):
        for key in ('m_ParticleA', 'm_ParticleB', 'm_ParticleC'):
            if not -1 <= p.get(key, -1) < n:
                errors.append('plane %d: %s %d is not a body' % (i, key, p.get(key)))
    for i, p in enumerate(spec.get('m_Possessions', [])):
        if not -1 <= p.get('m_BodyId', -1) < n:
            errors.append('possession %d: body %d is not a body' % (i, p.get('m_BodyId')))
    for i, s in enumerate(spec.get('m_ShapeMatchings', [])):
        count = s.get('m_TotalParticle', 0)
        ids = s.get('m_ParticleIds', [])
        if not 0 <= count <= len(ids) or any(not 0 <= x < n for x in ids[:count]):
            errors.append('shape matching %d lists bodies that are not there' % i)
    for i, s in enumerate(solvers):
        if s.get('m_GroupId', i) != i:
            warnings.append('group %d (%s) says it is group %d' % (i, s.get('m_GroupName'), s.get('m_GroupId')))
    scene = spec.get('m_SceneManager', {})
    if solvers and scene.get('m_TotalGroup', len(solvers)) != len(solvers):
        warnings.append('the scene says %d groups, there are %d' % (scene.get('m_TotalGroup'), len(solvers)))
    for total, batches, label in (('m_TotalCones', 'm_TotalConesInBatch', 'cones'),
                                  ('m_TotalCollisions', 'm_TotalCollisionsInBatch', 'collisions'),
                                  ('m_TotalSelfCollisions', 'm_TotalSelfCollisionsInBatch', 'self collisions')):
        if batches in scene or total in spec:
            listed = sum(scene.get(batches, [0]))
            if listed != spec.get(total, 0):
                warnings.append('%d %s, but the batches hold %d' % (spec.get(total, 0), label, listed))
    cones = sum(1 for l in links if l.get('m_EnableCone'))
    if 'm_TotalCones' in spec and cones != spec['m_TotalCones']:
        warnings.append('%d links have cones, the count says %d' % (cones, spec['m_TotalCones']))
    return errors, warnings


def bones_used(spec):
    """Every bone name the bodies are on, in body order, once each."""
    seen, out = set(), []
    for b in spec.get('m_Bodies', []):
        name = b.get('m_JointName', '')
        if name and name not in seen:
            seen.add(name)
            out.append(name)
    return out


def to_json(value):
    if isinstance(value, Enum):
        return value.entry
    if isinstance(value, (Vec, Quat)):
        return list(value)
    if isinstance(value, dict):
        return dict((k, to_json(v)) for k, v in value.items())
    if isinstance(value, list):
        return [to_json(v) for v in value]
    return value


def summary(spec):
    return dict(version=spec.get('m_VersionNo'), groups=len(spec.get('m_Solvers', [])), bodies=len(spec.get('m_Bodies', [])),
                links=len(spec.get('m_Links', [])), planes=len(spec.get('m_Planes', [])),
                shape_matchings=len(spec.get('m_ShapeMatchings', [])), possessions=len(spec.get('m_Possessions', [])),
                group_lods=len(spec.get('m_BonamikGroupLODs', [])), bones=len(bones_used(spec)))


def load_file(path):
    """(asset name, v2 data, notes, errors, warnings) for a KH3 Bonamik file, without the editor."""
    name, props = read_kh3_bonamik(path)
    spec, notes = convert(props)
    errors, warnings = check(spec)
    return name, spec, notes, errors, warnings


# ---------------------------------------------------------------------------------------------------------------------
# Editor part
# ---------------------------------------------------------------------------------------------------------------------

def _log(text):
    if unreal is not None:
        unreal.log('[%s] %s' % (TOOL, text.replace('\n', ' | ')))


def _saved_dir():
    saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
    path = os.path.join(saved, 'RebirthFx', 'KH3Bonamik')
    if not os.path.isdir(path):
        os.makedirs(path)
    return path


def _in_commandlet():
    try:
        return '-run=' in unreal.SystemLibrary.get_command_line().lower()
    except Exception:
        return False


def _message(text, title=TOOL):
    _log(text)
    if _in_commandlet():
        return
    try:
        unreal.EditorDialog.show_message(title, text, unreal.AppMsgType.OK)
    except Exception:
        pass


def _ask(text, title=TOOL):
    """True for Yes. (Yes without asking when there is no one to ask.)"""
    if _in_commandlet():
        return True
    answer = unreal.EditorDialog.show_message(title, text, unreal.AppMsgType.YES_NO)
    return answer == unreal.AppReturnType.YES


def _entry_suffix(enum, value):
    """'Inverse_Sphere' for ESQEX_Bonamik_CollisionShape_v2_Inverse_Sphere: the entry without the enum's prefix."""
    entries = V2_ENUMS[enum]
    prefix = os.path.commonprefix(entries)
    prefix = prefix[:prefix.rfind('_') + 1]
    return entries[value][len(prefix):]


def _ue_enum(value):
    cls = getattr(unreal, value.enum[1:], None) or getattr(unreal, value.enum, None)
    if cls is None:
        raise RuntimeError('the enum %s is not in Python here: is the Bonamik plugin enabled in this project?' % value.enum)
    entry = cls.cast(value.value)
    want = _entry_suffix(value.enum, value.value).replace('_', '').upper()
    got = str(getattr(entry, 'name', entry)).replace('_', '').upper()
    if not got.endswith(want):
        raise RuntimeError('%s %d is %s in this editor, expected %s' % (value.enum, value.value, got, value.entry))
    return entry


def _to_ue(kind, value):
    if isinstance(kind, tuple) and kind[0] == 'struct':
        return _make_struct(kind[1], value)
    if isinstance(kind, tuple) and kind[0] == 'array':
        return [_to_ue(kind[1], v) for v in value]
    if isinstance(value, Enum):
        return _ue_enum(value)
    if isinstance(value, Quat):
        return unreal.Quat(*value)
    if isinstance(value, Vec):
        return unreal.Vector(*value)
    if isinstance(value, list):
        return [_to_ue(kind, v) for v in value]
    return value


def _make_struct(type_name, fields):
    s = getattr(unreal, type_name, None)
    if s is None:
        raise RuntimeError('%s is not in Python here: is the Bonamik plugin enabled in this project?' % type_name)
    s = s()
    kinds = V2_FIELDS[type_name]
    for name, value in fields.items():
        s.set_editor_property(name, _to_ue(kinds[name][0], value))
    return s


def _same(kind, expected, actual):
    if isinstance(kind, tuple) and kind[0] == 'struct':
        return not _diff_struct(kind[1], expected, actual)
    if isinstance(kind, tuple) and kind[0] == 'array':
        actual = list(actual)
        return len(actual) == len(expected) and all(_same(kind[1], e, a) for e, a in zip(expected, actual))
    if isinstance(expected, list):
        actual = list(actual)
        return len(actual) == len(expected) and all(_same(kind, e, a) for e, a in zip(expected, actual))
    if isinstance(expected, Enum):
        return actual is not None and int(getattr(actual, 'value', actual)) == expected.value
    if isinstance(expected, Quat):
        return all(_float32(e) == _float32(a) for e, a in zip(expected, (actual.x, actual.y, actual.z, actual.w)))
    if isinstance(expected, Vec):
        return all(_float32(e) == _float32(a) for e, a in zip(expected, (actual.x, actual.y, actual.z)))
    if isinstance(expected, bool):
        return bool(actual) == expected
    if isinstance(expected, float):
        return _float32(actual) == _float32(expected)
    if isinstance(expected, int):
        return int(actual) == expected
    return str(actual) == str(expected)


def _diff_struct(type_name, fields, struct_value, where='', limit=20):
    out = []
    kinds = V2_FIELDS[type_name]
    for name, value in fields.items():
        actual = struct_value.get_editor_property(name)
        if not _same(kinds[name][0], value, actual):
            out.append('%s.%s' % (where, name))
            if len(out) >= limit:
                break
    return out


def mesh_bones(mesh, offsets=None):
    """(bone names, {bone name: parent bone name}) of a skeletal mesh, read through a temporary component.
    With a dict for offsets, it also gets {bone name: (x, y, z)}: each bone's reference-pose offset from its parent."""
    component = unreal.new_object(unreal.SkeletalMeshComponent)
    component.set_skeletal_mesh(mesh)
    count = component.get_num_bones()
    names = [str(component.get_bone_name(i)) for i in range(count)]
    if offsets is not None:
        try:
            for i, n in enumerate(names):
                p = component.get_ref_pose_position(i)
                offsets[n] = (p.x, p.y, p.z)
        except Exception:
            offsets.clear()
    return names, dict((n, str(component.get_parent_bone(n))) for n in names)


def _off_axis_bones(pairs, offsets):
    """Of the (parent, child) bone pairs, the children that do not sit along their parent's X axis.
    KH3's (and Rebirth's) skeletons run every bone down X; Bonamik's collision offsets and cone limits are in those axes."""
    checked, off = 0, []
    for parent, child in pairs:
        v = offsets.get(child)
        if v is None:
            continue
        length = (v[0] * v[0] + v[1] * v[1] + v[2] * v[2]) ** 0.5
        if length < 0.5:
            continue
        checked += 1
        if abs(v[0]) < 0.9 * length:
            off.append(child)
    return checked, off


def check_bones(spec, mesh, report):
    """Every body's bone has to be in the mesh. Bone names match without case, as Unreal's names do (the KH3 root
    'Trans' is the bone 'trans' of a KH3 skeleton). Returns the scene root bone to use."""
    offsets = {}
    try:
        names, parents = mesh_bones(mesh, offsets)
    except Exception as error:
        raise RuntimeError('could not read the bones of %s: %s' % (mesh.get_path_name(), error))
    if not names:
        raise RuntimeError('%s has no bones' % mesh.get_path_name())
    report['mesh_bones'] = len(names)
    by_lower = dict((n.lower(), n) for n in names)
    used = bones_used(spec)
    missing = [b for b in used if b.lower() not in by_lower]
    if missing:
        raise RuntimeError('%s is missing %d of the %d bones this Bonamik uses: %s%s\n(Is it the KH3 character\'s own '
                           'mesh, imported with its KH3 skeleton?)' % (
                               mesh.get_name(), len(missing), len(used), ', '.join(missing[:25]),
                               ' ...' if len(missing) > 25 else ''))
    case = ['%s/%s' % (b, by_lower[b.lower()]) for b in used if by_lower[b.lower()] != b]
    if case:
        report['notes_mesh'] = ('%d bone name%s differ%s from the KH3 ones only in upper/lower case (%s); Unreal matches '
                                'bone names without case, so that works' % (len(case), '' if len(case) == 1 else 's',
                                                                           's' if len(case) == 1 else '', ', '.join(case[:5])))
    # a chain whose bones hang differently in this mesh still runs, but swings differently: say so
    bodies = spec.get('m_Bodies', [])
    odd, pairs = [], []
    for l in spec.get('m_Links', []):
        if l.get('m_LinkType') != Enum('ESQEX_Bonamik_LinkType_v2', 1):
            continue
        parent_bone = by_lower[bodies[l['m_ParentId']]['m_JointName'].lower()]
        child_bone = by_lower[bodies[l['m_ChildId']]['m_JointName'].lower()]
        if parent_bone == child_bone:
            continue
        if parents.get(child_bone) == parent_bone:
            pairs.append((parent_bone, child_bone))
        bone, steps = child_bone, 0
        while bone in parents and bone != parent_bone and steps < 512:
            bone, steps = parents[bone], steps + 1
        if bone != parent_bone:
            odd.append('%s-%s' % (parent_bone, child_bone))
    if odd:
        report['warnings'].append('%d parent-child links join bones that are not parent and child in this mesh '
                                  '(first: %s): those chains may hang differently than in KH3' % (len(odd), ', '.join(odd[:5])))
    checked, off = _off_axis_bones(sorted(set(pairs)), offsets)
    report['bones_along_x'] = '%d of %d' % (checked - len(off), checked)
    if checked >= 4 and len(off) > 0.2 * checked:
        report['warnings'].append('%d of the %d chain bones checked do not run along their parent\'s X axis the way KH3\'s '
                                  'do (first: %s). Was the mesh re-exported with other bone axes (Blender does that)? Bonamik\'s '
                                  'collision offsets and cone limits are in the KH3 bone axes, so the cloth may sit or swing '
                                  'wrong: import the mesh with its original KH3 skeleton' % (len(off), checked, ', '.join(off[:5])))
    root = spec.get('m_SceneManager', {}).get('m_RootName', '')
    if root and root.lower() not in by_lower:
        mesh_root = next((n for n in names if parents.get(n) in ('None', '', None)), names[0])
        report['warnings'].append('the KH3 root bone %s is not in the mesh; %s (the mesh\'s root) is used' % (root, mesh_root))
        return mesh_root
    return root


def _clear_v2(v2):
    """Every v2 field back to its default, so a rebuilt asset keeps nothing of what it had."""
    for name, kind, dim in V2_TYPES['SQEX_BonamikAsset_v2']:
        if kind == 'object':
            v2.set_editor_property(name, None)
        elif isinstance(kind, tuple) and kind[0] == 'struct':
            v2.set_editor_property(name, getattr(unreal, kind[1])())
        elif isinstance(kind, tuple) and kind[0] == 'array':
            v2.set_editor_property(name, [])
        else:
            v2.set_editor_property(name, _to_ue(kind, _zero(kind)))


LEGACY_FIELDS = ('mBodies', 'mGroups', 'mLinks', 'mCones', 'mShapes', 'm_Bodies', 'm_Solvers', 'm_Links', 'm_Planes')


def _legacy_data(asset):
    used = []
    for name in LEGACY_FIELDS:
        try:
            if len(asset.get_editor_property(name) or []):
                used.append(name)
        except Exception:
            pass
    return used


def _asset_for(folder, name, replace, report):
    path = folder + '/' + name
    library = unreal.EditorAssetLibrary
    if library.does_asset_exist(path):
        asset = library.load_asset(path)
        if not isinstance(asset, unreal.SQEX_BonamikAsset):
            raise RuntimeError('%s already exists and is a %s, not a Bonamik' % (path, type(asset).__name__))
        legacy = _legacy_data(asset)
        if legacy:
            raise RuntimeError('%s already exists with Bonamik data of its own (%s); it was left as it is. Rename or move '
                               'it, then convert again' % (path, ', '.join(legacy)))
        if not replace:
            raise RuntimeError('%s already exists (not replaced)' % path)
        report['asset_action'] = 'replaced'
        return asset
    factory = unreal.DataAssetFactory()
    try:
        factory.set_editor_property('data_asset_class', unreal.SQEX_BonamikAsset.static_class())
    except Exception:
        pass
    asset = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.SQEX_BonamikAsset, factory)
    if asset is None:
        raise RuntimeError('could not create ' + path)
    report['asset_action'] = 'created'
    return asset


def _v2_object(asset):
    v2 = asset.get_editor_property('v2')
    if v2 is not None and v2.get_outer() == asset:
        return v2
    existing = unreal.find_object(asset, V2_OBJECT_NAME)
    if isinstance(existing, unreal.SQEX_BonamikAsset_v2):
        return existing
    if existing is None:
        return unreal.new_object(unreal.SQEX_BonamikAsset_v2, asset, V2_OBJECT_NAME)
    return unreal.new_object(unreal.SQEX_BonamikAsset_v2, asset)


def fill_asset(asset, spec):
    v2 = _v2_object(asset)
    _clear_v2(v2)
    for name, kind, dim in V2_TYPES['SQEX_BonamikAsset_v2']:
        if name in spec:
            v2.set_editor_property(name, _to_ue(kind, spec[name]))
    asset.set_editor_property('m_VersionNo', spec['m_VersionNo'])
    asset.set_editor_property('v2', v2)
    return v2


def verify_asset(asset, spec):
    """What did not come back as written (empty when everything did)."""
    problems = []
    v2 = asset.get_editor_property('v2')
    if v2 is None:
        return ['the asset has no v2 object']
    if v2.get_outer() != asset:
        problems.append('the v2 object does not live inside the asset')
    if int(asset.get_editor_property('m_VersionNo')) != spec['m_VersionNo']:
        problems.append('the asset\'s m_VersionNo')
    for name, kind, dim in V2_TYPES['SQEX_BonamikAsset_v2']:
        if name not in spec:
            continue
        actual = v2.get_editor_property(name)
        expected = spec[name]
        if isinstance(kind, tuple) and kind[0] == 'struct':
            problems += _diff_struct(kind[1], expected, actual, name)
        elif isinstance(kind, tuple) and kind[0] == 'array' and isinstance(kind[1], tuple) and kind[1][0] == 'struct':
            actual = list(actual)
            if len(actual) != len(expected):
                problems.append('%s has %d entries, not %d' % (name, len(actual), len(expected)))
                continue
            for i, (e, a) in enumerate(zip(expected, actual)):
                problems += _diff_struct(kind[1][1], e, a, '%s[%d]' % (name, i))
                if len(problems) > 40:
                    return problems
        elif not _same(kind, expected, actual):
            problems.append(name)
    return problems


def attach_to_mesh(mesh, asset):
    """Puts the asset in the mesh's SQEX_KBD_AssetUserData > Bonamik Data List (adds one when the mesh has none)."""
    user_data = [d for d in (mesh.get_editor_property('asset_user_data') or [])]
    kbd = None
    for data in user_data:
        if data is not None and isinstance(data, unreal.SQEX_KBD_AssetUserData):
            kbd = data
            break
    if kbd is None:
        kbd = unreal.new_object(unreal.SQEX_KBD_AssetUserData, mesh)
        kbd.set_editor_property('BonamikDataList', [asset])
        mesh.set_editor_property('asset_user_data', user_data + [kbd])
        return 'added with a new SQEX_KBD_AssetUserData', [asset.get_name()]
    current = [d for d in (kbd.get_editor_property('BonamikDataList') or [])]
    names = [d.get_name() for d in current if d is not None]
    if any(d is not None and d.get_path_name() == asset.get_path_name() for d in current):
        return 'already listed', names
    kbd.set_editor_property('BonamikDataList', current + [asset])
    return 'added', names + [asset.get_name()]


MESH_ACTION_TEXT = {
    'added with a new SQEX_KBD_AssetUserData': 'now lists it in its Bonamik Data List (in a new SQEX_KBD_AssetUserData)',
    'added': 'now lists it in its Bonamik Data List',
    'already listed': 'already listed it in its Bonamik Data List',
}


def _listed_on(mesh, asset):
    for data in mesh.get_editor_property('asset_user_data') or []:
        if data is not None and isinstance(data, unreal.SQEX_KBD_AssetUserData):
            for d in data.get_editor_property('BonamikDataList') or []:
                if d is not None and d.get_path_name() == asset.get_path_name():
                    return True
    return False


def _load_mesh(mesh):
    if mesh is None or isinstance(mesh, unreal.SkeletalMesh):
        return mesh
    loaded = unreal.EditorAssetLibrary.load_asset(str(mesh))
    if not isinstance(loaded, unreal.SkeletalMesh):
        raise RuntimeError('%s is not a skeletal mesh' % mesh)
    return loaded


def _package_path(obj):
    return obj.get_outermost().get_name() if hasattr(obj, 'get_outermost') else obj.get_path_name().split('.')[0]


def convert_file(path, mesh=None, folder=None, name=None, replace=True, attach=True, save=True):
    """Converts one KH3 Bonamik file into a v2 Bonamik asset. Returns the report (report['ok'] says if it worked).

    mesh:   a SkeletalMesh or its path: its bones are checked, the asset goes next to it and into its Bonamik Data List
    folder: where the asset goes (default: the mesh's folder, or /Game/KH3Bonamik without a mesh)
    name:   the asset's name (default: the KH3 asset's name)"""
    report = dict(ok=False, tool=TOOL, source=os.path.abspath(path), time=time.strftime('%Y-%m-%d %H:%M:%S'),
                  warnings=[], notes=[], saved=[])
    try:
        kh3_name, props = read_kh3_bonamik(path)
        report['kh3_asset'] = kh3_name
        spec, notes = convert(props)
        errors, warnings = check(spec)
        report['notes'] = notes.lines()
        report['warnings'] += warnings
        report['counts'] = summary(spec)
        if errors:
            raise ConvertError('the KH3 data does not hold together: ' + '; '.join(errors[:8]))
        mesh = _load_mesh(mesh)
        if mesh is not None:
            report['mesh'] = _package_path(mesh)
            root = check_bones(spec, mesh, report)
            if report.get('notes_mesh'):
                report['notes'].append(report.pop('notes_mesh'))
            if root != spec['m_SceneManager'].get('m_RootName', root):
                spec['m_SceneManager']['m_RootName'] = root
        else:
            report['warnings'].append('no mesh given: the bones were not checked and nothing lists the new asset yet')
        folder = (folder or (_package_path(mesh).rsplit('/', 1)[0] if mesh is not None else DEFAULT_FOLDER)).rstrip('/')
        name = name or kh3_name
        report['asset'] = folder + '/' + name
        asset = _asset_for(folder, name, replace, report)
        fill_asset(asset, spec)
        problems = verify_asset(asset, spec)
        if problems:
            report['problems'] = problems
            raise RuntimeError('%d values did not come back as written (first: %s)' % (len(problems), problems[0]))
        if mesh is not None and attach:
            report['mesh_action'], report['mesh_bonamiks'] = attach_to_mesh(mesh, asset)
            if not _listed_on(mesh, asset):
                raise RuntimeError('the mesh does not list the asset after adding it')
            if len(report['mesh_bonamiks']) > 1:
                report['warnings'].append('the mesh now lists %d Bonamiks (%s): if two of them move the same bones, '
                                          'keep only one' % (len(report['mesh_bonamiks']), ', '.join(report['mesh_bonamiks'])))
        if save:
            if not unreal.EditorAssetLibrary.save_loaded_asset(asset, False):
                raise RuntimeError('could not save ' + report['asset'])
            report['saved'].append(report['asset'])
            if mesh is not None and attach and report.get('mesh_action') != 'already listed':
                if not unreal.EditorAssetLibrary.save_loaded_asset(mesh, False):
                    raise RuntimeError('could not save ' + report['mesh'])
                report['saved'].append(report['mesh'])
        report['ok'] = True
        try:
            with open(os.path.join(_saved_dir(), name + '.v2.json'), 'w') as f:
                json.dump(to_json(spec), f, indent=1)
        except Exception:
            pass
    except ConvertError as error:
        report['error'] = str(error)
    except Exception as error:
        report['error'] = str(error)
        report['traceback'] = traceback.format_exc()
    try:
        out = os.path.join(_saved_dir(), (report.get('kh3_asset') or os.path.splitext(os.path.basename(path))[0]) + '.report.json')
        with open(out, 'w') as f:
            json.dump(report, f, indent=1)
        report['report_file'] = out
    except Exception:
        pass
    _log(('OK ' if report['ok'] else 'FAILED ') + json.dumps(dict((k, report.get(k)) for k in ('asset', 'counts', 'error'))))
    return report


def report_text(report):
    base = os.path.basename(report['source'])
    if not report['ok']:
        return '%s: not converted.\n%s' % (base, report.get('error', '?'))
    c = report.get('counts', {})
    lines = ['%s -> %s (%s)' % (base, report['asset'], report.get('asset_action', '?')),
             '%d bodies on %d bones, %d links, %d planes, %d groups (Bonamik %s)' % (
                 c.get('bodies', 0), c.get('bones', 0), c.get('links', 0), c.get('planes', 0), c.get('groups', 0),
                 c.get('version'))]
    if report.get('mesh'):
        action = report.get('mesh_action')
        lines.append('%s has all %d bones%s' % (
            report['mesh'].rsplit('/', 1)[-1], c.get('bones', 0),
            ' and ' + MESH_ACTION_TEXT.get(action, action) if action else ' (its Asset User Data was not changed)'))
    if report.get('saved'):
        lines.append('Saved: ' + ', '.join(p.rsplit('/', 1)[-1] for p in report['saved']))
    for w in report.get('warnings', []):
        lines.append('Note: ' + w)
    for n in report.get('notes', []):
        lines.append('Note: ' + n)
    return '\n'.join(lines)


# ---------------------------------------------------------------------------------------------------------------------
# Menu
# ---------------------------------------------------------------------------------------------------------------------

def _pick_files(title, start_dir=None):
    """The Windows file dialog, for one or more .uasset files. [] when cancelled."""
    import ctypes
    from ctypes import wintypes

    class OPENFILENAMEW(ctypes.Structure):
        _fields_ = [('lStructSize', wintypes.DWORD), ('hwndOwner', wintypes.HWND), ('hInstance', wintypes.HINSTANCE),
                    ('lpstrFilter', ctypes.c_void_p), ('lpstrCustomFilter', ctypes.c_void_p),
                    ('nMaxCustFilter', wintypes.DWORD), ('nFilterIndex', wintypes.DWORD), ('lpstrFile', ctypes.c_void_p),
                    ('nMaxFile', wintypes.DWORD), ('lpstrFileTitle', ctypes.c_void_p), ('nMaxFileTitle', wintypes.DWORD),
                    ('lpstrInitialDir', wintypes.LPCWSTR), ('lpstrTitle', wintypes.LPCWSTR), ('Flags', wintypes.DWORD),
                    ('nFileOffset', wintypes.WORD), ('nFileExtension', wintypes.WORD), ('lpstrDefExt', wintypes.LPCWSTR),
                    ('lCustData', wintypes.LPARAM), ('lpfnHook', ctypes.c_void_p), ('lpTemplateName', wintypes.LPCWSTR),
                    ('pvReserved', ctypes.c_void_p), ('dwReserved', wintypes.DWORD), ('FlagsEx', wintypes.DWORD)]

    filter_text = ctypes.create_unicode_buffer('KH3 Bonamik (*_Bonamik.uasset)\0*_Bonamik.uasset\0'
                                               'Unreal packages (*.uasset)\0*.uasset\0All files\0*.*\0\0')
    size = 1 << 16
    buffer = ctypes.create_unicode_buffer(size)
    user32, comdlg32 = ctypes.windll.user32, ctypes.windll.comdlg32
    user32.GetForegroundWindow.restype = wintypes.HWND
    comdlg32.GetOpenFileNameW.argtypes = [ctypes.POINTER(OPENFILENAMEW)]
    comdlg32.GetOpenFileNameW.restype = wintypes.BOOL
    comdlg32.CommDlgExtendedError.restype = wintypes.DWORD
    ofn = OPENFILENAMEW()
    ofn.lStructSize = ctypes.sizeof(OPENFILENAMEW)
    ofn.hwndOwner = user32.GetForegroundWindow()
    ofn.lpstrFilter = ctypes.cast(filter_text, ctypes.c_void_p).value
    ofn.nFilterIndex = 1
    ofn.lpstrFile = ctypes.cast(buffer, ctypes.c_void_p).value
    ofn.nMaxFile = size
    ofn.lpstrInitialDir = start_dir if start_dir and os.path.isdir(start_dir) else None
    ofn.lpstrTitle = title
    ofn.Flags = 0x00080000 | 0x00001000 | 0x00000800 | 0x00000200 | 0x00000008  # explorer, must exist, multi, no chdir
    if not comdlg32.GetOpenFileNameW(ctypes.byref(ofn)):
        code = comdlg32.CommDlgExtendedError()
        if code:
            raise RuntimeError('the file dialog failed (error 0x%x)' % code)
        return []
    raw = ctypes.wstring_at(ctypes.addressof(buffer), size)
    parts = []
    for part in raw.split('\0'):
        if not part:
            break
        parts.append(part)
    if len(parts) == 1:
        return parts
    return [os.path.join(parts[0], p) for p in parts[1:]]


def _last_dir_file():
    return os.path.join(_saved_dir(), 'last_folder.txt')


def _selected_meshes():
    try:
        assets = unreal.EditorUtilityLibrary.get_selected_assets()
    except Exception:
        return []
    return [a for a in assets if isinstance(a, unreal.SkeletalMesh)]


def menu():
    """Rebirth FX > KH3 Bonamik To Bonamik v2..."""
    try:
        meshes = _selected_meshes()
        if len(meshes) > 1:
            _message('%d skeletal meshes are selected. Select only the one the KH3 Bonamik is for, then run this again.' % len(meshes))
            return None
        mesh = meshes[0] if meshes else None
        if mesh is None and not _ask(
                'No skeletal mesh is selected in the Content Browser.\n\n'
                'Select the KH3 character\'s mesh first: the Bonamik then goes next to it, its bones are checked and it is '
                'added to the mesh\'s Bonamik Data List.\n\n'
                'Yes: convert anyway, into %s, without a mesh (add it to a mesh\'s Asset User Data yourself).\n'
                'No: stop.' % DEFAULT_FOLDER):
            return None
        start = None
        try:
            with open(_last_dir_file()) as f:
                start = f.read().strip()
        except Exception:
            pass
        try:
            files = _pick_files('Pick the KH3 Bonamik (.uasset; its .uexp has to be next to it)', start)
        except Exception as error:
            _message('The file dialog could not open (%s).\n\nFrom the Python console:\n'
                     'import rebirth_fx.kh3bonamik as k; k.convert_file(r"C:\\path\\p_ex011_Bonamik.uasset", mesh="/Game/...")' % error)
            return None
        if not files:
            return None
        try:
            with open(_last_dir_file(), 'w') as f:
                f.write(os.path.dirname(files[0]))
        except Exception:
            pass
        reports = []
        folder = _package_path(mesh).rsplit('/', 1)[0] if mesh is not None else DEFAULT_FOLDER
        for path in files:
            try:
                kh3_name = read_kh3_bonamik(path)[0]
            except Exception:
                kh3_name = None
            replace = True
            if kh3_name and unreal.EditorAssetLibrary.does_asset_exist(folder + '/' + kh3_name):
                replace = _ask('%s/%s already exists.\n\nReplace its Bonamik data with the converted %s?' % (
                    folder, kh3_name, os.path.basename(path)))
            if not replace:
                continue
            reports.append(convert_file(path, mesh=mesh, folder=folder, replace=True))
        if not reports:
            return None
        text = '\n\n'.join(report_text(r) for r in reports)
        if any(r['ok'] for r in reports):
            text += '\n\nThe editor\'s Bonamik preview shows 3.x data only: test the cloth and hair in game.'
            try:
                unreal.EditorAssetLibrary.sync_browser_to_objects([r['asset'] for r in reports if r['ok']])
            except Exception:
                pass
        _message(text)
        return reports
    except Exception:
        _message('The conversion failed:\n' + traceback.format_exc())
        return None


def add_menu_entries(menu_object, section='Tools'):
    """The Rebirth FX menu entry, plus one on skeletal meshes' right-click menu in the Content Browser."""
    entry = unreal.ToolMenuEntry(name='RebirthKH3Bonamik', type=unreal.MultiBlockType.MENU_ENTRY)
    entry.set_label('KH3 Bonamik To Bonamik v2...')
    entry.set_tool_tip('Turns a KINGDOM HEARTS III Bonamik (.uasset + .uexp) into a Rebirth v2 Bonamik for the skeletal '
                       'mesh selected in the Content Browser')
    entry.set_string_command(unreal.ToolMenuStringCommandType.PYTHON, '', 'import rebirth_fx.kh3bonamik as k; k.menu()')
    menu_object.add_menu_entry(section, entry)
    try:
        context = unreal.ToolMenus.get().extend_menu('ContentBrowser.AssetContextMenu.SkeletalMesh')
        entry = unreal.ToolMenuEntry(name='RebirthKH3BonamikMesh', type=unreal.MultiBlockType.MENU_ENTRY)
        entry.set_label('Add KH3 Bonamik...')
        entry.set_tool_tip('Converts a KINGDOM HEARTS III Bonamik (.uasset + .uexp) into a Rebirth v2 Bonamik for this mesh')
        entry.set_string_command(unreal.ToolMenuStringCommandType.PYTHON, '', 'import rebirth_fx.kh3bonamik as k; k.menu()')
        context.add_menu_entry('GetAssetActions', entry)
    except Exception:
        _log('the skeletal mesh right-click entry was not added: ' + traceback.format_exc())


# ---------------------------------------------------------------------------------------------------------------------
# Without the editor: python kh3bonamik.py <file.uasset> [out.json]
# ---------------------------------------------------------------------------------------------------------------------

def _main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    try:
        name, spec, notes, errors, warnings = load_file(argv[1])
    except ConvertError as error:
        print('not converted: %s' % error)
        return 1
    print('%s: %s' % (name, json.dumps(summary(spec))))
    for line in notes.lines() + warnings:
        print('  note: ' + line)
    for line in errors:
        print('  ERROR: ' + line)
    print('  bones: ' + ', '.join(bones_used(spec)))
    if len(argv) > 2:
        with open(argv[2], 'w') as f:
            json.dump(to_json(spec), f, indent=1)
        print('wrote ' + argv[2])
    return 1 if errors else 0


if __name__ == '__main__':
    if unreal is None:
        sys.exit(_main(sys.argv))
    menu()   # File > Execute Python Script... on this file does what the menu entry does
