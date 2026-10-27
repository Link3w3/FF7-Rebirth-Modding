import sys, struct
sys.path.insert(0,'/work/cs'); sys.path.insert(0,'.')
from zen import Zen
from tagged import export_layout, export_bytes
PROPS = ['SocketName', 'BoneName', 'RelativeLocation', 'RelativeRotation', 'RelativeScale', 'bForceAlwaysAnimated']
def unversioned(e):
    p = 0; frags = []; idx = 0; zero_needed = 0
    while True:
        frag = struct.unpack_from('<H', e, p)[0]; p += 2
        skip, has_zero, last, num = frag & 0x7f, bool(frag & 0x80), bool(frag & 0x100), frag >> 9
        idx += skip; frags.append((idx, num, has_zero))
        if has_zero: zero_needed += num
        idx += num
        if last: break
    mask = []
    if zero_needed:
        nbytes = 1 if zero_needed <= 8 else (2 if zero_needed <= 16 else 4 * ((zero_needed + 31) // 32))
        bits = int.from_bytes(e[p:p+nbytes], 'little'); p += nbytes
        mask = [bool(bits >> i & 1) for i in range(zero_needed)]
    present = []; zi = 0
    for start, num, hz in frags:
        for k in range(num):
            z = False
            if hz: z = mask[zi]; zi += 1
            present.append((start + k, z))
    return present, p
def sockets(path):
    z = Zen(open(path,'rb').read()); L = export_layout(z)
    out = []
    for i, ex in enumerate(z.exports):
        if not ex['name'].startswith('SkeletalMeshSocket'): continue
        e = export_bytes(z, i, L)
        present, p = unversioned(e)
        v = {}
        for prop, iszero in present:
            name = PROPS[prop]
            if iszero: v[name] = 'zero'; continue
            if name in ('SocketName', 'BoneName'):
                ni, num = struct.unpack_from('<II', e, p); p += 8; v[name] = z.names[ni] + ('' if num == 0 else '_%d' % (num-1))
            elif name in ('RelativeLocation', 'RelativeRotation', 'RelativeScale'):
                v[name] = tuple(round(x, 3) for x in struct.unpack_from('<3f', e, p)); p += 12
            else:
                v[name] = e[p]; p += 1
        out.append(v)
    return out
if __name__ == '__main__':
    for n in sys.argv[1:]:
        print('==', n.split('__')[-1])
        for s in sockets(n):
            if any(k in s.get('SocketName', '') for k in ('Weapon', 'Attach_Item', 'Holster')):
                print('   ', s)
