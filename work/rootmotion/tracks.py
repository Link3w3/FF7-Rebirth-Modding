"""TrackToSkeletonMapTable (bone tree index per compressed track) of a cooked FF7R animation package (tagged properties)."""
import struct, sys
sys.path.insert(0, '/work/cs')
from zen import Zen

def track_bones(d):
    z = Zen(d)
    names = list(z.names)
    try:
        bti = names.index('BoneTreeIndex'); ip = names.index('IntProperty')
    except ValueError:
        return None
    pat = struct.pack('<IIII', bti, 0, ip, 0)
    out = []
    p = d.find(pat, z.header_end)
    while p >= 0:
        size, aidx = struct.unpack_from('<ii', d, p + 16)
        hasguid = d[p + 24]
        val = struct.unpack_from('<i', d, p + 25)[0]
        out.append(val)
        p = d.find(pat, p + 29)
    return out


def compressed_track_bones(d, nbones):
    """The CompressedTrackToSkeletonMapTable before the ACL blob: int32 count == nbones, then nbones int32 bone indices."""
    tag = d.find(struct.pack('<I', 0xac10ac10))
    best = None
    p = d.find(struct.pack('<i', nbones))
    while 0 <= p < tag:
        vals = struct.unpack_from('<%di' % nbones, d, p + 4)
        if all(0 <= v < 2000 for v in vals) and len(set(vals)) == nbones:
            best = (p, list(vals))
        p = d.find(struct.pack('<i', nbones), p + 1)
    return best
