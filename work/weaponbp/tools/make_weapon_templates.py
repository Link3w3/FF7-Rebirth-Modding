"""The weapon Blueprint templates of Create a Character System (editor 1.20): every weapon blueprint of the game
(/Game/BluePrint/Character/Weapon/*, cooked) read with the game's usmap and written as one JSON file, each one flattened
through its parent blueprints (the game's weapon blueprints are data only: a native parent class, the class defaults,
the mesh component's settings and, for a few, components of their own).

The editor's Weapon Blueprint Maker makes a real Blueprint from one: its parent class the template's native class (the
End project's EndWeaponSkeletalMeshActor ...), every property the game's blueprint sets put on the new one's class
defaults and components as text (FProperty::ImportText), the mesh component's mesh the user's model.

    make_weapon_templates.py <dir of BluePrint__Character__Weapon__*.uasset> <out templates.json>

Each template: key (the blueprint's name), package, label, character, parent (the native class), chain (the game's
blueprints it is made of, base first), mesh (the game's model, for reference), defaults (class default object:
[{property, text}]), subobjects ({name: {class, properties}}: the native class's components, SkeletalMeshComponent0
first), components ([{name, class, parent, parent_native, socket, properties}]: the blueprint's own), refs (the game's
objects its values name), notes."""
import json, os, re, struct, sys
sys.path[:0] = ['/work/fx1018/tools', '/work/iostore', '/work/cs', '/work/weap1012/tools',
                '/work/swap1012/tools', '/work/weaponbp/tools', '/work/cacsabp/tools']
import fxlib, uprops
import wbpread

U = fxlib.usmap()
INT_TYPES = ('Int8Property', 'Int16Property', 'IntProperty', 'Int64Property', 'UInt16Property', 'UInt32Property', 'UInt64Property')
# properties that are the blueprint's structure, not settings (the editor makes them itself)
STRUCTURAL = {'SkeletalMeshComponent', 'RootComponent', 'Mesh', 'CapsuleComponent', 'CharacterMovement', 'AttachParent',
              'UCSSerializationIndex', 'bNetAddressable', 'CreationMethod', 'UCSModifiedProperties'}
PLAYERS = ['WE0000_00', 'WE0001_00', 'WE0002_00', 'WE0003_00', 'WE0004_00', 'WE0005_00', 'WE0007_00', 'WE0011_00',
           'WE1021_00', 'WE1021_10', 'WE1021_01', 'WE1021_02']


def prop_of(sname, key):
    """The usmap Prop called key in struct/class sname (or a super)."""
    name = re.sub(r'\[\d+\]$', '', key)
    s = U.structs.get(sname)
    while s is not None:
        for p in s.props:
            if p.name == name:
                return p
        s = U.structs.get(s.super) if s.super else None
    return None


def float_text(f):
    for digits in range(0, 10):
        t = '%.*f' % (digits, f)
        if struct.unpack('<f', struct.pack('<f', float(t)))[0] == struct.unpack('<f', struct.pack('<f', f))[0]:
            return t if '.' in t else t + '.0'
    return '%.9g' % f


def quote(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


NATIVE_FIELDS = {'Vector': 'XYZ', 'Vector2D': 'XY', 'Vector4': 'XYZW', 'Quat': 'XYZW', 'LinearColor': 'RGBA',
                 'IntPoint': 'XY', 'IntVector': 'XYZ', 'Rotator': ('Pitch', 'Yaw', 'Roll')}


class Text:
    """Decoded values as UE text (what ExportText writes and ImportText reads)."""

    def __init__(self, bp):
        self.bp = bp
        self.refs, self.notes = set(), []

    def zero(self, pt):
        t = pt.type
        if t == 'BoolProperty':
            return 'False'
        if t in INT_TYPES or t == 'ByteProperty' and not pt.enum:
            return '0'
        if t == 'ByteProperty' or t == 'EnumProperty':
            names = U.enums.get(pt.enum) or []
            return names[0] if names else '0'
        if t in ('FloatProperty', 'DoubleProperty'):
            return '0.0'
        if t == 'NameProperty':
            return 'None'
        if t in ('StrProperty', 'TextProperty'):
            return '""'
        if t in ('ObjectProperty', 'ClassProperty', 'WeakObjectProperty', 'SoftObjectProperty', 'SoftClassProperty', 'InterfaceProperty'):
            return 'None'
        if t == 'ArrayProperty':
            return None
        if t in ('SetProperty', 'MapProperty'):
            return '()'
        if t == 'StructProperty':
            return self.zero_struct(pt.struct)
        return None

    def zero_struct(self, sname):
        if sname in NATIVE_FIELDS:
            f = NATIVE_FIELDS[sname]
            return '(' + ','.join('%s=%s' % (k, '0' if sname in ('IntPoint', 'IntVector') else '0.0') for k in f) + ')'
        s = U.structs.get(sname)
        parts = []
        while s is not None:
            for p in s.props:
                z = self.zero(p.ptype)
                if z is not None:
                    parts.append('%s=%s' % (p.name, z))
            s = U.structs.get(s.super) if s.super else None
        return '(' + ','.join(parts) + ')'

    def native(self, sname, v):
        if sname in NATIVE_FIELDS:
            f = NATIVE_FIELDS[sname]
            vals = v.value
            if sname in ('IntPoint', 'IntVector'):
                return '(' + ','.join('%s=%d' % (k, x) for k, x in zip(f, vals)) + ')'
            return '(' + ','.join('%s=%s' % (k, float_text(x)) for k, x in zip(f, vals)) + ')'
        if sname == 'Color':
            b, g, r, a = v.value
            return '(B=%d,G=%d,R=%d,A=%d)' % (b, g, r, a)
        if sname == 'Transform':
            x = v.value
            return '(Rotation=(X=%s,Y=%s,Z=%s,W=%s),Translation=(X=%s,Y=%s,Z=%s),Scale3D=(X=%s,Y=%s,Z=%s))' % tuple(float_text(c) for c in x)
        if sname == 'Guid':
            return None
        if sname == 'SoftObjectPath' and isinstance(v.value, (tuple, list)):
            return quote(self.soft(v.value))
        if sname == 'PerPlatformFloat' and isinstance(v.value, dict) and 'Default' in v.value:
            return '(Default=%s)' % float_text(v.value['Default'])
        self.notes.append('a %s value is not written (it has no text form here)' % sname)
        return None

    def soft(self, value):
        n, sub = value
        path = n if not sub else n + ':' + sub
        if path and path != 'None':
            self.refs.add(path)
        return path

    def value(self, v, pt, top=False):
        """v as text; None to leave it out. top: the property itself (not a struct member or an array element): a name or
        a string then goes without quotes (the editor's ImportText of one on its own takes every character, quotes too),
        and an empty array is left out everywhere (its "()" makes one empty element in this editor)."""
        t = pt.type
        if t in ('ArrayProperty', 'SetProperty') and (v.zero or not v.value):
            return None if t == 'ArrayProperty' else '()'
        if top and t in ('NameProperty', 'StrProperty', 'Utf8StrProperty', 'AnsiStrProperty'):
            return 'None' if v.zero and t == 'NameProperty' else ('' if v.zero else str(v.value))
        if v.zero:
            return self.zero(pt)
        if t == 'BoolProperty':
            return 'True' if v.value else 'False'
        if t == 'ByteProperty':
            names = U.enums.get(pt.enum) if pt.enum else None
            if names and isinstance(v.value, int) and v.value < len(names):
                return names[v.value]
            return str(v.value)
        if t in INT_TYPES:
            return str(v.value)
        if t in ('FloatProperty', 'DoubleProperty'):
            return float_text(v.value)
        if t == 'NameProperty':
            return quote(v.value)
        if t in ('StrProperty', 'Utf8StrProperty', 'AnsiStrProperty'):
            return quote(v.value)
        if t == 'EnumProperty':
            return str(v.value).split('::')[-1]
        if t in ('ObjectProperty', 'ClassProperty', 'WeakObjectProperty', 'InterfaceProperty'):
            r = self.bp.ref(v.value)
            if r is None:
                return 'None'
            if r[0] == 'export':
                return ('export', r[1])
            if not r[1].startswith('/'):
                self.notes.append('an object the game names by an unknown id (%s) is left empty' % r[1])
                return 'None'
            self.refs.add(r[1])
            return quote(r[1])
        if t in ('SoftObjectProperty', 'AssetObjectProperty', 'SoftClassProperty'):
            return quote(self.soft(v.value))
        if t == 'StructProperty':
            if v.kind == 'native':
                return self.native(pt.struct, v)
            return self.struct(pt.struct, v)
        if t in ('ArrayProperty', 'SetProperty'):
            items = []
            for x in v.value:
                s = self.value(x, pt.inner)
                if s is None or isinstance(s, tuple):
                    return s if isinstance(s, tuple) else None
                items.append(s)
            return '(' + ','.join(items) + ')'
        if t == 'MapProperty':
            items = []
            for k, x in v.value:
                a, b = self.value(k, pt.inner), self.value(x, pt.value)
                if a is None or b is None or isinstance(a, tuple) or isinstance(b, tuple):
                    return None
                items.append('(%s, %s)' % (a, b))
            return '(' + ','.join(items) + ')'
        self.notes.append('a %s value is not written' % t)
        return None

    def struct(self, sname, v):
        parts = []
        for k, x in v.value.items():
            if k.startswith('@'):
                continue
            p = prop_of(sname, k)
            if p is None:
                self.notes.append('%s.%s: not in the usmap' % (sname, k))
                continue
            s = self.value(x, p.ptype)
            if s is None or isinstance(s, tuple):
                continue
            parts.append('%s=%s' % (k, s))
        return '(' + ','.join(parts) + ')'

    def properties(self, sname, v, skip=()):
        """[(property, text)] of an object's decoded properties (structure and blueprint-internal references left out)."""
        out = []
        for k, x in v.value.items():
            if k.startswith('@') or k in STRUCTURAL or k in skip:
                continue
            p = prop_of(sname, k)
            if p is None:
                self.notes.append('%s: %s is not in the usmap' % (sname, k))
                continue
            s = self.value(x, p.ptype, top=True)
            if s is None:
                continue
            if isinstance(s, tuple):
                continue   # (a reference to one of the blueprint's own objects: made by the editor)
            out.append((k, s))
        return out


def label_of(name):
    m = re.match(r'(WE\d+_\d+)_(.*)$', name)
    if not m:
        return name, ''
    code, rest = m.groups()
    parts = rest.split('_', 1)
    who = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', parts[0])
    what = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', parts[1]) if len(parts) > 1 else ''
    return ('%s: %s (%s)' % (who, what, code)) if what else ('%s (%s)' % (who, code)), who


def read_bp(b):
    """One blueprint's own part: {cdo, subobjects, components, overrides} with decoded values."""
    objs = {i: (name, cpath, outer, v) for i, name, cpath, outer, v, end, size in b.read()}
    cdo_index = [i for i, (name, cpath, outer, v) in objs.items() if name.startswith('Default__')]
    assert len(cdo_index) == 1
    cdo_index = cdo_index[0]
    part = dict(cdo=objs[cdo_index], subobjects={}, components=[], overrides={})
    for i, (name, cpath, outer, v) in objs.items():
        if outer == cdo_index:
            part['subobjects'][name] = (cpath, v)
    # the SCS: its nodes (but the default scene root) with their templates
    for i, (name, cpath, outer, v) in objs.items():
        if not cpath.endswith('.SCS_Node'):
            continue
        var = v.value.get('InternalVariableName')
        var = var.value if var is not None and not var.zero else None
        if var == 'DefaultSceneRoot':
            continue
        tmpl = v.value.get('ComponentTemplate')
        ti = tmpl.value - 1 if tmpl is not None and not tmpl.zero and tmpl.value > 0 else None
        tname, tcpath, touter, tv = objs[ti] if ti is not None else (None, None, None, None)
        def name_of(key):
            x = v.value.get(key)
            return None if x is None or x.zero else x.value
        part['components'].append(dict(name=var, cls=tcpath, template=(tcpath, tv), parent=name_of('ParentComponentOrVariableName'),
                                       parent_native=bool(name_of('bIsParentComponentNative')), socket=name_of('AttachToName')))
    # an InheritableComponentHandler: the parent blueprints' components' templates overridden
    for i, (name, cpath, outer, v) in objs.items():
        if cpath.endswith('.InheritableComponentHandler'):
            recs = v.value.get('Records')
            for rec in (recs.value if recs is not None else []):
                key = rec.value.get('ComponentKey')
                var = key.value.get('SCSVariableName') if key is not None else None
                tmpl = rec.value.get('ComponentTemplate')
                ti = tmpl.value - 1 if tmpl is not None and not tmpl.zero and tmpl.value > 0 else None
                if var is not None and ti is not None:
                    part['overrides'][var.value] = objs[ti][1:4:2] if False else (objs[ti][1], objs[ti][3])
    return part


def merge(base, over):
    """[(property, text)] lists: over's properties replace base's."""
    out = dict(base)
    out.update(dict(over))
    return list(out.items())


def build(folder, out_path):
    bps = wbpread.load_all(folder)
    parts, errors = {}, []
    for pkg, b in bps.items():
        try:
            parts[pkg] = read_bp(b)
        except Exception as ex:
            errors.append('%s: %s' % (pkg, ex))
    templates = []
    for pkg, b in sorted(bps.items()):
        if pkg not in parts:
            continue
        chain = [pkg]
        native = b.parent
        notes = []
        cur = b
        while cur.parent_is_bp:
            pp = cur.parent.rsplit('.', 1)[0]
            if pp not in bps:
                notes.append('its parent blueprint %s is not a weapon blueprint: its settings are not in the template' % pp)
                native = None
                break
            chain.insert(0, pp)
            cur = bps[pp]
            native = cur.parent
        if any(c not in parts for c in chain):
            errors.append('%s: a blueprint of its chain did not read' % pkg)
            continue
        txt = Text(b)
        defaults, subobjects, components, mesh = [], {}, [], None
        for c in chain:
            part = parts[c]
            tb = Text(bps[c])
            name, cpath, outer, v = part['cdo']
            defaults = merge(defaults, tb.properties(cpath.rsplit('.', 1)[-1], v))
            for sname, (scpath, sv) in part['subobjects'].items():
                props = tb.properties(scpath.rsplit('.', 1)[-1], sv, skip=('SkeletalMesh',) if sname == 'SkeletalMeshComponent0' else ())
                if sname == 'SkeletalMeshComponent0':
                    m = sv.value.get('SkeletalMesh')
                    if m is not None and not m.zero:
                        r = bps[c].ref(m.value)
                        if r and r[0] == 'import':
                            mesh = r[1]
                prev = subobjects.get(sname, dict(cls=scpath, properties=[]))
                subobjects[sname] = dict(cls=scpath, properties=merge(prev['properties'], props))
            for comp in part['components']:
                tcpath, tv = comp['template']
                props = tb.properties(tcpath.rsplit('.', 1)[-1], tv) if tv is not None else []
                components.append(dict(name=comp['name'], cls=tcpath, parent=comp['parent'], parent_native=comp['parent_native'],
                                       socket=comp['socket'], properties=props))
            for var, (ocpath, ov) in part['overrides'].items():
                for comp in components:
                    if comp['name'] == var:
                        comp['properties'] = merge(comp['properties'], tb.properties(ocpath.rsplit('.', 1)[-1], ov))
                        break
                else:
                    notes.append('an override of component %s, not in its chain' % var)
            txt.refs |= tb.refs
            notes += [n for n in tb.notes if n not in notes]
        name = pkg.rsplit('/', 1)[-1]
        label, who = label_of(name)
        if native is None or not native.startswith('/Script/'):
            notes.append('no native parent class found')
        order = (PLAYERS.index(name[:9]) if name[:9] in PLAYERS else len(PLAYERS), name)
        templates.append(dict(key=name, package=pkg, label=label, character=who, parent=native, chain=chain, mesh=mesh,
                              defaults=[dict(property=k, text=t) for k, t in defaults],
                              subobjects=[dict(name=n, cls=s['cls'], properties=[dict(property=k, text=t) for k, t in s['properties']])
                                          for n, s in sorted(subobjects.items(), key=lambda kv: (kv[0] != 'SkeletalMeshComponent0', kv[0]))],
                              components=[dict(name=c['name'], cls=c['cls'], parent=c['parent'], parent_native=c['parent_native'],
                                               socket=c['socket'], properties=[dict(property=k, text=t) for k, t in c['properties']])
                                          for c in components],
                              refs=sorted(r for r in txt.refs if r != mesh), notes=notes, _order=order))
    templates.sort(key=lambda t: t.pop('_order'))
    doc = dict(version=1, made_with='make_weapon_templates.py (Create a Character System editor 1.20)',
               about="the game's weapon blueprints (/Game/BluePrint/Character/Weapon), read from your game: not for sharing",
               templates=templates)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    json.dump(doc, open(out_path, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print('%d templates written to %s; %d blueprints did not read' % (len(templates), out_path, len(errors)))
    for e in errors:
        print('  NOT READ:', e)
    return doc


if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2])
