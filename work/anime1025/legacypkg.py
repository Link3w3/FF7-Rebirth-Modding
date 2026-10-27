"""A UE 4.26 legacy (editor, uncooked) package's summary, name map, imports and exports."""
import struct


class Pkg:
    def __init__(self, d):
        self.d = d
        p = 0
        tag, legacy = struct.unpack_from('<Ii', d, p); p += 8
        assert tag == 0x9E2A83C1
        if legacy != -4:
            p += 4
        self.ue4, self.lic = struct.unpack_from('<ii', d, p); p += 8
        n, = struct.unpack_from('<i', d, p); p += 4
        self.custom = []
        for i in range(n):
            self.custom.append((d[p:p + 16], struct.unpack_from('<i', d, p + 16)[0])); p += 20
        self.total_header, = struct.unpack_from('<i', d, p); p += 4
        self.folder, p = self.fstring(p)
        self.flags, = struct.unpack_from('<I', d, p); p += 4
        self.name_count, self.name_offset = struct.unpack_from('<ii', d, p); p += 8
        if self.ue4 >= 516 and not (self.flags & 0x80000000):
            self.localization_id, p = self.fstring(p)
        self.gather_count, self.gather_offset = struct.unpack_from('<ii', d, p); p += 8
        (self.export_count, self.export_offset, self.import_count, self.import_offset,
         self.depends_offset) = struct.unpack_from('<5i', d, p); p += 20
        self.soft_count, self.soft_offset = struct.unpack_from('<ii', d, p); p += 8
        self.searchable_offset, = struct.unpack_from('<i', d, p); p += 4
        self.thumb_offset, = struct.unpack_from('<i', d, p); p += 4
        self.guid = d[p:p + 16]; p += 16
        if self.ue4 >= 518 and not (self.flags & 0x80000000):
            self.persistent_guid = d[p:p + 16]; p += 16
            if self.ue4 < 520:
                p += 16
        gc, = struct.unpack_from('<i', d, p); p += 4
        p += 8 * gc
        self.saved_by = struct.unpack_from('<HHHI', d, p); p += 10
        self.saved_branch, p = self.fstring(p)
        self.compatible = struct.unpack_from('<HHHI', d, p); p += 10
        self.compatible_branch, p = self.fstring(p)
        self.compression, = struct.unpack_from('<I', d, p); p += 4
        cc, = struct.unpack_from('<i', d, p); p += 4
        assert cc == 0
        self.package_source, = struct.unpack_from('<I', d, p); p += 4
        ac, = struct.unpack_from('<i', d, p); p += 4
        for i in range(ac):
            _, p = self.fstring(p)
        self.asset_registry_offset, = struct.unpack_from('<i', d, p); p += 4
        self.bulk_start, = struct.unpack_from('<q', d, p); p += 8
        self.world_tile_offset, = struct.unpack_from('<i', d, p); p += 4
        cn, = struct.unpack_from('<i', d, p); p += 4
        p += 4 * cn
        self.preload_count, self.preload_offset = struct.unpack_from('<ii', d, p); p += 8
        self.summary_end = p
        # names
        self.names = []
        p = self.name_offset
        for i in range(self.name_count):
            s, p = self.fstring(p)
            p += 4  # hashes
            self.names.append(s)
        # imports
        self.imports = []
        p = self.import_offset
        for i in range(self.import_count):
            cp, cpn, cn_, cnn, outer, on, onn = struct.unpack_from('<iiiiiii', d, p); p += 28
            imp = dict(class_package=self.name(cp, cpn), class_name=self.name(cn_, cnn), outer=outer, name=self.name(on, onn))
            if self.ue4 >= 520 and not (self.flags & 0x80000000):
                pn, pnn = struct.unpack_from('<ii', d, p); p += 8
                imp['package_name'] = self.name(pn, pnn)
            self.imports.append(imp)
        # exports
        self.exports = []
        p = self.export_offset
        for i in range(self.export_count):
            cls, sup, tmpl, outer, on, onn, oflags = struct.unpack_from('<iiiiiiI', d, p); p += 28
            size, off = struct.unpack_from('<qq', d, p); p += 16
            forced, nfc, nfs = struct.unpack_from('<iii', d, p); p += 12
            pguid = d[p:p + 16]; p += 16
            pflags, nalefg, isasset = struct.unpack_from('<Iii', d, p); p += 12
            deps = struct.unpack_from('<5i', d, p); p += 20
            self.exports.append(dict(cls=cls, super=sup, template=tmpl, outer=outer, name=self.name(on, onn), flags=oflags,
                                     size=size, offset=off, is_asset=isasset, deps=deps))

    def fstring(self, p):
        L, = struct.unpack_from('<i', self.d, p); p += 4
        if L == 0:
            return '', p
        if L > 0:
            return self.d[p:p + L - 1].decode('latin1'), p + L
        return self.d[p:p - 2 * L - 2].decode('utf-16-le'), p - 2 * L

    def name(self, i, n):
        s = self.names[i]
        return s if n == 0 else '%s_%d' % (s, n - 1)

    def ref(self, i):
        if i == 0:
            return None
        if i < 0:
            return self.imports[-i - 1]['name']
        return self.exports[i - 1]['name']

    def import_path(self, i):
        parts = []
        k = i
        while k < 0:
            imp = self.imports[-k - 1]
            parts.append(imp['name'])
            k = imp['outer']
        return '.'.join(reversed(parts)) if len(parts) <= 2 else parts[-1] + '.' + '.'.join(reversed(parts[:-1]))

    def export_path(self, i):
        parts = []
        k = i
        while k > 0:
            e = self.exports[k - 1]
            parts.append(e['name'])
            k = e['outer']
        return '.'.join(reversed(parts))

    def class_of(self, e):
        return self.ref(e['cls'])
