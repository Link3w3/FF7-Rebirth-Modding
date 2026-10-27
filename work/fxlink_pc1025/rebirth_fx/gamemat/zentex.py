"""A texture the End editor cooked (legacy .uasset with its export inline, + .ubulk) as the game's IoStore holds one:
a zen package (FPackageSummary, name map + hashes, import map, export map, one export bundle, no graph arcs) with the
export data unchanged except the streamed mips' bulk data headers, and the .ubulk as the package's BulkData chunk.

What changes from the legacy file, as the game's own textures have it (checked on PC0010_00_Eye_C):
  - imports: /Script objects and packages by their script hash (FPackageObjectIndex type 1), /Game packages null
  - the export's class / template: those imports; its global import index: the hash of its path (type 2)
  - CookedHeaderSize = the legacy header size, the export's CookedSerialOffset its legacy offset (offsets written
    inside the export data, such as the platform data's skip offset and inline mips' offsets, stay valid)
  - streamed mips (BULKDATA_PayloadInSeperateFile): their offset in the .ubulk made absolute (the legacy file counts it
    from BulkDataStartOffset) and BULKDATA_NoOffsetFixUp set
  - package flags: PKG_Cooked added
"""
import struct

from ..cityhash import CityHash64
from .. import matcore

PACKAGE_TAG = 0x9E2A83C1
PKG_COOKED = 0x200
PKG_FILTER_EDITOR_ONLY = 0x80000000
BULKDATA_PAYLOAD_AT_END = 0x1
BULKDATA_FORCE_INLINE = 0x40
BULKDATA_SEPARATE_FILE = 0x100
BULKDATA_SIZE64 = 0x2000
BULKDATA_NO_OFFSET_FIXUP = 0x10000
NULL = 0xFFFFFFFFFFFFFFFF
NAME_HASH_VERSION = 0xC1640000


class R(object):
    def __init__(self, d, p=0):
        self.d, self.p = d, p

    def u(self, fmt):
        v = struct.unpack_from('<' + fmt, self.d, self.p)
        self.p += struct.calcsize('<' + fmt)
        return v if len(v) > 1 else v[0]

    def fstring(self):
        n = self.u('i')
        if n == 0:
            return ''
        if n < 0:
            s = self.d[self.p:self.p - 2 * n].decode('utf-16-le').rstrip('\0')
            self.p += -2 * n
            return s
        s = self.d[self.p:self.p + n].decode('latin1').rstrip('\0')
        self.p += n
        return s


class Legacy(object):
    """The parts of a cooked 4.26 legacy package this conversion needs (unversioned, file version -7)."""

    def __init__(self, data):
        self.data = data
        r = R(data)
        if r.u('I') != PACKAGE_TAG:
            raise ValueError('not a package')
        self.legacy = r.u('i')
        if self.legacy != -7:
            raise ValueError('legacy file version %d (expected -7)' % self.legacy)
        r.u('i')                                # legacy UE3 version
        self.ue4, self.licensee = r.u('i'), r.u('i')
        if self.ue4 != 0:
            raise ValueError('a versioned package (UE4 %d): the editor cooks unversioned ones' % self.ue4)
        n = r.u('i')
        r.p += 20 * n                           # custom versions (guid + version)
        self.total_header_size = r.u('i')
        r.fstring()                             # folder name
        self.flags = r.u('I')
        if not self.flags & PKG_FILTER_EDITOR_ONLY:
            raise ValueError('not a cooked package (editor data kept)')
        self.name_count, self.name_offset = r.u('i'), r.u('i')
        r.u('i'), r.u('i')                      # gatherable text data
        self.export_count, self.export_offset = r.u('i'), r.u('i')
        self.import_count, self.import_offset = r.u('i'), r.u('i')
        self.depends_offset = r.u('i')
        r.u('i'), r.u('i')                      # soft package references
        r.u('i')                                # searchable names
        r.u('i')                                # thumbnail table
        r.p += 16                               # guid
        n = r.u('i')
        r.p += 8 * n                            # generations
        for _ in range(2):                      # saved by / compatible with engine version
            r.u('HHHI')
            r.fstring()
        r.u('I')                                # compression flags
        if r.u('i') != 0:
            raise ValueError('compressed chunks')
        r.u('I')                                # package source
        for _ in range(r.u('i')):
            r.fstring()                         # additional packages to cook
        self.asset_registry_offset = r.u('i')
        self.bulk_data_start_offset = r.u('q')
        r.u('i')                                # world tile info
        for _ in range(r.u('i')):
            r.u('i')                            # chunk ids
        self.preload_count, self.preload_offset = r.u('i'), r.u('i')
        # names (FString + two 16-bit hashes)
        r.p = self.name_offset
        self.names = []
        for _ in range(self.name_count):
            self.names.append(r.fstring())
            r.p += 4
        # imports
        r.p = self.import_offset
        self.imports = []
        for _ in range(self.import_count):
            cp, cpn, cn, cnn = r.u('iiii')
            outer = r.u('i')
            nm, nn = r.u('ii')
            self.imports.append(dict(class_package=self.names[cp], class_name=self.names[cn], outer=outer,
                                     name=self._name(nm, nn)))
        # exports
        r.p = self.export_offset
        self.exports = []
        for _ in range(self.export_count):
            cls, sup, tmpl, outer = r.u('iiii')
            nm, nn = r.u('ii')
            oflags = r.u('I')
            size, offset = r.u('qq')
            forced, not_client, not_server = r.u('iii')
            r.p += 16                           # package guid
            pflags = r.u('I')
            not_always, is_asset = r.u('ii')
            r.p += 20                           # preload dependencies
            self.exports.append(dict(cls=cls, sup=sup, template=tmpl, outer=outer, name=self._name(nm, nn), name_index=nm,
                                     name_number=nn, flags=oflags, size=size, offset=offset))
        self.package_name = self.names[0] if self.names[0].startswith('/') else None
        for n in self.names:
            if n.startswith('/Game/'):
                self.package_name = n
                break

    def _name(self, index, number):
        s = self.names[index]
        return s if number == 0 else '%s_%d' % (s, number - 1)

    def import_path(self, i):
        """Object path of import i ('/Script/Engine.Texture2D', '/Script/Engine')."""
        parts = []
        k = i
        while True:
            imp = self.imports[k]
            parts.append(imp['name'])
            if imp['outer'] == 0:
                break
            k = -imp['outer'] - 1
        parts.reverse()
        if len(parts) == 1:
            return parts[0]
        return parts[0] + '.' + parts[1] + ''.join(':' + p for p in parts[2:])


def script_hash(object_path):
    """FPackageObjectIndex of a /Script object or package (type 1)."""
    s = ''.join('/' if ch in '.:' else ch.lower() for ch in object_path)
    return (1 << 62) | (CityHash64(s.encode('utf-16-le')) & ~(3 << 62))


def zen_import(legacy, i):
    path = legacy.import_path(i)
    if path.startswith('/Script/'):
        return script_hash(path)
    if legacy.imports[i]['outer'] == 0:
        return NULL                             # a /Game package
    return matcore.import_hash(path)


def zen_index(legacy, imports, index):
    if index == 0:
        return NULL
    if index < 0:
        return imports[-index - 1]
    return index - 1                            # an export of this package (type 0)


def _mapped(names, s):
    if '_' in s and s not in names:
        base, _, num = s.rpartition('_')
        if num.isdigit() and base in names:
            return names.index(base) | ((int(num) + 1) << 32)
    return names.index(s)


def fix_bulk_headers(export, legacy, export_offset):
    """The export data with every streamed mip's bulk data offset absolute in the .ubulk and BULKDATA_NoOffsetFixUp set.
    Finds the texture platform data (FName of the pixel format, then its skip offset to the closing None) and walks
    the mips; returns (bytes, [(mip, flags, size, offset in .ubulk or inline)])."""
    out = bytearray(export)
    pf = [k for k, n in enumerate(legacy.names) if n.startswith('PF_')]
    none = legacy.names.index('None')
    starts = []
    for k in pf:
        pat = struct.pack('<ii', k, 0)
        p = out.find(pat)
        while p >= 0:
            skip = struct.unpack_from('<q', out, p + 8)[0] - export_offset
            if 0 < skip <= len(out) - 8 and struct.unpack_from('<ii', out, skip) == (none, 0):
                starts.append(p)
            p = out.find(pat, p + 1)
    if len(starts) != 1:
        raise ValueError('the texture platform data was not found (%d candidates)' % len(starts))
    r = R(out, starts[0] + 16)
    sx, sy, packed = r.u('iiI')
    fmt = r.fstring()
    if packed & (1 << 30):
        r.u('ii')                               # opt data: ext data, num mips in tail
    first, nmips = r.u('ii')
    mips = []
    for m in range(nmips):
        cooked = r.u('i')
        at = r.p
        flags = r.u('I')
        if flags & BULKDATA_SIZE64:
            count, size = r.u('qq')
        else:
            count, size = r.u('ii')
        off_at = r.p
        offset = r.u('q')
        if flags & BULKDATA_FORCE_INLINE or not flags & BULKDATA_SEPARATE_FILE:
            r.p += size
            mips.append((m, flags, size, 'inline'))
        else:
            if not flags & BULKDATA_NO_OFFSET_FIXUP:
                offset += legacy.bulk_data_start_offset
                struct.pack_into('<I', out, at, flags | BULKDATA_NO_OFFSET_FIXUP)
                struct.pack_into('<q', out, off_at, offset)
            mips.append((m, flags | BULKDATA_NO_OFFSET_FIXUP, size, offset))
        r.u('iii')                              # mip size x, y, z
    return bytes(out), dict(size=(sx, sy), format=fmt, first_mip=first, mips=mips)


def convert(uasset, ubulk=b''):
    """(zen package bytes, bulk chunk bytes, report) of an editor-cooked legacy texture package."""
    lg = Legacy(uasset)
    if lg.export_count != 1:
        raise ValueError('%d exports: only single-export packages convert here' % lg.export_count)
    names = list(lg.names)
    imports = [zen_import(lg, i) for i in range(lg.import_count)]
    e = lg.exports[0]
    export = uasset[e['offset']:e['offset'] + e['size']]
    export, info = fix_bulk_headers(export, lg, e['offset'])
    for m, flags, size, off in info['mips']:
        if off != 'inline' and off + size > len(ubulk):
            raise ValueError('mip %d (%d bytes at %d) is past the end of the .ubulk (%d bytes)' % (m, size, off, len(ubulk)))
    package = lg.package_name
    short = package.rsplit('/', 1)[-1]
    gimp = matcore.import_hash(package + '.' + e['name']) if e['flags'] & 1 else NULL
    # name map + hashes
    nb = bytearray()
    for s in names:
        h, b, wide = matcore._encode_name(s)
        nb += h
        if wide and (64 + len(nb)) & 1:
            nb.append(0)
        nb += b
    nm_off, nm_size = 64, len(nb)
    pad = (8 - (nm_off + nm_size) % 8) % 8
    nh_off = nm_off + nm_size + pad
    hashes = struct.pack('<Q', NAME_HASH_VERSION) + b''.join(struct.pack('<Q', matcore._name_hash(s)) for s in names)
    imp = b''.join(struct.pack('<Q', x) for x in imports)
    exp = struct.pack('<QQIIQQQQQIB3x', e['offset'], e['size'], e['name_index'], e['name_number'],
                      zen_index(lg, imports, e['outer']), zen_index(lg, imports, e['cls']), zen_index(lg, imports, e['sup']),
                      zen_index(lg, imports, e['template']), gimp, e['flags'], 0)
    assert len(exp) == 72
    bundles = struct.pack('<II', 0, 2) + struct.pack('<IIII', 0, 0, 0, 1)
    graph = struct.pack('<i', 0)
    imp_off = nh_off + len(hashes)
    exp_off = imp_off + len(imp)
    eb_off = exp_off + len(exp)
    graph_off = eb_off + len(bundles)
    summary = struct.pack('<QQIIiiiiiiiiii', _mapped(names, package), _mapped(names, package), lg.flags | PKG_COOKED,
                          lg.total_header_size, nm_off, nm_size, nh_off, len(hashes), imp_off, exp_off, eb_off, graph_off,
                          len(graph), 0)
    zen = summary + bytes(nb) + b'\0' * pad + hashes + imp + exp + bundles + graph + export
    info.update(package=package, imports=[lg.import_path(i) for i in range(lg.import_count)], header_size=lg.total_header_size,
                bulk_data_start_offset=lg.bulk_data_start_offset, export_size=e['size'])
    return zen, ubulk, info
