"""Tagged (versioned) property streams of a cooked UE 4.26 package, read into uprops.V values as the unversioned reader
reads them. The game's own packages are unversioned; the mods its modding community cooks (the Parts Builder's skins,
the editable AnimBlueprints of editor 1.19) are versioned: each property a tag (name, type, size, array index, and the
struct / enum / inner types), enum values by name, an array of structs led by its inner struct's tag."""
import struct
import uprops
from uprops import V, ParseError
from usmap import PropType

PKG_UNVERSIONED = 0x00002000


def members(u, sname):
    out = {}
    s = u.structs.get(sname)
    seen = 0
    while s is not None and seen < 64:
        seen += 1
        for p in s.props:
            out.setdefault(p.name, p)
        s = u.structs.get(s.super) if s.super else None
    return out


class TaggedReader(uprops.Reader):
    def tag(self):
        name = self.name()
        if name == 'None':
            return None
        t = dict(name=name, type=self.name(), size=self.i32(), index=self.i32())
        ty = t['type']
        if ty == 'StructProperty':
            t['struct'] = self.name()
            t['guid'] = self.raw(16)
        elif ty == 'BoolProperty':
            t['bool'] = self.u8()
        elif ty in ('ByteProperty', 'EnumProperty'):
            t['enum'] = self.name()
        elif ty in ('ArrayProperty', 'SetProperty'):
            t['inner'] = self.name()
        elif ty == 'MapProperty':
            t['inner'] = self.name()
            t['value'] = self.name()
        if self.u8():
            t['prop_guid'] = self.raw(16)
        return t

    def props(self, sname):
        start = self.p
        self.trace.append(sname)
        try:
            mem = members(self.u, sname)
            out = {}
            while True:
                t = self.tag()
                if t is None:
                    break
                at = self.p
                end = at + t['size']
                p = mem.get(t['name'])
                self.trace.append(t['name'])
                try:
                    v = self.tagged_value(t, p.ptype if p is not None else None)
                except ParseError as e:
                    v = V('native', 'unread:' + t['type'], at, t['size'], str(e))
                    self.p = end
                finally:
                    self.trace.pop()
                if self.p != end and t['type'] != 'BoolProperty':
                    v = V('native', 'misread:' + t['type'], at, t['size'], 'read %d of %d bytes' % (self.p - at, t['size']))
                    self.p = end
                dim = p.array_dim if p is not None else 1
                key = t['name'] if dim == 1 and t['index'] == 0 else '%s[%d]' % (t['name'], t['index'])
                out[key] = v
            return V('struct', sname, start, self.p - start, out)
        finally:
            self.trace.pop()

    def inner_tag_follows(self, t):
        """Whether an array's inner struct tag comes next (its name is the array's, its type StructProperty)."""
        at = self.p
        try:
            return self.name() == t['name'] and self.name() == 'StructProperty'
        except ParseError:
            return False
        finally:
            self.p = at

    def elem(self, pt):
        """A container's element: a struct as its tagged stream (no tag of its own), an enum by name, a bool as a byte."""
        at = self.p
        ty = pt.type
        if ty == 'StructProperty':
            return self.struct(pt.struct)
        if ty == 'EnumProperty' or (ty == 'ByteProperty' and pt.enum):
            return V('enum', pt.enum, at, 8, self.name())
        if ty == 'BoolProperty':
            return V('prim', ty, at, 1, bool(self.u8()))
        return uprops.Reader.value(self, pt)

    def tagged_value(self, t, pt):
        ty = t['type']
        at = self.p
        if ty == 'BoolProperty':
            return V('prim', ty, at, 0, bool(t.get('bool')))
        if ty == 'StructProperty':
            return self.struct(t['struct'])
        if ty == 'EnumProperty' or (ty == 'ByteProperty' and t.get('enum') not in (None, 'None')):
            return V('enum', t.get('enum'), at, 8, self.name())
        if ty == 'ArrayProperty':
            n = self.i32()
            if n < 0 or n > 1 << 22:
                raise ParseError('bad array count %d at %d' % (n, at))
            if t['inner'] == 'StructProperty':
                # (the inner struct's tag: written for an empty array too)
                inner_tag = self.tag() if n > 0 or self.inner_tag_follows(t) else None
                sname = inner_tag['struct'] if inner_tag else (pt.inner.struct if pt is not None and pt.inner is not None else None)
                items = [self.struct(sname) for _ in range(n)]
                return V('array', 'Struct<%s>' % sname, at, self.p - at, items)
            ipt = pt.inner if pt is not None and pt.inner is not None else PropType(t['inner'])
            items = [self.elem(ipt) for _ in range(n)]
            return V('array', repr(ipt), at, self.p - at, items)
        if ty == 'SetProperty':
            ipt = pt.inner if pt is not None and pt.inner is not None else PropType(t['inner'])
            removed = self.i32()
            for _ in range(removed):
                self.elem(ipt)
            n = self.i32()
            items = [self.elem(ipt) for _ in range(n)]
            return V('set', repr(ipt), at, self.p - at, items)
        if ty == 'MapProperty':
            kpt = pt.inner if pt is not None and pt.inner is not None else PropType(t['inner'])
            vpt = pt.value if pt is not None and pt.value is not None else PropType(t['value'])
            removed = self.i32()
            for _ in range(removed):
                self.elem(kpt)
            n = self.i32()
            if n < 0 or n > 1 << 20:
                raise ParseError('bad map count %d at %d' % (n, at))
            items = [(self.elem(kpt), self.elem(vpt)) for _ in range(n)]
            return V('map', '%r,%r' % (kpt, vpt), at, self.p - at, items)
        return uprops.Reader.value(self, pt if pt is not None and pt.type == ty else PropType(ty))


def is_versioned(z):
    return not (z.flags & PKG_UNVERSIONED)


def read_export(u, z, i, script_paths):
    """As uprops.read_export, for a versioned package."""
    cls = uprops.class_of(z, i, script_paths)
    data = z.export_bytes(i)
    r = TaggedReader(u, z.names, data, 0, len(data))
    v = r.props(cls)
    return cls, v, r.p, data
