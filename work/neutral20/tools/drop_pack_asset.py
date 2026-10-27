"""Take one asset out of a CharaSpec pack (EndAssetDataAsset, tagged properties): its entry in AssetDataList's
AssetUserData, its import (nulled, as the cooker leaves imports it does not need), and its package in the graph.
    drop(data, object_path) -> (new package bytes, package id taken out of the graph)"""
import struct, sys
sys.path[:0] = ['/work/iostore', '/work/cs', '/work/gunmoves', '/work/evil1013/tools',
                '/work/swap1012/tools', '/work/vincentfix', '/work/weap1012/tools']
from zen import Zen
import tagged
import gameids
import iostore_write as W

NULL = 0xFFFFFFFFFFFFFFFF
_OBJ = None


def object_names():
    global _OBJ
    if _OBJ is None:
        _OBJ = gameids.load()[1]
    return _OBJ


class Tag:
    """One property tag at a position of the export data, with where its size field and value are."""
    def __init__(self, r):
        self.at = r.p
        self.name = r.name()
        if self.name == 'None':
            self.end = r.p
            return
        self.type = r.name()
        self.size_at = r.p
        self.size = r.i32()
        self.index = r.i32()
        self.inner = self.struct = None
        if self.type == 'StructProperty':
            self.struct = r.name(); r.p += 16
        elif self.type == 'BoolProperty':
            r.p += 1
        elif self.type in ('ByteProperty', 'EnumProperty'):
            r.name()
        elif self.type in ('ArrayProperty', 'SetProperty'):
            self.inner = r.name()
        elif self.type == 'MapProperty':
            r.name(); r.name()
        if r.u8():
            r.p += 16
        self.value_at = r.p
        self.end = r.p + self.size


def tags(r, end):
    out = []
    while r.p < end:
        t = Tag(r)
        if t.name == 'None':
            break
        out.append(t)
        r.p = t.end
    return out


def graph_entries(d, z):
    o = z.graph_off
    n = struct.unpack_from('<i', d, o)[0]; o += 4
    out = []
    for _ in range(n):
        pid, na = struct.unpack_from('<Qi', d, o)
        out.append((pid, bytes(d[o:o + 12 + 8 * na]))); o += 12 + 8 * na
    assert o == z.graph_off + z.graph_size
    return out


def drop(data, object_path):
    z = Zen(data)
    assert len(z.exports) == 1
    want = gameids.objhash(object_path) & ~(3 << 62)
    hits = [k for k, v in enumerate(z.imports) if v != NULL and (v & ~(3 << 62)) == want]
    assert len(hits) == 1, ('import of %s' % object_path, hits)
    imp = hits[0]
    ref = -(imp + 1)
    e = bytearray(z.export_data(0))
    assert len(e) == z.exports[0]['serial_size']
    r = tagged.Reader(z, bytes(e))
    top = tags(r, len(e))
    lists = [t for t in top if t.name == 'AssetDataList']
    assert len(lists) == 1 and lists[0].type == 'ArrayProperty' and lists[0].inner == 'StructProperty'
    adl = lists[0]
    r.p = adl.value_at
    count = r.i32()
    inner = Tag(r)                      # the inner tag of a struct array: its size is the size of all elements
    assert inner.type == 'StructProperty', inner.type
    found = []
    for k in range(count):
        for t in tags(r, adl.end):      # one element: tagged properties up to "None"
            if t.name == 'AssetUserData':
                assert t.type == 'ArrayProperty' and t.inner == 'ObjectProperty'
                n = struct.unpack_from('<i', e, t.value_at)[0]
                vals = list(struct.unpack_from('<%di' % n, e, t.value_at + 4))
                assert t.size == 4 + 4 * n
                for j, v in enumerate(vals):
                    if v == ref:
                        found.append((t, j, n))
    assert len(found) == 1, ('entries referring to import %d' % imp, len(found))
    t, j, n = found[0]
    at = t.value_at + 4 + 4 * j
    del e[at:at + 4]
    struct.pack_into('<i', e, t.value_at, n - 1)
    struct.pack_into('<i', e, t.size_at, t.size - 4)
    struct.pack_into('<i', e, inner.size_at, inner.size - 4)
    struct.pack_into('<i', e, adl.size_at, adl.size - 4)
    # the import: nulled; the package: out of the graph (when nothing else of it is imported)
    d = bytearray(data[:z.header_end])
    struct.pack_into('<Q', d, z.imp_off + 8 * imp, NULL)
    pkg = object_path.split('.', 1)[0]
    pid = W.package_id(pkg)
    others = [k for k, v in enumerate(z.imports) if k != imp and v != NULL and v >> 62 == 2 and
              (object_names().get(v & ~(3 << 62)) or '').split('.', 1)[0] == pkg]
    assert not others, others
    g = graph_entries(data, z)
    assert sum(1 for p, _ in g if p == pid) == 1, 'the package is not in the graph once'
    g = [(p, b) for p, b in g if p != pid]
    gb = struct.pack('<i', len(g)) + b''.join(b for _, b in g)
    d[z.graph_off:z.graph_off + z.graph_size] = gb
    # summary: graph size (the graph is the last part of the header)
    # FZenPackageSummary: name_mapped Q, srcname_mapped Q, flags I, cooked_header_size I, then 10 int32 offsets/sizes
    names = ['nm_off', 'nm_size', 'nh_off', 'nh_size', 'imp_off', 'exp_off', 'eb_off', 'graph_off', 'graph_size', 'pad']
    vals = list(struct.unpack_from('<10i', data, 24))
    assert vals[names.index('graph_off')] == z.graph_off and vals[names.index('graph_size')] == z.graph_size
    struct.pack_into('<i', d, 24 + 4 * names.index('graph_size'), len(gb))
    # export serial size
    struct.pack_into('<Q', d, z.exp_off + 8, len(e))
    out = bytes(d) + bytes(e)
    return out, pid, imp
