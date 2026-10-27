"""The curve names (and ACL block size) of each AnimSequence in a container: anim_curves.py <utoc> [substring]"""
import sys, struct, collections
sys.path[:0]=['/work/soradata','/work/iostore','/work/cs','/work/swap1012/tools','/work/sephforms/tools','/work/fx1018/editor/Python']
from build_sora_assets import Toc, Zen, Package


def curves(d, label):
    z = Zen(d); pkg = Package(d, label)
    for idx, (cls, v, b) in pkg.exports.items():
        if cls != 'AnimSequence':
            continue
        s, size = z.bundle_positions()[idx]
        p = s + v.at + v.size + 4 + 16
        sz, = struct.unpack_from('<I', d, p); p += 4
        if sz:
            tag, = struct.unpack_from('<I', d, p); p += 4
            if tag > 0xffff:
                al, pad = struct.unpack_from('<HH', d, p); p += 4 + pad
            p += sz
            n1, n2, n3 = struct.unpack_from('<III', d, p); p += 12
            for _ in range(n1):
                p += 8; cnt, = struct.unpack_from('<I', d, p); p += 4 + 8 * cnt
            for _ in range(n2 + n3):
                p += 8; cnt, = struct.unpack_from('<I', d, p); p += 4 + 4 * cnt
        p += 2
        bser, = struct.unpack_from('<I', d, p); p += 4
        names = []
        if bser:
            p += 4
            nt, = struct.unpack_from('<i', d, p); p += 4 + 4 * nt
            nc, = struct.unpack_from('<i', d, p); p += 4
            for k in range(nc):
                i, num = struct.unpack_from('<Ii', d, p); p += 8
                names.append(z.names[i & 0x3fffffff])
        return sz, names
    return None


if __name__ == '__main__':
    t = Toc(sys.argv[1]); sub = sys.argv[2] if len(sys.argv) > 2 else ''
    stats = collections.Counter(); names = collections.Counter()
    for i in range(t.entries):
        p = t.files.get(i)
        if not p or t.chunk_type(i) != 2 or sub not in p:
            continue
        r = curves(t.read(i), p)
        if r is None:
            continue
        stats['with curves' if r[1] else 'no curves'] += 1
        names.update(r[1])
    print(stats, names.most_common(10))
