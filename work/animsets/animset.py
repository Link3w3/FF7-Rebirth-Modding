"""Read FF7 Rebirth UEndAnimSet zen packages (unversioned properties): DisplayName and AnimationAssets (key -> object path)."""
import struct, sys
sys.path.insert(0, '/work/cs')
from zen import Zen
from cityhash import CityHash64

PROPS = ['DisplayName', 'AnimationAssets', 'ResidentBlendSequenceName', 'ResidentBlendBoneName', 'ResidentBlendBoneNames',
         'bDisableLookAt', 'bComponentSpaceLookAt', 'BaseLookAtWeight', 'BodyLookAtWeight', 'HeadLookAtWeight',
         'HandConstraintRate', 'bUseAim', 'AimOffset', 'bCanBeInCluster']


def import_hash(object_path):
    s = ''.join('/' if c in '.:' else c.lower() for c in object_path)
    return (CityHash64(s.encode('utf-16-le')) & ~(3 << 62)) | (2 << 62)


def object_path_of_package(pkg):
    return pkg + '.' + pkg.rsplit('/', 1)[-1]


class AnimSet:
    def __init__(self, data, extra_packages=()):
        self.data = data
        z = self.z = Zen(data)
        self.names = z.names
        lookup = {}
        for n in list(z.names) + list(extra_packages):
            if n.startswith('/'):
                lookup[import_hash(object_path_of_package(n))] = object_path_of_package(n)
        self.import_paths = [lookup.get(i) for i in z.imports]
        e = self.export = z.export_data(0)
        p = 0
        present = []  # schema indices with a serialized (non-zero) value
        zero_flags_needed = 0
        frags = []
        idx = 0
        while True:
            frag = struct.unpack_from('<H', e, p)[0]; p += 2
            skip, has_zero, last, num = frag & 0x7f, bool(frag & 0x80), bool(frag & 0x100), frag >> 9
            idx += skip
            frags.append((idx, num, has_zero))
            if has_zero:
                zero_flags_needed += num
            idx += num
            if last:
                break
        zero_mask = []
        if zero_flags_needed:
            if zero_flags_needed <= 8:
                bits = e[p]; p += 1; width = 8
            elif zero_flags_needed <= 16:
                bits = struct.unpack_from('<H', e, p)[0]; p += 2; width = 16
            else:
                words = (zero_flags_needed + 31) // 32
                bits = 0
                for w in range(words):
                    bits |= struct.unpack_from('<I', e, p)[0] << (32 * w); p += 4
            zero_mask = [bool(bits >> i & 1) for i in range(zero_flags_needed)]
        zi = 0
        for start, num, has_zero in frags:
            for k in range(num):
                is_zero = False
                if has_zero:
                    is_zero = zero_mask[zi]; zi += 1
                if not is_zero:
                    present.append(start + k)
        self.present = present
        self.values = {}
        for prop in present:
            name = PROPS[prop]
            if name in ('DisplayName', 'ResidentBlendSequenceName', 'ResidentBlendBoneName'):
                self.values[name] = self.fname(e, p); p += 8
            elif name == 'AnimationAssets':
                removed, count = struct.unpack_from('<ii', e, p); p += 8
                assert removed == 0
                entries = []
                for _ in range(count):
                    key = self.fname(e, p); p += 8
                    ref = struct.unpack_from('<i', e, p)[0]; p += 4
                    entries.append((key, ref))
                self.values[name] = entries
            elif name == 'ResidentBlendBoneNames':
                count = struct.unpack_from('<i', e, p)[0]; p += 4
                self.values[name] = [self.fname(e, p + 8 * i) for i in range(count)]; p += 8 * count
            elif name.startswith('b'):
                self.values[name] = e[p]; p += 1
            elif name == 'AimOffset':
                self.values[name] = struct.unpack_from('<3f', e, p); p += 12
            else:
                self.values[name] = struct.unpack_from('<f', e, p)[0]; p += 4
        self.end = p
        self.tail = e[p:]

    def fname(self, e, p):
        i, num = struct.unpack_from('<II', e, p)
        s = self.names[i]
        return s if num == 0 else '%s_%d' % (s, num - 1)

    def ref_path(self, ref):
        if ref < 0:
            return self.import_paths[-ref - 1] or 'import#%d(%016x)' % (-ref - 1, self.z.imports[-ref - 1])
        if ref > 0:
            return 'export#%d' % (ref - 1)
        return None

    def entries(self):
        return [(k, self.ref_path(r)) for k, r in self.values.get('AnimationAssets', [])]
