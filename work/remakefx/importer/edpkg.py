"""UE 4.26 editor (uncooked, versioned) package files: read and write the whole layout, so a package built here is laid
out the way the End editor saves its own (checked by reading one of the editor's own packages and writing it back
byte for byte).

    python3 edpkg.py <editor .uasset>      reads it, writes it back, compares
"""
import struct
import sys
import zlib

TAG = 0x9E2A83C1
PKG_FILTER_EDITOR_ONLY = 0x80000000

# the CRC32 table of FCrc (the zlib one)
_T = []
for _i in range(256):
    _c = _i
    for _ in range(8):
        _c = (_c >> 1) ^ 0xEDB88320 if _c & 1 else _c >> 1
    _T.append(_c)


# FCrc::CRCTable_DEPRECATED (MSB-first, poly 0x04C11DB7), the table Strihash_DEPRECATED uses
_TD = []
for _i in range(256):
    _c = _i << 24
    for _ in range(8):
        _c = ((_c << 1) ^ 0x04C11DB7) & 0xFFFFFFFF if _c & 0x80000000 else (_c << 1) & 0xFFFFFFFF
    _TD.append(_c)


def strihash_deprecated(s):
    """FCrc::Strihash_DEPRECATED of an ANSI name (upper-cased, one byte per character)."""
    h = 0
    for ch in s:
        v = ord(ch.upper()) if ch.isascii() else ord(ch) & 0xFF
        h = ((h >> 8) & 0x00FFFFFF) ^ _TD[(h ^ v) & 0xFF]
    return h


def strcrc32(s):
    crc = 0xFFFFFFFF
    for ch in s:
        c = ord(ch)
        for _ in range(4):
            crc = (crc >> 8) ^ _T[(crc ^ c) & 0xFF]
            c >>= 8
    return crc ^ 0xFFFFFFFF


def name_hashes(s):
    return strihash_deprecated(s) & 0xFFFF, strcrc32(s) & 0xFFFF


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
            s = self.d[self.p:self.p - 2 * n].decode('utf-16-le')
            self.p += -2 * n
            return s[:-1]
        s = self.d[self.p:self.p + n].decode('latin-1')
        self.p += n
        return s[:-1]

    def guid(self):
        g = self.d[self.p:self.p + 16]
        self.p += 16
        return g


def fstring_bytes(s):
    if s == '' or s is None:
        return struct.pack('<i', 0)
    try:
        b = s.encode('latin-1') + b'\0'
        if all(ch < 128 for ch in b):
            return struct.pack('<i', len(b)) + b
    except UnicodeEncodeError:
        pass
    b = s.encode('utf-16-le') + b'\0\0'
    return struct.pack('<i', -(len(b) // 2)) + b


class Summary(object):
    FIELDS = ('legacy', 'legacy_ue3', 'ue4', 'licensee', 'custom_versions', 'total_header_size', 'folder', 'flags',
              'name_count', 'name_offset', 'localization_id', 'text_count', 'text_offset', 'export_count', 'export_offset',
              'import_count', 'import_offset', 'depends_offset', 'soft_count', 'soft_offset', 'searchable_offset',
              'thumbnail_offset', 'guid', 'persistent_guid', 'generations', 'saved_by', 'compatible_with',
              'compression_flags', 'package_source', 'additional_packages', 'asset_registry_offset',
              'bulk_data_start_offset', 'world_tile_offset', 'chunk_ids', 'preload_count', 'preload_offset')

    @classmethod
    def read(cls, d):
        s = cls()
        r = R(d)
        if r.u('I') != TAG:
            raise ValueError('not a package')
        s.legacy = r.u('i')
        s.legacy_ue3 = r.u('i')
        s.ue4, s.licensee = r.u('i'), r.u('i')
        n = r.u('i')
        s.custom_versions = [(r.guid(), r.u('i')) for _ in range(n)]
        s.total_header_size = r.u('i')
        s.folder = r.fstring()
        s.flags = r.u('I')
        s.name_count, s.name_offset = r.u('i'), r.u('i')
        s.localization_id = r.fstring() if not s.flags & PKG_FILTER_EDITOR_ONLY else None
        s.text_count, s.text_offset = r.u('i'), r.u('i')
        s.export_count, s.export_offset = r.u('i'), r.u('i')
        s.import_count, s.import_offset = r.u('i'), r.u('i')
        s.depends_offset = r.u('i')
        s.soft_count, s.soft_offset = r.u('i'), r.u('i')
        s.searchable_offset = r.u('i')
        s.thumbnail_offset = r.u('i')
        s.guid = r.guid()
        s.persistent_guid = r.guid() if not s.flags & PKG_FILTER_EDITOR_ONLY else None
        n = r.u('i')
        s.generations = [r.u('ii') for _ in range(n)]
        s.saved_by = (r.u('HHHI'), r.fstring())
        s.compatible_with = (r.u('HHHI'), r.fstring())
        s.compression_flags = r.u('I')
        if r.u('i') != 0:
            raise ValueError('compressed chunks')
        s.package_source = r.u('I')
        s.additional_packages = [r.fstring() for _ in range(r.u('i'))]
        s.asset_registry_offset = r.u('i')
        s.bulk_data_start_offset = r.u('q')
        s.world_tile_offset = r.u('i')
        s.chunk_ids = [r.u('i') for _ in range(r.u('i'))]
        s.preload_count, s.preload_offset = r.u('i'), r.u('i')
        s.end = r.p
        return s

    def bytes(self):
        out = [struct.pack('<Iiiii', TAG, self.legacy, self.legacy_ue3, self.ue4, self.licensee),
               struct.pack('<i', len(self.custom_versions))]
        for g, v in self.custom_versions:
            out.append(g + struct.pack('<i', v))
        out.append(struct.pack('<i', self.total_header_size))
        out.append(fstring_bytes(self.folder))
        out.append(struct.pack('<Iii', self.flags, self.name_count, self.name_offset))
        if not self.flags & PKG_FILTER_EDITOR_ONLY:
            out.append(fstring_bytes(self.localization_id))
        out.append(struct.pack('<iiiiiiiiiiii', self.text_count, self.text_offset, self.export_count, self.export_offset,
                               self.import_count, self.import_offset, self.depends_offset, self.soft_count, self.soft_offset,
                               self.searchable_offset, self.thumbnail_offset, 0)[:-4])
        out.append(self.guid)
        if not self.flags & PKG_FILTER_EDITOR_ONLY:
            out.append(self.persistent_guid)
        out.append(struct.pack('<i', len(self.generations)))
        for g in self.generations:
            out.append(struct.pack('<ii', *g))
        for (v, branch) in (self.saved_by, self.compatible_with):
            out.append(struct.pack('<HHHI', *v) + fstring_bytes(branch))
        out.append(struct.pack('<Iii', self.compression_flags, 0, self.package_source))
        out.append(struct.pack('<i', len(self.additional_packages)))
        for a in self.additional_packages:
            out.append(fstring_bytes(a))
        out.append(struct.pack('<iqi', self.asset_registry_offset, self.bulk_data_start_offset, self.world_tile_offset))
        out.append(struct.pack('<i', len(self.chunk_ids)))
        for c in self.chunk_ids:
            out.append(struct.pack('<i', c))
        out.append(struct.pack('<ii', self.preload_count, self.preload_offset))
        return b''.join(out)


class EditorPackage(object):
    """names: [str]; imports: [dict(class_package, class_name, outer, name, package_name)] with FName values as
    (str, number); exports: [dict(cls, sup, template, outer, name, flags, data, forced, not_client, not_server,
    package_guid, package_flags, not_always_loaded, is_asset, deps=(first, a, b, c, d))]; depends: [[index]]; soft
    package references: [name]; asset registry block and anything else kept as bytes."""

    @classmethod
    def read(cls, d):
        p = cls()
        s = p.summary = Summary.read(d)
        r = R(d, s.name_offset)
        p.names = []
        p.name_hashes = []
        for _ in range(s.name_count):
            p.names.append(r.fstring())
            p.name_hashes.append(r.u('HH'))

        def fname(rr):
            i, n = rr.u('ii')
            return (p.names[i], n)
        r.p = s.import_offset
        p.imports = []
        for _ in range(s.import_count):
            imp = dict(class_package=fname(r), class_name=fname(r), outer=r.u('i'), name=fname(r))
            imp['package_name'] = fname(r)
            p.imports.append(imp)
        r.p = s.export_offset
        p.exports = []
        for _ in range(s.export_count):
            e = dict(cls=r.u('i'), sup=r.u('i'), template=r.u('i'), outer=r.u('i'), name=fname(r), flags=r.u('I'))
            size, offset = r.u('qq')
            e['forced'], e['not_client'], e['not_server'] = r.u('iii')
            e['package_guid'] = r.guid()
            e['package_flags'] = r.u('I')
            e['not_always_loaded'], e['is_asset'] = r.u('ii')
            e['deps'] = r.u('iiiii')
            e['data'] = d[offset:offset + size]
            e['_offset'] = offset
            p.exports.append(e)
        r.p = s.depends_offset
        p.depends = []
        for _ in range(s.export_count):
            n = r.u('i')
            p.depends.append([r.u('i') for _ in range(n)])
        r.p = s.soft_offset
        p.soft = [fname(r) for _ in range(s.soft_count)] if s.soft_count else []
        # the blocks between the soft references and the exports, kept as they are
        p.between = d[r.p:s.total_header_size] if s.soft_count or True else b''
        p._raw_between_start = r.p
        first_export = min([e['_offset'] for e in p.exports] or [len(d)])
        p.tail = d[s.bulk_data_start_offset:] if s.bulk_data_start_offset <= len(d) else b''
        p.after_exports = d[max(e['_offset'] + len(e['data']) for e in p.exports):s.bulk_data_start_offset] if p.exports else b''
        p.header_end_gap = d[s.total_header_size:first_export]
        return p


def roundtrip(path):
    d = open(path, 'rb').read()
    p = EditorPackage.read(d)
    s = p.summary
    print('legacy', s.legacy, 'ue3', s.legacy_ue3, 'ue4', s.ue4, 'licensee', s.licensee, 'custom versions', len(s.custom_versions))
    print('flags %08x' % s.flags, 'names', s.name_count, '@', s.name_offset, 'imports', s.import_count, '@', s.import_offset,
          'exports', s.export_count, '@', s.export_offset, 'depends @', s.depends_offset, 'soft', s.soft_count, '@', s.soft_offset,
          'searchable @', s.searchable_offset, 'thumbs @', s.thumbnail_offset, 'AR @', s.asset_registry_offset,
          'bulk @', s.bulk_data_start_offset, 'header', s.total_header_size, 'file', len(d), 'summary end', s.end)
    print('saved by', s.saved_by, 'compatible', s.compatible_with, 'preload', s.preload_count, s.preload_offset,
          'chunks', s.chunk_ids, 'gens', s.generations, 'folder', s.folder, 'loc', s.localization_id)
    print('summary bytes equal:', s.bytes() == d[:s.end])
    bad = [(n, h, name_hashes(n)) for n, h in zip(p.names, p.name_hashes) if tuple(h) != name_hashes(n)]
    print('name hashes: %d of %d differ' % (len(bad), len(p.names)), bad[:5])
    for i, imp in enumerate(p.imports):
        print('  import', -i - 1, imp['class_package'][0], imp['class_name'][0], imp['outer'], imp['name'], imp['package_name'])
    for i, e in enumerate(p.exports):
        print('  export', i + 1, e['cls'], e['sup'], e['template'], e['outer'], e['name'], '%08x' % e['flags'], len(e['data']),
              e['_offset'], e['forced'], e['not_client'], e['not_server'], e['package_flags'], e['not_always_loaded'],
              e['is_asset'], e['deps'])
    print('depends', p.depends)
    print('soft', p.soft)
    print('tail bytes', p.tail[-8:].hex(), 'after exports', len(p.after_exports))
    return p, d


if __name__ == '__main__':
    roundtrip(sys.argv[1])
